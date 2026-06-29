#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Hardware/BrightnessService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function extractFunctionBodyAfter(anchor, functionName) {
  const anchorIndex = source.indexOf(anchor);
  assert.notEqual(anchorIndex, -1, `missing anchor: ${anchor}`);
  return extractFunctionBody(source.slice(anchorIndex), functionName);
}

function qmlMonitorFunction(functionName, ...argNames) {
  const body = extractFunctionBodyAfter("component Monitor:", functionName);
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

function createDdcDetectionContext(overrides = {}) {
  const ctx = {
    Settings: {
      data: {
        brightness: {
          enableDdcSupport: true,
        },
      },
    },
    ddcDetectionPending: false,
    ddcDetectionCompletedOnce: false,
    ddcMonitors: [{ model: "existing" }],
    startCount: 0,
    _ddcRunning: false,
    ddcProc: {},
  };

  Object.defineProperty(ctx.ddcProc, "running", {
    get() {
      return ctx._ddcRunning;
    },
    set(value) {
      if (value && !ctx._ddcRunning) {
        ctx.startCount++;
      }
      ctx._ddcRunning = value;
    },
  });

  Object.assign(ctx, overrides);
  return ctx;
}

function testDdcDetectionRequestDoesNotStartWhenSupportDisabled() {
  const requestDdcDetection = qmlFunction("requestDdcDetection", "clearExisting");
  const ctx = createDdcDetectionContext();
  ctx.Settings.data.brightness.enableDdcSupport = false;

  requestDdcDetection(ctx, true);

  assert.equal(ctx.startCount, 0);
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.equal(ctx.ddcDetectionPending, false);
}

function testDdcDetectionRequestStartsProcessAndClearsWhenRequested() {
  const requestDdcDetection = qmlFunction("requestDdcDetection", "clearExisting");
  const ctx = createDdcDetectionContext();

  requestDdcDetection(ctx, true);

  assert.equal(ctx.startCount, 1);
  assert.deepEqual(ctx.ddcMonitors, []);
  assert.equal(ctx.ddcDetectionPending, false);
}

function testDdcDetectionRequestWhileRunningDoesNotStartOrClearAgain() {
  const requestDdcDetection = qmlFunction("requestDdcDetection", "clearExisting");
  const ctx = createDdcDetectionContext();
  ctx.ddcProc.running = true;
  ctx.ddcMonitors = [{ model: "existing" }];

  requestDdcDetection(ctx, true);

  assert.equal(ctx.startCount, 1);
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.equal(ctx.ddcDetectionPending, false);
}

function testDdcDetectionFinishConsumesPendingRequestOnce() {
  const requestDdcDetection = qmlFunction("requestDdcDetection", "clearExisting");
  const finishDdcDetection = qmlFunction("finishDdcDetection");
  const ctx = createDdcDetectionContext();
  ctx.ddcDetectionCompletedOnce = true;
  ctx.ddcProc.running = true;
  ctx.requestDdcDetection = clearExisting => requestDdcDetection(ctx, clearExisting);

  requestDdcDetection(ctx, true);
  ctx.ddcProc.running = false;
  finishDdcDetection(ctx);
  ctx.ddcProc.running = false;
  finishDdcDetection(ctx);

  assert.equal(ctx.startCount, 2);
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.equal(ctx.ddcDetectionPending, false);
  assert.equal(ctx.ddcDetectionCompletedOnce, true);
}

function createMonitorContext(overrides = {}) {
  const commands = [];
  const timerRestarts = [];
  const ctx = {
    brightness: 0.4,
    busNum: "4",
    ignoreNextChange: false,
    isAppleDisplay: false,
    isDdc: false,
    minBrightnessValue: 0.01,
    published: [],
    queuedBrightness: Number.NaN,
    publishBrightnessUpdate() {
      this.published.push(this.brightness);
    },
    timer: {
      running: false,
      restart() {
        timerRestarts.push("restart");
      },
    },
    Quickshell: {
      execDetached(command) {
        commands.push(command);
      },
    },
  };
  Object.assign(ctx, overrides);
  ctx.monitor = ctx;
  return { ctx, commands, timerRestarts };
}

function testMonitorSetBrightnessRoutesInternalBacklightCommand() {
  const setBrightness = qmlMonitorFunction("setBrightness", "value");
  const { ctx, commands, timerRestarts } = createMonitorContext();

  setBrightness(ctx, 0.456);

  assert.equal(ctx.brightness, 0.456);
  assert.equal(ctx.ignoreNextChange, true);
  assert.deepEqual(ctx.published, [0.456]);
  assert.deepEqual(commands, [["brightnessctl", "s", "46%"]]);
  assert.deepEqual(timerRestarts, [], "internal backlight updates must not start the DDC debounce timer");
}

function testMonitorSetBrightnessRoutesDdcCommandAndRestartsTimer() {
  const setBrightness = qmlMonitorFunction("setBrightness", "value");
  const { ctx, commands, timerRestarts } = createMonitorContext({ isDdc: true });

  setBrightness(ctx, 0.456);

  assert.equal(ctx.brightness, 0.456);
  assert.equal(ctx.ignoreNextChange, true);
  assert.deepEqual(ctx.published, [0.456]);
  assert.deepEqual(commands, [["ddcutil", "-b", "4", "setvcp", "10", 46]]);
  assert.deepEqual(timerRestarts, ["restart"]);
}

function testMonitorSetBrightnessRoutesAppleDisplayCommand() {
  const setBrightness = qmlMonitorFunction("setBrightness", "value");
  const { ctx, commands, timerRestarts } = createMonitorContext({ isAppleDisplay: true });

  setBrightness(ctx, 0.456);

  assert.equal(ctx.brightness, 0.456);
  assert.equal(ctx.ignoreNextChange, true);
  assert.deepEqual(ctx.published, [0.456]);
  assert.deepEqual(commands, [["asdbctl", "set", 46]]);
  assert.deepEqual(timerRestarts, [], "Apple display updates must not start the DDC debounce timer");
}

function testMonitorSetBrightnessClampsToConfiguredBounds() {
  const setBrightness = qmlMonitorFunction("setBrightness", "value");
  const low = createMonitorContext();
  const high = createMonitorContext();

  setBrightness(low.ctx, -1);
  setBrightness(high.ctx, 2);

  assert.equal(low.ctx.brightness, 0.01);
  assert.deepEqual(low.commands, [["brightnessctl", "s", "1%"]]);
  assert.equal(high.ctx.brightness, 1);
  assert.deepEqual(high.commands, [["brightnessctl", "s", "100%"]]);
}

function testMonitorSetBrightnessQueuesWhileDebouncing() {
  const setBrightness = qmlMonitorFunction("setBrightness", "value");
  const { ctx, commands, timerRestarts } = createMonitorContext({
    brightness: 0.4,
    isDdc: true,
  });
  ctx.timer.running = true;

  setBrightness(ctx, 0.7);

  assert.equal(ctx.brightness, 0.4);
  assert.equal(ctx.queuedBrightness, 0.7);
  assert.equal(ctx.ignoreNextChange, false);
  assert.deepEqual(ctx.published, []);
  assert.deepEqual(commands, []);
  assert.deepEqual(timerRestarts, []);
}

const tests = [
  testBrightnessServiceAvailableMethodsReflectsConfiguredDisplays,
  testBrightnessServiceScreenLookupFindsMatchingMonitor,
  testBrightnessServiceIncreaseBrightnessDelegatesToEveryMonitor,
  testBrightnessServiceDecreaseBrightnessDelegatesToEveryMonitor,
  testBrightnessServiceDetectedDisplaysPassThrough,
  testDdcDetectionRequestDoesNotStartWhenSupportDisabled,
  testDdcDetectionRequestStartsProcessAndClearsWhenRequested,
  testDdcDetectionRequestWhileRunningDoesNotStartOrClearAgain,
  testDdcDetectionFinishConsumesPendingRequestOnce,
  testMonitorSetBrightnessRoutesInternalBacklightCommand,
  testMonitorSetBrightnessRoutesDdcCommandAndRestartsTimer,
  testMonitorSetBrightnessRoutesAppleDisplayCommand,
  testMonitorSetBrightnessClampsToConfiguredBounds,
  testMonitorSetBrightnessQueuesWhileDebouncing,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
