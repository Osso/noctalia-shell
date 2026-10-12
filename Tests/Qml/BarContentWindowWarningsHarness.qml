import QtQuick
import Quickshell
import qs.Commons
import qs.Modules.Bar.Extras as Extras
import qs.Modules.MainScreen

ShellRoot {
  id: testCase
  property var temporaryObjects: []

  function verify(value) {
    if (!value)
      throw new Error("verification failed");
  }

  function compare(actual, expected) {
    if (actual !== expected)
      throw new Error("expected " + expected + ", got " + actual);
  }

  function createTemporaryObject(component, owner, properties) {
    const object = component.createObject(owner, properties);
    temporaryObjects.push(object);
    return object;
  }

  Timer {
    interval: 10
    running: true
    onTriggered: {
      try {
        for (const test of [testCase.test_rotationAndFloatingMargins, testCase.test_twoRealScreensRoutingAndOrientation, testCase.test_exclusionRoutingAndRecreation]) {
          testCase.init();
          test();
          for (const object of testCase.temporaryObjects)
            object.destroy();
          testCase.temporaryObjects = [];
        }
        console.log("BAR_SCREEN_OWNER_PASS three cases two real ShellScreens");
        Qt.quit();
      } catch (error) {
        console.error(error);
        Qt.exit(1);
      }
    }
  }

  Component {
    id: windowComponent
    BarContentWindow {}
  }
  readonly property ShellScreen wideScreen: Quickshell.screens.find(screen => screen.name === "wide")
  readonly property ShellScreen portraitScreen: Quickshell.screens.find(screen => screen.name === "portrait")
  property var activeScreens: []

  Component {
    id: mainExclusion
    BarExclusionZone {}
  }
  Component {
    id: extraExclusion
    Extras.BarExclusionZone {}
  }

  function init() {
    Settings.data.bar.position = "top";
    Settings.data.bar.floating = false;
    Settings.data.bar.marginHorizontal = 1.5;
    Settings.data.bar.marginVertical = 0.75;
    Style.barHeight = 40;
    Style.marginXL = 12;
    Logger.events = [];
    activeScreens = [wideScreen, portraitScreen];
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
    const bar = window.contentItem.children[0];
    verify(bar !== null);
    compare(bar.width, width);
    compare(bar.height, height);
    compare(bar.screen, window.screen);
    compare(window.selectedScreen, window.screen);
    compare(window.fixtureNamespace, "noctalia-bar-content-" + window.screen.name);
    compare(String(window.color), "#00000000");
  }

  function test_exclusionRoutingAndRecreation() {
    for (const component of [mainExclusion, extraExclusion]) {
      let zone = component.createObject(testCase, {
                                          screen: wideScreen
                                        });
      verify(zone !== null);
      compare(zone.selectedScreen, wideScreen);
      compare(zone.screenName, "wide");
      zone.screen = portraitScreen;
      compare(zone.selectedScreen, portraitScreen);
      compare(zone.screenName, "portrait");
      for (const position of ["top", "bottom", "left", "right"]) {
        Settings.data.bar.position = position;
        Settings.data.bar.floating = true;
        const vertical = position === "left" || position === "right";
        compare(zone.implicitWidth, vertical ? 58 : 0);
        compare(zone.implicitHeight, vertical ? 0 : 49);
        compare(zone.fixtureNamespace, "noctalia-bar-exclusion-portrait");
      }
      zone.destroy();
      zone = component.createObject(testCase, {
                                      screen: wideScreen
                                    });
      verify(zone !== null);
      compare(zone.selectedScreen, wideScreen);
      compare(zone.screenName, "wide");
      zone.destroy();
    }
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

  function test_twoRealScreensRoutingAndOrientation() {
    const first = createTemporaryObject(windowComponent, testCase, {
                                          screen: Qt.binding(() => testCase.activeScreens[0])
                                        });
    const second = createTemporaryObject(windowComponent, testCase, {
                                           screen: portraitScreen
                                         });
    verify(first !== null && second !== null);
    assertLayout(first, "top", 1920, 40, 0, 0);
    assertLayout(second, "top", 900, 40, 0, 0);
    activeScreens = [portraitScreen];
    assertLayout(first, "top", 900, 40, 0, 0);
    assertLayout(second, "top", 900, 40, 0, 0);
    Settings.data.bar.position = "right";
    Style.barHeight = 48;
    assertLayout(first, "right", 48, 1600, 0, 0);
    assertLayout(second, "right", 48, 1600, 0, 0);
    Settings.data.bar.floating = true;
    Settings.data.bar.marginHorizontal = 0.3;
    Settings.data.bar.marginVertical = 0.2;
    assertLayout(first, "right", 48, 1600, 4, 2);
    activeScreens = [wideScreen, portraitScreen];
    assertLayout(first, "right", 48, 1080, 4, 2);
    assertLayout(second, "right", 48, 1600, 4, 2);
  }
}
