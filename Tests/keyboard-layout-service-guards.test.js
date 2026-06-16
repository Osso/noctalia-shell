#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Keyboard/KeyboardLayoutService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext(languageMap = {}) {
  return {
    root: {
      currentLayout: "",
    },
    languageMap,
    I18n: {
      tr(key) {
        return `tr:${key}`;
      },
    },
  };
}

function testExtractLayoutCodeReturnsUnknownForMissingLayout() {
  const extractLayoutCode = qmlFunction("extractLayoutCode", "layoutString");
  const ctx = createContext();

  assert.equal(extractLayoutCode(ctx, ""), "tr:system.unknown-layout");
  assert.equal(extractLayoutCode(ctx, null), "tr:system.unknown-layout");
}

function testExtractLayoutCodeKeepsShortCodesAndDropsVariants() {
  const extractLayoutCode = qmlFunction("extractLayoutCode", "layoutString");
  const ctx = createContext();

  assert.equal(extractLayoutCode(ctx, "US"), "us");
  assert.equal(extractLayoutCode(ctx, "fr+oss"), "fr");
}

function testExtractLayoutCodeReadsParenthesizedCodes() {
  const extractLayoutCode = qmlFunction("extractLayoutCode", "layoutString");
  const ctx = createContext();

  assert.equal(extractLayoutCode(ctx, "English (US)"), "us");
  assert.equal(extractLayoutCode(ctx, "German (DE)"), "de");
}

function testExtractLayoutCodeUsesLanguageMapBeforePrefixFallback() {
  const extractLayoutCode = qmlFunction("extractLayoutCode", "layoutString");
  const ctx = createContext({
    english: "us",
    french: "fr",
  });

  assert.equal(extractLayoutCode(ctx, "Canadian French"), "fr");
}

function testExtractLayoutCodeFallsBackToPrefixOrUnknown() {
  const extractLayoutCode = qmlFunction("extractLayoutCode", "layoutString");
  const ctx = createContext();

  assert.equal(extractLayoutCode(ctx, "Esperanto custom"), "esp");
  assert.equal(extractLayoutCode(ctx, "123 keyboard"), "tr:system.unknown-layout");
}

function testSetCurrentLayoutStoresExtractedCode() {
  const setCurrentLayout = qmlFunction("setCurrentLayout", "layoutString");
  const ctx = createContext({
    german: "de",
  });
  ctx.extractLayoutCode = layoutString => qmlFunction("extractLayoutCode", "layoutString")(ctx, layoutString);

  setCurrentLayout(ctx, "German");

  assert.equal(ctx.root.currentLayout, "de");
}

const tests = [
  testExtractLayoutCodeReturnsUnknownForMissingLayout,
  testExtractLayoutCodeKeepsShortCodesAndDropsVariants,
  testExtractLayoutCodeReadsParenthesizedCodes,
  testExtractLayoutCodeUsesLanguageMapBeforePrefixFallback,
  testExtractLayoutCodeFallsBackToPrefixOrUnknown,
  testSetCurrentLayoutStoresExtractedCode,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
