#!/usr/bin/env node

const assert = require("assert/strict");
const {
  extractComponentBlocks,
  findComponentBlock,
  readQml,
  stripQmlComments,
} = require("./qml-test-utils");

const source = stripQmlComments(readQml("Modules/Panels/Settings/Tabs/ScreenRecorderTab.qml"));

function control(componentName, labelKey) {
  return findComponentBlock(source, componentName, labelKey);
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
  const picker = extractComponentBlocks(source, "NFilePicker")[0];
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
