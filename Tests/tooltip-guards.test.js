#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Tooltip/Tooltip.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createCounter() {
  const counter = {
    count: 0,
    start() {
      this.count += 1;
    },
    stop() {
      this.count += 1;
    },
  };
  return counter;
}

function createTooltipContext(overrides = {}) {
  const ctx = {
    text: "",
    direction: "auto",
    margin: 6,
    padding: 10,
    delay: 0,
    hideDelay: 0,
    maxWidth: 160,
    animationScale: 0.92,
    targetItem: null,
    anchorX: 0,
    anchorY: 0,
    isPositioned: false,
    animatingOut: false,
    screenWidth: 300,
    screenHeight: 200,
    visible: false,
    root: null,
    showTimer: createCounter(),
    hideTimer: createCounter(),
    showAnimation: createCounter(),
    hideAnimation: createCounter(),
    tooltipContainer: {
      opacity: 1,
      scale: 1,
    },
    tooltipText: {
      implicitWidth: 80,
      implicitHeight: 24,
      family: "",
    },
    Quickshell: {
      screens: [{ x: 0, y: 0, width: 300, height: 200 }],
    },
    Logger: {
      warnings: [],
      w(scope, message) {
        this.warnings.push([scope, message]);
      },
    },
    Settings: {
      data: {
        ui: {
          fontDefault: "Inter",
        },
      },
    },
    Qt: {
      callLater(callback) {
        callback();
      },
    },
  };
  ctx.root = ctx;
  Object.assign(ctx, overrides);
  if (!ctx.root) {
    ctx.root = ctx;
  }
  return ctx;
}

function createTarget(overrides = {}) {
  return {
    width: 40,
    height: 20,
    parent: {},
    mapToGlobal() {
      return { x: 35, y: 45 };
    },
    mapToItem() {
      return { x: 35, y: 45 };
    },
    ...overrides,
  };
}

function testTooltipShowGuardsMissingTargetsAndText() {
  const show = qmlFunction("show", "target", "tipText", "customDirection", "showDelay", "fontFamily");
  const ctx = createTooltipContext({ text: "existing" });

  assert.match(source, /function show\(target: Item, tipText: string, customDirection, showDelay, fontFamily\)/, "show must type required target and text inputs while keeping optional display inputs flexible");

  show(ctx, null, "tip", undefined, 100, undefined);
  show(ctx, createTarget(), "", undefined, 100, undefined);

  assert.equal(ctx.text, "existing");
  assert.equal(ctx.targetItem, null);
  assert.equal(ctx.showTimer.count, 0);
}

function testTooltipShowInitializesStateAndScreen() {
  const show = qmlFunction("show", "target", "tipText", "customDirection", "showDelay", "fontFamily");
  const target = createTarget();
  let hideImmediatelyCalled = 0;
  const ctx = createTooltipContext({
    visible: true,
    targetItem: createTarget(),
    hideImmediately() {
      hideImmediatelyCalled += 1;
      this.visible = false;
    },
  });

  show(ctx, target, "hello\nworld", "right", 250, "");

  assert.equal(ctx.delay, 250);
  assert.equal(hideImmediatelyCalled, 1);
  assert.equal(ctx.text, "hello<br>world");
  assert.equal(ctx.targetItem, target);
  assert.equal(ctx.screenWidth, 300);
  assert.equal(ctx.screenHeight, 200);
  assert.equal(ctx.tooltipContainer.opacity, 0);
  assert.equal(ctx.tooltipContainer.scale, 0.92);
  assert.equal(ctx.showTimer.count, 2);
  assert.equal(ctx.direction, "right");
  assert.equal(ctx.tooltipText.family, "Inter");
}

function testTooltipPositionAndShowUsesAutoPlacement() {
  const positionAndShow = qmlFunction("positionAndShow");
  const ctx = createTooltipContext({
    targetItem: createTarget(),
    tooltipText: {
      implicitWidth: 80,
      implicitHeight: 24,
      family: "",
    },
  });

  positionAndShow(ctx);

  assert.equal(ctx.root.implicitWidth, 100);
  assert.equal(ctx.root.implicitHeight, 44);
  assert.equal(ctx.anchorX, -30);
  assert.equal(ctx.anchorY, 26);
  assert.equal(ctx.isPositioned, true);
  assert.equal(ctx.visible, true);
  assert.equal(ctx.showAnimation.count, 1);
}

function testTooltipPositionAndShowGuardsMissingParent() {
  const positionAndShow = qmlFunction("positionAndShow");
  const ctx = createTooltipContext({
    targetItem: createTarget({ parent: null }),
  });

  positionAndShow(ctx);

  assert.equal(ctx.visible, false);
  assert.equal(ctx.isPositioned, false);
  assert.equal(ctx.showAnimation.count, 0);
}

function testTooltipHideUsesDelayOrAnimation() {
  const hide = qmlFunction("hide");
  let startHideAnimationCalls = 0;
  const ctx = createTooltipContext({
    hideDelay: 150,
    visible: true,
    startHideAnimation() {
      startHideAnimationCalls += 1;
    },
  });

  hide(ctx);

  assert.equal(ctx.hideTimer.count, 2);
  assert.equal(startHideAnimationCalls, 0);

  ctx.hideDelay = 0;
  hide(ctx);

  assert.equal(startHideAnimationCalls, 1);
}

function testTooltipStartAndCompleteHideLifecycle() {
  const startHideAnimation = qmlFunction("startHideAnimation");
  const completeHide = qmlFunction("completeHide");
  const ctx = createTooltipContext({
    visible: true,
    text: "tip",
    isPositioned: true,
    tooltipContainer: {
      opacity: 0.2,
      scale: 0.5,
    },
  });

  startHideAnimation(ctx);

  assert.equal(ctx.animatingOut, true);
  assert.equal(ctx.showAnimation.count, 1);
  assert.equal(ctx.hideAnimation.count, 1);

  completeHide(ctx);

  assert.equal(ctx.visible, false);
  assert.equal(ctx.animatingOut, false);
  assert.equal(ctx.text, "");
  assert.equal(ctx.isPositioned, false);
  assert.equal(ctx.tooltipContainer.opacity, 1);
  assert.equal(ctx.tooltipContainer.scale, 1);
}

function testTooltipHideImmediatelyStopsEverythingAndCompletes() {
  const hideImmediately = qmlFunction("hideImmediately");
  let completed = 0;
  const ctx = createTooltipContext({
    animatingOut: true,
    completeHide() {
      completed += 1;
      this.visible = false;
    },
  });

  hideImmediately(ctx);

  assert.equal(ctx.showTimer.count, 1);
  assert.equal(ctx.hideTimer.count, 1);
  assert.equal(ctx.showAnimation.count, 1);
  assert.equal(ctx.hideAnimation.count, 1);
  assert.equal(ctx.animatingOut, false);
  assert.equal(completed, 1);
}

function testTooltipUpdateTextRepositionsAndRefreshesAnchor() {
  const updateText = qmlFunction("updateText", "newText");
  let anchorUpdates = 0;
  const ctx = createTooltipContext({
    visible: true,
    targetItem: createTarget({
      width: 50,
      height: 20,
      mapToItem() {
        return { x: 5, y: 40 };
      },
    }),
    anchorX: 0,
    anchorY: 30,
    tooltipText: {
      implicitWidth: 80,
      implicitHeight: 20,
      family: "",
    },
    root: null,
  });
  ctx.root = {
    ...ctx,
    anchor: {
      updateAnchor() {
        anchorUpdates += 1;
      },
    },
  };
  ctx.root.root = ctx.root;

  updateText(ctx, "new\ntip");

  assert.equal(ctx.text, "new<br>tip");
  assert.equal(ctx.root.implicitWidth, 100);
  assert.equal(ctx.root.implicitHeight, 40);
  assert.equal(ctx.anchorX, 1);
  assert.equal(ctx.anchorY, 30);
  assert.equal(anchorUpdates, 1);
}

function testTooltipResetClearsStateAndStopsTimers() {
  const reset = qmlFunction("reset");
  const ctx = createTooltipContext({
    visible: true,
    animatingOut: true,
    text: "tip",
    isPositioned: true,
    direction: "left",
    delay: 50,
    hideDelay: 75,
    tooltipContainer: {
      opacity: 0.5,
      scale: 0.5,
    },
  });

  reset(ctx);

  assert.equal(ctx.showTimer.count, 1);
  assert.equal(ctx.hideTimer.count, 1);
  assert.equal(ctx.showAnimation.count, 1);
  assert.equal(ctx.hideAnimation.count, 1);
  assert.equal(ctx.visible, false);
  assert.equal(ctx.animatingOut, false);
  assert.equal(ctx.text, "");
  assert.equal(ctx.isPositioned, false);
  assert.equal(ctx.direction, "auto");
  assert.equal(ctx.delay, 0);
  assert.equal(ctx.hideDelay, 0);
  assert.equal(ctx.tooltipContainer.opacity, 1);
  assert.equal(ctx.tooltipContainer.scale, 1);
}

const tests = [
  testTooltipShowGuardsMissingTargetsAndText,
  testTooltipShowInitializesStateAndScreen,
  testTooltipPositionAndShowUsesAutoPlacement,
  testTooltipPositionAndShowGuardsMissingParent,
  testTooltipHideUsesDelayOrAnimation,
  testTooltipStartAndCompleteHideLifecycle,
  testTooltipHideImmediatelyStopsEverythingAndCompletes,
  testTooltipUpdateTextRepositionsAndRefreshesAnchor,
  testTooltipResetClearsStateAndStopsTimers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
