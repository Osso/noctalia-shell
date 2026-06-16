#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/MainScreen/SmartPanel.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createTimer(name) {
  return {
    name,
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

function createLogger() {
  return {
    debug: [],
    warnings: [],
    d(...args) {
      this.debug.push(args);
    },
    w(...args) {
      this.warnings.push(args);
    },
  };
}

function createSmartPanelContext(overrides = {}) {
  const logger = createLogger();
  const panelServiceCalls = [];
  const ctx = {
    Logger: logger,
    PanelService: {
      closedPanel(panel) {
        panelServiceCalls.push(panel);
      },
    },
    objectName: "panel-under-test",
    opacity: 1,
    isClosing: false,
    sizeAnimationComplete: true,
    closeFinalized: true,
    openWatchdogActive: true,
    closeWatchdogActive: false,
    opacityFadeComplete: true,
    isPanelVisible: true,
    isPanelOpen: true,
    opacityTrigger: createTimer("opacityTrigger"),
    openWatchdogTimer: createTimer("openWatchdogTimer"),
    closeWatchdogTimer: createTimer("closeWatchdogTimer"),
    panelBackground: {
      dimensionsInitialized: true,
    },
    closedCount: 0,
    closed() {
      this.closedCount += 1;
    },
    ...overrides,
  };
  ctx.root = ctx;
  ctx.panelServiceCalls = panelServiceCalls;
  return ctx;
}

function testSmartPanelCloseStartsCloseSequenceAndWatchdog() {
  const close = qmlFunction("close");
  const ctx = createSmartPanelContext();

  close(ctx);

  assert.equal(ctx.isClosing, true);
  assert.equal(ctx.sizeAnimationComplete, false);
  assert.equal(ctx.closeFinalized, false);
  assert.equal(ctx.openWatchdogActive, false);
  assert.equal(ctx.closeWatchdogActive, true);
  assert.equal(ctx.opacityFadeComplete, false);
  assert.equal(ctx.opacityTrigger.stops, 1);
  assert.equal(ctx.openWatchdogTimer.stops, 1);
  assert.equal(ctx.closeWatchdogTimer.restarts, 1);
  assert.deepEqual(ctx.Logger.debug.at(-1), ["SmartPanel", "Closing panel", "panel-under-test"]);
}

function testSmartPanelCloseMarksOpacityCompleteWhenAlreadyHidden() {
  const close = qmlFunction("close");
  const ctx = createSmartPanelContext({
    opacity: 0,
  });

  close(ctx);

  assert.equal(ctx.opacityFadeComplete, true);
  assert.equal(ctx.closeWatchdogTimer.restarts, 1);
}

function testSmartPanelFinalizeCloseIgnoresDuplicateFinalization() {
  const finalizeClose = qmlFunction("finalizeClose");
  const ctx = createSmartPanelContext({
    closeFinalized: true,
  });

  finalizeClose(ctx);

  assert.deepEqual(ctx.Logger.warnings, [
    ["SmartPanel", "finalizeClose called but already finalized - ignoring", "panel-under-test"],
  ]);
  assert.equal(ctx.closeWatchdogTimer.stops, 0);
  assert.equal(ctx.panelServiceCalls.length, 0);
  assert.equal(ctx.closedCount, 0);
}

function testSmartPanelFinalizeCloseResetsStateAndNotifiesPanelService() {
  const finalizeClose = qmlFunction("finalizeClose");
  const ctx = createSmartPanelContext({
    closeFinalized: false,
    closeWatchdogActive: true,
    isPanelVisible: true,
    isPanelOpen: true,
    isClosing: true,
    opacityFadeComplete: true,
  });

  finalizeClose(ctx);

  assert.equal(ctx.closeFinalized, true);
  assert.equal(ctx.closeWatchdogActive, false);
  assert.equal(ctx.closeWatchdogTimer.stops, 1);
  assert.equal(ctx.isPanelVisible, false);
  assert.equal(ctx.isPanelOpen, false);
  assert.equal(ctx.isClosing, false);
  assert.equal(ctx.opacityFadeComplete, false);
  assert.equal(ctx.panelBackground.dimensionsInitialized, false);
  assert.deepEqual(ctx.panelServiceCalls, [ctx]);
  assert.equal(ctx.closedCount, 1);
  assert.deepEqual(ctx.Logger.debug.at(-1), ["SmartPanel", "Panel close finalized", "panel-under-test"]);
}

const tests = [
  testSmartPanelCloseStartsCloseSequenceAndWatchdog,
  testSmartPanelCloseMarksOpacityCompleteWhenAlreadyHidden,
  testSmartPanelFinalizeCloseIgnoresDuplicateFinalization,
  testSmartPanelFinalizeCloseResetsStateAndNotifiesPanelService,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
