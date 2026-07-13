#!/usr/bin/env node

const assert = require("assert/strict");
const { readQml } = require("./qml-test-utils");

function stripComments(qml) {
  let result = "";
  let quote = "";
  for (let index = 0; index < qml.length; index++) {
    const current = qml[index];
    const next = qml[index + 1];
    if (quote) {
      result += current;
      if (current === "\\") {
        result += next || "";
        index++;
      } else if (current === quote) quote = "";
    } else if (current === '"' || current === "'" || current === "`") {
      quote = current;
      result += current;
    } else if (current === "/" && next === "/") {
      while (index < qml.length && qml[index] !== "\n") index++;
      result += "\n";
    } else if (current === "/" && next === "*") {
      index += 2;
      while (index < qml.length - 1 && !(qml[index] === "*" && qml[index + 1] === "/")) index++;
      index++;
    } else result += current;
  }
  return result;
}

const source = stripComments(readQml("Modules/Panels/Settings/Tabs/ScreenRecorderTab.qml"));

function blocks(componentName) {
  const result = [];
  const marker = `${componentName} {`;
  let start = source.indexOf(marker);
  while (start !== -1) {
    const open = source.indexOf("{", start);
    let depth = 0;
    let quote = "";
    let end = -1;
    for (let index = open; index < source.length; index++) {
      const current = source[index];
      if (quote) {
        if (current === "\\") index++;
        else if (current === quote) quote = "";
        continue;
      }
      if (current === '"' || current === "'" || current === "`") {
        quote = current;
        continue;
      }
      if (current === "{") depth++;
      if (current === "}") depth--;
      if (depth === 0) { end = index; break; }
    }
    assert.notEqual(end, -1, `unterminated ${componentName} block`);
    result.push(source.slice(start, end + 1));
    start = source.indexOf(marker, end + 1);
  }
  return result;
}

function control(componentName, labelKey) {
  const matches = blocks(componentName).filter(block => block.includes(labelKey));
  assert.equal(matches.length, 1, `${labelKey} control must be unique`);
  return matches[0];
}

function modelKeys(combo) {
  return [...combo.matchAll(/"key":\s*"([^"]+)"/g)].map(match => match[1]);
}

function assertCombo(labelKey, setting, keys) {
  const combo = control("NComboBox", labelKey);
  assert.deepEqual(modelKeys(combo), keys);
  assert.match(combo, new RegExp(`currentKey: Settings\\.data\\.screenRecorder\\.${setting}`));
  assert.match(combo, new RegExp(`onSelected: key => Settings\\.data\\.screenRecorder\\.${setting} = key`));
}

function testGeneralControlsWriteMatchingSettings() {
  const directory = control("NTextInputButton", "output-folder.label");
  assert.match(directory, /text: Settings\.data\.screenRecorder\.directory/);
  assert.match(directory, /onInputEditingFinished: Settings\.data\.screenRecorder\.directory = text/);
  const cursor = control("NToggle", "show-cursor.label");
  assert.match(cursor, /checked: Settings\.data\.screenRecorder\.showCursor/);
  assert.match(cursor, /onToggled: checked => Settings\.data\.screenRecorder\.showCursor = checked/);
  const picker = blocks("NFilePicker")[0];
  assert.match(picker, /selectionMode: "folders"/);
  assert.match(picker, /Settings\.data\.screenRecorder\.directory = paths\[0\]/);
}

function testVideoSourceUsesDiscoveredAndFallbackSources() {
  const combo = control("NComboBox", "video-source.label");
  assert.match(combo, /ScreenRecorderService\.captureSources\.length > 0/);
  assert.match(combo, /\? ScreenRecorderService\.captureSources/);
  assert.deepEqual(modelKeys(combo), ["portal", "screen"]);
  assert.match(combo, /currentKey: Settings\.data\.screenRecorder\.videoSource/);
  assert.match(combo, /onSelected: key => Settings\.data\.screenRecorder\.videoSource = key/);
}

function testFrameRateBridgesStringKeysToNumericSetting() {
  const combo = control("NComboBox", "frame-rate.label");
  assert.deepEqual(modelKeys(combo), ["30", "60", "100", "120", "144", "165", "240"]);
  assert.match(combo, /currentKey: String\(Settings\.data\.screenRecorder\.frameRate\)/);
  assert.match(combo, /onSelected: key => Settings\.data\.screenRecorder\.frameRate = parseInt\(key, 10\)/);
}

function testCodecQualityAndAudioControls() {
  assertCombo("video-quality.label", "quality", ["medium", "high", "very_high", "ultra"]);
  assertCombo("video-codec.label", "videoCodec", ["h264", "hevc", "av1", "vp8", "vp9"]);
  assertCombo("color-range.label", "colorRange", ["limited", "full"]);
  assertCombo("audio-source.label", "audioSource", ["default_output", "default_input", "both"]);
  assertCombo("audio-codec.label", "audioCodec", ["opus", "aac"]);
}

for (const test of [
  testGeneralControlsWriteMatchingSettings,
  testVideoSourceUsesDiscoveredAndFallbackSources,
  testFrameRateBridgesStringKeysToNumericSetting,
  testCodecQualityAndAudioControls,
]) {
  test();
  console.log(`ok ${test.name}`);
}
