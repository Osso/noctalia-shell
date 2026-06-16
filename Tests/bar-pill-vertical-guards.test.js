#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Extras/BarPillVertical.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createTimer() {
  return {
    starts: 0,
    stops: 0,
    restarts: 0,
    start() {
      this.starts += 1;
    },
    stop() {
      this.stops += 1;
    },
    restart() {
      this.restarts += 1;
    },
  };
}

function testBarPillVerticalCenterOffsetTracksOpenDirection() {
  const getVerticalCenterOffset = qmlFunction("getVerticalCenterOffset");
  const ctx = {
    Style: {
      marginXS: 6,
    },
    openDownward: true,
  };

  assert.equal(getVerticalCenterOffset(ctx), 6);

  ctx.openDownward = false;
  assert.equal(getVerticalCenterOffset(ctx), -6);
}

function testBarPillVerticalShowDelayedIgnoresCollapsedIconMode() {
  const showDelayed = qmlFunction("showDelayed");
  const ctx = {
    collapseToIcon: true,
    showPill: false,
    autoHide: true,
    shouldAnimateHide: false,
    showTimer: createTimer(),
    hideAnim: createTimer(),
    delayedHideAnim: createTimer(),
  };

  showDelayed(ctx);

  assert.equal(ctx.shouldAnimateHide, false);
  assert.equal(ctx.showTimer.starts, 0);
  assert.equal(ctx.hideAnim.stops, 0);
  assert.equal(ctx.delayedHideAnim.restarts, 0);
}

function testBarPillVerticalShowDelayedStartsShowTimerWhenClosed() {
  const showDelayed = qmlFunction("showDelayed");
  const ctx = {
    collapseToIcon: false,
    showPill: false,
    autoHide: true,
    shouldAnimateHide: false,
    showTimer: createTimer(),
    hideAnim: createTimer(),
    delayedHideAnim: createTimer(),
  };

  showDelayed(ctx);

  assert.equal(ctx.shouldAnimateHide, true);
  assert.equal(ctx.showTimer.starts, 1);
  assert.equal(ctx.hideAnim.stops, 0);
  assert.equal(ctx.delayedHideAnim.restarts, 0);
}

function testBarPillVerticalShowDelayedRestartsDelayedHideWhenOpen() {
  const showDelayed = qmlFunction("showDelayed");
  const ctx = {
    collapseToIcon: false,
    showPill: true,
    autoHide: true,
    shouldAnimateHide: false,
    showTimer: createTimer(),
    hideAnim: createTimer(),
    delayedHideAnim: createTimer(),
  };

  showDelayed(ctx);

  assert.equal(ctx.shouldAnimateHide, false);
  assert.equal(ctx.showTimer.starts, 0);
  assert.equal(ctx.hideAnim.stops, 1);
  assert.equal(ctx.delayedHideAnim.restarts, 1);
}

const tests = [
  testBarPillVerticalCenterOffsetTracksOpenDirection,
  testBarPillVerticalShowDelayedIgnoresCollapsedIconMode,
  testBarPillVerticalShowDelayedStartsShowTimerWhenClosed,
  testBarPillVerticalShowDelayedRestartsDelayedHideWhenOpen,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
