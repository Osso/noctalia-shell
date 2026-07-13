pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.UI

Singleton {
  id: root

  property var connections: ({})
  property bool refreshing: false
  property bool connecting: false
  property bool disconnecting: false
  property string connectingUuid: ""
  property string disconnectingUuid: ""
  property string lastError: ""
  property bool refreshPending: false
  property int pollingRefs: 0

  readonly property var activeConnections: {
    const result = [];
    const map = connections;
    for (const key in map) {
      const conn = map[key];
      if (conn && conn.active) {
        result.push(conn);
      }
    }
    return result;
  }

  readonly property var inactiveConnections: {
    const result = [];
    const map = connections;
    for (const key in map) {
      const conn = map[key];
      if (conn && !conn.active) {
        result.push(conn);
      }
    }
    return result;
  }

  readonly property bool hasActiveConnection: activeConnections.length > 0

  Timer {
    id: refreshTimer
    interval: 5000
    running: root.isPollingActive()
    repeat: true
    onTriggered: refresh()
  }

  Timer {
    id: delayedRefreshTimer
    interval: 1000
    repeat: false
    onTriggered: {
      if (root.isPollingActive()) {
        refresh();
      }
    }
  }

  Component.onCompleted: {
    Logger.i("VPN", "Service started with lazy polling");
  }

  function beginPolling() {
    pollingRefs = pollingRefs + 1;
    refresh();
  }

  function endPolling() {
    pollingRefs = Math.max(0, pollingRefs - 1);
  }

  function isPollingActive() {
    return pollingRefs > 0;
  }

  function refresh() {
    if (refreshing) {
      refreshPending = true;
      return;
    }
    refreshing = true;
    lastError = "";
    refreshProcess.exitObserved = false;
    refreshProcess.running = true;
  }

  function connect(uuid) {
    if (connecting || connectProcess.running || !uuid) {
      return;
    }
    const conn = connections[uuid];
    if (!conn) {
      return;
    }
    connecting = true;
    connectingUuid = uuid;
    lastError = "";
    connectProcess.uuid = uuid;
    connectProcess.name = conn.name;
    connectProcess.output = "";
    connectProcess.errorOutput = "";
    connectProcess.exitObserved = false;
    connectProcess.running = true;
  }

  function disconnect(uuid) {
    if (disconnecting || disconnectProcess.running || !uuid) {
      return;
    }
    const conn = connections[uuid];
    if (!conn) {
      return;
    }
    disconnecting = true;
    disconnectingUuid = uuid;
    lastError = "";
    disconnectProcess.uuid = uuid;
    disconnectProcess.name = conn.name;
    disconnectProcess.output = "";
    disconnectProcess.errorOutput = "";
    disconnectProcess.exitObserved = false;
    disconnectProcess.running = true;
  }

  function toggle(uuid) {
    const conn = connections[uuid];
    if (!conn) {
      return;
    }
    if (conn.active) {
      disconnect(uuid);
    } else {
      connect(uuid);
    }
  }

  function setConnection(uuid, data) {
    if (!uuid) {
      return;
    }
    const map = Object.assign({}, connections);
    if (map[uuid]) {
      map[uuid] = Object.assign({}, map[uuid], data);
      connections = map;
    }
  }

  function scheduleRefresh(interval) {
    delayedRefreshTimer.interval = interval;
    delayedRefreshTimer.restart();
  }

  function finishRefresh(exitCode, output, errorOutput) {
    const pending = root.refreshPending;
    root.refreshing = false;
    root.refreshPending = false;

    if (exitCode === 0) {
      root.connections = root.parseRefreshOutput(output);
      if (pending) {
        root.scheduleRefresh(200);
      }
      return;
    }

    root.lastError = errorOutput.trim().split("\n")[0] || `nmcli VPN refresh failed with exit ${exitCode}`;
    Logger.w("VPN", "Refresh error: " + root.lastError);
    if (pending) {
      root.scheduleRefresh(2000);
    }
  }

  function handleRefreshStartFailure(exitObserved) {
    if (!exitObserved && root.refreshing) {
      finishRefresh(-1, "", "nmcli VPN refresh failed to start");
    }
  }

  function finishConnect(uuid, name, exitCode, output, errorOutput) {
    if (!root.connecting || root.connectingUuid !== uuid)
      return;
    root.connectingUuid = "";
    root.connecting = false;
    if (exitCode === 0) {
      root.setConnection(uuid, {
                           "active": true
                         });
      root.lastError = "";
      Logger.i("VPN", "Connected to " + name);
      ToastService.showNotice(name, I18n.tr("toast.vpn.connected", {
                                             "name": name
                                           }), "shield-lock");
      root.scheduleRefresh(1000);
      return;
    }

    root.lastError = (errorOutput.trim() || output.trim()).split("\n")[0].trim() || `nmcli VPN connect failed with exit ${exitCode}`;
    Logger.w("VPN", "Connect error: " + root.lastError);
    ToastService.showWarning(name, root.lastError);
  }

  function handleConnectStartFailure(uuid, name, exitObserved) {
    if (!exitObserved && root.connecting)
      root.finishConnect(uuid, name, -1, "", "nmcli VPN connect failed to start");
  }

  function finishDisconnect(uuid, name, exitCode, output, errorOutput) {
    if (!root.disconnecting || root.disconnectingUuid !== uuid)
      return;
    root.disconnectingUuid = "";
    root.disconnecting = false;
    if (exitCode === 0) {
      root.setConnection(uuid, {
                           "active": false,
                           "device": ""
                         });
      root.lastError = "";
      Logger.i("VPN", "Disconnected from " + name);
      ToastService.showNotice(name, I18n.tr("toast.vpn.disconnected", {
                                             "name": name
                                           }), "shield-off");
      root.scheduleRefresh(1000);
      return;
    }

    root.lastError = (errorOutput.trim() || output.trim()).split("\n")[0].trim() || `nmcli VPN disconnect failed with exit ${exitCode}`;
    Logger.w("VPN", "Disconnect error: " + root.lastError);
    ToastService.showWarning(name, root.lastError);
  }

  function handleDisconnectStartFailure(uuid, name, exitObserved) {
    if (!exitObserved && root.disconnecting)
      root.finishDisconnect(uuid, name, -1, "", "nmcli VPN disconnect failed to start");
  }

  function parseRefreshOutput(rawOutput) {
    const lines = rawOutput.split("\n");
    const map = {};
    for (let i = 0; i < lines.length; ++i) {
      const line = lines[i].trim();
      if (!line) {
        continue;
      }
      const lastColonIdx = line.lastIndexOf(":");
      if (lastColonIdx === -1) {
        continue;
      }
      const device = line.substring(lastColonIdx + 1);
      const remaining = line.substring(0, lastColonIdx);
      const secondLastColonIdx = remaining.lastIndexOf(":");
      if (secondLastColonIdx === -1) {
        continue;
      }
      const type = remaining.substring(secondLastColonIdx + 1);
      if (type !== "vpn" && type !== "wireguard") {
        continue;
      }
      const remaining2 = remaining.substring(0, secondLastColonIdx);
      const thirdLastColonIdx = remaining2.lastIndexOf(":");
      if (thirdLastColonIdx === -1) {
        continue;
      }
      const uuid = remaining2.substring(thirdLastColonIdx + 1);
      const name = remaining2.substring(0, thirdLastColonIdx);
      if (!uuid || !name) {
        continue;
      }
      const active = device && device !== "--";
      map[uuid] = {
        "uuid": uuid,
        "name": name,
        "device": device,
        "active": active
      };
    }
    return map;
  }

  Process {
    id: refreshProcess
    running: false
    command: ["nmcli", "-t", "-f", "NAME,UUID,TYPE,DEVICE", "connection", "show"]
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false

    stdout: StdioCollector {
      onStreamFinished: refreshProcess.output = text
    }
    stderr: StdioCollector {
      onStreamFinished: refreshProcess.errorOutput = text
    }
    onExited: function (exitCode) {
      refreshProcess.exitObserved = true;
      const output = refreshProcess.output;
      const errorOutput = refreshProcess.errorOutput;
      refreshProcess.output = "";
      refreshProcess.errorOutput = "";
      root.finishRefresh(exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleRefreshStartFailure(exitObserved);
        exitObserved = false;
      }
    }
  }

  Process {
    id: connectProcess
    property string uuid: ""
    property string name: ""
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false
    running: false
    command: ["nmcli", "connection", "up", "uuid", uuid]

    stdout: StdioCollector {
      onStreamFinished: connectProcess.output = text
    }
    stderr: StdioCollector {
      onStreamFinished: connectProcess.errorOutput = text
    }
    onExited: function (exitCode) {
      connectProcess.exitObserved = true;
      const output = connectProcess.output;
      const errorOutput = connectProcess.errorOutput;
      connectProcess.output = "";
      connectProcess.errorOutput = "";
      root.finishConnect(connectProcess.uuid, connectProcess.name, exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleConnectStartFailure(connectProcess.uuid, connectProcess.name, connectProcess.exitObserved);
        connectProcess.exitObserved = false;
      }
    }
  }

  Process {
    id: disconnectProcess
    property string uuid: ""
    property string name: ""
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false
    running: false
    command: ["nmcli", "connection", "down", "uuid", uuid]

    stdout: StdioCollector {
      onStreamFinished: disconnectProcess.output = text
    }
    stderr: StdioCollector {
      onStreamFinished: disconnectProcess.errorOutput = text
    }
    onExited: function (exitCode) {
      disconnectProcess.exitObserved = true;
      const output = disconnectProcess.output;
      const errorOutput = disconnectProcess.errorOutput;
      disconnectProcess.output = "";
      disconnectProcess.errorOutput = "";
      root.finishDisconnect(disconnectProcess.uuid, disconnectProcess.name, exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleDisconnectStartFailure(disconnectProcess.uuid, disconnectProcess.name, disconnectProcess.exitObserved);
        disconnectProcess.exitObserved = false;
      }
    }
  }
}
