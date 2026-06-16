#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Hardware/BrightnessService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBrightnessServiceAvailableMethodsReflectsConfiguredDisplays() {
  const getAvailableMethods = qmlFunction("getAvailableMethods");
  const ctx = {
    Settings: {
      data: {
        brightness: {
          enableDdcSupport: true,
        },
      },
    },
    monitors: [
      { isDdc: true },
      { isDdc: false },
    ],
    appleDisplayPresent: true,
  };

  assert.deepEqual(getAvailableMethods(ctx), ["ddcutil", "internal", "apple"]);

  ctx.Settings.data.brightness.enableDdcSupport = false;
  assert.deepEqual(getAvailableMethods(ctx), ["internal", "apple"]);

  ctx.monitors = [{ isDdc: true }];
  ctx.appleDisplayPresent = false;
  assert.deepEqual(getAvailableMethods(ctx), []);
}

function testBrightnessServiceScreenLookupFindsMatchingMonitor() {
  const getMonitorForScreen = qmlFunction("getMonitorForScreen", "screen");
  const leftScreen = { name: "left" };
  const rightScreen = { name: "right" };
  const leftMonitor = { modelData: leftScreen, name: "left-monitor" };
  const rightMonitor = { modelData: rightScreen, name: "right-monitor" };
  const ctx = {
    monitors: [leftMonitor, rightMonitor],
  };

  assert.equal(getMonitorForScreen(ctx, rightScreen), rightMonitor, "getMonitorForScreen must return the monitor for the exact screen object");
  assert.equal(getMonitorForScreen(ctx, { name: "right" }), undefined, "getMonitorForScreen must not match a different screen object with the same shape");
}

function testBrightnessServiceIncreaseBrightnessDelegatesToEveryMonitor() {
  const increaseBrightness = qmlFunction("increaseBrightness");
  const calls = [];
  const ctx = {
    monitors: [
      {
        increaseBrightness() {
          calls.push("left");
        },
      },
      {
        increaseBrightness() {
          calls.push("right");
        },
      },
    ],
  };

  increaseBrightness(ctx);

  assert.deepEqual(calls, ["left", "right"]);
}

function testBrightnessServiceDecreaseBrightnessDelegatesToEveryMonitor() {
  const decreaseBrightness = qmlFunction("decreaseBrightness");
  const calls = [];
  const ctx = {
    monitors: [
      {
        decreaseBrightness() {
          calls.push("left");
        },
      },
      {
        decreaseBrightness() {
          calls.push("right");
        },
      },
    ],
  };

  decreaseBrightness(ctx);

  assert.deepEqual(calls, ["left", "right"]);
}

function testBrightnessServiceDetectedDisplaysPassThrough() {
  const getDetectedDisplays = qmlFunction("getDetectedDisplays");
  const detectedDisplays = [
    { model: "LG ULTRAWIDE", method: "ddcutil" },
    { model: "Built-in", method: "internal" },
  ];
  const ctx = { detectedDisplays };

  assert.equal(getDetectedDisplays(ctx), detectedDisplays);
}

const tests = [
  testBrightnessServiceAvailableMethodsReflectsConfiguredDisplays,
  testBrightnessServiceScreenLookupFindsMatchingMonitor,
  testBrightnessServiceIncreaseBrightnessDelegatesToEveryMonitor,
  testBrightnessServiceDecreaseBrightnessDelegatesToEveryMonitor,
  testBrightnessServiceDetectedDisplaysPassThrough,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
