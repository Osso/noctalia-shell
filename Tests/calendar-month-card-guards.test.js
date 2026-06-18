#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Cards/CalendarMonthCard.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function localDayStart(year, month, day) {
  return Math.floor(new Date(year, month, day).getTime() / 1000);
}

function testCalendarMonthIsoWeekNumberHandlesYearBoundaries() {
  const getISOWeekNumber = qmlFunction("getISOWeekNumber", "date");

  assert.equal(getISOWeekNumber({}, new Date(2026, 0, 1)), 1);
  assert.equal(getISOWeekNumber({}, new Date(2026, 11, 31)), 53);
  assert.equal(getISOWeekNumber({}, new Date(2027, 0, 1)), 53);
  assert.equal(getISOWeekNumber({}, new Date(2027, 0, 4)), 1);
}

function testCalendarMonthAllDayAndMultiDayClassification() {
  const isAllDayEvent = qmlFunction("isAllDayEvent", "event");
  const isMultiDayEvent = qmlFunction("isMultiDayEvent", "event");
  const dayStart = localDayStart(2026, 5, 15);
  const ctx = {
    root: {
      isAllDayEvent(event) {
        return isAllDayEvent(ctx, event);
      },
    },
  };

  assert.equal(isAllDayEvent(ctx, { start: dayStart, end: dayStart + 86400 }), true);
  assert.equal(isAllDayEvent(ctx, { start: dayStart + 3600, end: dayStart + 90000 }), false);
  assert.equal(isMultiDayEvent(ctx, { start: dayStart, end: dayStart + 86400 }), false);
  assert.equal(isMultiDayEvent(ctx, { start: dayStart + 3600, end: dayStart + 90000 }), true);
}

function testCalendarMonthEventsForDateFiltersOverlaps() {
  const getEventsForDate = qmlFunction("getEventsForDate", "year", "month", "day");
  const dayStart = localDayStart(2026, 5, 15);
  const previousDay = { id: "previous", start: dayStart - 7200, end: dayStart - 3600 };
  const startsInside = { id: "starts-inside", start: dayStart + 3600, end: dayStart + 7200 };
  const endsInside = { id: "ends-inside", start: dayStart - 3600, end: dayStart + 3600 };
  const spansDay = { id: "spans-day", start: dayStart - 3600, end: dayStart + 90000 };
  const nextDay = { id: "next", start: dayStart + 90000, end: dayStart + 93600 };
  const ctx = {
    CalendarService: {
      available: true,
      events: [previousDay, startsInside, endsInside, spansDay, nextDay],
    },
  };

  assert.deepEqual(getEventsForDate(ctx, 2026, 5, 15).map(event => event.id), [
    "starts-inside",
    "ends-inside",
    "spans-day",
  ]);

  ctx.CalendarService.available = false;
  assert.deepEqual(getEventsForDate(ctx, 2026, 5, 15), []);
}

function testCalendarMonthEventColorByEventKindAndToday() {
  const getEventColor = qmlFunction("getEventColor", "event", "isToday");
  const ctx = {
    Color: {
      mOnSecondary: "on-secondary",
      mTertiary: "tertiary",
      mSecondary: "secondary",
      mPrimary: "primary",
    },
    root: {
      isAllDayEvent(event) {
        return event.kind === "all-day";
      },
    },
    isMultiDayEvent(event) {
      return event.kind === "multi-day";
    },
  };

  assert.equal(getEventColor(ctx, { kind: "multi-day" }, false), "tertiary");
  assert.equal(getEventColor(ctx, { kind: "multi-day" }, true), "on-secondary");
  assert.equal(getEventColor(ctx, { kind: "all-day" }, false), "secondary");
  assert.equal(getEventColor(ctx, { kind: "timed" }, false), "primary");
}

function testCalendarMonthHelperInputsAreTyped() {
  assert.match(source, /function getISOWeekNumber\(date\)/, "getISOWeekNumber must type the date input");
  assert.match(source, /function hasEventsOnDate\(year, month, day\)/, "hasEventsOnDate must type calendar date inputs");
  assert.match(source, /function getEventsForDate\(year, month, day\)/, "getEventsForDate must type calendar date inputs");
  assert.match(source, /function getEventColor\(event, isToday\)/, "getEventColor must type the today flag");
}

const tests = [
  testCalendarMonthIsoWeekNumberHandlesYearBoundaries,
  testCalendarMonthAllDayAndMultiDayClassification,
  testCalendarMonthEventsForDateFiltersOverlaps,
  testCalendarMonthEventColorByEventKindAndToday,
  testCalendarMonthHelperInputsAreTyped,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
