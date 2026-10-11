import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Services.UI
import qs.Modules.MainScreen

ShellRoot {
  id: harness
  property var window
  readonly property var panelNames: ["audioPanel", "batteryPanel", "bluetoothPanel", "brightnessPanel", "changelogPanel", "clockPanel", "controlCenterPanel", "launcherPanel", "notificationHistoryPanel", "sessionMenuPanel", "settingsPanel", "setupWizardPanel", "processPanel", "trayDrawerPanel", "wallpaperPanel", "wifiPanel", "vpnPanel"]

  Component {
    id: factory
    MainScreen {
      visible: false
      screen: Quickshell.screens[0]
    }
  }

  function check(condition, message) {
    if (!condition)
      throw new Error(message);
  }

  function checkEmptyInputMask() {
    check(window.mask.width === window.width && window.mask.height === window.height, "mask covers window");
    check(window.mask.intersection === Intersection.Xor, "full-window XOR");
    check(window.mask.regions.length === 2, "bar and background regions");
    for (const region of window.mask.regions) {
      check(region.intersection === Intersection.Subtract, "input subtraction");
      check(region.width === 0 && region.height === 0, "empty input region");
    }
  }

  function checkClosed() {
    check(!window.visible, "window must stay nonvisible");
    check(!window.isPanelOpen, "closed panel state");
    check(window.color.a === 0, "transparent closed color");
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.None, "closed keyboard focus");
    checkEmptyInputMask();
  }

  function exercisePanel(name) {
    const key = name + "-" + window.screenName;
    const placeholder = window[name + "Placeholder"];
    check(window[name] === null, name + " starts unloaded");
    check(placeholder.width === 0 && placeholder.height === 0, name + " empty placeholder");
    PanelService.open(key);
    const panel = window[name];
    check(panel !== null && panel.objectName === key, name + " caller context/name");
    check(panel.screen === window.screen, name + " screen routing");
    check(window[name + "Placeholder"] === panel.panelRegion, name + " loaded region");
    check(window.isPanelOpen && !window.isPanelClosing, name + " open state");
    check(Math.abs(window.color.a - 0.6) < 0.01, name + " dim color");
    check(window.color.r === 0 && window.color.g === 0 && window.color.b === 0, name + " not white");
    check(window.mask.regions[1].width === window.width && window.mask.regions[1].height === window.height, name + " click-to-close region");
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.OnDemand, name + " keyboard focus");
    panel.exclusiveKeyboard = true;
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.Exclusive, name + " exclusive keyboard focus");
    panel.close();
    check(window.isPanelClosing && window.color.a === 0, name + " closing color");
    checkEmptyInputMask();
    PanelService.finishClose();
    checkClosed();
    PanelService.open(key);
    check(window[name] === panel, name + " reuses loaded panel");
    panel.close();
    PanelService.finishClose();
    checkClosed();
  }

  Component.onCompleted: {
    check(Quickshell.screens.length > 0, "offscreen screen exists");
    window = factory.createObject(harness);
    check(window !== null, "actual MainScreen created");
    check(window.width > 0 && window.height > 0, "nonzero window geometry");
    check(Object.keys(PanelService.loaders).length === panelNames.length, "17 registered loaders");
    checkClosed();
    for (const name of panelNames)
      exercisePanel(name);
    window.destroy();
    Qt.callLater(() => {
      check(Object.keys(PanelService.loaders).length === 0, "destroy unregisters all loaders");
      check(PanelService.removed === panelNames.length, "each loader removed once");
      console.log("MAIN_SCREEN_RUNTIME_PASS 17 register/open/close/reopen/destroy cases");
      Qt.quit();
    });
  }
}
