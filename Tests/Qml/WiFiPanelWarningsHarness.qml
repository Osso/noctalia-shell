import QtQuick
import Quickshell
import qs.Commons
import qs.Services.Networking
import qs.Modules.Panels.WiFi

ShellRoot {
  id: harness
  property int phase: 0
  property var networks: ({
      home: {
        ssid: "Home",
        signal: 30,
        connected: true,
        existing: true,
        cached: true,
        security: "WPA2"
      },
      saved: {
        ssid: "Saved",
        signal: 90,
        connected: false,
        existing: true,
        cached: true,
        security: "WPA2"
      },
      cached: {
        ssid: "Cached",
        signal: 50,
        connected: false,
        existing: false,
        cached: true,
        security: "WPA2"
      },
      cafe: {
        ssid: "Cafe",
        signal: 80,
        connected: false,
        existing: false,
        cached: false,
        security: "Open"
      },
      secure: {
        ssid: "Secure",
        signal: 40,
        connected: false,
        existing: false,
        cached: false,
        security: "WPA2"
      }
    })

  // Offscreen platform only; no Wayland/X11 connection or layer surface.
  Window {
    visible: true
    width: 400
    height: 500
    WiFiPanel {
      id: panel
      anchors.fill: parent
    }
  }

  function require(condition, message) {
    if (!condition)
      throw new Error(message);
  }

  function descendants(item) {
    let result = [];
    for (const child of item.children || [])
      result = result.concat([child], descendants(child));
    return result;
  }

  function row(ssid) {
    const found = descendants(panel).find(item => item.networkSsid === ssid);
    require(found !== undefined, "missing real delegate " + ssid);
    return found;
  }

  function button(item, key) {
    const found = descendants(item).find(child => child.visible && typeof child.clicked === "function" && child.text === I18n.tr(key));
    require(found !== undefined, "missing visible action " + key);
    return found;
  }

  function icon(item, name) {
    const found = descendants(item).find(child => child.visible && child.icon === name && typeof child.clicked === "function");
    require(found !== undefined, "missing visible icon " + name);
    return found;
  }

  function request(action, ssid, password) {
    const last = NetworkService.requests[NetworkService.requests.length - 1];
    require(last.action === action && last.ssid === (ssid || "") && last.password === (password || ""), "wrong network request " + JSON.stringify(last));
  }

  function advance() {
    switch (harness.phase++) {
    case 0:
      panel.open();
      require(NetworkService.polling === 1 && !panel.hasHadNetworks, "open starts fresh polling");
      NetworkService.networks = harness.networks;
      break;
    case 1:
      require(panel.knownNetworks.map(n => n.ssid).join(",") === "Home,Saved,Cached", "connected first then saved signal ordering");
      require(panel.availableNetworks.map(n => n.ssid).join(",") === "Cafe,Secure", "discovered signal ordering");
      require(panel.hasHadNetworks, "discovery recorded");
      require(row("Saved").networkSignal === 90 && row("Home").networkConnected && !row("Cafe").networkConnected, "concrete delegate roles");
      button(row("Home"), "wifi.panel.disconnect").clicked();
      request("disconnect", "Home");
      button(row("Saved"), "wifi.panel.connect").clicked();
      request("connect", "Saved");
      button(row("Cafe"), "wifi.panel.connect").clicked();
      request("connect", "Cafe");
      button(row("Secure"), "wifi.panel.password").clicked();
      require(panel.passwordSsid === "Secure" && panel.expandedSsid === "", "password routes to panel");
      break;
    case 2:
      {
        const editor = descendants(row("Secure")).find(item => item.echoMode !== undefined);
        require(editor.echoMode === TextInput.Password, "protected password editor");
        require(!button(row("Secure"), "wifi.panel.connect").enabled, "empty password disabled");
        editor.text = "fixture-secret";
        editor.accepted();
        request("connect", "Secure", "fixture-secret");
        require(panel.passwordSsid === "" && editor.text === "", "submission clears password");
        button(row("Secure"), "wifi.panel.password").clicked();
        break;
      }
    case 3:
      icon(row("Secure"), "close").clicked();
      require(panel.passwordSsid === "", "password cancel clears panel state");
      icon(row("Saved"), "trash").clicked();
      require(panel.expandedSsid === "Saved", "forget confirmation expanded");
      break;
    case 4:
      icon(row("Saved"), "close").clicked();
      require(panel.expandedSsid === "", "forget cancel");
      icon(row("Saved"), "trash").clicked();
      break;
    case 5:
      button(row("Saved"), "wifi.panel.forget").clicked();
      request("forget", "Saved");
      require(panel.expandedSsid === "", "forget collapses confirmation");
      icon(panel, "refresh").clicked();
      request("scan");
      NetworkService.lastError = "Fixture failure";
      break;
    case 6:
      {
        const errorText = descendants(panel).find(item => item.text === "Fixture failure");
        require(errorText.visible, "error shown");
        icon(errorText.parent, "close").clicked();
        require(NetworkService.lastError === "", "error dismissed");
        const toggle = descendants(panel).find(item => typeof item.toggled === "function");
        toggle.toggled(false);
        request("disable");
        require(!Settings.data.network.wifiEnabled && !panel.hasHadNetworks && panel.knownNetworks.length === 0 && panel.availableNetworks.length === 0, "disable clears lists and discovery state");
        toggle.toggled(true);
        request("enable");
        NetworkService.networks = {};
        break;
      }
    case 7:
      require(panel.hasHadNetworks, "enabled fixture networks were discovered");
      button(panel, "wifi.panel.scan-again").clicked();
      request("scan");
      panel.close();
      require(NetworkService.polling === 0, "close ends polling");
      panel.open();
      require(!panel.hasHadNetworks && NetworkService.polling === 1, "reopen resets discovery");
      break;
    case 8:
      NetworkService.networks = harness.networks;
      break;
    case 9:
      require(row("Home").networkConnected, "Loader recreation keeps owner and model roles");
      icon(panel, "close").clicked();
      require(!panel.isPanelOpen && NetworkService.polling === 0, "header closes owning panel");
      console.log("WIFI_PANEL_BEHAVIOR_PASS");
      Qt.quit();
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
        console.error(error);
        Qt.exit(1);
      }
    }
  }
}
