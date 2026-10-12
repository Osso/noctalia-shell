import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.LoaderProof
import qs.Services.UI

Item {
  id: host

  width: 400
  height: 300

  ShellScreen {
    id: firstScreen

    name: "first"
  }

  ShellScreen {
    id: secondScreen

    name: "second"
  }

  Component {
    id: widget

    Item {
      property string caption: "default"
      property ShellScreen screen
      property real scaling: 7
      property int loadedCount: 0
      property string loadedSnapshot: ""
      property bool registeredBeforeCallback: false
      property string hideMode: "hidden"

      function onLoaded() {
        loadedCount++;
        loadedSnapshot = caption + ":" + (screen ? screen.name : "unset") + ":" + scaling;
        const entries = BarService.registrations;
        registeredBeforeCallback = entries.length > 0 && entries[entries.length - 1].item === this;
      }

      implicitWidth: 71.4
      implicitHeight: 29.6
    }
  }

  Component {
    id: plainWidget

    Item {
      property string caption: "plain"

      implicitWidth: 33.2
      implicitHeight: 18.7
    }
  }

  Component {
    id: subject

    BarWidgetLoader {}
  }

  TestCase {
    function init() {
      BarWidgetRegistry.widgets = {
        "first": widget,
        "second": plainWidget
      };
      BarService.registrations = [];
      BarService.removals = [];
      Logger.warnings = [];
    }

    function createLoader(id, screen, caption) {
      const loaded = createTemporaryObject(subject, host, {
                                             "widgetId": id,
                                             "widgetScreen": screen,
                                             "barDensity": "compact",
                                             "widgetProps": {
                                               "caption": caption,
                                               "screen": secondScreen,
                                               "scaling": 4,
                                               "section": "left",
                                               "sectionWidgetIndex": 2,
                                               "unknown": "ignored"
                                             }
                                           });
      verify(loaded !== null);
      return loaded;
    }

    function findWidget(loaded) {
      for (let index = 0; index < loaded.children.length; index++) {
        const child = loaded.children[index];
        if (child.item !== undefined)
          return child.item;
      }
      return null;
    }

    function test_assignments_and_registration_precede_callback() {
      const loaded = createLoader("first", firstScreen, "initial");
      const item = findWidget(loaded);
      compare(item.caption, "initial");
      compare(item.screen, firstScreen);
      compare(item.scaling, 0.9);
      compare(item.loadedCount, 1);
      compare(item.loadedSnapshot, "initial:first:0.9");
      verify(item.registeredBeforeCallback);
      compare(item.unknown, undefined);
      const registration = BarService.registrations[0];
      compare(registration.screen, "first");
      compare(registration.section, "left");
      compare(registration.id, "first");
      compare(registration.index, 2);
      compare(registration.item, item);
      compare(Logger.warnings.length, 0);
    }

    function test_two_owners_and_reload_keep_optional_members_optional() {
      const first = createLoader("first", firstScreen, "one");
      const second = createLoader("second", secondScreen, "two");
      const plain = findWidget(second);
      compare(plain.caption, "two");
      compare(plain.screen, undefined);
      compare(plain.scaling, undefined);
      compare(plain.onLoaded, undefined);
      compare(findWidget(first).caption, "one");
      second.widgetProps = {
        "caption": "reloaded",
        "section": "right",
        "sectionWidgetIndex": 4
      };
      second.widgetScreen = firstScreen;
      second.barDensity = "mini";
      compare(plain.caption, "two");
      second.widgetId = "first";
      compare(findWidget(second).loadedSnapshot, "reloaded:first:0.8");
      compare(findWidget(second).loadedCount, 1);
      verify(findWidget(second).registeredBeforeCallback);
      compare(findWidget(first).loadedSnapshot, "one:first:0.9");
      const registration = BarService.registrations[2];
      compare(registration.section, "right");
      compare(registration.index, 4);
    }

    function test_scaling_binding_tracks_only_its_owner() {
      const first = createLoader("first", firstScreen, "one");
      const second = createLoader("first", secondScreen, "two");
      first.barDensity = "mini";
      compare(findWidget(first).scaling, 0.8);
      compare(findWidget(second).scaling, 0.9);
      second.barDensity = "default";
      compare(findWidget(second).scaling, 1);
      compare(findWidget(first).loadedCount, 1);
      compare(findWidget(second).loadedCount, 1);
    }

    function test_geometry_and_transparent_hide_mode() {
      const loaded = createLoader("first", firstScreen, "initial");
      const item = findWidget(loaded);
      compare(loaded.implicitWidth, 71);
      compare(loaded.implicitHeight, 30);
      item.implicitWidth = 109.7;
      compare(loaded.implicitWidth, 110);
      item.visible = false;
      compare(loaded.implicitWidth, 0);
      compare(loaded.implicitHeight, 0);
      item.visible = true;
      item.opacity = 0;
      compare(loaded.visible, false);
      item.hideMode = "transparent";
      compare(loaded.visible, true);
      compare(loaded.implicitWidth, 110);
    }

    function test_missing_widget() {
      const loaded = createLoader("missing", firstScreen, "initial");
      compare(findWidget(loaded), null);
      compare(loaded.visible, false);
      compare(loaded.implicitWidth, 0);
      compare(loaded.implicitHeight, 0);
      compare(Logger.warnings.length, 1);
      compare(Logger.warnings[0][2], "missing");
      compare(BarService.registrations.length, 0);
    }

    function test_destruction_unregisters_owner() {
      const loaded = createLoader("first", firstScreen, "initial");
      loaded.destroy();
      tryCompare(BarService, "removals", [
                   {
                     "screen": "first",
                     "section": "left",
                     "id": "first",
                     "index": 2
                   }
                 ]);
    }

    name: "BarWidgetLoader"
    when: windowShown
  }
}
