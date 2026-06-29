#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Location/NightLightService.qml");

function qmlFunction(functionName) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", `with (ctx) { return (function() ${body}).call(ctx); }`);
}

function createContext(params = {}) {
  return {
    params: {
      enabled: true,
      forced: false,
      autoSchedule: false,
      nightTemp: 3800,
      dayTemp: 6500,
      manualSunrise: "07:30",
      manualSunset: "19:45",
      ...params,
    },
    lastCommand: [],
    runner: {
      command: [],
      running: true,
    },
    LocationService: {
      coordinatesReady: true,
      stableLatitude: 32.78,
      stableLongitude: -96.8,
    },
    cleanupStaleWlsunset() {},
  };
}

function testBuildCommandUsesManualSchedule() {
  const buildCommand = qmlFunction("buildCommand");
  const ctx = createContext();

  assert.deepEqual(buildCommand(ctx), [
    "wlsunset",
    "-t",
    "3800",
    "-T",
    "6500",
    "-S",
    "07:30",
    "-s",
    "19:45",
    "-d",
    900,
  ]);
}

function testBuildCommandUsesCoordinatesForAutoSchedule() {
  const buildCommand = qmlFunction("buildCommand");
  const ctx = createContext({ autoSchedule: true });

  assert.deepEqual(buildCommand(ctx), [
    "wlsunset",
    "-t",
    "3800",
    "-T",
    "6500",
    "-l",
    "32.78",
    "-L",
    "-96.8",
    "-d",
    900,
  ]);
}

function testBuildCommandUsesForcedAllDayNightSettings() {
  const buildCommand = qmlFunction("buildCommand");
  const ctx = createContext({ forced: true, nightTemp: 3400, dayTemp: 6000 });

  assert.deepEqual(buildCommand(ctx), [
    "wlsunset",
    "-t",
    "3400",
    "-T",
    "6000",
    "-S",
    "23:59",
    "-s",
    "00:00",
    "-d",
    1,
  ]);
}

function testApplyWaitsForCoordinatesWhenAutoScheduleNeedsLocation() {
  const apply = qmlFunction("apply");
  const ctx = createContext({ autoSchedule: true });
  ctx.LocationService.coordinatesReady = false;
  ctx.buildCommand = () => {
    throw new Error("buildCommand should not run before coordinates are ready");
  };

  apply(ctx);

  assert.deepEqual(ctx.runner.command, []);
  assert.equal(ctx.runner.running, true);
}

function testApplyRestartsRunnerOnlyWhenCommandChanges() {
  const apply = qmlFunction("apply");
  const ctx = createContext();
  ctx.lastCommand = ["old"];
  ctx.buildCommand = () => ["new"];

  apply(ctx);

  assert.deepEqual(ctx.lastCommand, ["new"]);
  assert.deepEqual(ctx.runner.command, ["new"]);
  assert.equal(ctx.runner.running, true);

  ctx.runner.running = true;
  apply(ctx);

  assert.deepEqual(ctx.runner.command, ["new"]);
  assert.equal(ctx.runner.running, true);
}

function testApplyUsesEnabledFlagForRunnerState() {
  const apply = qmlFunction("apply");
  const ctx = createContext({ enabled: false });
  ctx.buildCommand = () => ["wlsunset"];

  apply(ctx);

  assert.equal(ctx.runner.running, false);
}

function testApplyCleansStaleWlsunsetBeforeEnablingRunner() {
  const apply = qmlFunction("apply");
  const calls = [];
  const ctx = createContext({ enabled: true });
  ctx.runner.running = false;
  ctx.buildCommand = () => ["wlsunset"];
  ctx.cleanupStaleWlsunset = () => {
    calls.push(["cleanup", ctx.runner.running]);
  };

  Object.defineProperty(ctx.runner, "running", {
    get() {
      return this.runningValue;
    },
    set(value) {
      calls.push(["runner", value]);
      this.runningValue = value;
    },
  });
  ctx.runner.runningValue = false;

  apply(ctx);

  assert.deepEqual(calls, [
    ["runner", false],
    ["cleanup", false],
    ["runner", true],
  ]);
}

function testStaleWlsunsetCleanupCommandTargetsOnlyNonQuickshellChildren() {
  const buildStaleWlsunsetCleanupCommand = qmlFunction("buildStaleWlsunsetCleanupCommand");
  const command = buildStaleWlsunsetCleanupCommand(createContext());
  const script = command[2];

  assert.deepEqual(command.slice(0, 2), ["sh", "-c"]);
  assert.match(script, /current_ppid="\$PPID"/);
  assert.match(script, /pgrep -x wlsunset/);
  assert.match(script, /ps -o ppid= -p "\$pid"/);
  assert.match(script, /\[ "\$ppid" != "\$current_ppid" \]/);
  assert.match(script, /kill "\$pid"/);
}

function testSettingsSignalHandlersApplyAndToast() {
  const onEnabledChanged = qmlFunction("onEnabledChanged");
  const onForcedChanged = qmlFunction("onForcedChanged");
  const onNightTempChanged = qmlFunction("onNightTempChanged");
  const onDayTempChanged = qmlFunction("onDayTempChanged");
  const calls = [];
  const ctx = {
    Settings: {
      data: {
        nightLight: {
          enabled: true,
          forced: false,
        },
      },
    },
    I18n: {
      tr(key) {
        return key;
      },
    },
    ToastService: {
      showNotice(...args) {
        calls.push(["toast", ...args]);
      },
    },
    apply() {
      calls.push(["apply"]);
    },
  };

  onEnabledChanged(ctx);
  assert.deepEqual(calls, [
    ["apply"],
    ["toast", "settings.display.night-light.section.label", "toast.night-light.enabled", "nightlight-on"],
  ]);

  calls.length = 0;
  ctx.Settings.data.nightLight.enabled = false;
  onEnabledChanged(ctx);
  assert.deepEqual(calls, [
    ["apply"],
    ["toast", "settings.display.night-light.section.label", "toast.night-light.disabled", "nightlight-off"],
  ]);

  calls.length = 0;
  ctx.Settings.data.nightLight.enabled = true;
  ctx.Settings.data.nightLight.forced = true;
  onForcedChanged(ctx);
  assert.deepEqual(calls, [
    ["apply"],
    ["toast", "settings.display.night-light.section.label", "toast.night-light.forced", "nightlight-forced"],
  ]);

  calls.length = 0;
  ctx.Settings.data.nightLight.enabled = false;
  onForcedChanged(ctx);
  assert.deepEqual(calls, [["apply"]]);

  calls.length = 0;
  onNightTempChanged(ctx);
  onDayTempChanged(ctx);
  assert.deepEqual(calls, [["apply"], ["apply"]]);
}

function testCoordinatesReadyHandlerAppliesWhenReady() {
  const onCoordinatesReadyChanged = qmlFunction("onCoordinatesReadyChanged");
  const calls = [];
  const ctx = {
    LocationService: {
      coordinatesReady: false,
    },
    apply() {
      calls.push("apply");
    },
  };

  onCoordinatesReadyChanged(ctx);
  assert.deepEqual(calls, []);

  ctx.LocationService.coordinatesReady = true;
  onCoordinatesReadyChanged(ctx);
  assert.deepEqual(calls, ["apply"]);
}

function testDestructionStopsNightLightRunner() {
  const stopNightLightRunner = qmlFunction("stopNightLightRunner");
  const ctx = createContext();

  stopNightLightRunner(ctx);

  assert.equal(ctx.runner.running, false);
  assert.match(
    source,
    /Component\.onDestruction:\s*stopNightLightRunner\(\)/,
    "NightLightService must stop wlsunset when the singleton is destroyed or reloaded",
  );
}

const tests = [
  testBuildCommandUsesManualSchedule,
  testBuildCommandUsesCoordinatesForAutoSchedule,
  testBuildCommandUsesForcedAllDayNightSettings,
  testApplyWaitsForCoordinatesWhenAutoScheduleNeedsLocation,
  testApplyRestartsRunnerOnlyWhenCommandChanges,
  testApplyUsesEnabledFlagForRunnerState,
  testApplyCleansStaleWlsunsetBeforeEnablingRunner,
  testStaleWlsunsetCleanupCommandTargetsOnlyNonQuickshellChildren,
  testSettingsSignalHandlersApplyAndToast,
  testCoordinatesReadyHandlerAppliesWhenReady,
  testDestructionStopsNightLightRunner,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
