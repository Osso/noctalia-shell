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
    LocationService: {
      coordinatesReady: true,
      stableLatitude: 32.78,
      stableLongitude: -96.8,
    },
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

function testAutomaticScheduleWaitsForCoordinates() {
  const ctx = createContext({ autoSchedule: true });
  ctx.LocationService.coordinatesReady = false;
  ctx.lastCommand = [];
  ctx.runner = { running: false };
  ctx.staleCleanup = { running: false, command: [] };
  ctx.cleanupPending = false;
  ctx.buildCommand = () => qmlFunction("buildCommand")(ctx);
  ctx.buildStaleWlsunsetCleanupCommand = () => qmlFunction("buildStaleWlsunsetCleanupCommand")(ctx);

  qmlFunction("apply")(ctx);

  assert.deepEqual(ctx.lastCommand, []);
  assert.equal(ctx.runner.running, false);
  assert.equal(ctx.staleCleanup.running, false);
  assert.equal(ctx.cleanupPending, false);
}

function testStopNightLightRunnerClearsRunningState() {
  const ctx = { runner: { running: true } };

  qmlFunction("stopNightLightRunner")(ctx);

  assert.equal(ctx.runner.running, false);
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

const tests = [
  testBuildCommandUsesManualSchedule,
  testBuildCommandUsesCoordinatesForAutoSchedule,
  testBuildCommandUsesForcedAllDayNightSettings,
  testAutomaticScheduleWaitsForCoordinates,
  testStopNightLightRunnerClearsRunningState,
  testSettingsSignalHandlersApplyAndToast,
  testCoordinatesReadyHandlerAppliesWhenReady,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
