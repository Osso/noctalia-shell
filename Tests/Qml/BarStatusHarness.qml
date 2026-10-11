import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.System
import qs.Services.Media
import qs.Services.Networking
import qs.Services.UI
import qs.Modules.Bar.Widgets as W

Item {
  id: scene
  width: 800
  height: 600
  ShellScreen {
    id: fixtureScreen
    name: "fixture"
  }
  Component {
    id: notificationFactory
    W.NotificationHistory {}
  }
  Component {
    id: recorderFactory
    W.ScreenRecorder {}
  }
  Component {
    id: wifiFactory
    W.WiFi {}
  }
  Component {
    id: visualizerFactory
    W.AudioVisualizer {}
  }

  TestCase {
    id: tests
    name: "BarStatus"
    when: windowShown
    property var widget

    function init() {
      Settings.data.bar.position = "top";
      Settings.data.bar.widgets.left = [];
      Settings.data.audio.visualizerType = "linear";
      Settings.data.network.wifiEnabled = true;
      Settings.dataChanged();
      NotificationService.historyList.clear();
      NotificationService.lastSeenTs = 100;
      NotificationService.doNotDisturb = false;
      ScreenRecorderService.isAvailable = true;
      ScreenRecorderService.isRecording = false;
      ScreenRecorderService.isPending = false;
      ScreenRecorderService.stopCount = 0;
      ScreenRecorderService.toggleCount = 0;
      NetworkService.ethernetConnected = false;
      NetworkService.internetConnectivity = true;
      NetworkService.networks = {
        "FixtureNet": {
          connected: true,
          signal: 80
        }
      };
      NetworkService.requests = [];
      MediaService.isPlaying = true;
      CavaService.values = [0.2, 0.6, 0.9];
      PanelService.events = [];
      PanelService.lastMenu = null;
      BarService.settingsArgs = [];
      ToastService.errors = [];
    }

    function make(factory, name, config) {
      const props = {
        screen: fixtureScreen,
        x: 200,
        y: 200
      };
      if (name !== "ScreenRecorder") {
        Settings.data.bar.widgets.left = [config || {
            id: name
          }];
        Settings.dataChanged();
        props.widgetId = name;
        props.section = "left";
        props.sectionWidgetIndex = 0;
      }
      widget = createTemporaryObject(factory, scene, props);
      verify(widget !== null);
      wait(150);
      verify(widget.width > 0 && widget.height > 0);
      return widget;
    }

    function button() {
      return widget.children.find(child => child.forceOpen !== undefined) || widget;
    }

    function click(target, which) {
      mouseClick(target, target.width / 2, target.height / 2, which || Qt.LeftButton);
    }

    function menu(target) {
      PanelService.events = [];
      click(target, Qt.RightButton);
      compare(PanelService.events, ["menu"]);
      compare(PanelService.lastScreen, fixtureScreen);
      const popup = PanelService.lastMenu;
      verify(popup !== null);
      compare(popup.lastAnchor, target);
      compare(popup.lastX, 7);
      compare(popup.lastY, 9);
      return popup;
    }

    function assertSettings(popup, name) {
      popup.triggered("widget-settings");
      compare(BarService.settingsArgs, [fixtureScreen, "left", 0, name, widget.widgetSettings]);
      compare(PanelService.events[PanelService.events.length - 1], "close");
    }

    function test_notification_click_menu_wheel() {
      make(notificationFactory, "NotificationHistory");
      click(widget);
      compare(PanelService.events, ["notificationHistoryPanel", "toggle"]);
      compare(PanelService.lastScreen, fixtureScreen);
      compare(PanelService.lastAnchor, widget);
      const popup = menu(widget);
      popup.triggered("toggle-dnd");
      compare(NotificationService.doNotDisturb, true);
      compare(widget.icon, "bell-off");
      NotificationService.historyList.append({
        timestamp: 200
      });
      popup.triggered("clear-history");
      compare(NotificationService.historyList.count, 0);
      assertSettings(popup, "NotificationHistory");
      PanelService.events = [];
      mouseWheel(widget, 10, 10, 0, 120);
      compare(PanelService.events, []);
      compare(NotificationService.doNotDisturb, true);
    }

    function test_notification_badge_loader_recreation() {
      make(notificationFactory, "NotificationHistory", {
        id: "NotificationHistory",
        showUnreadBadge: true,
        hideWhenZero: true
      });
      const loader = widget.children.find(child => child.sourceComponent !== undefined);
      verify(loader !== undefined);
      compare(loader.active, false);
      NotificationService.historyList.append({
        timestamp: 50
      });
      NotificationService.historyList.append({
        timestamp: 200
      });
      NotificationService.historyList.append({
        timestamp: 300
      });
      compare(widget.computeUnreadCount(), 2);
      // ListModel mutation is not a binding dependency of this helper; advance
      // lastSeenTs to exercise the production service's reactive boundary.
      NotificationService.lastSeenTs = 150;
      tryCompare(loader, "active", true);
      verify(loader.item !== null);
      compare(loader.item.count, 2);
      compare(loader.item.width, 8);
      NotificationService.lastSeenTs = 300;
      tryCompare(loader, "active", false);
      compare(loader.item, null);
      widget.widgetSettings = {
        showUnreadBadge: true,
        hideWhenZero: false
      };
      tryCompare(loader, "active", true);
      compare(loader.item.count, 0);
      compare(loader.item.visible, true);
      widget.widgetSettings = {
        showUnreadBadge: false,
        hideWhenZero: false
      };
      tryCompare(loader, "active", false);
      widget.widgetSettings = {
        showUnreadBadge: true,
        hideWhenZero: true
      };
      NotificationService.lastSeenTs = 0;
      tryCompare(loader, "active", true);
      compare(loader.item.count, 3);
    }

    function test_recorder_dispatch_and_source_menu() {
      make(recorderFactory, "ScreenRecorder");
      ScreenRecorderService.isAvailable = false;
      click(widget);
      compare(ToastService.errors.length, 1);
      compare(ScreenRecorderService.toggleCount, 0);
      compare(PanelService.events, []);
      ScreenRecorderService.isAvailable = true;
      click(widget);
      compare(PanelService.events, ["menu"]);
      compare(PanelService.lastScreen, fixtureScreen);
      const popup = PanelService.lastMenu;
      compare(popup.model, ScreenRecorderService.captureSources);
      compare(popup.lastAnchor, widget);
      compare(popup.lastX, 7);
      compare(popup.lastY, 9);
      popup.triggered("window");
      compare(Settings.data.screenRecorder.videoSource, "window");
      compare(ScreenRecorderService.toggleCount, 1);
      compare(ScreenRecorderService.isPending, true);
      compare(PanelService.events, ["menu", "close"]);
      click(widget);
      compare(ScreenRecorderService.stopCount, 1);
      ScreenRecorderService.isRecording = true;
      click(widget);
      compare(ScreenRecorderService.stopCount, 2);
      compare(ScreenRecorderService.isRecording, false);
      PanelService.events = [];
      click(widget, Qt.RightButton);
      mouseWheel(widget, 10, 10, 0, -120);
      compare(PanelService.events, []);
      compare(ScreenRecorderService.toggleCount, 1);
    }

    function test_recorder_spinner_hover_animation() {
      make(recorderFactory, "ScreenRecorder");
      const spinner = widget.children.find(child => child.transformOrigin !== undefined && child.icon === "loader-2");
      verify(spinner !== undefined);
      compare(spinner.visible, false);
      ScreenRecorderService.isPending = true;
      compare(widget.icon, "");
      compare(spinner.visible, true);
      wait(40);
      verify(spinner.rotation > 0 && spinner.rotation < 360);
      mouseMove(widget, 10, 10);
      tryCompare(widget, "hovering", true);
      compare(spinner.color, widget.colorFgHover);
      mouseMove(scene, 700, 500);
      tryCompare(widget, "hovering", false);
      compare(spinner.color, widget.colorFg);
      ScreenRecorderService.isPending = false;
      tryCompare(spinner, "rotation", 0);
      compare(spinner.visible, false);
      compare(widget.icon, "camera-video");
    }

    function test_wifi_network_display_and_orientation() {
      make(wifiFactory, "WiFi", {
        id: "WiFi",
        displayMode: "alwaysShow"
      });
      const pill = button();
      compare(pill.icon, "wifi");
      compare(pill.text, "FixtureNet");
      compare(pill.forceOpen, true);
      NetworkService.networks = {
        "WeakNet": {
          connected: true,
          signal: 20
        }
      };
      compare(pill.icon, "wifi-1");
      compare(pill.text, "WeakNet");
      NetworkService.ethernetConnected = true;
      compare(pill.icon, "ethernet");
      compare(pill.text, "");
      compare(pill.forceClose, true);
      NetworkService.internetConnectivity = false;
      compare(pill.icon, "ethernet-off");
      NetworkService.ethernetConnected = false;
      NetworkService.networks = {};
      compare(pill.icon, "wifi-off");
      compare(pill.text, "");
      compare(pill.tooltipText, "tooltips.manage-wifi");
      NetworkService.networks = {
        "FixtureNet": {
          connected: true,
          signal: 80
        }
      };
      Settings.data.bar.position = "left";
      Settings.dataChanged();
      compare(pill.forceOpen, false);
      compare(pill.forceClose, true);
      wait(150);
      verify(widget.width > 0 && widget.height > 0);
    }

    function test_wifi_click_menu_wheel() {
      make(wifiFactory, "WiFi");
      const pill = button();
      click(pill);
      compare(PanelService.events, ["wifiPanel", "toggle"]);
      compare(PanelService.lastScreen, fixtureScreen);
      compare(PanelService.lastAnchor, pill);
      const popup = menu(pill);
      popup.triggered("toggle-wifi");
      compare(NetworkService.requests, [false]);
      Settings.data.network.wifiEnabled = false;
      Settings.dataChanged();
      popup.triggered("toggle-wifi");
      compare(NetworkService.requests, [false, true]);
      assertSettings(popup, "WiFi");
      PanelService.events = [];
      mouseWheel(pill, 10, 10, 0, 120);
      compare(PanelService.events, []);
      compare(NetworkService.requests, [false, true]);
    }

    function test_visualizer_click_menu_wheel() {
      make(visualizerFactory, "AudioVisualizer");
      click(widget);
      compare(Settings.data.audio.visualizerType, "mirrored");
      Settings.dataChanged();
      const popup = menu(widget);
      popup.triggered("cycle-visualizer");
      compare(Settings.data.audio.visualizerType, "wave");
      Settings.dataChanged();
      click(widget);
      compare(Settings.data.audio.visualizerType, "linear");
      assertSettings(popup, "AudioVisualizer");
      PanelService.events = [];
      mouseWheel(widget, 10, 10, 0, -120);
      compare(Settings.data.audio.visualizerType, "linear");
      compare(PanelService.events, []);
    }

    function test_visualizer_frames_loader_and_animation() {
      make(visualizerFactory, "AudioVisualizer", {
        id: "AudioVisualizer",
        width: 120,
        hideWhenIdle: true,
        colorName: "primary"
      });
      const loader = widget.children.find(child => child.sourceComponent !== undefined);
      verify(loader !== undefined);
      for (const type of ["linear", "mirrored", "wave"]) {
        Settings.data.audio.visualizerType = type;
        Settings.dataChanged();
        tryCompare(loader, "status", Loader.Ready);
        verify(loader.item !== null);
        compare(loader.item.values, CavaService.values);
        compare(loader.item.fillColor, NColor.mPrimary);
        compare(loader.item.vertical, false);
        CavaService.values = [0.8, 0, 0.4, 1];
        compare(loader.item.values, [0.8, 0, 0.4, 1]);
        widget.widgetSettings = {
          width: 120,
          hideWhenIdle: true,
          colorName: "error"
        };
        compare(loader.item.fillColor, NColor.mError);
        Settings.data.bar.position = "left";
        Settings.dataChanged();
        compare(loader.item.vertical, true);
        wait(120);
        compare(widget.implicitWidth, 40);
        compare(widget.implicitHeight, 120);
        Settings.data.bar.position = "top";
        Settings.dataChanged();
        widget.widgetSettings = {
          width: 120,
          hideWhenIdle: true,
          colorName: "primary"
        };
        wait(120);
      }
      compare(widget.implicitWidth, 120);
      MediaService.isPlaying = false;
      compare(widget.visible, false);
      compare(loader.active, false);
      wait(120);
      compare(widget.implicitWidth, 0);
      compare(widget.implicitHeight, 0);
      compare(loader.item, null);
      MediaService.isPlaying = true;
      compare(widget.visible, true);
      wait(30);
      verify(widget.implicitWidth > 0 && widget.implicitWidth < 120);
      wait(100);
      compare(widget.implicitWidth, 120);
      tryCompare(loader, "status", Loader.Ready);
      compare(loader.item.values, CavaService.values);
      Settings.data.audio.visualizerType = "none";
      Settings.dataChanged();
      compare(loader.active, false);
      wait(120);
      compare(widget.implicitWidth, 0);
    }

    function cleanup() {
      mouseMove(scene, 750, 550);
      ScreenRecorderService.isPending = false;
    }
  }
}
