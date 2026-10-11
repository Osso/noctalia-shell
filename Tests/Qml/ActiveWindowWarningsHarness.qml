import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Bar.Extras
import qs.Modules.Bar.Widgets
import qs.Services.Compositor
import qs.Services.UI

ShellRoot {
  id: harness

  property var standalone: null
  property var loaded: null
  property Item widgetLoader: null

  PersistentProperties {
    id: reloadState
    property int generation: 0
  }

  function require(condition, message) {
    if (!condition) {
      console.error("ACTIVE_WINDOW_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function setSettings(widget, position) {
    Settings.data = Object.assign({}, Settings.data, {
                                    "bar": Object.assign({}, Settings.data.bar, {
                                                           "position": position,
                                                           "widgets": {
                                                             "left": [widget],
                                                             "center": [],
                                                             "right": []
                                                           }
                                                         })
                                  });
  }

  function assertDimensions(width, height, message) {
    for (const item of [harness.standalone, harness.loaded]) {
      harness.require(item.implicitWidth === width && item.implicitHeight === height, message + ": expected " + width + "x" + height + ", actual " + item.implicitWidth + "x" + item.implicitHeight);
    }
    harness.require(harness.widgetLoader.implicitWidth === width && harness.widgetLoader.implicitHeight === height, message + " loader dimensions");
  }

  Component {
    id: widgetComponent
    ActiveWindow {}
  }

  Component {
    id: loaderComponent
    BarWidgetLoader {}
  }

  Window {
    id: offscreen
    visible: true // No desktop display connection; runner forces offscreen.
    width: 480
    height: 120
  }

  Timer {
    id: scenario
    property int step: 0
    interval: 400
    running: true
    repeat: true
    onTriggered: {
      switch (scenario.step) {
      case 0:
        harness.require(!Settings.ready, "settings hydration deliberately delayed");
        harness.standalone = widgetComponent.createObject(offscreen.contentItem);
        harness.widgetLoader = loaderComponent.createObject(offscreen.contentItem, {
                                                              "widgetId": "ActiveWindow",
                                                              "widgetScreen": Quickshell.screens[0],
                                                              "widgetProps": {
                                                                "widgetId": "ActiveWindow",
                                                                "section": "left",
                                                                "sectionWidgetIndex": 0
                                                              }
                                                            });
        harness.loaded = BarWidgetRegistry.constructed.ActiveWindow;
        harness.require(harness.standalone !== null && harness.loaded !== undefined, "actual widgets constructed");
        harness.require(BarWidgetRegistry.snapshots.length === 1, "production onLoaded observed");
        const before = BarWidgetRegistry.snapshots[0];
        harness.require(before.widgetId === "" && before.metadataReady && before.maxWidth === 145 && !before.fixed, "metadata before production widgetProps assignment");
        harness.require(harness.loaded.widgetId === "ActiveWindow" && harness.loaded.sectionWidgetIndex === 0, "production widgetProps assignment before settings ready");
        if (Settings.focusedStart && Style.animationNormal > 0) {
          for (const item of [harness.standalone, harness.loaded]) {
            harness.require(item.visible && Number.isFinite(item.implicitWidth) && item.implicitWidth >= 0 && item.implicitWidth <= 145, "focused construction animation has bounded width");
          }
        } else {
          harness.assertDimensions(Settings.focusedStart ? 145 : 0, Settings.focusedStart ? Settings.expectedHeight : 0, "pre-ready focus-dependent state");
        }
        break;
      case 1:
        harness.require(!Settings.ready, "settings still delayed after construction");
        harness.assertDimensions(Settings.focusedStart ? 145 : 0, Settings.focusedStart ? Settings.expectedHeight : 0, "settled pre-ready focus-dependent state");
        CompositorService.focusedWindow = null;
        harness.standalone.widgetId = "ActiveWindow";
        harness.standalone.section = "left";
        harness.standalone.sectionWidgetIndex = 0;
        harness.setSettings({
                              "id": "ActiveWindow",
                              "hideMode": "visible",
                              "maxWidth": 210,
                              "useFixedWidth": true,
                              "showIcon": false
                            }, "top");
        Settings.ready = true;
        break;
      case 2:
        harness.assertDimensions(210, Settings.expectedHeight, "hydrated fixed horizontal dimensions");
        for (const item of [harness.standalone, harness.loaded]) {
          harness.require(item.visible && item.opacity === 1 && !item.showIcon && item.windowTitle === "No active window", "hydrated empty visible state");
        }
        CompositorService.focusedWindow = {
          "title": "Concrete long focused window title exceeding ninety pixels",
          "appId": "fixture"
        };
        CompositorService.activeWindowChanged();
        harness.setSettings({
                              "id": "ActiveWindow",
                              "hideMode": "visible",
                              "maxWidth": 90,
                              "useFixedWidth": false,
                              "scrollingMode": "always"
                            }, "top");
        break;
      case 3:
        harness.assertDimensions(90, Settings.expectedHeight, "focused title dynamic cap");
        harness.require(harness.loaded.windowTitle === CompositorService.focusedWindow.title, "focused title rendered");
        harness.setSettings({
                              "id": "ActiveWindow",
                              "hideMode": "visible"
                            }, "left");
        harness.standalone.scaling = 0.8;
        harness.widgetLoader.barDensity = "mini";
        break;
      case 4:
        harness.assertDimensions(22, 22, "vertical density scaling");
        CompositorService.focusedWindow = null;
        CompositorService.windowListChanged();
        harness.setSettings({
                              "id": "ActiveWindow",
                              "hideMode": "transparent",
                              "maxWidth": 160,
                              "useFixedWidth": true
                            }, "top");
        break;
      case 5:
        harness.assertDimensions(160, Settings.expectedHeight, "transparent mode retains layout space");
        harness.require(harness.loaded.visible && harness.loaded.opacity === 0 && harness.widgetLoader.visible, "transparent widget and loader visible");
        harness.loaded.handleContextMenuAction("widget-settings");
        harness.require(PanelService.actions.join(",") === "close,settings", "settings closes menu before opening");
        harness.require(BarService.settingsArgs[0] === Quickshell.screens[0] && BarService.settingsArgs[1] === "left" && BarService.settingsArgs[2] === 0 && BarService.settingsArgs[3] === "ActiveWindow" && BarService.settingsArgs[4].maxWidth === 160, "context settings instance arguments");
        harness.setSettings({
                              "id": "ActiveWindow",
                              "hideMode": "hidden"
                            }, "top");
        break;
      case 6:
        harness.assertDimensions(0, 0, "hidden empty state after hydration");
        harness.require(!harness.loaded.visible && !harness.widgetLoader.visible, "hidden mode removes widget and loader");
        CompositorService.focusedWindow = {
          "title": "Focus restored for fade test",
          "appId": "fixture"
        };
        break;
      case 7:
        harness.require(harness.loaded.visible && harness.loaded.opacity === 1, "hidden mode shows focused window");
        CompositorService.focusedWindow = null;
        if (Style.animationNormal > 0) {
          harness.require(harness.loaded.visible && harness.loaded.opacity > 0, "hidden widget remains visible during fade");
        }
        // Geometry animates to zero after opacity finishes hiding the widget.
        scenario.interval = Math.max(400, Style.animationNormal * 2 + 100);
        break;
      case 8:
        harness.assertDimensions(0, 0, "hidden dimensions after fade");
        harness.require(!harness.loaded.visible && !harness.widgetLoader.visible, "fade removes widget and loader");
        if (Settings.reloadLifecycle && reloadState.generation === 0) {
          CompositorService.focusedWindow = {
            "title": "Visible focused widget during isolated soft reload",
            "appId": "fixture"
          };
          break;
        }
        harness.require(!Settings.reloadLifecycle || reloadState.generation === 1, "isolated generation survived reload");
        harness.widgetLoader.destroy();
        harness.standalone.destroy();
        scenario.running = false;
        console.log("ACTIVE_WINDOW_BEHAVIOR_PASS", "9 stages: direct widget and production Loader");
        Qt.quit();
        break;
      case 9:
        harness.require(harness.loaded.visible && harness.loaded.opacity === 1, "old generation widget visible at reload");
        reloadState.generation = 1;
        scenario.running = false;
        console.log("ACTIVE_WINDOW_ISOLATED_RELOAD_BEGIN");
        Quickshell.reload(false);
        break;
      }
      scenario.step++;
    }
  }
}
