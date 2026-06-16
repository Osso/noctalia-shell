#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const barSource = readQml("Modules/Bar/Bar.qml");
const loaderSource = readQml("Modules/Bar/Extras/BarWidgetLoader.qml");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testToggleControlCenterPanelIgnoresMissingPanel() {
  const toggleControlCenterPanel = qmlFunction(barSource, "toggleControlCenterPanel");
  const ctx = {
    screen: { name: "HDMI-A-1" },
    PanelService: {
      getPanel() {
        return null;
      },
    },
    Settings: {
      data: {
        controlCenter: {
          position: "close_to_bar_button",
        },
      },
    },
  };

  toggleControlCenterPanel(ctx);
}

function testToggleControlCenterPanelUsesAnchorHintNearBarButton() {
  const toggleControlCenterPanel = qmlFunction(barSource, "toggleControlCenterPanel");
  const calls = [];
  const screen = { name: "HDMI-A-1" };
  const ctx = {
    screen,
    PanelService: {
      getPanel(name, targetScreen) {
        assert.equal(name, "controlCenterPanel");
        assert.equal(targetScreen, screen);
        return {
          toggle(...args) {
            calls.push(args);
          },
        };
      },
    },
    Settings: {
      data: {
        controlCenter: {
          position: "close_to_bar_button",
        },
      },
    },
  };

  toggleControlCenterPanel(ctx);

  assert.deepEqual(calls, [[null, "ControlCenter"]]);
}

function testToggleControlCenterPanelUsesDefaultToggleAwayFromBarButton() {
  const toggleControlCenterPanel = qmlFunction(barSource, "toggleControlCenterPanel");
  const calls = [];
  const ctx = {
    screen: {},
    PanelService: {
      getPanel() {
        return {
          toggle(...args) {
            calls.push(args);
          },
        };
      },
    },
    Settings: {
      data: {
        controlCenter: {
          position: "center",
        },
      },
    },
  };

  toggleControlCenterPanel(ctx);

  assert.deepEqual(calls, [[]]);
}

function testBarWidgetLoaderImplicitSizeRoundsVisibleItems() {
  const getImplicitSize = qmlFunction(loaderSource, "getImplicitSize", "item", "prop");

  assert.equal(getImplicitSize({}, { visible: true, implicitWidth: 42.6 }, "implicitWidth"), 43);
  assert.equal(getImplicitSize({}, { visible: true, implicitHeight: 12.2 }, "implicitHeight"), 12);
}

function testBarWidgetLoaderImplicitSizeReturnsZeroForHiddenOrMissingItems() {
  const getImplicitSize = qmlFunction(loaderSource, "getImplicitSize", "item", "prop");

  assert.equal(getImplicitSize({}, null, "implicitWidth"), 0);
  assert.equal(getImplicitSize({}, { visible: false, implicitWidth: 42.6 }, "implicitWidth"), 0);
}

const tests = [
  testToggleControlCenterPanelIgnoresMissingPanel,
  testToggleControlCenterPanelUsesAnchorHintNearBarButton,
  testToggleControlCenterPanelUsesDefaultToggleAwayFromBarButton,
  testBarWidgetLoaderImplicitSizeRoundsVisibleItems,
  testBarWidgetLoaderImplicitSizeReturnsZeroForHiddenOrMissingItems,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
