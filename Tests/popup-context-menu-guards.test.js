#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Widgets/NPopupContextMenu.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createMeasure() {
  return {
    text: "",
    contentWidth: 0,
    forceLayout() {
      this.contentWidth = this.text.length * 10;
    },
  };
}

function testPopupContextMenuCalculateWidthSkipsHiddenItemsAndUsesMinimum() {
  const calculateWidth = qmlFunction("calculateWidth");
  const ctx = {
    model: [
      { label: "Run", icon: "play" },
      { text: "Hidden and very wide", icon: "warning", visible: false },
      { text: "Inspect details" },
    ],
    textMeasure: createMeasure(),
    iconMeasure: { width: 16 },
    Style: {
      marginS: 4,
      marginM: 8,
    },
    calculatedWidth: 0,
  };

  calculateWidth(ctx);

  assert.equal(ctx.calculatedWidth, 182);
  assert.equal(ctx.textMeasure.text, "Inspect details");
}

function testPopupContextMenuCalculateWidthFallsBackForEmptyModels() {
  const calculateWidth = qmlFunction("calculateWidth");
  const ctx = {
    model: [],
    textMeasure: createMeasure(),
    iconMeasure: { width: 16 },
    Style: {
      marginS: 4,
      marginM: 8,
    },
    calculatedWidth: 999,
  };

  calculateWidth(ctx);

  assert.equal(ctx.calculatedWidth, 120);
}

function testPopupContextMenuOpenAtRequiresAnchorItem() {
  const openAt = qmlFunction("openAt", "x", "y", "item");
  const warnings = [];
  const ctx = {
    Logger: {
      w(scope, message) {
        warnings.push([scope, message]);
      },
    },
    calculateWidth() {
      throw new Error("calculateWidth should not run without an anchor item");
    },
    anchorItem: "previous",
    anchorX: 1,
    anchorY: 2,
    visible: false,
    Qt: {
      callLater() {
        throw new Error("callLater should not run without an anchor item");
      },
    },
    root: {},
  };

  openAt(ctx, 30, 40, null);

  assert.deepEqual(warnings, [["NPopupContextMenu", "anchorItem is undefined, won't show menu."]]);
  assert.equal(ctx.anchorItem, "previous");
  assert.equal(ctx.anchorX, 1);
  assert.equal(ctx.anchorY, 2);
  assert.equal(ctx.visible, false);
}

function testPopupContextMenuOpenAtPositionsAndRefreshesAnchor() {
  const openAt = qmlFunction("openAt", "x", "y", "item");
  let widthCalculated = 0;
  let anchorUpdated = 0;
  const anchorItem = { id: "launcher" };
  const ctx = {
    Logger: { w() {} },
    calculateWidth() {
      widthCalculated += 1;
    },
    anchorItem: null,
    anchorX: 0,
    anchorY: 0,
    visible: false,
    Qt: {
      callLater(callback) {
        callback();
      },
    },
    root: {
      anchor: {
        updateAnchor() {
          anchorUpdated += 1;
        },
      },
    },
  };

  openAt(ctx, 11, 22, anchorItem);

  assert.equal(widthCalculated, 1);
  assert.equal(ctx.anchorItem, anchorItem);
  assert.equal(ctx.anchorX, 11);
  assert.equal(ctx.anchorY, 22);
  assert.equal(ctx.visible, true);
  assert.equal(anchorUpdated, 1);
}

function testPopupContextMenuOpenAtItemDefaultsCoordinatesAndCloseDelegates() {
  const openAtItem = qmlFunction("openAtItem", "item", "mouseX", "mouseY");
  const close = qmlFunction("close");
  const closeMenu = qmlFunction("closeMenu");
  const calls = [];
  const ctx = {
    visible: true,
    openAt(x, y, item) {
      calls.push({ x, y, item });
    },
    close() {
      close(ctx);
    },
  };
  const anchorItem = { id: "tray" };

  openAtItem(ctx, anchorItem, undefined, 42);
  openAtItem(ctx, anchorItem, 9, undefined);
  closeMenu(ctx);

  assert.deepEqual(calls, [
    { x: 0, y: 42, item: anchorItem },
    { x: 9, y: 0, item: anchorItem },
  ]);
  assert.equal(ctx.visible, false);
}

const tests = [
  testPopupContextMenuCalculateWidthSkipsHiddenItemsAndUsesMinimum,
  testPopupContextMenuCalculateWidthFallsBackForEmptyModels,
  testPopupContextMenuOpenAtRequiresAnchorItem,
  testPopupContextMenuOpenAtPositionsAndRefreshesAnchor,
  testPopupContextMenuOpenAtItemDefaultsCoordinatesAndCloseDelegates,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
