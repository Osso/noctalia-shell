#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Location/DarkModeService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function withFrozenNow(timestamp, fn) {
  const originalNow = Date.now;
  Date.now = () => timestamp;
  try {
    return fn();
  } finally {
    Date.now = originalNow;
  }
}

function logger() {
  const messages = [];
  return {
    messages,
    d(...args) {
      messages.push(args);
    },
  };
}

function testDarkModeParseTime() {
  const parseTime = qmlFunction("parseTime", "timeString");

  assert.deepEqual(parseTime({}, "06:30"), { hour: 6, minute: 30 });
  assert.deepEqual(parseTime({}, "18:05"), { hour: 18, minute: 5 });
}

function testDarkModeCollectManualChanges() {
  const parseTime = qmlFunction("parseTime", "timeString");
  const collectManualChanges = qmlFunction("collectManualChanges");
  const ctx = {
    Settings: {
      data: {
        colorSchemes: {
          manualSunrise: "06:30",
          manualSunset: "18:15",
        },
      },
    },
    parseTime(timeString) {
      return parseTime(ctx, timeString);
    },
  };

  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const day = now.getDate();
  const changes = collectManualChanges(ctx);

  assert.deepEqual(changes, [
    { time: new Date(year, month, day - 1, 18, 15).getTime(), darkMode: true },
    { time: new Date(year, month, day, 6, 30).getTime(), darkMode: false },
    { time: new Date(year, month, day, 18, 15).getTime(), darkMode: true },
    { time: new Date(year, month, day + 1, 6, 30).getTime(), darkMode: false },
  ]);
}

function testDarkModeCollectWeatherChangesIncludesPreSunriseState() {
  const collectWeatherChanges = qmlFunction("collectWeatherChanges", "weather");
  const sunrise = "2026-06-16T12:00:00.000Z";
  const sunset = "2026-06-17T00:00:00.000Z";
  const beforeSunrise = Date.parse("2026-06-16T11:00:00.000Z");
  const ctx = {};

  const changes = withFrozenNow(beforeSunrise, () => collectWeatherChanges(ctx, {
    daily: {
      sunrise: [sunrise],
      sunset: [sunset],
    },
  }));

  assert.deepEqual(changes, [
    { time: beforeSunrise - 1, darkMode: true },
    { time: Date.parse(sunrise), darkMode: false },
    { time: Date.parse(sunset), darkMode: true },
  ]);
}

function testDarkModeApplyCurrentModeUsesLastPastChange() {
  const applyCurrentMode = qmlFunction("applyCurrentMode", "changes");
  const log = logger();
  const ctx = {
    Settings: {
      data: {
        colorSchemes: {
          darkMode: false,
        },
      },
    },
    Logger: log,
  };
  const now = 1000;

  withFrozenNow(now, () => applyCurrentMode(ctx, [
    { time: 100, darkMode: true },
    { time: 900, darkMode: false },
    { time: 1200, darkMode: true },
  ]));

  assert.equal(ctx.Settings.data.colorSchemes.darkMode, false);
  assert.deepEqual(log.messages, [["DarkModeService", "Reset: darkmode=false"]]);

  log.messages.length = 0;
  ctx.Settings.data.colorSchemes.darkMode = true;
  withFrozenNow(now, () => applyCurrentMode(ctx, [{ time: 1200, darkMode: false }]));
  assert.equal(ctx.Settings.data.colorSchemes.darkMode, true);
  assert.deepEqual(log.messages, []);
}

function testDarkModeScheduleNextModeUsesNextFutureChange() {
  const scheduleNextMode = qmlFunction("scheduleNextMode", "changes");
  const log = logger();
  let restarts = 0;
  const ctx = {
    root: {
      nextDarkModeState: false,
    },
    timer: {
      interval: 0,
      restart() {
        restarts++;
      },
    },
    Logger: log,
  };
  const now = 1000;

  withFrozenNow(now, () => scheduleNextMode(ctx, [
    { time: 500, darkMode: false },
    { time: 1500, darkMode: true },
    { time: 2000, darkMode: false },
  ]));

  assert.equal(ctx.root.nextDarkModeState, true);
  assert.equal(ctx.timer.interval, 500);
  assert.equal(restarts, 1);
  assert.deepEqual(log.messages, [["DarkModeService", "Scheduled: darkmode=true in 500 ms"]]);

  withFrozenNow(now, () => scheduleNextMode(ctx, [{ time: 500, darkMode: false }]));
  assert.equal(restarts, 1);
}

function testDarkModeInitSelectsManualAndLocationScheduling() {
  const init = qmlFunction("init");
  const calls = [];
  const manualChanges = [{ time: 100, darkMode: false }];
  const weatherChanges = [{ time: 200, darkMode: true }];
  const weather = {
    daily: {
      sunrise: ["2026-06-16T12:00:00.000Z"],
      sunset: ["2026-06-17T00:00:00.000Z"],
    },
  };
  const ctx = {
    initComplete: false,
    Settings: {
      data: {
        colorSchemes: {
          schedulingMode: "manual",
        },
      },
    },
    LocationService: {
      data: {
        weather,
      },
    },
    Logger: {
      i(...args) {
        calls.push(["log", ...args]);
      },
    },
    collectManualChanges() {
      calls.push(["manual"]);
      return manualChanges;
    },
    collectWeatherChanges(value) {
      calls.push(["weather", value]);
      return weatherChanges;
    },
    applyCurrentMode(changes) {
      calls.push(["apply", changes]);
    },
    scheduleNextMode(changes) {
      calls.push(["schedule", changes]);
    },
  };

  init(ctx);
  assert.equal(ctx.initComplete, true);
  assert.deepEqual(calls, [
    ["log", "DarkModeService", "Service started"],
    ["manual"],
    ["apply", manualChanges],
    ["schedule", manualChanges],
  ]);

  calls.length = 0;
  ctx.initComplete = false;
  ctx.Settings.data.colorSchemes.schedulingMode = "location";
  init(ctx);
  assert.equal(ctx.initComplete, true);
  assert.deepEqual(calls, [
    ["log", "DarkModeService", "Service started"],
    ["weather", weather],
    ["apply", weatherChanges],
    ["schedule", weatherChanges],
  ]);

  calls.length = 0;
  ctx.initComplete = false;
  ctx.LocationService.data.weather = null;
  init(ctx);
  assert.equal(ctx.initComplete, false);
  assert.deepEqual(calls, [["log", "DarkModeService", "Service started"]]);
}

function testDarkModeTimerTriggerAppliesNextStateAndReschedulesWeather() {
  const handleTimerTriggered = qmlFunction("handleTimerTriggered");
  const weather = {
    daily: {
      sunrise: ["2026-06-16T12:00:00.000Z"],
      sunset: ["2026-06-17T00:00:00.000Z"],
    },
  };
  const changes = [{ time: 200, darkMode: false }];
  const calls = [];
  const ctx = {
    nextDarkModeState: true,
    Settings: {
      data: {
        colorSchemes: {
          darkMode: false,
        },
      },
    },
    LocationService: {
      data: {
        weather,
      },
    },
    collectWeatherChanges(value) {
      calls.push(["weather", value]);
      return changes;
    },
    scheduleNextMode(value) {
      calls.push(["schedule", value]);
    },
  };

  handleTimerTriggered(ctx);
  assert.equal(ctx.Settings.data.colorSchemes.darkMode, true);
  assert.deepEqual(calls, [
    ["weather", weather],
    ["schedule", changes],
  ]);

  calls.length = 0;
  ctx.nextDarkModeState = false;
  ctx.LocationService.data.weather = null;
  handleTimerTriggered(ctx);
  assert.equal(ctx.Settings.data.colorSchemes.darkMode, false);
  assert.deepEqual(calls, []);
}

const tests = [
  testDarkModeParseTime,
  testDarkModeCollectManualChanges,
  testDarkModeCollectWeatherChangesIncludesPreSunriseState,
  testDarkModeApplyCurrentModeUsesLastPastChange,
  testDarkModeScheduleNextModeUsesNextFutureChange,
  testDarkModeInitSelectsManualAndLocationScheduling,
  testDarkModeTimerTriggerAppliesNextStateAndReschedulesWeather,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
