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
  const warnings = [];
  const ctx = {
    Settings: {
      data: {
        brightness: {
          enableDdcSupport: true,
        },
      },
    },
    ddcDetectionPending: false,
    ddcDetectionGeneration: 0,
    ddcMonitors: [{ model: "existing" }],
    startCount: 0,
    _ddcRunning: false,
    ddcProc: { generation: 0 },
    Logger: {
      i() {},
      w(...args) {
        warnings.push(args.join(" "));
      },
    },
  };
  ctx.warnings = warnings;
  ctx.hasMalformedDdcMonitor = detectedMonitors => qmlFunction("hasMalformedDdcMonitor", "detectedMonitors")(ctx, detectedMonitors);

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
  const requestDdcDetection = qmlFunction("requestDdcDetection");
  const ctx = createDdcDetectionContext();
  ctx.Settings.data.brightness.enableDdcSupport = false;

  requestDdcDetection(ctx);

  assert.equal(ctx.startCount, 0);
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.equal(ctx.ddcDetectionPending, false);
}

function testDdcDetectionRequestStartsProcessAndPreservesKnownMonitors() {
  const requestDdcDetection = qmlFunction("requestDdcDetection");
  const ctx = createDdcDetectionContext();

  requestDdcDetection(ctx);

  assert.equal(ctx.startCount, 1);
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }], "existing monitors remain until successful replacement");
  assert.equal(ctx.ddcDetectionGeneration, 1);
  assert.equal(ctx.ddcProc.generation, 1);
  assert.equal(ctx.ddcDetectionPending, false);
}

function testDdcDetectionRequestWhileRunningCoalescesIncludingInitialDetection() {
  const requestDdcDetection = qmlFunction("requestDdcDetection");
  const ctx = createDdcDetectionContext();
  ctx.ddcProc.running = true;
  ctx.ddcMonitors = [{ model: "existing" }];

  requestDdcDetection(ctx);

  assert.equal(ctx.startCount, 1);
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.equal(ctx.ddcDetectionPending, true);
}

function testDdcDetectionFinishConsumesPendingRequestOnce() {
  const requestDdcDetection = qmlFunction("requestDdcDetection");
  const finishDdcDetection = qmlFunction("finishDdcDetection", "generation", "exitCode", "output", "errorOutput");
  const restartPendingDdcDetection = qmlFunction("restartPendingDdcDetection");
  const ctx = createDdcDetectionContext();
  ctx.ddcProc.running = true;
  ctx.requestDdcDetection = () => requestDdcDetection(ctx);
  ctx.root = ctx;

  requestDdcDetection(ctx);
  const completedGeneration = ctx.ddcDetectionGeneration;
  ctx.ddcProc.running = false;
  finishDdcDetection(ctx, completedGeneration, 1, "", "detection failed");
  restartPendingDdcDetection(ctx);
  restartPendingDdcDetection(ctx);

  assert.equal(ctx.startCount, 2);
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.equal(ctx.ddcDetectionPending, false);
}

function testDdcStaleCompletionAfterDisableReenableRestartsPendingDetection() {
  const requestDdcDetection = qmlFunction("requestDdcDetection");
  const finishDdcDetection = qmlFunction("finishDdcDetection", "generation", "exitCode", "output", "errorOutput");
  const restartPendingDdcDetection = qmlFunction("restartPendingDdcDetection");
  const ctx = createDdcDetectionContext();
  ctx.root = ctx;
  ctx.ddcDetectionGeneration = 2;
  ctx.ddcProc.generation = 1;
  ctx.ddcProc.running = true;
  ctx.requestDdcDetection = () => requestDdcDetection(ctx);

  requestDdcDetection(ctx);
  assert.equal(ctx.ddcDetectionPending, true);
  finishDdcDetection(ctx, 1, 0, "stale", "");
  assert.equal(ctx.ddcDetectionPending, true);

  ctx.ddcProc.running = false;
  restartPendingDdcDetection(ctx);
  assert.equal(ctx.ddcDetectionPending, false);
  assert.equal(ctx.ddcDetectionGeneration, 3);
  assert.equal(ctx.ddcProc.generation, 3);
  assert.equal(ctx.startCount, 2);
}

function testDdcMalformedPredicateDistinguishesUnsupportedDisplays() {
  const hasMalformedDdcMonitor = qmlFunction("hasMalformedDdcMonitor", "detectedMonitors");

  assert.equal(hasMalformedDdcMonitor({}, [{ model: "Unknown", busNum: "Unknown", isDdc: false }]), false);
  assert.equal(hasMalformedDdcMonitor({}, [{ model: "Unknown", busNum: "Unknown", isDdc: true }]), true);
  assert.equal(hasMalformedDdcMonitor({}, [{ model: "LG", busNum: "4", isDdc: true }]), false);
}

function testDdcDetectionSuccessReplacesMonitorsAndFailurePreservesThem() {
  const finishDdcDetection = qmlFunction("finishDdcDetection", "generation", "exitCode", "output", "errorOutput");
  const ctx = createDdcDetectionContext();
  ctx.root = ctx;
  ctx.BrightnessParsing = {
    parseDdcMonitors() {
      return [
        { model: "LG", busNum: "4", isDdc: true },
        { model: "Unsupported", busNum: "5", isDdc: false },
      ];
    },
  };
  ctx.requestDdcDetection = () => {};

  finishDdcDetection(ctx, 0, 0, "valid output", "");
  assert.deepEqual(ctx.ddcMonitors, [{ model: "LG", busNum: "4", isDdc: true }]);

  finishDdcDetection(ctx, 0, 1, "", "permission denied");
  assert.deepEqual(ctx.ddcMonitors, [{ model: "LG", busNum: "4", isDdc: true }]);
  assert.match(ctx.warnings.at(-1), /permission denied/);
}

function testDdcMalformedAndDisabledCompletionsPreserveState() {
  const finishDdcDetection = qmlFunction("finishDdcDetection", "generation", "exitCode", "output", "errorOutput");
  const ctx = createDdcDetectionContext();
  ctx.root = ctx;
  ctx.requestDdcDetection = () => {};
  ctx.BrightnessParsing = {
    parseDdcMonitors() {
      return [{ model: "Unknown", busNum: "Unknown", isDdc: true }];
    },
  };

  finishDdcDetection(ctx, 0, 0, "garbage", "");
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.match(ctx.warnings.at(-1), /malformed/i);

  const warningCount = ctx.warnings.length;
  ctx.Settings.data.brightness.enableDdcSupport = false;
  finishDdcDetection(ctx, 0, 0, "valid but stale", "");
  assert.deepEqual(ctx.ddcMonitors, [{ model: "existing" }]);
  assert.equal(ctx.warnings.length, warningCount);
}

function testDdcUnsupportedOnlySuccessClearsKnownMonitors() {
  const finishDdcDetection = qmlFunction("finishDdcDetection", "generation", "exitCode", "output", "errorOutput");
  const ctx = createDdcDetectionContext();
  ctx.root = ctx;
  ctx.requestDdcDetection = () => {};
  ctx.BrightnessParsing = {
    parseDdcMonitors() {
      return [{ model: "Unsupported", busNum: "5", isDdc: false }];
    },
  };

  finishDdcDetection(ctx, 0, 0, "unsupported display", "");
  assert.deepEqual(ctx.ddcMonitors, []);
}

function testDdcDetectionStartFailureExecutesWithoutExitedSignal() {
  const handleDdcStartFailure = qmlFunction("handleDdcStartFailure", "generation", "exitObserved");
  const finishDdcDetection = qmlFunction("finishDdcDetection", "generation", "exitCode", "output", "errorOutput");
  const ctx = createDdcDetectionContext();
  ctx.root = ctx;
  ctx.requestDdcDetection = () => {};
  ctx.finishDdcDetection = (generation, exitCode, output, errorOutput) => finishDdcDetection(ctx, generation, exitCode, output, errorOutput);

  handleDdcStartFailure(ctx, 0, false);
  assert.match(ctx.warnings.at(-1), /failed to start/);

  const warningCount = ctx.warnings.length;
  handleDdcStartFailure(ctx, 0, true);
  assert.equal(ctx.warnings.length, warningCount);
}

function testDdcProcessRoutesExitAndStartFailure() {
  assert.match(source, /id:\s*ddcProc[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?finishDdcDetection/);
  assert.match(source, /id:\s*ddcProc[\s\S]*?onRunningChanged:\s*\{[\s\S]*?handleDdcStartFailure[\s\S]*?exitObserved = false[\s\S]*?restartPendingDdcDetection/);
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
  testDdcDetectionRequestStartsProcessAndPreservesKnownMonitors,
  testDdcDetectionRequestWhileRunningCoalescesIncludingInitialDetection,
  testDdcDetectionFinishConsumesPendingRequestOnce,
  testDdcStaleCompletionAfterDisableReenableRestartsPendingDetection,
  testDdcMalformedPredicateDistinguishesUnsupportedDisplays,
  testDdcDetectionSuccessReplacesMonitorsAndFailurePreservesThem,
  testDdcMalformedAndDisabledCompletionsPreserveState,
  testDdcUnsupportedOnlySuccessClearsKnownMonitors,
  testDdcDetectionStartFailureExecutesWithoutExitedSignal,
  testDdcProcessRoutesExitAndStartFailure,
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
