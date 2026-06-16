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

const tests = [
  testDarkModeParseTime,
  testDarkModeCollectManualChanges,
  testDarkModeCollectWeatherChangesIncludesPreSunriseState,
  testDarkModeApplyCurrentModeUsesLastPastChange,
  testDarkModeScheduleNextModeUsesNextFutureChange,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
