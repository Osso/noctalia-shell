pragma ComponentBehavior: Bound

import QtQuick
import QtTest
import qs.Commons
import qs.Services.UI
import qs.Modules.Panels.Settings.Tabs
import qs.Modules.Panels.Settings.Bar

Item {
  id: scene
  width: 900
  height: 2200

  Component {
    id: factory
    BarTab {
      width: scene.width
      height: implicitHeight
    }
  }
  Component {
    id: dialogFactory
    BarWidgetSettingsDialog {}
  }

  TestCase {
    name: "BarTabWarnings"
    when: windowShown
    property var tab

    function descendants(item) {
      let result = [];
      for (const child of item.children || [])
        result = result.concat([child], descendants(child));
      return result;
    }

    function section(id) {
      const matches = descendants(tab).filter(item => item.sectionId === id && item.addWidget !== undefined);
      compare(matches.length, 1);
      return matches[0];
    }

    function init() {
      Settings.data.bar.position = "top";
      Settings.data.bar.density = "default";
      Settings.data.bar.monitors = ["eDP-1"];
      Settings.data.bar.widgets.left = [
        {
          id: "CustomButton",
          icon: "star"
        },
        {
          id: "Clock"
        }
      ];
      Settings.data.bar.widgets.center = [];
      Settings.data.bar.widgets.right = [
        {
          id: "ControlCenter"
        }
      ];
      BarService.instances = [
        {
          widgetId: "Clock",
          section: "left"
        },
        {
          widgetId: "Clock",
          section: "right"
        }
      ];
      ToastService.warnings = [];
      Settings.saveRequests = 0;
      tab = createTemporaryObject(factory, scene);
      verify(tab !== null);
      wait(30);
    }

    function test_registry_sections_and_refresh() {
      for (const id of ["left", "center", "right"]) {
        const control = section(id);
        compare(control.availableWidgets.count, 3);
        compare(control.availableWidgets.get(0).key, "Clock");
        compare(control.availableWidgets.get(0).name, "Clock");
        compare(control.availableWidgets.get(0).badgeLocations, "LR");
        compare(control.widgetModel, Settings.data.bar.widgets[id]);
        verify(control.width > 0 && control.height > 0);
      }
      BarService.instances = [
        {
          widgetId: "Clock",
          section: "center"
        }
      ];
      BarService.activeWidgetsChanged();
      compare(section("center").availableWidgets.get(0).badgeLocations, "C");
      compare(section("right").availableWidgets.get(1).badgeLocations, "");
    }

    function test_monitor_placement_density_controls() {
      const controls = descendants(tab);
      const monitors = controls.filter(item => item.monitorName !== undefined);
      compare(monitors.length, 2);
      compare(monitors[0].label, "eDP-1");
      compare(monitors[0].description, "Laptop:1920x1080@1");
      compare(monitors[1].description, "External:3840x2160@1.5");
      compare(monitors[0].checked, true);
      compare(monitors[1].checked, false);
      monitors[1].toggled(true);
      compare(Settings.data.bar.monitors, ["eDP-1", "DP-1"]);
      monitors[1].toggled(true);
      compare(Settings.data.bar.monitors, ["eDP-1", "DP-1"]);
      monitors[0].toggled(false);
      compare(Settings.data.bar.monitors, ["DP-1"]);
      compare(monitors[0].checked, false);
      const position = controls.find(item => item.label === "settings.bar.appearance.position.label" && item.selected !== undefined);
      const density = controls.find(item => item.label === "settings.bar.appearance.density.label" && item.selected !== undefined);
      verify(position !== undefined && density !== undefined);
      position.activateCurrentIndex(3);
      density.activateCurrentIndex(1);
      compare(Settings.data.bar.position, "right");
      compare(Settings.data.bar.density, "compact");
      compare(position.currentKey, "right");
      compare(density.currentKey, "compact");
    }

    function test_add_remove_reorder_move_and_update() {
      for (const id of ["left", "center", "right"]) {
        const control = section(id);
        const before = Settings.data.bar.widgets[id].slice();
        control.addWidget("CustomButton", id);
        compare(Settings.data.bar.widgets[id][before.length], {
          id: "CustomButton",
          icon: "terminal",
          command: "never-run"
        });
        control.addWidget("Clock", id);
        compare(Settings.data.bar.widgets[id][before.length + 1], {
          id: "Clock"
        });
        control.reorderWidget(id, before.length + 1, 0);
        compare(Settings.data.bar.widgets[id][0], {
          id: "Clock"
        });
        control.removeWidget(id, 0);
        compare(Settings.data.bar.widgets[id].slice(0, before.length), before);
        control.updateWidgetSettings(id, before.length, {
          id: "CustomButton",
          icon: "changed"
        });
        compare(Settings.data.bar.widgets[id][before.length].icon, "changed");
        const unchanged = JSON.stringify(Settings.data.bar.widgets[id]);
        control.removeWidget(id, -1);
        control.reorderWidget(id, 99, 0);
        compare(JSON.stringify(Settings.data.bar.widgets[id]), unchanged);
      }
      section("left").moveWidget("left", 2, "center");
      compare(Settings.data.bar.widgets.left, [
        {
          id: "CustomButton",
          icon: "star"
        },
        {
          id: "Clock"
        }
      ]);
      compare(Settings.data.bar.widgets.center[1], {
        id: "CustomButton",
        icon: "changed"
      });
      section("center").moveWidget("center", 1, "right");
      compare(Settings.data.bar.widgets.center.length, 1);
      compare(Settings.data.bar.widgets.right[2], {
        id: "CustomButton",
        icon: "changed"
      });
      section("right").removeWidget("right", 0);
      compare(ToastService.warnings.length, 1);
      compare(ToastService.warnings[0][2], 12000);
    }

    function test_settings_dialog_discard_and_save() {
      const left = section("left");
      const dialog = createTemporaryObject(dialogFactory, scene, {
        widgetIndex: 0,
        sectionId: "left",
        widgetId: "CustomButton",
        widgetData: Settings.data.bar.widgets.left[0]
      });
      verify(dialog !== null);
      dialog.updateWidgetSettings.connect(function (sectionId, index, settings) {
        left.updateWidgetSettings(sectionId, index, settings);
      });
      dialog.open();
      tryCompare(dialog, "opened", true);
      let editor = descendants(dialog.contentItem).find(item => item.draftIcon !== undefined);
      verify(editor !== undefined);
      editor.draftIcon = "discarded";
      const cancel = descendants(dialog.contentItem).find(item => item.text === "bar.widget-settings.dialog.cancel" && item.clicked !== undefined);
      verify(cancel !== undefined);
      cancel.clicked();
      tryCompare(dialog, "opened", false);
      compare(Settings.data.bar.widgets.left[0], {
        id: "CustomButton",
        icon: "star"
      });
      dialog.open();
      tryCompare(dialog, "opened", true);
      editor = descendants(dialog.contentItem).find(item => item.draftIcon !== undefined);
      verify(editor !== undefined);
      editor.draftIcon = "saved";
      const apply = descendants(dialog.contentItem).find(item => item.text === "bar.widget-settings.dialog.apply" && item.clicked !== undefined);
      verify(apply !== undefined);
      apply.clicked();
      tryCompare(dialog, "opened", false);
      compare(Settings.data.bar.widgets.left[0], {
        id: "CustomButton",
        icon: "saved"
      });
      // BarTab edits draft settings; this dialog does not request immediate persistence.
      compare(Settings.saveRequests, 0);
    }
  }
}
