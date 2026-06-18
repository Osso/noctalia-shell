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

function testCalendarProcessParsingAndFallbacks() {
  assert.match(source, /function handleCalendarsOutput\(output\)/, "calendar list stdout helper must type raw output");
  assert.match(source, /function handleEventsOutput\(output\)/, "event stdout helper must type raw output");
  assert.match(source, /function handleEventsError\(output\)/, "event stderr helper must type raw output");
  assert.match(source, /root\.handleCalendarsOutput\(text\)/, "calendar list process must route stdout through helper");
  assert.match(source, /root\.handleEventsOutput\(text\)/, "event process must route stdout through helper");
  assert.match(source, /root\.handleEventsError\(text\)/, "event process must route stderr through helper");

  const handleCalendarsOutput = qmlFunction("handleCalendarsOutput", "output");
  const handleEventsOutput = qmlFunction("handleEventsOutput", "output");
  const handleEventsError = qmlFunction("handleEventsError", "output");
  const log = logger();
  const saveCalls = [];
  const loadCalls = [];
  const ctx = {
    root: null,
    calendars: [],
    events: [],
    loading: true,
    lastError: "",
    cacheAdapter: {
      cachedCalendars: [],
      cachedEvents: [{ title: "cached" }],
      lastUpdate: "",
    },
    Logger: log,
    saveCache() {
      saveCalls.push("save");
    },
    loadEvents() {
      loadCalls.push("load");
    },
  };
  ctx.root = ctx;

  handleCalendarsOutput(ctx, JSON.stringify([{ name: "Work" }]));

  assert.deepEqual(ctx.calendars, [{ name: "Work" }]);
  assert.deepEqual(ctx.cacheAdapter.cachedCalendars, [{ name: "Work" }]);
  assert.deepEqual(saveCalls, ["save"]);
  assert.deepEqual(loadCalls, ["load"]);

  handleEventsOutput(ctx, JSON.stringify([{ title: "Meeting" }]));

  assert.equal(ctx.loading, false);
  assert.deepEqual(ctx.events, [{ title: "Meeting" }]);
  assert.deepEqual(ctx.cacheAdapter.cachedEvents, [{ title: "Meeting" }]);
  assert.match(ctx.cacheAdapter.lastUpdate, /^\d{4}-\d{2}-\d{2}T/);
  assert.deepEqual(saveCalls, ["save", "save"]);

  ctx.loading = true;
  ctx.cacheAdapter.cachedEvents = [{ title: "fallback" }];
  handleEventsOutput(ctx, "{not json");

  assert.equal(ctx.loading, false);
  assert.equal(ctx.lastError, "Failed to parse events");
  assert.deepEqual(ctx.events, [{ title: "fallback" }], "parse failure must restore cached events");

  ctx.loading = true;
  handleEventsError(ctx, "backend failed\n");

  assert.equal(ctx.loading, false);
  assert.equal(ctx.lastError, "backend failed");
  assert.deepEqual(ctx.events, [{ title: "fallback" }], "stderr failure must preserve cached events");

  const logs = log.messages.map(message => message.slice(1).join(" "));
  assert.ok(logs.some(message => message.includes("Found 1 calendar(s)")), "calendar parse must log count");
  assert.ok(logs.some(message => message.includes("Loaded 1 event(s)")), "event parse must log count");
  assert.ok(logs.some(message => message.includes("Using cached events")), "parse fallback must log cached events");
  assert.ok(logs.some(message => message.includes("Using cached events due to error")), "stderr fallback must log cached events");
}

const tests = [
  testCalendarSaveCacheDebouncesWrites,
  testCalendarLoadFromCacheCopiesAvailableData,
  testCalendarAvailabilityAndCalendarLoadingGuards,
  testCalendarLoadEventsDisabledAndConcurrentGuards,
  testCalendarLoadEventsStartsProcessWithWindow,
  testCalendarFormatDateTimeDelegatesToQt,
  testCalendarProcessParsingAndFallbacks,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
