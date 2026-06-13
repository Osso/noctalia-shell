#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const repoRoot = path.resolve(__dirname, "..");

function loadHelper(relativePath) {
  const context = vm.createContext({
    console,
    Math,
    Number,
    parseFloat,
    parseInt,
    isFinite,
    isNaN,
    Map,
    Object,
  });
  const source = fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
  const runnableSource = source.replace(/^\.pragma library\s*$/m, "");
  vm.runInContext(runnableSource, context, {
    filename: relativePath,
  });
  return context;
}

function assertAlmostEqual(actual, expected, message, epsilon = 1e-9) {
  assert.ok(
    Math.abs(actual - expected) <= epsilon,
    `${message}: expected ${expected}, got ${actual}`,
  );
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function testColorsConvert() {
  const colors = loadHelper("Helpers/ColorsConvert.js");

  assert.deepEqual(plain(colors.hexToRgb("#336699")), { r: 51, g: 102, b: 153 });
  assert.deepEqual(plain(colors.hexToRgb("336699")), { r: 51, g: 102, b: 153 });
  assert.equal(colors.rgbToHex(51, 102, 153), "#336699");
  assert.equal(colors.rgbToHex(-10, 260, 127.6), "#00ff80");

  const redHsl = colors.rgbToHsl(255, 0, 0);
  assertAlmostEqual(redHsl.h, 0, "red hue");
  assertAlmostEqual(redHsl.s, 100, "red saturation");
  assertAlmostEqual(redHsl.l, 50, "red lightness");
  assert.equal(colors.hslToHex(0, 100, 50), "#ff0000");

  assertAlmostEqual(colors.getLuminance("#000000"), 0, "black luminance");
  assertAlmostEqual(colors.getLuminance("#ffffff"), 1, "white luminance");
  assertAlmostEqual(colors.getContrastRatio("#000000", "#ffffff"), 21, "black/white contrast");
  assert.equal(colors.isLightColor("#ffffff"), true);
  assert.equal(colors.isLightColor("#000000"), false);
}

function testAdvancedMath() {
  const advancedMath = loadHelper("Helpers/AdvancedMath.js");

  assertAlmostEqual(advancedMath.toRadians(180), Math.PI, "degrees to radians");
  assertAlmostEqual(advancedMath.toDegrees(Math.PI), 180, "radians to degrees");
  assert.equal(advancedMath.evaluate("sqrt(9)+pow(2,3)"), 11);
  assert.equal(advancedMath.evaluate("sind(30)+cosd(60)"), 1);
  assert.equal(advancedMath.formatResult(42), "42");
  assert.equal(advancedMath.formatResult(1 / 3), "0.3333333333");
  assert.equal(advancedMath.formatResult(1e-7), "1.000000e-7");
  assert.throws(() => advancedMath.evaluate("process.exit()"), /Evaluation failed/);
}

function testSha256() {
  const crypto = loadHelper("Helpers/sha256.js");

  assert.equal(
    crypto.sha256(""),
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  );
  assert.equal(
    crypto.sha256("abc"),
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  );
  assert.equal(
    crypto.sha256("The quick brown fox jumps over the lazy dog"),
    "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
  );
}

function testThemeIconResolver() {
  const resolver = loadHelper("Helpers/ThemeIconResolver.js");
  const calls = [];
  const iconApi = {
    hasThemeIcon(name) {
      calls.push(["hasThemeIcon", name]);
      return name === "known-primary" || name === "application-x-executable";
    },
    iconPath(name, check) {
      calls.push(["iconPath", name, check]);
      if (typeof check !== "boolean")
        return `${name}?fallback=${check}`;
      return check ? `image://icon/${name}` : "";
    },
  };

  assert.equal(
    resolver.resolveIconPath(iconApi, "known-primary", "application-x-executable"),
    "image://icon/known-primary",
  );
  assert.equal(
    resolver.resolveIconPath(iconApi, "missing-primary", "application-x-executable"),
    "image://icon/application-x-executable",
  );
  assert.equal(
    resolver.resolveIconPath(iconApi, "", "application-x-executable"),
    "image://icon/application-x-executable",
  );
  assert.equal(
    resolver.resolveIconPath({ hasThemeIcon: () => false, iconPath: () => "" }, "missing", "also-missing"),
    "",
  );

  assert.equal(
    calls.some(call => call[0] === "iconPath" && typeof call[2] === "string"),
    false,
    "resolver must not call iconPath(icon, fallbackString)",
  );
}

function testFuzzySort() {
  const fuzzySort = loadHelper("Helpers/FuzzySort.js");

  const single = fuzzySort.single("fox", "Firefox");
  assert.equal(single.target, "Firefox");
  assert.deepEqual(plain(single.indexes), [4, 5, 6]);
  assert.equal(single.highlight("[", "]"), "Fire[fox]");

  const results = fuzzySort.go("qs", ["Firefox", "Quickshell", "Terminal"]);
  assert.equal(results.length, 1);
  assert.equal(results[0].target, "Quickshell");

  const keyed = fuzzySort.go(
    "term",
    [
      { name: "Terminal", id: "org.term" },
      { name: "Firefox", id: "firefox" },
    ],
    { key: "name" },
  );
  assert.equal(keyed.length, 1);
  assert.equal(keyed[0].obj.id, "org.term");
  assert.equal(keyed[0].target, "Terminal");

  fuzzySort.cleanup();
}

function testQtObjectToPlainObject() {
  const qtObj = loadHelper("Helpers/QtObj2JS.js");
  const source = {
    keep: 1,
    objectName: "ignored",
    keepChanged: "ignored",
    nested: { value: 2 },
    list: { 0: "a", 1: { value: 3 }, length: 2 },
    emptyList: { length: 0 },
    color: {
      r: 1,
      g: 0,
      b: 0,
      a: 1,
      valid: true,
      toString() {
        return "#ff0000";
      },
    },
    fn() {
      return "ignored";
    },
  };

  assert.deepEqual(plain(qtObj.qtObjectToPlainObject(source)), {
    keep: 1,
    nested: { value: 2 },
    list: ["a", { value: 3 }],
    emptyList: [],
    color: "#ff0000",
  });
}

const tests = [
  testColorsConvert,
  testAdvancedMath,
  testSha256,
  testThemeIconResolver,
  testFuzzySort,
  testQtObjectToPlainObject,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
