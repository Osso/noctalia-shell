import QtQuick
import Quickshell as Native
import qs.TestScreens
import qs.Commons
import qs.Services.UI
import qs.Modules.MainScreen

Native.ShellRoot {
  id: harness
  property int step: 0
  property var variants
  readonly property var kinds: ["MainScreen", "BarContentWindow", "BarExclusionZone", "PopupMenuWindow"]

  ShellScreen {
    id: first
    name: "FAKE-A"
  }
  ShellScreen {
    id: second
    name: "FAKE-B"
  }
  Component {
    id: factory
    AllScreens {}
  }

  function check(condition, message) {
    if (!condition)
      throw new Error(message);
  }

  function checkRoutes(expected) {
    const keys = Object.keys(Routes.live).sort();
    compareKeys(keys, expected.map(entry => entry[0]).sort());
    for (const entry of expected)
      check(Routes.live[entry[0]] === entry[1], "exact screen identity " + entry[0]);
  }

  function compareKeys(actual, expected) {
    check(JSON.stringify(actual) === JSON.stringify(expected), "routes " + JSON.stringify(actual) + " expected " + JSON.stringify(expected));
  }

  function routesFor(screens, allKinds) {
    const expected = [];
    for (const screen of screens) {
      for (const kind of allKinds)
        expected.push([kind + ":" + screen.name, screen]);
    }
    return expected;
  }

  Timer {
    interval: 30
    repeat: true
    running: true
    onTriggered: {
      try {
        switch (harness.step++) {
        case 0:
          Quickshell.screens = [first, second];
          harness.variants = factory.createObject(harness);
          break;
        case 1:
          harness.checkRoutes(harness.routesFor([first, second], harness.kinds));
          Quickshell.screens = [second];
          break;
        case 2:
          harness.checkRoutes(harness.routesFor([second], harness.kinds));
          Quickshell.screens = [second, first];
          break;
        case 3:
          harness.checkRoutes(harness.routesFor([first, second], harness.kinds));
          Settings.data.bar.monitors = [second.name];
          break;
        case 4:
          harness.checkRoutes(harness.routesFor([second], harness.kinds));
          Settings.data.general.allowPanelsOnScreenWithoutBar = true;
          break;
        case 5:
          harness.checkRoutes(harness.routesFor([second], harness.kinds).concat(harness.routesFor([first], ["MainScreen"])));
          BarService.isVisible = false;
          break;
        case 6:
          harness.checkRoutes(harness.routesFor([first, second], ["MainScreen"]));
          BarService.isVisible = true;
          break;
        case 7:
          harness.checkRoutes(harness.routesFor([second], harness.kinds).concat(harness.routesFor([first], ["MainScreen"])));
          Settings.data.bar.monitors = [];
          break;
        case 8:
          harness.checkRoutes(harness.routesFor([first, second], harness.kinds));
          harness.variants.destroy();
          break;
        case 9:
          harness.checkRoutes([]);
          harness.check(Routes.events.filter(event => event.startsWith("+")).length === Routes.events.filter(event => event.startsWith("-")).length, "balanced create/destroy");
          console.log("ALL_SCREENS_RUNTIME_PASS 9 routing/lifecycle cases");
          Qt.quit();
        }
      } catch (error) {
        console.error("ALL_SCREENS_RUNTIME_FAIL", error.message);
        Qt.quit();
      }
    }
  }
}
