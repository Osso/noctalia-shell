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

function testColorsConvertGeneratedVariants() {
  const colors = loadHelper("Helpers/ColorsConvert.js");

  assert.deepEqual(plain(colors.rgbToHsv(0, 0, 255)), { h: 240, s: 100, v: 100 });
  assert.deepEqual(plain(colors.hsvToRgb(30, 100, 100)), { r: 255, g: 128, b: 0 });

  assert.equal(colors.adjustLightness("#336699", 20), "#6699cc");
  assert.equal(colors.adjustLightness("#ffffff", 20), "#ffffff");
  assert.equal(colors.adjustSaturation("#336699", -50), "#666666");
  assert.equal(colors.adjustLightnessAndSaturation("#336699", 10, -20), "#597fa6");

  assert.equal(colors.generateOnColor("#eeeeee", false), "#000000");
  assert.equal(colors.generateOnColor("#222222", true), "#ffffff");
  assert.equal(colors.generateContainerColor("#336699", false), "#a6bfd9");
  assert.equal(colors.generateContainerColor("#336699", true), "#143352");
  assert.equal(colors.generateSurfaceVariant("#eeeeee", 3, false), "#dfdfdf");
  assert.equal(colors.generateSurfaceVariant("#222222", 3, true), "#393939");
}

function testColorListShape() {
  const colorList = loadHelper("Helpers/ColorList.js");
  const colors = plain(colorList.colors);

  assert.ok(Array.isArray(colors), "color list must export an array");
  assert.equal(colors.length, 170);

  const seenPairs = new Set();
  for (const entry of colors) {
    assert.equal(typeof entry.name, "string");
    assert.equal(typeof entry.color, "string");
    assert.notEqual(entry.name.trim(), "");
    assert.match(entry.color, /^(#[0-9a-fA-F]{6}|[a-z]+)$/);

    const pair = `${entry.name}\0${entry.color}`;
    assert.equal(seenPairs.has(pair), false, `duplicate color entry: ${entry.name}`);
    seenPairs.add(pair);
  }

  assert.deepEqual(colors[0], { name: "MistyRose", color: "mistyrose" });
  assert.deepEqual(colors[colors.length - 1], { name: "Black", color: "black" });
  assert.ok(colors.some(entry => entry.name === "Blue 500" && entry.color === "#2196F3"));
  assert.ok(colors.some(entry => entry.name === "Wet Asphalt" && entry.color === "#34495E"));
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

function testTextFormatterEscapesHtml() {
  const textFormatter = loadHelper("Helpers/TextFormatter.js");
  const formatted = textFormatter.wrapTextForDisplay("<tag attr=\"value\">Tom & 'Jerry'</tag>");

  assert.match(formatted, /font-family:/);
  assert.match(formatted, /white-space: pre-wrap/);
  assert.match(formatted, /&lt;tag attr=&quot;value&quot;&gt;Tom &amp; &#39;Jerry&#39;&lt;\/tag&gt;/);
  assert.equal(formatted.includes("<tag attr=\"value\">"), false);
}

function testCustomButtonContentParser() {
  const customButton = loadHelper("Helpers/CustomButtonContent.js");

  assert.deepEqual(
    plain(customButton.parseDynamicContent("old\n{\"text\":\"CPU 12%\",\"icon\":\"cpu\",\"tooltip\":\"<b>Load</b> & ok\"}", {
      parseJson: true,
      textStream: false,
      maxTextLength: 20,
    })),
    {
      collapsed: false,
      text: "CPU 12%",
      icon: "cpu",
      tooltip: "<b>Load</b> &amp; ok",
      originalText: "CPU 12%",
      needsScrolling: false,
      visibleText: "CPU 12%",
      parseFailed: false,
    },
  );

  assert.deepEqual(
    plain(customButton.parseDynamicContent("plain & text", {
      parseJson: true,
      maxTextLength: 20,
    })),
    {
      collapsed: false,
      text: "plain & text",
      icon: "",
      tooltip: "plain &amp; text",
      originalText: "plain & text",
      needsScrolling: false,
      visibleText: "plain & text",
      parseFailed: true,
    },
  );

  assert.deepEqual(
    plain(customButton.parseDynamicContent("hidden", {
      textCollapse: "/^hid/",
      maxTextLength: 10,
    })),
    {
      collapsed: true,
      text: "",
      icon: "",
      tooltip: "",
      originalText: "",
      needsScrolling: false,
      visibleText: "",
      parseFailed: false,
    },
  );

  const scrolling = customButton.parseDynamicContent("abcdefghijkl", {
    maxTextLength: 5,
  });
  assert.equal(scrolling.needsScrolling, true);
  assert.equal(scrolling.visibleText, "abcde");
  assert.equal(scrolling.tooltip, "abcdefghijkl");
}

function testTimerDigitsParser() {
  const timerDigits = loadHelper("Helpers/TimerDigits.js");

  assert.deepEqual(plain(timerDigits.parseDigits("")), { hours: 0, minutes: 0, seconds: 0 });
  assert.deepEqual(plain(timerDigits.parseDigits("5")), { hours: 0, minutes: 0, seconds: 5 });
  assert.deepEqual(plain(timerDigits.parseDigits("1234")), { hours: 0, minutes: 12, seconds: 34 });
  assert.deepEqual(plain(timerDigits.parseDigits("123456")), { hours: 12, minutes: 34, seconds: 56 });
  assert.deepEqual(plain(timerDigits.parseDigits("999999")), { hours: 99, minutes: 59, seconds: 59 });
  assert.deepEqual(plain(timerDigits.parseDigits("1h2m3s")), { hours: 0, minutes: 1, seconds: 23 });

  assert.equal(timerDigits.totalSecondsFromDigits("123456"), 45296);
  assert.equal(timerDigits.totalSecondsFromDigits("999999"), 359999);
  assert.equal(timerDigits.formatFromDigits("1234"), "00:12:34");
  assert.equal(timerDigits.formatDuration(75, true), "01:15");
  assert.equal(timerDigits.formatDuration(75, false), "00:01:15");
  assert.equal(timerDigits.formatDuration(3661, true), "01:01:01");
}

function testBrightnessParsing() {
  const brightness = loadHelper("Helpers/BrightnessParsing.js");
  const ddcOutput = `Invalid display
   I2C bus:  /dev/i2c-3
   EDID synopsis:
      Model:                Internal Panel
   This is a laptop display.  Laptop displays do not support DDC/CI.

Display 1
   I2C bus:  /dev/i2c-4
   EDID synopsis:
      Model:                DELL 2707WFP
   VCP version:         2.0`;

  assert.deepEqual(plain(brightness.parseDdcMonitors(ddcOutput)), [
    { model: "Internal Panel", busNum: "3", isDdc: false },
    { model: "DELL 2707WFP", busNum: "4", isDdc: true },
  ]);
  assert.deepEqual(plain(brightness.parseDdcBrightness("VCP 10 C 56 100")), {
    current: 56,
    max: 100,
    ratio: 0.56,
  });
  assert.equal(brightness.parseDdcBrightness("VCP 10 C bad 100"), null);
  assert.deepEqual(plain(brightness.parseAppleBrightness("50")), {
    current: 50,
    max: 101,
    ratio: 50 / 101,
  });
  assert.deepEqual(plain(brightness.parseInternalBacklight("/sys/class/backlight/amdgpu_bl1\n36268\n64764")), {
    devicePath: "/sys/class/backlight/amdgpu_bl1",
    brightnessPath: "/sys/class/backlight/amdgpu_bl1/brightness",
    maxBrightnessPath: "/sys/class/backlight/amdgpu_bl1/max_brightness",
    current: 36268,
    max: 64764,
    ratio: 36268 / 64764,
  });
  assert.equal(brightness.isValidBrightnessRatio(0), true);
  assert.equal(brightness.isValidBrightnessRatio(0.5), true);
  assert.equal(brightness.isValidBrightnessRatio(null), false);
  assert.equal(brightness.isValidBrightnessRatio(NaN), false);
}

function testDebugStringifyHandlesCircularReferences() {
  const debug = loadHelper("Helpers/Debug.js");
  const source = {
    name: "root",
    nested: {},
  };
  source.self = source;
  source.nested.parent = source;

  const formatted = debug.stringify(source, null, 2);

  assert.match(formatted, /"name": "root"/);
  assert.match(formatted, /"self": "\[Circular ~\]"/);
  assert.match(formatted, /"parent": "\[Circular ~\]"/);
}

const tests = [
  testColorsConvert,
  testColorsConvertGeneratedVariants,
  testColorListShape,
  testAdvancedMath,
  testSha256,
  testThemeIconResolver,
  testFuzzySort,
  testQtObjectToPlainObject,
  testTextFormatterEscapesHtml,
  testCustomButtonContentParser,
  testTimerDigitsParser,
  testBrightnessParsing,
  testDebugStringifyHandlesCircularReferences,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
