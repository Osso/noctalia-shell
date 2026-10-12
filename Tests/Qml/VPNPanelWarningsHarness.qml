import QtQuick
import Quickshell
import qs.Modules.Panels.VPN
import qs.Services.Networking

ShellRoot {
  id: harness

  property int phase: 0
  property var profiles: ({
                            zulu: {
                              uuid: "zulu-uuid",
                              name: "Zulu Office",
                              active: true,
                              type: "vpn",
                              device: "tun0"
                            },
                            beta: {
                              uuid: "beta-uuid",
                              name: "Beta Failed",
                              active: false,
                              type: "vpn",
                              device: "--"
                            },
                            alpha: {
                              uuid: "alpha-uuid",
                              name: "Alpha Home",
                              active: false,
                              type: "wireguard",
                              device: "--"
                            }
                          })

  function action(uuid, key) {
    const found = descendants(row(uuid)).find(child => typeof child.clicked === "function" && child.text === key);
    require(found !== undefined, "missing action " + uuid + " " + key);
    return found;
  }
  function advance() {
    switch (harness.phase++) {
    case 0:
      VPNService.connections = harness.profiles;
      panel.open();
      require(VPNService.pollingRefs === 1, "open polling");
      break;
    case 1:
      assertOrder(["zulu-uuid", "beta-uuid", "alpha-uuid"]);
      require(row("zulu-uuid").connectionName === "Zulu Office", "active role name");
      require(row("zulu-uuid").connectionActive, "active role flag");
      require(!row("beta-uuid").connectionActive, "inactive role flag");
      assertText("zulu-uuid", "vpn.panel.connected");
      assertText("beta-uuid", "vpn.panel.disconnected");
      action("beta-uuid", "vpn.panel.connect").clicked();
      request("connect", "beta-uuid");
      break;
    case 2:
      require(!action("beta-uuid", "vpn.panel.connecting").enabled, "connecting row enabled");
      require(action("alpha-uuid", "vpn.panel.connect").enabled, "unrelated row disabled");
      assertText("beta-uuid", "vpn.panel.connecting");
      VPNService.lastError = "Beta Failed: authentication rejected";
      VPNService.connectingUuid = "";
      break;
    case 3:
      require(!row("beta-uuid").connectionActive, "failed connect changed active state");
      require(action("beta-uuid", "vpn.panel.connect").enabled, "failed connect remains busy");
      assertText("beta-uuid", "vpn.panel.disconnected");
      action("alpha-uuid", "vpn.panel.connect").clicked();
      request("connect", "alpha-uuid");
      VPNService.connectingUuid = "";
      VPNService.connections = {
        alpha: Object.assign({}, harness.profiles.alpha, {
                               active: true,
                               device: "wg0"
                             }),
        zulu: harness.profiles.zulu,
        beta: harness.profiles.beta
      };
      break;
    case 4:
      assertOrder(["alpha-uuid", "zulu-uuid", "beta-uuid"]);
      assertText("alpha-uuid", "vpn.panel.connected");
      action("alpha-uuid", "vpn.panel.disconnect").clicked();
      request("disconnect", "alpha-uuid");
      break;
    case 5:
      require(!action("alpha-uuid", "vpn.panel.disconnecting").enabled, "disconnecting row enabled");
      assertText("alpha-uuid", "vpn.panel.disconnecting");
      VPNService.disconnectingUuid = "";
      VPNService.connections = {
        zulu: harness.profiles.zulu,
        alpha: harness.profiles.alpha,
        beta: harness.profiles.beta
      };
      break;
    case 6:
      assertOrder(["zulu-uuid", "alpha-uuid", "beta-uuid"]);
      require(action("alpha-uuid", "vpn.panel.connect").enabled, "disconnect did not restore connect");
      icon("refresh").clicked();
      request("refresh", "");
      VPNService.refreshing = true;
      break;
    case 7:
      icon("stop");
      icon("close").clicked();
      require(!panel.isPanelOpen && VPNService.pollingRefs === 0, "close polling");
      VPNService.connections = {};
      panel.open();
      break;
    case 8:
      require(!panel.hasConnections && rows().length === 0, "empty state rows");
      require(descendants(panel).some(child => child.text === "vpn.panel.no-connections"), "empty state message");
      panel.close();
      require(VPNService.pollingRefs === 0, "empty close polling");
      console.log("VPN_PANEL_BEHAVIOR_PASS");
      Qt.quit();
      break;
    }
  }
  function assertOrder(expected) {
    const actual = rows().map(child => child.connectionUuid);
    require(JSON.stringify(actual) === JSON.stringify(expected), "service ordering changed " + JSON.stringify(actual));
  }
  function assertText(uuid, key) {
    require(descendants(row(uuid)).some(child => child.text === key), "missing row text " + key);
  }
  function descendants(item) {
    let found = [];
    for (const child of item.children || [])
      found = found.concat([child], descendants(child));
    return found;
  }
  function icon(name) {
    const found = descendants(panel).find(child => child.icon === name && typeof child.clicked === "function");
    require(found !== undefined, "missing header icon " + name);
    return found;
  }
  function request(actionName, uuid) {
    const last = VPNService.requests[VPNService.requests.length - 1];
    require(last.action === actionName && last.uuid === uuid, "wrong target " + JSON.stringify(last));
  }
  function require(condition, message) {
    if (!condition)
      throw new Error(message);
  }
  function row(uuid) {
    const found = rows().find(child => child.connectionUuid === uuid);
    require(found !== undefined, "missing production row " + uuid);
    return found;
  }
  function rows() {
    return descendants(panel).filter(child => typeof child.connectionUuid === "string");
  }

  // Offscreen platform: never connects to a desktop or creates a layer surface.
  Window {
    height: 500
    visible: true
    width: 400

    VPNPanel {
      id: panel

      anchors.fill: parent
    }
  }
  Timer {
    interval: 100
    repeat: true
    running: true

    onTriggered: {
      try {
        harness.advance();
      } catch (error) {
        console.error(error.stack);
        Qt.exit(1);
      }
    }
  }
}
