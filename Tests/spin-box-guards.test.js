#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Widgets/NSpinBox.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createRepeatTimer() {
  return {
    stopped: 0,
    interval: 80,
    stop() {
      this.stopped += 1;
    },
  };
}

function createSpinBoxContext(overrides = {}) {
  const repeatTimer = overrides.repeatTimer || createRepeatTimer();
  const ctx = {
    value: 5,
    from: 0,
    to: 10,
    stepSize: 1,
    initialRepeatDelay: 400,
    _repeatDirection: 1,
    repeatTimer,
    ...overrides,
  };
  ctx.root = ctx;
  ctx.stopRepeat = qmlFunction("stopRepeat").bind(null, ctx);
  return ctx;
}

function testSpinBoxChangeValueIncrementsDecrementsAndUsesDefaultStep() {
  const changeValue = qmlFunction("changeValue", "direction", "step");
  const ctx = createSpinBoxContext();

  changeValue(ctx, 1);
  assert.equal(ctx.value, 6);

  changeValue(ctx, -1, 3);
  assert.equal(ctx.value, 3);
  assert.equal(ctx.repeatTimer.stopped, 0);
}

function testSpinBoxChangeValueClampsAtBoundsAndStopsRepeat() {
  const changeValue = qmlFunction("changeValue", "direction", "step");
  const ctx = createSpinBoxContext({
    value: 9,
    _repeatDirection: 1,
  });

  changeValue(ctx, 1, 5);

  assert.equal(ctx.value, 10);
  assert.equal(ctx._repeatDirection, 0);
  assert.equal(ctx.repeatTimer.stopped, 1);
  assert.equal(ctx.repeatTimer.interval, 400);

  ctx.value = 1;
  ctx._repeatDirection = -1;
  ctx.repeatTimer.interval = 80;
  changeValue(ctx, -1, 5);

  assert.equal(ctx.value, 0);
  assert.equal(ctx._repeatDirection, 0);
  assert.equal(ctx.repeatTimer.stopped, 2);
  assert.equal(ctx.repeatTimer.interval, 400);
}

function testSpinBoxChangeValueIgnoresInvalidDirectionAndExistingBounds() {
  const changeValue = qmlFunction("changeValue", "direction", "step");
  const ctx = createSpinBoxContext({
    value: 10,
  });

  changeValue(ctx, 1, 1);
  changeValue(ctx, 0, 1);
  changeValue(ctx, 2, 1);

  assert.equal(ctx.value, 10);
  assert.equal(ctx.repeatTimer.stopped, 0);
}

function testSpinBoxChangeValueUsesTypedInputs() {
  assert.match(source, /function changeValue\(direction, step\)/, "changeValue must type numeric step inputs while keeping omission behavior");
}

function testSpinBoxStopRepeatClearsDirectionAndRestoresInitialDelay() {
  const stopRepeat = qmlFunction("stopRepeat");
  const ctx = createSpinBoxContext({
    _repeatDirection: -1,
    repeatTimer: createRepeatTimer(),
  });
  ctx.repeatTimer.interval = 80;

  stopRepeat(ctx);

  assert.equal(ctx._repeatDirection, 0);
  assert.equal(ctx.repeatTimer.stopped, 1);
  assert.equal(ctx.repeatTimer.interval, 400);
}

function testSpinBoxApplyValueParsesAndClampsInputText() {
  const applyValue = qmlFunction("applyValue");
  const ctx = createSpinBoxContext({
    from: 10,
    to: 20,
    text: "999",
    value: 12,
  });

  applyValue(ctx);
  assert.equal(ctx.value, 20);

  ctx.text = "15px";
  applyValue(ctx);
  assert.equal(ctx.value, 15);

  ctx.text = "-4";
  applyValue(ctx);
  assert.equal(ctx.value, 10);
}

function testSpinBoxApplyValueIgnoresNonNumericText() {
  const applyValue = qmlFunction("applyValue");
  const ctx = createSpinBoxContext({
    text: "not a number",
    value: 7,
  });

  applyValue(ctx);

  assert.equal(ctx.value, 7);
}

const tests = [
  testSpinBoxChangeValueIncrementsDecrementsAndUsesDefaultStep,
  testSpinBoxChangeValueClampsAtBoundsAndStopsRepeat,
  testSpinBoxChangeValueIgnoresInvalidDirectionAndExistingBounds,
  testSpinBoxChangeValueUsesTypedInputs,
  testSpinBoxStopRepeatClearsDirectionAndRestoresInitialDelay,
  testSpinBoxApplyValueParsesAndClampsInputText,
  testSpinBoxApplyValueIgnoresNonNumericText,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
