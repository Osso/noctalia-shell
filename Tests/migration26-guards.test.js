#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Commons/Migrations/Migration26.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    entries: [],
    i(...args) {
      this.entries.push(args);
    },
  };
}

function testMigration26ReplacesLegacyCalendarCardsAndPreservesOtherCards() {
  const migrate = qmlFunction("migrate", "adapter", "logger");
  const adapter = {
    calendar: {
      cards: [
        { id: "timer-card", enabled: true },
        { id: "banner-card", enabled: false },
        { id: "weather-card", enabled: false },
        { id: "calendar-card", enabled: true },
      ],
    },
  };
  const logger = createLogger();

  assert.equal(migrate({}, adapter, logger), true);

  assert.deepEqual(adapter.calendar.cards, [
    { id: "calendar-header-card", enabled: true },
    { id: "calendar-month-card", enabled: true },
    { id: "timer-card", enabled: true },
    { id: "weather-card", enabled: false },
  ]);
  assert.deepEqual(logger.entries, [
    ["Settings", "Migrating settings to v26"],
    ["Settings", "Replaced old calendar cards with calendar-header-card + calendar-month-card"],
  ]);
}

function testMigration26DisablesSplitCardsWhenLegacyCalendarCardsWereDisabled() {
  const migrate = qmlFunction("migrate", "adapter", "logger");
  const adapter = {
    calendar: {
      cards: [
        { id: "banner-card", enabled: false },
        { id: "calendar-card", enabled: false },
      ],
    },
  };

  migrate({}, adapter, createLogger());

  assert.deepEqual(adapter.calendar.cards, [
    { id: "calendar-header-card", enabled: false },
    { id: "calendar-month-card", enabled: false },
  ]);
}

function testMigration26LeavesMissingCalendarConfigUntouched() {
  const migrate = qmlFunction("migrate", "adapter", "logger");
  const adapter = {
    other: true,
  };
  const logger = createLogger();

  assert.equal(migrate({}, adapter, logger), true);

  assert.deepEqual(adapter, { other: true });
  assert.deepEqual(logger.entries, [["Settings", "Migrating settings to v26"]]);
}

const tests = [
  testMigration26ReplacesLegacyCalendarCardsAndPreservesOtherCards,
  testMigration26DisablesSplitCardsWhenLegacyCalendarCardsWereDisabled,
  testMigration26LeavesMissingCalendarConfigUntouched,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
