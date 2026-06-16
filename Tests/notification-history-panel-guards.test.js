#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/NotificationHistory/NotificationHistoryPanel.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function listModel(items) {
  return {
    items,
    get count() {
      return this.items.length;
    },
    get(index) {
      return this.items[index];
    },
  };
}

function startOfToday() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function testNotificationHistoryDateOnlyClearsTime() {
  const dateOnly = qmlFunction("dateOnly", "d");
  const result = dateOnly({}, new Date(2026, 5, 16, 23, 45, 12));

  assert.equal(result.getFullYear(), 2026);
  assert.equal(result.getMonth(), 5);
  assert.equal(result.getDate(), 16);
  assert.equal(result.getHours(), 0);
  assert.equal(result.getMinutes(), 0);
  assert.equal(result.getSeconds(), 0);
}

function testNotificationHistoryRangeForTimestampBucketsByDay() {
  const dateOnly = qmlFunction("dateOnly", "d");
  const rangeForTimestamp = qmlFunction("rangeForTimestamp", "ts");
  const today = startOfToday();
  const ctx = {
    dateOnly(d) {
      return dateOnly(ctx, d);
    },
  };

  assert.equal(rangeForTimestamp(ctx, today.getTime() + 3600000), 0);
  assert.equal(rangeForTimestamp(ctx, today.getTime() - 86400000 + 3600000), 1);
  assert.equal(rangeForTimestamp(ctx, today.getTime() - 2 * 86400000 + 3600000), 2);
}

function testNotificationHistoryCurrentRangeGuard() {
  const dateOnly = qmlFunction("dateOnly", "d");
  const rangeForTimestamp = qmlFunction("rangeForTimestamp", "ts");
  const isInCurrentRange = qmlFunction("isInCurrentRange", "ts");
  const today = startOfToday();
  const ctx = {
    currentRange: 0,
    dateOnly(d) {
      return dateOnly(ctx, d);
    },
    rangeForTimestamp(ts) {
      return rangeForTimestamp(ctx, ts);
    },
  };
  const yesterdayTs = today.getTime() - 86400000 + 3600000;

  assert.equal(isInCurrentRange(ctx, yesterdayTs), true);

  ctx.currentRange = 1;
  assert.equal(isInCurrentRange(ctx, yesterdayTs), false);

  ctx.currentRange = 2;
  assert.equal(isInCurrentRange(ctx, yesterdayTs), true);
}

function testNotificationHistoryRecalcRangeCountsHandlesEmptyAndInvalidItems() {
  const dateOnly = qmlFunction("dateOnly", "d");
  const rangeForTimestamp = qmlFunction("rangeForTimestamp", "ts");
  const recalcRangeCounts = qmlFunction("recalcRangeCounts");
  const today = startOfToday();
  const ctx = {
    NotificationService: {
      historyList: null,
    },
    rangeCounts: [9, 9, 9, 9],
    dateOnly(d) {
      return dateOnly(ctx, d);
    },
    rangeForTimestamp(ts) {
      return rangeForTimestamp(ctx, ts);
    },
  };

  recalcRangeCounts(ctx);
  assert.deepEqual(ctx.rangeCounts, [0, 0, 0, 0]);

  ctx.NotificationService.historyList = listModel([
    { timestamp: today.getTime() + 3600000 },
    { timestamp: today.getTime() - 86400000 + 3600000 },
    { timestamp: today.getTime() - 2 * 86400000 + 3600000 },
    {},
    null,
  ]);
  recalcRangeCounts(ctx);
  assert.deepEqual(ctx.rangeCounts, [5, 1, 1, 1]);
}

function testNotificationHistoryCountForRangeFailsClosed() {
  const countForRange = qmlFunction("countForRange", "range");
  const ctx = {
    rangeCounts: [3, 2, 1, 0],
  };

  assert.equal(countForRange(ctx, 0), 3);
  assert.equal(countForRange(ctx, 2), 1);
  assert.equal(countForRange(ctx, 3), 0);
  assert.equal(countForRange(ctx, 99), 0);
}

const tests = [
  testNotificationHistoryDateOnlyClearsTime,
  testNotificationHistoryRangeForTimestampBucketsByDay,
  testNotificationHistoryCurrentRangeGuard,
  testNotificationHistoryRecalcRangeCountsHandlesEmptyAndInvalidItems,
  testNotificationHistoryCountForRangeFailsClosed,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
