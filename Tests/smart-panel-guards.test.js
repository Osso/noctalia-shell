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

function createPositionContext(overrides = {}) {
  const ctx = createSmartPanelContext({
    width: 1000,
    height: 800,
    preferredWidth: 300,
    preferredHeight: 200,
    preferredWidthRatio: undefined,
    preferredHeightRatio: undefined,
    useButtonPosition: false,
    buttonPosition: { x: 0, y: 0 },
    buttonWidth: 0,
    buttonHeight: 0,
    barPosition: "top",
    barIsVertical: false,
    barFloating: false,
    barMarginH: 10,
    barMarginV: 10,
    panelAnchorHorizontalCenter: false,
    panelAnchorVerticalCenter: false,
    effectivePanelAnchorTop: false,
    effectivePanelAnchorBottom: false,
    effectivePanelAnchorLeft: false,
    effectivePanelAnchorRight: false,
    hasExplicitHorizontalAnchor: false,
    hasExplicitVerticalAnchor: false,
    edgeSnapDistance: 8,
    contentLoader: {
      item: null,
    },
    panelContent: {
      allowAttach: false,
    },
    panelBackground: {
      targetWidth: 0,
      targetHeight: 0,
      targetX: 0,
      targetY: 0,
      dimensionsInitialized: true,
    },
    Style: {
      marginL: 16,
      marginM: 12,
      barHeight: 48,
      radiusL: 20,
    },
    Qt: {
      callLater(callback) {
        this.calledLater = callback;
      },
    },
    setPosition() {},
    ...overrides,
  });
  ctx.root = ctx;
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

function testSmartPanelSetPositionRetriesWhenDimensionsAreMissing() {
  const setPosition = qmlFunction("setPosition");
  const ctx = createPositionContext({
    width: 0,
    height: 800,
  });

  setPosition(ctx);

  assert.equal(ctx.Qt.calledLater, ctx.setPosition);
  assert.equal(ctx.panelBackground.targetWidth, 0);
  assert.deepEqual(ctx.Logger.debug[0], ["SmartPanel", "Skipping setPosition - dimensions not ready:", 0, "x", 800]);
}

function testSmartPanelSetPositionUsesButtonAttachedTopBarPlacement() {
  const setPosition = qmlFunction("setPosition");
  const ctx = createPositionContext({
    useButtonPosition: true,
    buttonPosition: { x: 450, y: 0 },
    buttonWidth: 100,
    buttonHeight: 48,
    panelContent: {
      allowAttach: true,
    },
  });

  setPosition(ctx);

  assert.equal(ctx.panelBackground.targetWidth, 300);
  assert.equal(ctx.panelBackground.targetHeight, 200);
  assert.equal(ctx.panelBackground.targetX, 350);
  assert.equal(ctx.panelBackground.targetY, 58);
}

function testSmartPanelSetPositionUsesDetachedStandardPlacement() {
  const setPosition = qmlFunction("setPosition");
  const ctx = createPositionContext();

  setPosition(ctx);

  assert.equal(ctx.panelBackground.targetWidth, 300);
  assert.equal(ctx.panelBackground.targetHeight, 200);
  assert.equal(ctx.panelBackground.targetX, 350);
  assert.equal(ctx.panelBackground.targetY, 86);
}

const tests = [
  testSmartPanelCloseStartsCloseSequenceAndWatchdog,
  testSmartPanelCloseMarksOpacityCompleteWhenAlreadyHidden,
  testSmartPanelFinalizeCloseIgnoresDuplicateFinalization,
  testSmartPanelFinalizeCloseResetsStateAndNotifiesPanelService,
  testSmartPanelSetPositionRetriesWhenDimensionsAreMissing,
  testSmartPanelSetPositionUsesButtonAttachedTopBarPlacement,
  testSmartPanelSetPositionUsesDetachedStandardPlacement,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
