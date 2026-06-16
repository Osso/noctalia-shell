#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Location/CalendarService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function logger() {
  const messages = [];
  return {
    messages,
    d(...args) {
      messages.push(["d", ...args]);
    },
  };
}

function testCalendarSaveCacheDebouncesWrites() {
  const saveCache = qmlFunction("saveCache");
  let restarts = 0;
  const ctx = {
    saveDebounce: {
      restart() {
        restarts++;
      },
    },
  };

  saveCache(ctx);

  assert.equal(restarts, 1);
}

function testCalendarLoadFromCacheCopiesAvailableData() {
  const loadFromCache = qmlFunction("loadFromCache");
  const log = logger();
  const cachedEvents = [{ title: "Standup" }];
  const cachedCalendars = [{ name: "Work" }];
  const ctx = {
    root: {
      events: [],
      calendars: [],
    },
    cacheAdapter: {
      cachedEvents,
      cachedCalendars,
      lastUpdate: "2026-06-15T12:00:00Z",
    },
    Logger: log,
  };

  loadFromCache(ctx);

  assert.equal(ctx.root.events, cachedEvents);
  assert.equal(ctx.root.calendars, cachedCalendars);
  assert.deepEqual(log.messages, [
    ["d", "Calendar", "Loaded 1 cached event(s)"],
    ["d", "Calendar", "Loaded 1 cached calendar(s)"],
    ["d", "Calendar", "Cache last updated: 2026-06-15T12:00:00Z"],
  ]);
}

function testCalendarAvailabilityAndCalendarLoadingGuards() {
  const checkAvailability = qmlFunction("checkAvailability");
  const loadCalendars = qmlFunction("loadCalendars");
  const ctx = {
    Settings: {
      data: {
        location: {
          showCalendarEvents: false,
        },
      },
    },
    root: {
      available: true,
    },
    availabilityCheckProcess: {
      running: false,
    },
    listCalendarsProcess: {
      running: false,
    },
  };

  checkAvailability(ctx);
  assert.equal(ctx.root.available, false);
  assert.equal(ctx.availabilityCheckProcess.running, false);

  ctx.Settings.data.location.showCalendarEvents = true;
  checkAvailability(ctx);
  assert.equal(ctx.availabilityCheckProcess.running, true);

  loadCalendars(ctx);
  assert.equal(ctx.listCalendarsProcess.running, true);
}

function testCalendarLoadEventsDisabledAndConcurrentGuards() {
  const loadEvents = qmlFunction("loadEvents", "daysAhead", "daysBehind");
  const ctx = {
    Settings: {
      data: {
        location: {
          showCalendarEvents: false,
        },
      },
    },
    root: {
      loading: true,
      events: [{ title: "old" }],
    },
    loading: true,
    loadEventsProcess: {
      running: false,
    },
  };

  loadEvents(ctx, 31, 14);
  assert.equal(ctx.root.loading, false);
  assert.deepEqual(ctx.root.events, []);
  assert.equal(ctx.loadEventsProcess.running, false);

  ctx.Settings.data.location.showCalendarEvents = true;
  ctx.loading = true;
  ctx.root.loading = true;
  loadEvents(ctx, 31, 14);
  assert.equal(ctx.loadEventsProcess.running, false);
}

function testCalendarLoadEventsStartsProcessWithWindow() {
  const loadEvents = qmlFunction("loadEvents", "daysAhead", "daysBehind");
  const log = logger();
  const before = Math.floor(Date.now() / 1000);
  const ctx = {
    Settings: {
      data: {
        location: {
          showCalendarEvents: true,
        },
      },
    },
    Logger: log,
    root: {},
    loading: false,
    lastError: "old error",
    loadEventsProcess: {
      startTime: 0,
      endTime: 0,
      running: false,
    },
  };

  loadEvents(ctx, 2, 1);
  const after = Math.floor(Date.now() / 1000);

  assert.equal(ctx.loading, true);
  assert.equal(ctx.lastError, "");
  assert.equal(ctx.loadEventsProcess.running, true);
  assert.ok(ctx.loadEventsProcess.startTime >= before - 86400 - 1);
  assert.ok(ctx.loadEventsProcess.startTime <= after - 86400 + 1);
  assert.ok(ctx.loadEventsProcess.endTime >= before + (2 * 86400) - 1);
  assert.ok(ctx.loadEventsProcess.endTime <= after + (2 * 86400) + 1);
  assert.match(log.messages[0][2], /Loading events \(1 days behind, 2 days ahead\):/);
}

function testCalendarFormatDateTimeDelegatesToQt() {
  const formatDateTime = qmlFunction("formatDateTime", "timestamp");
  const seen = [];
  const ctx = {
    Qt: {
      formatDateTime(date, format) {
        seen.push([date.getTime(), format]);
        return "formatted";
      },
    },
  };

  assert.equal(formatDateTime(ctx, 42), "formatted");
  assert.deepEqual(seen, [[42000, "yyyy-MM-dd hh:mm"]]);
}

const tests = [
  testCalendarSaveCacheDebouncesWrites,
  testCalendarLoadFromCacheCopiesAvailableData,
  testCalendarAvailabilityAndCalendarLoadingGuards,
  testCalendarLoadEventsDisabledAndConcurrentGuards,
  testCalendarLoadEventsStartsProcessWithWindow,
  testCalendarFormatDateTimeDelegatesToQt,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
