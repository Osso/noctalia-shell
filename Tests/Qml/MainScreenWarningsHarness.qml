pragma ComponentBehavior: Bound

import QtQuick
import QtTest
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Services.UI
import qs.Modules.MainScreen
import qs.Modules.Panels.Audio

TestCase {
  id: harness
  name: "MainScreenWarnings"
  property MainScreen window
  readonly property var panelNames: ["audioPanel", "batteryPanel", "bluetoothPanel", "brightnessPanel", "changelogPanel", "clockPanel", "controlCenterPanel", "launcherPanel", "notificationHistoryPanel", "sessionMenuPanel", "settingsPanel", "setupWizardPanel", "processPanel", "trayDrawerPanel", "wallpaperPanel", "wifiPanel", "vpnPanel"]

  ShellScreen {
    id: firstScreen
    name: "fixture-A"
    width: 1920
    height: 1080
    x: -1920
    y: 40
  }

  ShellScreen {
    id: secondScreen
    name: "fixture-B"
    width: 1280
    height: 720
    x: 0
    y: 0
  }

  Item {
    id: foreignPanel
    property ShellScreen screen: secondScreen
    property bool isClosing: false
    property bool exclusiveKeyboard: true
  }

  Component {
    id: factory
    MainScreen {
      screen: firstScreen
    }
  }

  function configureBar(values) {
    Settings.data = Object.assign({}, Settings.data, {
      bar: Object.assign({}, Settings.data.bar, values)
    });
  }

  function init() {
    secondScreen.width = 1280;
    secondScreen.height = 720;
    Logger.entries = [];
    PanelService.removed = 0;
    BarService.isVisible = false;
    configureBar({
      position: "top",
      floating: false,
      monitors: [],
      marginHorizontal: 1.5,
      marginVertical: 0.75
    });
    window = factory.createObject(harness);
    verify(window !== null, "production MainScreen created");
    verify(!window.visible, "no visible PanelWindow transport");
  }

  function cleanup() {
    PanelService.finishClose();
    window.destroy();
    wait(0);
    compare(Object.keys(PanelService.loaders).length, 0, "destroy unregisters loaders");
    compare(PanelService.removed, panelNames.length, "each loader removed once");
  }

  function barItem() {
    const container = window.contentItem.children[0];
    for (const child of container.children) {
      if (child.bar !== undefined)
        return child.bar;
    }
    fail("background must receive production bar placeholder");
  }

  function checkEmptyInputMask() {
    compare(window.mask.width, window.width);
    compare(window.mask.height, window.height);
    compare(window.mask.intersection, Intersection.Xor);
    compare(window.mask.regions.length, 2);
    for (const region of window.mask.regions) {
      compare(region.intersection, Intersection.Subtract);
      compare(region.width, 0);
      compare(region.height, 0);
    }
  }

  function checkClosed() {
    verify(!window.isPanelOpen);
    compare(window.color.a, 0);
    compare(window.fixtureKeyboardfocus, WlrKeyboardFocus.None);
    checkEmptyInputMask();
  }

  function activateShortcut(sequence) {
    for (const child of window.data) {
      if (child.sequence === sequence) {
        verify(child.enabled, sequence + " enabled for open panel");
        child.activated();
        return;
      }
    }
    fail("missing shortcut " + sequence);
  }

  function checkOptionalNavigation(name, panel) {
    const backTabPanel = ["launcherPanel", "sessionMenuPanel", "settingsPanel"].includes(name);
    activateShortcut("Backtab");
    compare(panel.selectedIndex, backTabPanel ? 1 : 2, name + " backward tab selection");
    panel.selectedIndex = 2;
    activateShortcut("Ctrl+N");
    compare(panel.selectedIndex, name === "launcherPanel" ? 3 : 2, name + " next selection");
    activateShortcut("Ctrl+P");
    compare(panel.selectedIndex, 2, name + " previous selection or unsupported no-op");
  }

  function exercisePanel(name) {
    const key = name + "-" + window.screenName;
    const placeholder = window[name + "Placeholder"];
    compare(window[name], null, name + " starts unloaded");
    compare(placeholder.width, 0);
    compare(placeholder.height, 0);
    PanelService.open(key);
    const panel = window[name];
    verify(panel !== null);
    compare(panel.objectName, key);
    compare(panel.screen, window.screen, name + " screen routing");
    compare(window[name + "Placeholder"], panel.panelRegion);
    compare(panel.width, window.width, name + " loader width");
    compare(panel.height, window.height, name + " loader height");
    verify(window.isPanelOpen && !window.isPanelClosing);
    verify(Math.abs(window.color.a - 0.6) < 0.01);
    compare(window.color.r, 0);
    compare(window.color.g, 0);
    compare(window.color.b, 0);
    compare(window.mask.regions[1].width, window.width);
    compare(window.mask.regions[1].height, window.height);
    compare(window.fixtureKeyboardfocus, WlrKeyboardFocus.OnDemand);
    checkOptionalNavigation(name, panel);
    panel.exclusiveKeyboard = true;
    compare(window.fixtureKeyboardfocus, WlrKeyboardFocus.Exclusive);
    panel.close();
    verify(window.isPanelClosing);
    compare(window.color.a, 0);
    checkEmptyInputMask();
    PanelService.finishClose();
    checkClosed();
    PanelService.open(key);
    compare(window[name], panel, name + " reuses loaded panel");
    panel.close();
    PanelService.finishClose();
    checkClosed();
  }

  function test_panelLifecycleAndRouting() {
    compare(window.screenName, firstScreen.name);
    const expectedLog = ["MainScreen", "Initialized for screen:", firstScreen.name, "- Dimensions:", 1920, "x", 1080, "- Position:", -1920, ",", 40];
    compare(Logger.entries.length, 1);
    compare(JSON.stringify(Logger.entries[0]), JSON.stringify(expectedLog));
    compare(Object.keys(PanelService.loaders).length, panelNames.length);
    checkClosed();
    for (const name of panelNames)
      exercisePanel(name);
  }

  function test_barGeometry_data() {
    return [
      {
        tag: "top",
        position: "top",
        floating: false,
        geometry: [0, 0, 1920, 33]
      },
      {
        tag: "bottom",
        position: "bottom",
        floating: false,
        geometry: [0, 1047, 1920, 33]
      },
      {
        tag: "left",
        position: "left",
        floating: false,
        geometry: [0, 0, 33, 1080]
      },
      {
        tag: "right",
        position: "right",
        floating: false,
        geometry: [1887, 0, 33, 1080]
      },
      {
        tag: "floating-top",
        position: "top",
        floating: true,
        geometry: [24, 12, 1872, 33]
      },
      {
        tag: "floating-bottom",
        position: "bottom",
        floating: true,
        geometry: [24, 1035, 1872, 33]
      },
      {
        tag: "floating-left",
        position: "left",
        floating: true,
        geometry: [24, 12, 33, 1056]
      },
      {
        tag: "floating-right",
        position: "right",
        floating: true,
        geometry: [1863, 12, 33, 1056]
      }
    ];
  }

  function test_barGeometry(row) {
    configureBar({
      position: row.position,
      floating: row.floating
    });
    BarService.isVisible = true;
    const bar = barItem();
    compare([bar.x, bar.y, bar.width, bar.height], row.geometry);
    const region = window.mask.regions[0];
    compare([region.x, region.y, region.width, region.height], row.geometry);
    BarService.isVisible = false;
    compare(region.width, 0);
    compare(region.height, 0);
  }

  function test_reactiveScreenSelection() {
    configureBar({
      monitors: ["fixture-B"],
      position: "bottom"
    });
    BarService.isVisible = true;
    verify(!window.barShouldShow);
    PanelService.open("audioPanel-fixture-A");
    const panel = window.audioPanel as AudioPanel;
    window.screen = secondScreen;
    compare(window.screenName, "fixture-B");
    compare(panel.screen, secondScreen);
    compare(panel.objectName, "audioPanel-fixture-B");
    verify(window.barShouldShow);
    compare(window.fixtureNamespace, "noctalia-background-fixture-B");
    compare([barItem().x, barItem().y, barItem().width, barItem().height], [0, 687, 1280, 33]);
    secondScreen.width = 900;
    secondScreen.height = 600;
    compare([panel.width, panel.height], [900, 600]);
    compare([window.mask.width, window.mask.height], [900, 600]);
    compare([barItem().y, barItem().width], [567, 900]);
    PanelService.openedPanel = foreignPanel;
    verify(window.isPanelOpen);
    window.screen = firstScreen;
    verify(!window.isPanelOpen, "foreign-screen panel cannot capture this window");
    compare(window.color.a, 0);
    compare(window.fixtureKeyboardfocus, WlrKeyboardFocus.None);
    compare(window.mask.regions[1].width, 0);
    window.screen = null;
    compare(window.screenName, "unknown");
    verify(!window.barShouldShow);
    compare([barItem().screenWidth, barItem().screenHeight], [0, 0]);
    window.screen = secondScreen;
    verify(window.barShouldShow);
    verify(window.isPanelOpen);
  }

  function cleanupTestCase() {
    console.log("MAIN_SCREEN_RUNTIME_PASS 17 panels, 8 geometries, reactive screen selection");
  }
}
