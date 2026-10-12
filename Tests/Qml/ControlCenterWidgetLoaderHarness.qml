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
      property int loadedCount: 0
      property string loadedSnapshot: ""

      function onLoaded() {
        loadedCount++;
        loadedSnapshot = caption + ":" + (screen ? screen.name : "unset");
      }

      implicitWidth: 71
      implicitHeight: 29
    }
  }

  Component {
    id: plainWidget

    Item {
      property string caption: "plain"

      implicitWidth: 33
      implicitHeight: 18
    }
  }

  Component {
    id: subject

    ControlCenterWidgetLoader {}
  }

  TestCase {
    id: tests

    function init() {
      ControlCenterWidgetRegistry.widgets = {
        "first": widget,
        "second": widget,
        "plain": plainWidget
      };
      Logger.warnings = [];
    }

    function createLoader(id) {
      const loaded = createTemporaryObject(subject, host, {
                                             "widgetId": id,
                                             "widgetScreen": firstScreen,
                                             "widgetProps": {
                                               "caption": "initial",
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

    function test_loading_properties_screen_and_callback_order() {
      const loaded = createLoader("first");
      const item = findWidget(loaded);
      verify(item !== null);
      compare(item.caption, "initial");
      compare(item.screen, firstScreen);
      compare(item.loadedCount, 1);
      compare(item.loadedSnapshot, "initial:first");
      compare(item.unknown, undefined);
      compare(loaded.section, "left");
      compare(loaded.sectionIndex, 2);
      compare(Logger.warnings.length, 0);
    }

    function test_reload_reads_current_owner_properties() {
      const loaded = createLoader("first");
      loaded.widgetProps = {
        "caption": "updated",
        "section": "right",
        "sectionWidgetIndex": 4
      };
      loaded.widgetScreen = secondScreen;
      // Existing widget receives assignments only at loading, not on props changes.
      compare(findWidget(loaded).caption, "initial");
      compare(loaded.section, "right");
      compare(loaded.sectionIndex, 4);
      loaded.widgetId = "plain";
      compare(findWidget(loaded).caption, "updated");
      loaded.widgetId = "second";
      compare(findWidget(loaded).loadedSnapshot, "updated:second");
      compare(findWidget(loaded).loadedCount, 1);
    }

    function test_two_owners_preserve_optional_members() {
      const first = createLoader("first");
      const second = createLoader("plain");
      second.widgetProps = {
        "caption": "second-owner",
        "section": "right"
      };
      second.widgetScreen = secondScreen;
      compare(findWidget(second).screen, undefined);
      compare(findWidget(second).onLoaded, undefined);
      second.widgetId = "second";
      compare(findWidget(second).loadedSnapshot, "second-owner:second");
      compare(findWidget(second).loadedCount, 1);
      compare(findWidget(first).loadedSnapshot, "initial:first");
      compare(first.section, "left");
      compare(second.section, "right");
    }

    function test_implicit_geometry_tracks_visibility_and_size() {
      const loaded = createLoader("first");
      const item = findWidget(loaded);
      compare(loaded.implicitWidth, 71);
      compare(loaded.implicitHeight, 29);
      item.implicitWidth = 109;
      item.implicitHeight = 47;
      compare(loaded.implicitWidth, 109);
      compare(loaded.implicitHeight, 47);
      item.visible = false;
      compare(loaded.implicitWidth, 0);
      compare(loaded.implicitHeight, 0);
      item.visible = true;
      compare(loaded.implicitWidth, 109);
    }

    function test_optional_members_and_missing_widget() {
      const plain = createLoader("plain");
      compare(findWidget(plain).caption, "initial");
      compare(plain.implicitWidth, 33);
      const missing = createLoader("missing");
      compare(findWidget(missing), null);
      compare(missing.implicitWidth, 0);
      compare(missing.implicitHeight, 0);
      compare(Logger.warnings.length, 1);
      compare(Logger.warnings[0][2], "missing");
    }

    function test_destruction_clears_owner_reference() {
      const loaded = createLoader("first");
      let cleared = false;
      loaded.widgetPropsChanged.connect(function () {
        cleared = loaded.widgetProps === null;
      });
      loaded.destroy();
      tryVerify(function () {
        return cleared;
      });
    }

    name: "ControlCenterWidgetLoader"
    when: windowShown
  }
}
