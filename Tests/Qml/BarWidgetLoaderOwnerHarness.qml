import QtQuick
import QtTest
import Quickshell
import qs.Modules.Bar.Extras
import qs.Services.UI

Item {
  id: scene

  width: 400
  height: 200

  ShellScreen {
    id: firstScreen

    name: "DP-fixture"
  }

  ShellScreen {
    id: secondScreen

    name: "eDP-fixture"
  }

  QtObject {
    id: fakeWindow

    property rect inputRegion: Qt.rect(0, 0, 400, 30)
  }

  MouseArea {
    id: receiver

    property int clicks: 0

    anchors.fill: parent
    onClicked: clicks++
  }

  Component {
    id: loaderComponent

    BarWidgetLoader {}
  }

  TestCase {
    function createLoader(screen, index, x) {
      return loaderComponent.createObject(scene, {
                                            "widgetId": "Fixture",
                                            "widgetScreen": screen,
                                            "widgetProps": {
                                              "section": "left",
                                              "sectionWidgetIndex": index,
                                              "label": screen.name,
                                              "nonexistent": 42
                                            },
                                            "x": x,
                                            "width": 60,
                                            "height": 30
                                          });
    }

    function key(screen, index) {
      return screen.name + "|left|Fixture|" + index;
    }

    function destroyLoader(loader, screen, index) {
      loader.destroy();
      tryVerify(function () {
        return !BarService.widgets[key(screen, index)];
      });
    }

    function test_per_screen_registration_sizing_and_teardown() {
      const first = createLoader(firstScreen, 2, 0);
      const second = createLoader(secondScreen, 5, 100);
      verify(first !== null);
      verify(second !== null);
      const widget = BarService.widgets[key(firstScreen, 2)];
      const other = BarService.widgets[key(secondScreen, 5)];
      verify(widget !== other);
      compare(widget.screen, firstScreen);
      compare(other.screen, secondScreen);
      compare(widget.label, firstScreen.name);
      compare(other.label, secondScreen.name);
      compare(widget.sectionWidgetIndex, 2);
      compare(other.sectionWidgetIndex, 5);
      compare(widget.loadedCalls, 1);
      verify(widget.registeredBeforeLoaded);
      verify(other.registeredBeforeLoaded);
      compare(widget.hasOwnProperty("nonexistent"), false);
      compare(first.implicitWidth, 24);
      compare(first.implicitHeight, 15);
      compare(widget.width, first.width);
      compare(widget.height, first.height);
      first.width = 90;
      compare(widget.width, 90);
      first.barDensity = "mini";
      compare(widget.scaling, 0.8);
      compare(first.implicitWidth, 19);
      compare(first.implicitHeight, 12);
      compare(other.scaling, 1);
      first.barDensity = "compact";
      compare(widget.scaling, 0.9);
      widget.visible = false;
      compare(first.implicitWidth, 0);
      compare(first.implicitHeight, 0);
      widget.visible = true;
      widget.opacity = 0;
      compare(first.visible, false);
      widget.hideMode = "transparent";
      compare(first.visible, true);
      compare(first.implicitWidth, 21);
      const before = receiver.clicks;
      mouseClick(scene, 10, 10);
      mouseClick(scene, 110, 10);
      compare(receiver.clicks, before + 2);
      compare(fakeWindow.inputRegion, Qt.rect(0, 0, 400, 30));
      destroyLoader(first, firstScreen, 2);
      compare(BarService.widgets[key(secondScreen, 5)], other);
      destroyLoader(second, secondScreen, 5);
      compare(Object.keys(BarService.widgets).length, 0);
      compare(BarService.events, ["register:DP-fixture|left|Fixture|2", "register:eDP-fixture|left|Fixture|5", "unregister:DP-fixture|left|Fixture|2", "unregister:eDP-fixture|left|Fixture|5"]);
      const recreated = createLoader(firstScreen, 2, 0);
      compare(BarService.widgets[key(firstScreen, 2)].loadedCalls, 1);
      destroyLoader(recreated, firstScreen, 2);
      compare(Object.keys(BarService.widgets).length, 0);
    }

    name: "BarWidgetLoaderOwners"
    when: windowShown
  }
}
