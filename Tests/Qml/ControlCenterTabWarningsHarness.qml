import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Modules.Panels.Settings.Tabs
import qs.Modules.Panels.Settings.ControlCenter

Item {
  id: scene
  width: 900
  height: 1400

  Component {
    id: factory
    ControlCenterTab {
      width: scene.width
      height: implicitHeight
    }
  }
  Component {
    id: dialogFactory
    ControlCenterWidgetSettingsDialog {}
  }

  TestCase {
    name: "ControlCenterTabWarnings"
    when: windowShown
    property var tab

    function descendants(item) {
      let result = [];
      for (const child of item.children || [])
        result = result.concat([child], descendants(child));
      return result;
    }

    function cardsControl() {
      const matches = descendants(tab).filter(item => item.itemToggled !== undefined);
      compare(matches.length, 1);
      return matches[0];
    }

    function section(id) {
      const matches = descendants(tab).filter(item => item.sectionId === id && item.addWidget !== undefined);
      compare(matches.length, 1);
      return matches[0];
    }

    function init() {
      Settings.data.location.weatherEnabled = false;
      Settings.data.controlCenter.position = "center";
      Settings.data.controlCenter.cards = [
        {
          id: "audio-card",
          enabled: false
        },
        {
          id: "profile-card",
          enabled: true
        }
      ];
      Settings.data.controlCenter.shortcuts.left = [
        {
          id: "CustomButton",
          icon: "star"
        },
        {
          id: "WiFi"
        }
      ];
      Settings.data.controlCenter.shortcuts.right = [
        {
          id: "Bluetooth"
        }
      ];
      Settings.saveRequests = 0;
      tab = createTemporaryObject(factory, scene);
      verify(tab !== null);
      wait(30);
    }

    function test_initial_cards_registry_and_geometry() {
      compare(Settings.data.controlCenter.cards, [
        {
          id: "audio-card",
          enabled: false
        },
        {
          id: "profile-card",
          enabled: true
        },
        {
          id: "shortcuts-card",
          enabled: true
        },
        {
          id: "weather-card",
          enabled: false
        },
        {
          id: "media-sysmon-card",
          enabled: true
        }
      ]);
      const left = section("left");
      compare(left.availableWidgets.count, 3);
      compare(left.availableWidgets.get(0).key, "Bluetooth");
      compare(left.availableWidgets.get(1).key, "CustomButton");
      compare(left.availableWidgets.get(2).key, "WiFi");
      verify(left.width > 0 && left.height > 0);
      const right = section("right");
      verify(right.y >= left.y + left.height);
      compare(left.maxWidgets, 5);
      compare(right.maxWidgets, 5);
      // Initialization pushes into the bound JS array without notifying the ListView.
      compare(cardsControl().height, 0);
      for (const width of [600, 900]) {
        tab.width = width;
        wait(30);
        verify(tab.implicitHeight > 0);
        for (const item of [left, right]) {
          verify(item.width > 0 && item.width <= tab.width, "tab=" + tab.width + " control=" + item + " width=" + item.width);
          verify(item.height > 0, "control=" + item + " height=" + item.height);
          verify(isFinite(item.x) && isFinite(item.y));
        }
      }
    }

    function test_toggle_reorder_and_weather_notification() {
      const cards = cardsControl();
      cards.toggleItem(0);
      tryVerify(function () {
        return cards.height > 0;
      });
      compare(Settings.data.controlCenter.cards[0], {
        id: "audio-card",
        enabled: true
      });
      cards.toggleItem(1);
      compare(Settings.data.controlCenter.cards[1].enabled, true);
      cards.moveItem(0, 4);
      compare(Settings.data.controlCenter.cards.map(card => card.id), ["profile-card", "shortcuts-card", "weather-card", "media-sysmon-card", "audio-card"]);
      Settings.data.location.weatherEnabled = true;
      compare(Settings.data.controlCenter.cards[2].enabled, true);
      compare(cards.disabledIds, []);
      Settings.data.location.weatherEnabled = false;
      compare(Settings.data.controlCenter.cards[2].enabled, false);
      compare(cards.disabledIds, ["weather-card"]);
      compare(Settings.saveRequests, 0);
    }

    function test_position_selection_and_shortcut_signals() {
      const positions = descendants(tab).filter(item => item.label === "settings.control-center.position.label" && item.selected !== undefined);
      compare(positions.length, 1);
      positions[0].activateCurrentIndex(4);
      compare(Settings.data.controlCenter.position, "top_right");
      const left = section("left");
      left.addWidget("CustomButton", "left");
      compare(Settings.data.controlCenter.shortcuts.left[2], {
        id: "CustomButton",
        icon: "terminal",
        command: "fixture-never-run"
      });
      left.reorderWidget("left", 2, 0);
      compare(Settings.data.controlCenter.shortcuts.left[0].icon, "terminal");
      const unchanged = JSON.stringify(Settings.data.controlCenter.shortcuts.left);
      left.reorderWidget("left", -1, 1);
      left.removeWidget("left", 99);
      compare(JSON.stringify(Settings.data.controlCenter.shortcuts.left), unchanged);
      left.moveWidget("left", 0, "right");
      compare(Settings.data.controlCenter.shortcuts.left.length, 2);
      compare(Settings.data.controlCenter.shortcuts.right[1].icon, "terminal");
      left.removeWidget("left", 1);
      compare(Settings.data.controlCenter.shortcuts.left, [
        {
          id: "CustomButton",
          icon: "star"
        }
      ]);
    }

    function test_shortcut_dialog_cancel_and_apply() {
      const left = section("left");
      const dialog = createTemporaryObject(dialogFactory, scene, {
        widgetIndex: 0,
        sectionId: "left",
        widgetId: "CustomButton",
        widgetData: Settings.data.controlCenter.shortcuts.left[0]
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
      const cancel = descendants(dialog.contentItem).find(item => item.text === "Cancel" && item.clicked !== undefined);
      verify(cancel !== undefined);
      cancel.clicked();
      tryCompare(dialog, "opened", false);
      compare(Settings.data.controlCenter.shortcuts.left[0].icon, "star");
      compare(Settings.saveRequests, 0);
      dialog.open();
      tryCompare(dialog, "opened", true);
      editor = descendants(dialog.contentItem).find(item => item.draftIcon !== undefined);
      editor.draftIcon = "saved";
      const apply = descendants(dialog.contentItem).find(item => item.text === "Apply" && item.clicked !== undefined);
      verify(apply !== undefined);
      apply.clicked();
      tryCompare(dialog, "opened", false);
      compare(Settings.data.controlCenter.shortcuts.left[0], {
        id: "CustomButton",
        icon: "saved"
      });
      compare(Settings.saveRequests, 1);
    }
  }
}
