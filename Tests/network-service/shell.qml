import QtQuick
import Quickshell
import "Commons"
import "Services/Networking"
import "Services/UI"

ShellRoot {
  id: test

  property string mode: Quickshell.env("NETWORK_FIXTURE_MODE")
  property int phase: 0
  property int ticks: 0
  property int startupNotices: 0

  function require(condition, message) {
    if (!condition) {
      console.error("NETWORK_FAIL", mode, phase, message);
      Qt.quit();
      throw new Error(message);
    }
  }

  function finish() {
    require(!NetworkService.activePolling, "private requests must not enable polling");
    console.log("NETWORK_PASS", mode);
    Qt.quit();
  }

  function checkStartup() {
    if (!Settings.data.network.wifiEnabled || !NetworkService.ethernetConnected || NetworkService.networkConnectivity !== "full")
      return;
    require(Settings.data.network.wifiEnabled, "provider Wi-Fi state");
    require(NetworkService.networks.Home.connected, "provider connected SSID");
    require(NetworkService.internetConnectivity, "provider internet state");
    if (mode !== "missing" && mode !== "malformed") {
      if (NetworkService.cachedLastConnected !== "Saved")
        return;
      require(NetworkService.cachedNetworks.Saved.lastConnected === 123, "loaded adapter cache");
    } else {
      require(NetworkService.cachedLastConnected === "", "failed load resets last connection");
      require(Object.keys(NetworkService.cachedNetworks).length === 0, "failed load resets known networks");
    }
    startupNotices = ToastService.notices.length;
    require(startupNotices === 1, "provider state change delivered Wi-Fi notice");
    NetworkService.scan();
    require(NetworkService.scanning, "scan exposes busy state before callback");
    phase++;
  }

  function checkScan() {
    if (NetworkService.scanning)
      return;
    if (mode === "profile-error" || mode === "scan-error") {
      const diagnostic = mode === "profile-error" ? "profile fixture denied" : "scan fixture denied";
      require(NetworkService.lastError === diagnostic, "stderr error delivery");
      require(NetworkService.networks.Home.connected, "failure preserves prior provider state");
      require(NetworkService.cachedLastConnected === "Saved", "failure preserves cache");
      finish();
      return;
    }
    require(NetworkService.lastError === "", "scan succeeds");
    require(NetworkService.networks.Guest.connected, "scan callback publishes connected SSID");
    require(NetworkService.networks.Saved.existing, "profile callback reaches scan callback");
    require(NetworkService.networks.Saved.cached === (mode === "valid"), "scan reads loaded cache");
    require(NetworkService.cachedLastConnected === "Guest", "scan callback updates same adapter");
    NetworkService.connect("Saved");
    require(NetworkService.connecting && NetworkService.connectingTo === "Saved", "connect exposes busy state");
    phase++;
  }

  function checkSavedConnect() {
    if (NetworkService.connecting)
      return;
    require(NetworkService.lastError === "", "saved connect succeeds");
    require(NetworkService.cachedNetworks.Saved.profileName === "Saved", "connect callback updates cache");
    require(NetworkService.cachedLastConnected === "Saved", "connect callback updates last connection");
    require(NetworkService.networks.Saved.connected && !NetworkService.networks.Guest.connected, "connect updates provider state");
    NetworkService.connect("New", "fixture-secret");
    phase++;
  }

  function checkNewConnect() {
    if (NetworkService.connecting)
      return;
    require(NetworkService.cachedLastConnected === "New", "new connect updates cache binding");
    require(NetworkService.cachedNetworks.New.profileName === "New", "new connect adds known network");
    require(NetworkService.networks.New.connected, "new connect creates provider entry");
    NetworkService.connect("Denied");
    phase++;
  }

  function checkDeniedConnect() {
    if (NetworkService.connecting)
      return;
    require(NetworkService.lastError === "permission denied", "stderr preferred and first line delivered");
    require(NetworkService.connectingTo === "", "error callback clears busy SSID");
    require(NetworkService.cachedLastConnected === "New", "error does not mutate adapter");
    require(!NetworkService.cachedNetworks.Denied, "failed connection not cached");
    require(ToastService.notices.length === startupNotices + 2, "only successful connections notify");
    NetworkService.forget("New");
    require(NetworkService.forgettingNetwork === "New", "forget exposes busy state");
    phase++;
  }

  function checkForget() {
    if (NetworkService.forgettingNetwork)
      return;
    require(NetworkService.lastError === "", "forget succeeds");
    require(!NetworkService.cachedNetworks.New, "forget removes same adapter entry");
    require(NetworkService.cachedLastConnected === "", "forget clears last connection");
    require(!NetworkService.networks.New.cached && !NetworkService.networks.New.existing, "forget publishes cache flags");
    poll.stop();
    // Wait past the production debounce; Python checks actual serialized cache.
    persisted.start();
  }

  Timer {
    id: poll
    interval: 20
    running: true
    repeat: true
    onTriggered: {
      test.ticks++;
      test.require(test.ticks < 500, "bounded callback wait");
      switch (test.phase) {
      case 0:
        test.checkStartup();
        break;
      case 1:
        test.checkScan();
        break;
      case 2:
        test.checkSavedConnect();
        break;
      case 3:
        test.checkNewConnect();
        break;
      case 4:
        test.checkDeniedConnect();
        break;
      case 5:
        test.checkForget();
        break;
      }
    }
  }

  Timer {
    id: persisted
    interval: 1300
    onTriggered: test.finish()
  }
}
