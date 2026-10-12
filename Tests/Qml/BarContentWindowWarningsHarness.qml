import QtQuick
import QtTest
import qs.Commons
import qs.Modules.MainScreen

TestCase {
  id: testCase
  name: "BarContentWindow"

  Component {
    id: windowComponent
    BarContentWindow {}
  }
  QtObject {
    id: wideScreen
    property string name: "wide"
    property real width: 1920
    property real height: 1080
  }
  QtObject {
    id: portraitScreen
    property string name: "portrait"
    property real width: 900
    property real height: 1600
  }

  function init() {
    Settings.data.bar.position = "top";
    Settings.data.bar.floating = false;
    Settings.data.bar.marginHorizontal = 1.5;
    Settings.data.bar.marginVertical = 0.75;
    Style.barHeight = 40;
    Style.marginXL = 12;
    Logger.events = [];
  }

  function assertLayout(window, position, width, height, marginH, marginV) {
    const vertical = position === "left" || position === "right";
    compare(window.barPosition, position);
    compare(window.barIsVertical, vertical);
    compare(window.anchors.top, position === "top" || vertical);
    compare(window.anchors.bottom, position === "bottom" || vertical);
    compare(window.anchors.left, position === "left" || !vertical);
    compare(window.anchors.right, position === "right" || !vertical);
    compare(window.margins.top, position === "top" || vertical ? marginV : 0);
    compare(window.margins.bottom, position === "bottom" || vertical ? marginV : 0);
    compare(window.margins.left, position === "left" || !vertical ? marginH : 0);
    compare(window.margins.right, position === "right" || !vertical ? marginH : 0);
    compare(window.implicitWidth, width);
    compare(window.implicitHeight, height);
    const bar = findChild(window.contentItem, "fixtureBar");
    verify(bar !== null);
    compare(bar.width, width);
    compare(bar.height, height);
    compare(bar.screen, window.screen);
    compare(window.fixtureNamespace, "noctalia-bar-content-" + window.screen.name);
    compare(window.color, "#00000000");
  }

  function test_rotationAndFloatingMargins() {
    const window = createTemporaryObject(windowComponent, testCase, {
      screen: wideScreen
    });
    verify(window !== null);
    compare(Logger.events.length, 1);
    compare(Logger.events[0][2], "wide");
    for (const position of ["top", "right", "bottom", "left"]) {
      Settings.data.bar.position = position;
      const vertical = position === "left" || position === "right";
      assertLayout(window, position, vertical ? 40 : 1920, vertical ? 1080 : 40, 0, 0);
      Settings.data.bar.floating = true;
      assertLayout(window, position, vertical ? 40 : 1920, vertical ? 1080 : 40, 18, 9);
      Settings.data.bar.floating = false;
    }
    Settings.data.bar.position = "";
    assertLayout(window, "top", 1920, 40, 0, 0);
  }

  function test_screenRoutingAndReactiveDimensions() {
    const first = createTemporaryObject(windowComponent, testCase, {
      screen: wideScreen
    });
    const second = createTemporaryObject(windowComponent, testCase, {
      screen: portraitScreen
    });
    verify(first !== null && second !== null);
    assertLayout(first, "top", 1920, 40, 0, 0);
    assertLayout(second, "top", 900, 40, 0, 0);
    first.screen = portraitScreen;
    assertLayout(first, "top", 900, 40, 0, 0);
    portraitScreen.width = 920;
    assertLayout(first, "top", 920, 40, 0, 0);
    assertLayout(second, "top", 920, 40, 0, 0);
    Settings.data.bar.position = "right";
    Style.barHeight = 48;
    portraitScreen.height = 1700;
    assertLayout(first, "right", 48, 1700, 0, 0);
    assertLayout(second, "right", 48, 1700, 0, 0);
    Settings.data.bar.floating = true;
    Settings.data.bar.marginHorizontal = 0.3;
    Settings.data.bar.marginVertical = 0.2;
    assertLayout(first, "right", 48, 1700, 4, 2);
    first.screen = wideScreen;
    assertLayout(first, "right", 48, 1080, 4, 2);
    assertLayout(second, "right", 48, 1700, 4, 2);
    portraitScreen.width = 900;
    portraitScreen.height = 1600;
  }
}
