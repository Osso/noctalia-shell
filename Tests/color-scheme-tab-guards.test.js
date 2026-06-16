#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/ColorSchemeTab.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testSchemeLoadedCachesJsonAndIncrementsVersion() {
  const schemeLoaded = qmlFunction("schemeLoaded", "schemeName", "jsonData");
  const ctx = {
    schemeColorsCache: {},
    cacheVersion: 4,
  };
  const colors = { primary: "#ffffff", surface: "#111111" };

  schemeLoaded(ctx, "nord", colors);

  assert.equal(ctx.schemeColorsCache.nord, colors);
  assert.equal(ctx.cacheVersion, 5);
}

function testSchemeLoadedFallsBackToEmptyObject() {
  const schemeLoaded = qmlFunction("schemeLoaded", "schemeName", "jsonData");
  const ctx = {
    schemeColorsCache: {},
    cacheVersion: 0,
  };

  schemeLoaded(ctx, "empty", null);

  assert.deepEqual(ctx.schemeColorsCache.empty, {});
  assert.equal(ctx.cacheVersion, 1);
}

function testOpenDownloadPopupDelegatesToLoader() {
  const openDownloadPopup = qmlFunction("openDownloadPopup");
  const ctx = {
    openCount: 0,
    downloadPopupLoader: {
      open() {
        ctx.openCount += 1;
      },
    },
  };

  openDownloadPopup(ctx);

  assert.equal(ctx.openCount, 1);
}

const tests = [
  testSchemeLoadedCachesJsonAndIncrementsVersion,
  testSchemeLoadedFallsBackToEmptyObject,
  testOpenDownloadPopupDelegatesToLoader,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
