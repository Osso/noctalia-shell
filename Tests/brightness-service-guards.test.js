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
  testBrightnessServiceIncreaseBrightnessDelegatesToEveryMonitor,
  testBrightnessServiceDecreaseBrightnessDelegatesToEveryMonitor,
  testBrightnessServiceDetectedDisplaysPassThrough,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
