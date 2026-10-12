import QtQuick
import QtQuick.Shapes
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.MainScreen.Backgrounds
import qs.Services.UI

Item {
  id: scene

  width: 640
  height: 360

  ShellScreen {
    id: screenA

    name: "DP-fixture"
  }

  BackgroundRegion {
    id: fakeBar

    topLeftCornerState: -1
    topRightCornerState: -1
    bottomLeftCornerState: -1
    bottomRightCornerState: -1

    x: 20
    y: 10
    width: 240
    height: 30
  }

  BackgroundRegion {
    id: panelGeometry

    topLeftCornerState: -1
    topRightCornerState: -1
    bottomLeftCornerState: -1
    bottomRightCornerState: -1

    x: 80
    y: 100
    width: 120
    height: 90
  }

  QtObject {
    id: fakeWindow

    property ShellScreen screen: screenA
    property rect inputRegion: Qt.rect(20, 10, 240, 30)
    property BackgroundRegion audioPanelPlaceholder: panelGeometry
    property BackgroundRegion batteryPanelPlaceholder: panelGeometry
    property BackgroundRegion bluetoothPanelPlaceholder: panelGeometry
    property BackgroundRegion brightnessPanelPlaceholder: panelGeometry
    property BackgroundRegion clockPanelPlaceholder: panelGeometry
    property BackgroundRegion controlCenterPanelPlaceholder: panelGeometry
    property BackgroundRegion changelogPanelPlaceholder: panelGeometry
    property BackgroundRegion launcherPanelPlaceholder: panelGeometry
    property BackgroundRegion notificationHistoryPanelPlaceholder: panelGeometry
    property BackgroundRegion sessionMenuPanelPlaceholder: panelGeometry
    property BackgroundRegion settingsPanelPlaceholder: panelGeometry
    property BackgroundRegion setupWizardPanelPlaceholder: panelGeometry
    property BackgroundRegion trayDrawerPanelPlaceholder: panelGeometry
    property BackgroundRegion wallpaperPanelPlaceholder: panelGeometry
    property BackgroundRegion wifiPanelPlaceholder: panelGeometry
    property BackgroundRegion vpnPanelPlaceholder: panelGeometry
    property BackgroundRegion processPanelPlaceholder: panelGeometry
  }

  Rectangle {
    id: underlay

    anchors.fill: parent
    color: "#123456"
  }

  Item {
    id: canvas

    anchors.fill: parent

    MouseArea {
      id: receiver

      property int clicks: 0

      anchors.fill: parent
      onClicked: clicks++
    }

    AllBackgrounds {
      id: backgrounds

      bar: fakeBar
      windowRoot: fakeWindow
    }
  }

  TestCase {
    function shape() {
      return backgrounds.children[0].children[0];
    }

    function paths() {
      return Array.from(shape().data).filter(entry => {
        return entry.hasOwnProperty("backgroundColor");
      });
    }

    function compareColors(panelOpacity, barOpacity) {
      const entries = paths();
      compare(entries.length, 18);
      compare(entries[0].backgroundColor, Qt.alpha(NColor.mSurface, barOpacity));
      for (let index = 1; index < entries.length; index++)
        compare(entries[index].backgroundColor, Qt.alpha(NColor.mSurface, panelOpacity));
    }

    function test_colors_geometry_and_transparent_canvas() {
      compareColors(0.6, 0.8);
      Settings.data.ui.panelBackgroundOpacity = 0.25;
      Settings.data.bar.backgroundOpacity = 0.4;
      NColor.mSurface = "#804020";
      compareColors(0.25, 0.4);
      compare(paths()[0].barWidth, 240);
      compare(paths()[1].panelWidth, 120);
      compare(paths()[1].panelX, 80);
      panelGeometry.width = 180;
      compare(paths()[1].panelWidth, 180);
      panelGeometry.visible = false;
      compare(paths()[1].panelWidth, 0);
      panelGeometry.visible = true;
      BarService.isVisible = false;
      compare(paths()[0].barWidth, 0);
      BarService.isVisible = true;
      Settings.data.bar.monitors = ["other-screen"];
      compare(paths()[0].barWidth, 0);
      Settings.data.bar.monitors = [screenA.name];
      compare(paths()[0].barWidth, 240);
      compare(backgrounds.width, 640);
      scene.width = 700;
      // Anchors retain the parent's canvas size.
      compare(backgrounds.width, canvas.width);
      compare(grabImage(canvas).pixel(600, 300), underlay.color);
      underlay.color = "#654321";
      tryVerify(function () {
        return grabImage(canvas).pixel(600, 300) === underlay.color;
      }, 2000, "transparent canvas reveals changed underlay");
    }

    function test_backgrounds_do_not_capture_input() {
      compare(shape().enabled, false);
      const before = receiver.clicks;
      mouseClick(canvas, 30, 20);
      mouseClick(canvas, 90, 110);
      mouseClick(canvas, 600, 300);
      compare(receiver.clicks, before + 3);
      compare(fakeWindow.inputRegion, Qt.rect(20, 10, 240, 30));
    }

    name: "AllBackgroundsOwners"
    when: windowShown
  }
}
