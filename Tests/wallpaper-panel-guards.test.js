#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Wallpaper/WallpaperPanel.qml");

function qmlFunction(functionName) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", `with (ctx) { return (function() ${body}).call(ctx); }`);
}

function testCurrentWallpaperViewReturnsNullWithoutContent() {
  const currentWallpaperView = qmlFunction("currentWallpaperView");
  const ctx = {
    contentItem: null,
  };

  assert.equal(currentWallpaperView(ctx), null);
}

function testCurrentWallpaperViewReturnsCurrentRepeaterItem() {
  const currentWallpaperView = qmlFunction("currentWallpaperView");
  const view = { screenName: "HDMI-A-1" };
  const ctx = {
    contentItem: {
      currentScreenIndex: 2,
      screenRepeater: {
        requestedIndexes: [],
        itemAt(index) {
          this.requestedIndexes.push(index);
          return view;
        },
      },
    },
  };

  assert.equal(currentWallpaperView(ctx), view);
  assert.deepEqual(ctx.contentItem.screenRepeater.requestedIndexes, [2]);
}

function testCurrentGridViewReturnsCurrentViewGrid() {
  const currentGridView = qmlFunction("currentGridView");
  const gridView = { currentIndex: 4 };
  const ctx = {
    currentWallpaperView() {
      return { gridView };
    },
  };

  assert.equal(currentGridView(ctx), gridView);
}

function testCurrentGridViewReturnsNullWithoutCurrentGrid() {
  const currentGridView = qmlFunction("currentGridView");

  assert.equal(currentGridView({ currentWallpaperView: () => null }), null);
  assert.equal(currentGridView({ currentWallpaperView: () => ({}) }), null);
}

const tests = [
  testCurrentWallpaperViewReturnsNullWithoutContent,
  testCurrentWallpaperViewReturnsCurrentRepeaterItem,
  testCurrentGridViewReturnsCurrentViewGrid,
  testCurrentGridViewReturnsNullWithoutCurrentGrid,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
