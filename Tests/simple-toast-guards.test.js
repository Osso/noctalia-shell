#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Toast/SimpleToast.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function counterTimer() {
  return {
    stops: 0,
    restarts: 0,
    stop() {
      this.stops += 1;
    },
    restart() {
      this.restarts += 1;
    },
  };
}

function createContext(overrides = {}) {
  const ctx = {
    message: "",
    description: "",
    icon: "",
    type: "notice",
    duration: 3000,
    visible: false,
    opacity: 0,
    scale: 0.7,
    initialScale: 0.7,
    hiddenCalls: 0,
    hideTimer: counterTimer(),
    hideAnimation: counterTimer(),
    hidden() {
      this.hiddenCalls += 1;
    },
  };
  Object.assign(ctx, overrides);
  ctx.root = ctx;
  return ctx;
}

function testSimpleToastShowStoresFieldsAndStartsTimer() {
  const show = qmlFunction("show", "msg", "desc", "msgIcon", "msgType", "msgDuration");
  const ctx = createContext();

  assert.match(source, /function show\(msg: string, desc, msgIcon, msgType, msgDuration\)/, "show must type the required message input while keeping optional display inputs flexible");

  show(ctx, "Saved", "Done", "check", "notice", 2500);

  assert.equal(ctx.hideTimer.stops, 1);
  assert.equal(ctx.hideAnimation.stops, 1);
  assert.equal(ctx.message, "Saved");
  assert.equal(ctx.description, "Done");
  assert.equal(ctx.icon, "check");
  assert.equal(ctx.type, "notice");
  assert.equal(ctx.duration, 2500);
  assert.equal(ctx.visible, true);
  assert.equal(ctx.opacity, 1);
  assert.equal(ctx.scale, 1.0);
  assert.equal(ctx.hideTimer.restarts, 1);
}

function testSimpleToastShowAppliesFallbackFields() {
  const show = qmlFunction("show", "msg", "desc", "msgIcon", "msgType", "msgDuration");
  const ctx = createContext();

  show(ctx, "Saved", "", "", "", 0);

  assert.equal(ctx.message, "Saved");
  assert.equal(ctx.description, "");
  assert.equal(ctx.icon, "");
  assert.equal(ctx.type, "notice");
  assert.equal(ctx.duration, 3000);
}

function testSimpleToastHideStartsHideAnimation() {
  const hide = qmlFunction("hide");
  const ctx = createContext({
    visible: true,
    opacity: 1,
    scale: 1,
  });

  hide(ctx);

  assert.equal(ctx.hideTimer.stops, 1);
  assert.equal(ctx.opacity, 0);
  assert.equal(ctx.scale, ctx.initialScale);
  assert.equal(ctx.hideAnimation.restarts, 1);
}

function testSimpleToastHideImmediatelyStopsAndEmitsHidden() {
  const hideImmediately = qmlFunction("hideImmediately");
  const ctx = createContext({
    visible: true,
    opacity: 1,
    scale: 1,
  });

  hideImmediately(ctx);

  assert.equal(ctx.hideTimer.stops, 1);
  assert.equal(ctx.hideAnimation.stops, 1);
  assert.equal(ctx.opacity, 0);
  assert.equal(ctx.scale, ctx.initialScale);
  assert.equal(ctx.visible, false);
  assert.equal(ctx.hiddenCalls, 1);
}

const tests = [
  testSimpleToastShowStoresFieldsAndStartsTimer,
  testSimpleToastShowAppliesFallbackFields,
  testSimpleToastHideStartsHideAnimation,
  testSimpleToastHideImmediatelyStopsAndEmitsHidden,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
