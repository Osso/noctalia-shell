#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Widgets/NSectionEditor.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

const colorContext = {
  Color: {
    mPrimary: "primary",
    mOnPrimary: "on-primary",
    mSecondary: "secondary",
    mOnSecondary: "on-secondary",
    mTertiary: "tertiary",
    mOnTertiary: "on-tertiary",
    mError: "error",
    mOnError: "on-error",
    mOnSurface: "on-surface",
    mSurface: "surface",
    mOnSurfaceVariant: "on-surface-variant",
    mSurfaceVariant: "surface-variant",
  },
};

function createDropContext(overrides = {}) {
  return {
    dragStarted: true,
    draggedIndex: 1,
    widgetModel: [{ id: "a" }, { id: "b" }, { id: "c" }],
    widgetFlow: {
      children: [
        { widgetIndex: 0, x: 10, y: 20, width: 40, height: 30 },
        { widgetIndex: 1, x: 70, y: 20, width: 40, height: 30 },
        { widgetIndex: 2, x: 130, y: 20, width: 40, height: 30 },
      ],
    },
    dropIndicator: {
      width: 10,
      x: 0,
      y: 0,
      opacity: 0,
    },
    pulseAnimation: {
      running: false,
    },
    dropTargetIndex: -1,
    Style: {
      marginXS: 4,
      marginS: 8,
    },
    Qt: {
      point(x, y) {
        return { x, y };
      },
    },
    ...overrides,
  };
}

function testGetWidgetColorReturnsStablePalettePairs() {
  const getWidgetColor = qmlFunction("getWidgetColor", "widget");

  assert.deepEqual(getWidgetColor(colorContext, "d"), ["primary", "on-primary"]);
  assert.deepEqual(getWidgetColor(colorContext, "e"), ["secondary", "on-secondary"]);
  assert.deepEqual(getWidgetColor(colorContext, "f"), ["tertiary", "on-tertiary"]);
  assert.deepEqual(getWidgetColor(colorContext, "a"), ["error", "on-error"]);
  assert.deepEqual(getWidgetColor(colorContext, "b"), ["on-surface", "surface"]);
  assert.deepEqual(getWidgetColor(colorContext, "c"), ["on-surface-variant", "surface-variant"]);
}

function testUpdateDropIndicatorHidesWhenDragIsInactive() {
  const updateDropIndicator = qmlFunction("updateDropIndicator", "mouseX", "mouseY");
  const ctx = createDropContext({
    dragStarted: false,
    dropIndicator: { width: 10, opacity: 1 },
    pulseAnimation: { running: true },
  });

  updateDropIndicator(ctx, 12, 20);

  assert.equal(ctx.dropIndicator.opacity, 0);
  assert.equal(ctx.pulseAnimation.running, false);
}

function testUpdateDropIndicatorShowsNearbyInsertionPoint() {
  const updateDropIndicator = qmlFunction("updateDropIndicator", "mouseX", "mouseY");
  const ctx = createDropContext();

  updateDropIndicator(ctx, 168, 35);

  assert.equal(ctx.dropTargetIndex, 2);
  assert.equal(ctx.dropIndicator.opacity, 1);
  assert.equal(ctx.dropIndicator.x, 169);
  assert.equal(ctx.dropIndicator.y, 20);
  assert.equal(ctx.pulseAnimation.running, true);
}

function testUpdateDropIndicatorSuppressesSameAdjustedPosition() {
  const updateDropIndicator = qmlFunction("updateDropIndicator", "mouseX", "mouseY");
  const ctx = createDropContext();

  updateDropIndicator(ctx, 128, 35);

  assert.equal(ctx.dropTargetIndex, -1);
  assert.equal(ctx.dropIndicator.opacity, 0);
  assert.equal(ctx.pulseAnimation.running, false);
}

function testUpdateDropIndicatorChoosesBeginningInsertion() {
  const updateDropIndicator = qmlFunction("updateDropIndicator", "mouseX", "mouseY");
  const ctx = createDropContext({
    draggedIndex: 2,
  });

  updateDropIndicator(ctx, 1, 20);

  assert.equal(ctx.dropTargetIndex, 0);
  assert.equal(ctx.dropIndicator.opacity, 1);
  assert.equal(ctx.dropIndicator.x, 0);
  assert.equal(ctx.dropIndicator.y, 20);
}

function testUpdateDropIndicatorHidesWhenNoTargetIsClose() {
  const updateDropIndicator = qmlFunction("updateDropIndicator", "mouseX", "mouseY");
  const ctx = createDropContext({
    dropIndicator: { width: 10, opacity: 1 },
    pulseAnimation: { running: true },
    dropTargetIndex: 2,
  });

  updateDropIndicator(ctx, 500, 500);

  assert.equal(ctx.dropTargetIndex, -1);
  assert.equal(ctx.dropIndicator.opacity, 0);
  assert.equal(ctx.pulseAnimation.running, false);
}

const tests = [
  testGetWidgetColorReturnsStablePalettePairs,
  testUpdateDropIndicatorHidesWhenDragIsInactive,
  testUpdateDropIndicatorShowsNearbyInsertionPoint,
  testUpdateDropIndicatorSuppressesSameAdjustedPosition,
  testUpdateDropIndicatorChoosesBeginningInsertion,
  testUpdateDropIndicatorHidesWhenNoTargetIsClose,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
