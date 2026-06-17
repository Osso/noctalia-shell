#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Commons/Icons.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    debug: [],
    errors: [],
    d(...args) {
      this.debug.push(args);
    },
    e(...args) {
      this.errors.push(args);
    },
  };
}

function createFontLoader(name = "Tabler Icons") {
  const loader = {
    name,
    status: null,
    destroyed: 0,
    callbacks: [],
    destroy() {
      this.destroyed += 1;
    },
    statusChanged: {
      connect(callback) {
        loader.callbacks.push(callback);
      },
    },
  };
  return loader;
}

function createLoadContext({ currentFontLoader = null, createdLoader = createFontLoader(), fontVersion = 3 } = {}) {
  const logger = createLogger();
  const created = [];
  const ctx = {
    Logger: logger,
    FontLoader: {
      Ready: 1,
      Error: 2,
    },
    Qt: {
      createQmlObject(sourceText, parent, objectName) {
        created.push({ sourceText, parent, objectName });
        return createdLoader;
      },
    },
    cacheBustingPath: "/shell/Assets/Fonts/tabler/tabler-icons.ttf?v=3&t=1000",
    currentFontLoader,
    fontVersion,
    fontReloadedCount: 0,
    fontReloaded() {
      this.fontReloadedCount += 1;
    },
  };
  ctx.root = ctx;
  return { ctx, logger, created, createdLoader };
}

function testIconsGetResolvesAliasesCodepointsAndMissingIcons() {
  const get = qmlFunction("get", "iconName");
  const ctx = {
    aliases: {
      close: "x",
    },
    icons: {
      x: "\\uea76",
      check: "\\uea67",
    },
  };

  assert.equal(get(ctx, "close"), "\\uea76");
  assert.equal(get(ctx, "check"), "\\uea67");
  assert.equal(get(ctx, "missing"), undefined);
}

function testIconsGetUsesTypedIconName() {
  assert.match(source, /function get\(iconName: string\)/, "get must type the icon name input");
}

function testIconsLoadFontDestroysOldLoaderAndCreatesCacheBustedLoader() {
  const loadFontWithCacheBusting = qmlFunction("loadFontWithCacheBusting");
  const oldLoader = createFontLoader("Old Icons");
  const { ctx, created, createdLoader } = createLoadContext({
    currentFontLoader: oldLoader,
    fontVersion: 7,
  });
  ctx.cacheBustingPath = "/shell/Assets/Fonts/tabler/tabler-icons.ttf?v=7&t=2000";

  loadFontWithCacheBusting(ctx);

  assert.equal(oldLoader.destroyed, 1);
  assert.equal(ctx.currentFontLoader, createdLoader);
  assert.equal(created.length, 1);
  assert.equal(created[0].parent, ctx.root);
  assert.equal(created[0].objectName, "dynamicFontLoader_7");
  assert.match(created[0].sourceText, /FontLoader\s*\{/);
  assert.match(created[0].sourceText, /source: "\/shell\/Assets\/Fonts\/tabler\/tabler-icons\.ttf\?v=7&t=2000"/);
  assert.equal(createdLoader.callbacks.length, 1);
}

function testIconsLoadFontEmitsReloadedWhenLoaderBecomesReady() {
  const loadFontWithCacheBusting = qmlFunction("loadFontWithCacheBusting");
  const { ctx, logger, createdLoader } = createLoadContext();

  loadFontWithCacheBusting(ctx);
  createdLoader.status = ctx.FontLoader.Ready;
  createdLoader.callbacks[0]();

  assert.equal(ctx.fontReloadedCount, 1);
  assert.deepEqual(logger.errors, []);
  assert.deepEqual(logger.debug.at(-1), [
    "Icons",
    "Font loaded successfully:",
    "Tabler Icons",
    "(version 3)",
  ]);
}

function testIconsLoadFontLogsErrorStatusWithoutReloadSignal() {
  const loadFontWithCacheBusting = qmlFunction("loadFontWithCacheBusting");
  const { ctx, logger, createdLoader } = createLoadContext();

  loadFontWithCacheBusting(ctx);
  createdLoader.status = ctx.FontLoader.Error;
  createdLoader.callbacks[0]();

  assert.equal(ctx.fontReloadedCount, 0);
  assert.deepEqual(logger.errors, [["Icons", "Font failed to load (version 3)"]]);
}

function testIconsReloadFontIncrementsVersionAndReloads() {
  const reloadFont = qmlFunction("reloadFont");
  const calls = [];
  const ctx = {
    Logger: createLogger(),
    fontVersion: 4,
    loadFontWithCacheBusting() {
      calls.push(this.fontVersion);
    },
  };

  reloadFont(ctx);

  assert.equal(ctx.fontVersion, 5);
  assert.deepEqual(calls, [5]);
}

const tests = [
  testIconsGetResolvesAliasesCodepointsAndMissingIcons,
  testIconsGetUsesTypedIconName,
  testIconsLoadFontDestroysOldLoaderAndCreatesCacheBustedLoader,
  testIconsLoadFontEmitsReloadedWhenLoaderBecomesReady,
  testIconsLoadFontLogsErrorStatusWithoutReloadSignal,
  testIconsReloadFontIncrementsVersionAndReloads,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
