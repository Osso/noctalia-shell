pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.UI

Singleton {
  id: root

  // Core state
  property var networks: ({})
  property bool scanning: false
  property bool connecting: false
  property string connectingTo: ""
  property string lastError: ""
  property bool ethernetConnected: false
  property string disconnectingFrom: ""
  property string forgettingNetwork: ""
  property string networkConnectivity: "unknown"
  property bool internetConnectivity: true
  property bool ignoreScanResults: false
  property bool scanPending: false
  property int activePollingRefs: 0
  readonly property bool activePolling: activePollingRefs > 0

  // Persistent cache
  property string cacheFile: Settings.cacheDir + "network.json"
  readonly property string cachedLastConnected: cacheAdapter.lastConnected
  readonly property var cachedNetworks: cacheAdapter.knownNetworks

  // Cache file handling
  FileView {
    id: cacheFileView
    path: root.cacheFile
    printErrors: false

    JsonAdapter {
      id: cacheAdapter
      property var knownNetworks: ({})
      property string lastConnected: ""
    }

    onLoadFailed: {
      cacheAdapter.knownNetworks = ({});
      cacheAdapter.lastConnected = "";
    }
  }

  Connections {
    target: Settings.data.network
    function onWifiEnabledChanged() {
      if (Settings.data.network.wifiEnabled) {
        if (!BluetoothService.airplaneModeToggled) {
          ToastService.showNotice(I18n.tr("wifi.panel.title"), I18n.tr("toast.wifi.enabled"), "wifi");
        }
        refreshNetworkStatus();
        // Perform a scan to update the UI only while a network panel is active.
        if (activePolling) {
          delayedScanTimer.interval = 3000;
          delayedScanTimer.restart();
        }
      } else {
        if (!BluetoothService.airplaneModeToggled) {
          ToastService.showNotice(I18n.tr("wifi.panel.title"), I18n.tr("toast.wifi.disabled"), "wifi-off");
        }
        // Clear networks so the widget icon changes
        root.networks = ({});
      }
    }
  }

  Component.onCompleted: {
    Logger.i("Network", "Service started");
    syncWifiState();
    refreshNetworkStatus();
  }

  // Save cache with debounce
  Timer {
    id: saveDebounce
    interval: 1000
    onTriggered: cacheFileView.writeAdapter()
  }

  function saveCache() {
    saveDebounce.restart();
  }

  // Delayed scan timer
  Timer {
    id: delayedScanTimer
    interval: 7000
    onTriggered: {
      if (root.activePolling) {
        scan();
      }
    }
  }

  // Ethernet check timer
  // Runs only while network UI is active.
  Timer {
    id: ethernetCheckTimer
    interval: 30000
    running: root.activePolling
    repeat: true
    onTriggered: {
      if (!ethernetStateProcess.running) {
        ethernetStateProcess.running = true;
      }
    }
  }

  // Internet connectivity check timer
  // Runs only while network UI is active.
  Timer {
    id: connectivityCheckTimer
    interval: 15000
    running: root.activePolling
    repeat: true
    onTriggered: {
      if (!connectivityCheckProcess.running) {
        connectivityCheckProcess.running = true;
      }
    }
  }

  // Core functions
  function refreshNetworkStatus() {
    if (!ethernetStateProcess.running) {
      ethernetStateProcess.running = true;
    }
    if (!connectivityCheckProcess.running) {
      connectivityCheckProcess.running = true;
    }
  }

  function beginActivePolling() {
    activePollingRefs++;
    refreshNetworkStatus();
    scan();
  }

  function endActivePolling() {
    activePollingRefs = Math.max(0, activePollingRefs - 1);
  }

  function syncWifiState() {
    wifiStateProcess.running = true;
  }

  function setWifiEnabled(enabled) {
    Settings.data.network.wifiEnabled = enabled;
    wifiStateEnableProcess.running = true;
  }

  function scan() {
    if (!Settings.data.network.wifiEnabled)
      return;
    if (scanning) {
      // Mark current scan results to be ignored and schedule a new scan
      Logger.d("Network", "Scan already in progress, will ignore results and rescan");
      ignoreScanResults = true;
      scanPending = true;
      return;
    }

    scanning = true;
    lastError = "";
    ignoreScanResults = false;

    // Get existing profiles first, then scan
    profileCheckProcess.exitObserved = false;
    profileCheckProcess.running = true;
    Logger.d("Network", "Wi-Fi scan in progress...");
  }

  function connect(ssid, password = "") {
    if (!ssid || connecting || connectProcess.running)
      return;
    connecting = true;
    connectingTo = ssid;
    lastError = "";

    if ((networks[ssid] && networks[ssid].existing) || cachedNetworks[ssid]) {
      connectProcess.mode = "saved";
      connectProcess.password = "";
    } else {
      connectProcess.mode = "new";
      connectProcess.password = password;
    }
    connectProcess.ssid = ssid;
    connectProcess.output = "";
    connectProcess.errorOutput = "";
    connectProcess.exitObserved = false;
    connectProcess.generation += 1;
    connectProcess.running = true;
  }

  function finishConnect(ssid, generation, exitCode, output, errorOutput) {
    if (connectProcess.generation !== generation || root.connectingTo !== ssid)
      return;
    connectProcess.password = "";
    root.connectingTo = "";
    root.connecting = false;

    if (exitCode === 0) {
      const known = Object.assign({}, cacheAdapter.knownNetworks);
      known[ssid] = {
        "profileName": ssid,
        "lastConnected": Date.now()
      };
      cacheAdapter.knownNetworks = known;
      cacheAdapter.lastConnected = ssid;
      root.saveCache();
      root.updateNetworkStatus(ssid, true);
      root.lastError = "";
      Logger.i("Network", `Connected to network: '${ssid}'`);
      ToastService.showNotice(I18n.tr("wifi.panel.title"), I18n.tr("toast.wifi.connected", {
                                                                     "ssid": ssid
                                                                   }), "wifi");
      root.refreshNetworkStatus();
      if (root.activePolling) {
        delayedScanTimer.interval = 5000;
        delayedScanTimer.restart();
      }
      return;
    }

    const diagnostic = errorOutput.trim() || output.trim();
    if (diagnostic.includes("Secrets were required") || diagnostic.includes("no secrets provided")) {
      root.lastError = "Incorrect password";
      root.forget(ssid);
    } else if (diagnostic.includes("No network with SSID")) {
      root.lastError = "Network not found";
    } else if (diagnostic.includes("Timeout")) {
      root.lastError = "Connection timeout";
    } else {
      root.lastError = diagnostic.split("\n")[0].trim() || `nmcli connect failed with exit ${exitCode}`;
    }
    Logger.w("Network", "Connect error: " + root.lastError);
  }

  function handleConnectStartFailure(ssid, generation, exitObserved) {
    if (!exitObserved && connectProcess.generation === generation && root.connectingTo === ssid)
      root.finishConnect(ssid, generation, -1, "", "nmcli connect failed to start");
  }

  function disconnect(ssid) {
    if (!ssid || disconnectingFrom || disconnectProcess.running)
      return;
    disconnectingFrom = ssid;
    disconnectProcess.ssid = ssid;
    disconnectProcess.output = "";
    disconnectProcess.errorOutput = "";
    disconnectProcess.exitObserved = false;
    disconnectProcess.generation += 1;
    disconnectProcess.running = true;
  }

  function finishDisconnect(ssid, generation, exitCode, output, errorOutput) {
    if (disconnectProcess.generation !== generation || root.disconnectingFrom !== ssid)
      return;
    root.disconnectingFrom = "";

    if (exitCode === 0) {
      root.updateNetworkStatus(ssid, false);
      root.lastError = "";
      Logger.i("Network", `Disconnected from network: '${ssid}'`);
      ToastService.showNotice(I18n.tr("wifi.panel.title"), I18n.tr("toast.wifi.disconnected", {
                                                                     "ssid": ssid
                                                                   }), "wifi-off");
      root.refreshNetworkStatus();
      if (root.activePolling) {
        delayedScanTimer.interval = 1000;
        delayedScanTimer.restart();
      }
      return;
    }

    root.lastError = (errorOutput.trim() || output.trim()).split("\n")[0].trim() || `nmcli disconnect failed with exit ${exitCode}`;
    Logger.w("Network", "Disconnect error: " + root.lastError);
  }

  function handleDisconnectStartFailure(ssid, generation, exitObserved) {
    if (!exitObserved && disconnectProcess.generation === generation && root.disconnectingFrom === ssid)
      root.finishDisconnect(ssid, generation, -1, "", "nmcli disconnect failed to start");
  }

  function forget(ssid) {
    if (!ssid || forgettingNetwork || forgetProcess.running)
      return;
    forgettingNetwork = ssid;
    forgetProcess.ssid = ssid;
    forgetProcess.output = "";
    forgetProcess.errorOutput = "";
    forgetProcess.exitObserved = false;
    forgetProcess.running = true;
  }

  function finishForget(ssid, exitCode, output, errorOutput) {
    if (root.forgettingNetwork !== ssid)
      return;
    root.forgettingNetwork = "";

    if (exitCode === 0) {
      const known = Object.assign({}, cacheAdapter.knownNetworks);
      delete known[ssid];
      cacheAdapter.knownNetworks = known;
      if (cacheAdapter.lastConnected === ssid)
        cacheAdapter.lastConnected = "";
      root.saveCache();

      const nets = Object.assign({}, root.networks);
      if (nets[ssid]) {
        nets[ssid] = Object.assign({}, nets[ssid], {
                                    "cached": false,
                                    "existing": false
                                  });
        root.networks = nets;
      }
      root.lastError = "";
      Logger.i("Network", `Forget network: "${ssid}"`);
      Logger.d("Network", output.trim().replace(/[\r\n]/g, " "));
      if (root.activePolling) {
        delayedScanTimer.interval = 5000;
        delayedScanTimer.restart();
      }
    } else {
      root.lastError = (errorOutput.trim() || output.trim()).split("\n")[0].trim() || `nmcli forget failed with exit ${exitCode}`;
      Logger.w("Network", "Forget error: " + root.lastError);
    }
  }

  function handleForgetStartFailure(ssid, exitObserved) {
    if (!exitObserved && root.forgettingNetwork === ssid)
      root.finishForget(ssid, -1, "", "nmcli forget failed to start");
  }

  // Helper function to immediately update network status
  function updateNetworkStatus(ssid, connected) {
    let nets = networks;

    // Update all networks connected status
    for (let key in nets) {
      if (nets[key].connected && key !== ssid) {
        nets[key].connected = false;
      }
    }

    // Update the target network if it exists
    if (nets[ssid]) {
      nets[ssid].connected = connected;
      nets[ssid].existing = true;
      nets[ssid].cached = true;
    } else if (connected) {
      // Create a temporary entry if network doesn't exist yet
      nets[ssid] = {
        "ssid": ssid,
        "security": "--",
        "signal": 100,
        "connected": true,
        "existing": true,
        "cached": true
      };
    }

    // Trigger property change notification
    networks = ({});
    networks = nets;
  }

  function applyDeviceStateOutput(text) {
    const lines = text.split("\n");
    var wiredConnected = false;
    var wifiConnection = "";

    for (var i = 0; i < lines.length; i++) {
      const parts = lines[i].split(":");
      if (parts.length < 4) {
        continue;
      }
      if (parts[1] === "ethernet" && parts[2] === "connected") {
        wiredConnected = true;
      }
      if (parts[1] === "wifi" && parts[2] === "connected" && parts[3]) {
        wifiConnection = parts[3];
      }
    }

    if (root.ethernetConnected !== wiredConnected) {
      root.ethernetConnected = wiredConnected;
      Logger.d("Network", "Ethernet connected:", root.ethernetConnected);
    }

    if (wifiConnection) {
      updateNetworkStatus(wifiConnection, true);
    } else {
      let nets = root.networks;
      for (let key in nets) {
        if (nets[key].connected) {
          nets[key].connected = false;
        }
      }
      networks = ({});
      networks = nets;
    }
  }

  // Helper functions
  function signalIcon(signal, isConnected = false) {
    if (isConnected && root.networkConnectivity !== "unknown" && !root.internetConnectivity)
      return "world-off";
    if (signal >= 80)
      return "wifi";
    if (signal >= 50)
      return "wifi-2";
    if (signal >= 20)
      return "wifi-1";
    return "wifi-0";
  }

  function isSecured(security) {
    return security && security !== "--" && security.trim() !== "";
  }

  function parseNetworkScanOutput(text, existingProfiles, knownNetworks, lastConnected) {
    const lines = text.split("\n");
    const networksMap = {};
    var nextLastConnected = lastConnected;
    var shouldSaveCache = false;

    for (var i = 0; i < lines.length; ++i) {
      const line = lines[i].trim();
      if (!line)
        continue;

      // Parse from the end to handle SSIDs with colons.
      // Format is SSID:SECURITY:SIGNAL:IN-USE.
      const lastColonIdx = line.lastIndexOf(":");
      if (lastColonIdx === -1) {
        Logger.w("Network", "Malformed nmcli output line:", line);
        continue;
      }

      const inUse = line.substring(lastColonIdx + 1);
      const remainingLine = line.substring(0, lastColonIdx);

      const secondLastColonIdx = remainingLine.lastIndexOf(":");
      if (secondLastColonIdx === -1) {
        Logger.w("Network", "Malformed nmcli output line:", line);
        continue;
      }

      const signal = remainingLine.substring(secondLastColonIdx + 1);
      const remainingLine2 = remainingLine.substring(0, secondLastColonIdx);

      const thirdLastColonIdx = remainingLine2.lastIndexOf(":");
      if (thirdLastColonIdx === -1) {
        Logger.w("Network", "Malformed nmcli output line:", line);
        continue;
      }

      const security = remainingLine2.substring(thirdLastColonIdx + 1);
      const ssid = remainingLine2.substring(0, thirdLastColonIdx);

      if (!ssid)
        continue;

      const signalInt = parseInt(signal) || 0;
      const connected = inUse === "*";
      const normalizedSecurity = security || "--";

      if (connected && nextLastConnected !== ssid) {
        nextLastConnected = ssid;
        shouldSaveCache = true;
      }

      if (!networksMap[ssid]) {
        networksMap[ssid] = {
          "ssid": ssid,
          "security": normalizedSecurity,
          "signal": signalInt,
          "connected": connected,
          "existing": ssid in existingProfiles,
          "cached": ssid in knownNetworks
        };
        continue;
      }

      const existingNet = networksMap[ssid];
      if (connected) {
        existingNet.connected = true;
      }
      if (signalInt > existingNet.signal) {
        existingNet.signal = signalInt;
        existingNet.security = normalizedSecurity;
      }
    }

    return {
      "networks": networksMap,
      "lastConnected": nextLastConnected,
      "shouldSaveCache": shouldSaveCache
    };
  }

  // Processes
  Process {
    id: ethernetStateProcess
    running: false
    command: ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]

    stdout: StdioCollector {
      onStreamFinished: applyDeviceStateOutput(text)
    }
  }

  // Only check the state of the actual interface
  // and update our setting to be in sync.
  Process {
    id: wifiStateProcess
    running: false
    command: ["nmcli", "radio", "wifi"]

    stdout: StdioCollector {
      onStreamFinished: {
        const enabled = text.trim() === "enabled";
        Logger.d("Network", "Wi-Fi adapter was detect as enabled:", enabled);
        if (Settings.data.network.wifiEnabled !== enabled) {
          Settings.data.network.wifiEnabled = enabled;
        }
      }
    }
  }

  // Process to enable/disable the Wi-Fi interface
  Process {
    id: wifiStateEnableProcess
    running: false
    command: ["nmcli", "radio", "wifi", Settings.data.network.wifiEnabled ? "on" : "off"]

    stdout: StdioCollector {
      onStreamFinished: {
        Logger.i("Network", "Wi-Fi state change command executed.");
        // Re-check the state to ensure it's in sync
        syncWifiState();
      }
    }

    stderr: StdioCollector {
      onStreamFinished: {
        if (text.trim()) {
          Logger.w("Network", "Error changing Wi-Fi state: " + text);
        }
      }
    }
  }

  // Process to check the internet connectivity of the connected network
  Process {
    id: connectivityCheckProcess
    running: false
    command: ["nmcli", "networking", "connectivity", "check"]

    property int failedChecks: 0

    stdout: StdioCollector {
      onStreamFinished: {
        const result = text.trim();
        if (!result) {
          return;
        }

        if (result === "none" && root.networkConnectivity !== result) {
          root.networkConnectivity = result;
          connectivityCheckProcess.failedChecks = 0;
          if (root.activePolling) {
            root.scan();
          }
        }

        if (result === "full" && root.networkConnectivity !== result) {
          root.networkConnectivity = result;
          root.internetConnectivity = true;
          connectivityCheckProcess.failedChecks = 0;
          if (root.activePolling) {
            root.scan();
          }
        }

        if ((result === "limited" || result === "portal") && root.networkConnectivity !== result) {
          connectivityCheckProcess.failedChecks++;
          if (connectivityCheckProcess.failedChecks === 3) {
            root.networkConnectivity = result;
            pingCheckProcess.running = true;
          }
        }

        if (result === "unknown" && root.networkConnectivity !== result) {
          root.networkConnectivity = result;
          connectivityCheckProcess.failedChecks = 0;
        }
      }
    }

    stderr: StdioCollector {
      onStreamFinished: {
        if (text.trim()) {
          Logger.w("Network", "Connectivity check error: " + text);
          root.networkConnectivity = "unknown";
          root.internetConnectivity = true;
          connectivityCheckProcess.failedChecks = 0;
        }
      }
    }
  }

  Process {
    id: pingCheckProcess
    command: ["sh", "-c", "ping -c1 -W2 ping.archlinux.org >/dev/null 2>&1 || " + "ping -c1 -W2 1.1.1.1 >/dev/null 2>&1 || " + "curl -fsI --max-time 5 https://cloudflare.com/cdn-cgi/trace >/dev/null 2>&1"]

    onExited: (exitCode, exitStatus) => {
      if (exitCode === 0) {
        connectivityCheckProcess.failedChecks = 0;
      } else {
        root.internetConnectivity = false;
        Logger.i("Network", "No internet connectivity");
        ToastService.showWarning(root.cachedLastConnected, I18n.tr("toast.internet.limited"));
        connectivityCheckProcess.failedChecks = 0;
      }
      if (root.activePolling) {
        root.scan();
      }
    }
  }

  // Helper process to get existing profiles
  function finishScanFailure(message) {
    root.scanning = false;
    root.lastError = message;

    if (root.scanPending) {
      root.scanPending = false;
      delayedScanTimer.interval = 100;
      delayedScanTimer.restart();
    } else if (root.activePolling) {
      delayedScanTimer.interval = 5000;
      delayedScanTimer.restart();
    }
  }

  function finishSupersededScan() {
    root.scanning = false;
    if (root.scanPending) {
      root.scanPending = false;
      delayedScanTimer.interval = 100;
      delayedScanTimer.restart();
    }
  }

  function handleScanStartFailure(processName, exitObserved) {
    if (!exitObserved && root.scanning) {
      finishScanFailure(`${processName} failed to start`);
    }
  }

  function finishProfileCheck(exitCode, output, errorOutput) {
    if (root.ignoreScanResults) {
      root.finishSupersededScan();
      return;
    }
    if (exitCode !== 0) {
      finishScanFailure(errorOutput.trim() || `nmcli profile check failed with exit ${exitCode}`);
      return;
    }

    const profiles = {};
    const lines = output.split("\n").filter(line => line.trim());
    for (const line of lines) {
      profiles[line.trim()] = true;
    }
    scanProcess.existingProfiles = profiles;
    scanProcess.exitObserved = false;
    scanProcess.running = true;
  }

  function finishNetworkScan(exitCode, output, errorOutput) {
    if (root.ignoreScanResults) {
      root.finishSupersededScan();
      return;
    }
    if (exitCode !== 0) {
      finishScanFailure(errorOutput.trim() || `nmcli scan failed with exit ${exitCode}`);
      return;
    }

    const parsed = parseNetworkScanOutput(output, scanProcess.existingProfiles, cacheAdapter.knownNetworks, cacheAdapter.lastConnected);
    const networksMap = parsed.networks;
    if (parsed.shouldSaveCache) {
      cacheAdapter.lastConnected = parsed.lastConnected;
      saveCache();
    }

    root.logNetworkChanges(networksMap);
    Logger.d("Network", "Wi-Fi scan completed");
    root.networks = networksMap;
    root.scanning = false;
    if (root.scanPending) {
      root.scanPending = false;
      delayedScanTimer.interval = 100;
      delayedScanTimer.restart();
    }
  }

  function logNetworkChanges(networksMap) {
    const oldSSIDs = Object.keys(root.networks);
    const newSSIDs = Object.keys(networksMap);
    const newNetworks = newSSIDs.filter(ssid => !oldSSIDs.includes(ssid));
    const lostNetworks = oldSSIDs.filter(ssid => !newSSIDs.includes(ssid));

    if (newNetworks.length > 0) {
      Logger.d("Network", "New Wi-Fi SSID discovered:", newNetworks.join(", "));
    }
    if (lostNetworks.length > 0) {
      Logger.d("Network", "Wi-Fi SSID disappeared:", lostNetworks.join(", "));
    }
    if (newNetworks.length > 0 || lostNetworks.length > 0) {
      Logger.d("Network", "Total Wi-Fi SSIDs:", newSSIDs.length);
    }
  }

  Process {
    id: profileCheckProcess
    running: false
    command: ["nmcli", "-t", "-f", "NAME", "connection", "show"]
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false

    stdout: StdioCollector {
      onStreamFinished: profileCheckProcess.output = text
    }
    stderr: StdioCollector {
      onStreamFinished: profileCheckProcess.errorOutput = text
    }
    onExited: function (exitCode) {
      profileCheckProcess.exitObserved = true;
      const output = profileCheckProcess.output;
      const errorOutput = profileCheckProcess.errorOutput;
      profileCheckProcess.output = "";
      profileCheckProcess.errorOutput = "";
      root.finishProfileCheck(exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleScanStartFailure("nmcli profile check", exitObserved);
        exitObserved = false;
      }
    }
  }

  Process {
    id: scanProcess
    running: false
    command: ["nmcli", "-t", "-f", "SSID,SECURITY,SIGNAL,IN-USE", "device", "wifi", "list", "--rescan", "yes"]
    property var existingProfiles: ({})
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false

    stdout: StdioCollector {
      onStreamFinished: scanProcess.output = text
    }
    stderr: StdioCollector {
      onStreamFinished: scanProcess.errorOutput = text
    }
    onExited: function (exitCode) {
      scanProcess.exitObserved = true;
      const output = scanProcess.output;
      const errorOutput = scanProcess.errorOutput;
      scanProcess.output = "";
      scanProcess.errorOutput = "";
      root.finishNetworkScan(exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleScanStartFailure("nmcli Wi-Fi scan", exitObserved);
        exitObserved = false;
      }
    }
  }
  Process {
    id: connectProcess
    property string mode: "new"
    property string ssid: ""
    property string password: ""
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false
    property int generation: 0
    running: false

    command: {
      if (mode === "saved") {
        return ["nmcli", "connection", "up", "id", ssid];
      } else {
        const cmd = ["nmcli", "device", "wifi", "connect", ssid];
        if (password) {
          cmd.push("password", password);
        }
        return cmd;
      }
    }
    environment: ({
                    "LC_ALL": "C"
                  })

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
      const generation = connectProcess.generation;
      connectProcess.output = "";
      connectProcess.errorOutput = "";
      root.finishConnect(connectProcess.ssid, generation, exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleConnectStartFailure(connectProcess.ssid, connectProcess.generation, connectProcess.exitObserved);
        connectProcess.exitObserved = false;
      }
    }
  }

  Process {
    id: disconnectProcess
    property string ssid: ""
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false
    property int generation: 0
    running: false
    command: ["nmcli", "connection", "down", "id", ssid]

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
      const generation = disconnectProcess.generation;
      disconnectProcess.output = "";
      disconnectProcess.errorOutput = "";
      root.finishDisconnect(disconnectProcess.ssid, generation, exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleDisconnectStartFailure(disconnectProcess.ssid, disconnectProcess.generation, disconnectProcess.exitObserved);
        disconnectProcess.exitObserved = false;
      }
    }
  }

  Process {
    id: forgetProcess
    property string ssid: ""
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false
    running: false

    command: ["bash", Quickshell.shellDir + "/Bin/network-forget-profiles.sh", ssid]

    stdout: StdioCollector {
      onStreamFinished: forgetProcess.output = text
    }
    stderr: StdioCollector {
      onStreamFinished: forgetProcess.errorOutput = text
    }
    onExited: function (exitCode) {
      forgetProcess.exitObserved = true;
      const output = forgetProcess.output;
      const errorOutput = forgetProcess.errorOutput;
      forgetProcess.output = "";
      forgetProcess.errorOutput = "";
      root.finishForget(forgetProcess.ssid, exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleForgetStartFailure(forgetProcess.ssid, forgetProcess.exitObserved);
        forgetProcess.exitObserved = false;
      }
    }
  }
}
