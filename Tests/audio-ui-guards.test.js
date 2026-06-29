#!/usr/bin/env node

const assert = require("assert/strict");
const { readQml } = require("./qml-test-utils");

function testAudioCardUsesOnDemandVolumeSync() {
  const source = readQml("Modules/Cards/AudioCard.qml");

  assert.doesNotMatch(source, /Timer\s*\{[\s\S]*interval:\s*100[\s\S]*running:\s*true[\s\S]*repeat:\s*true[\s\S]*AudioService\.setVolume/, "AudioCard must not run a permanent 100ms volume sync timer");
  assert.match(source, /Timer\s*\{[\s\S]*id:\s*volumeSyncTimer[\s\S]*interval:\s*100[\s\S]*running:\s*false[\s\S]*repeat:\s*false/, "AudioCard must use an idle debounce timer for volume sync");
  assert.match(source, /function syncPendingVolumeChanges\(\)/, "AudioCard must name the volume sync work");
  assert.match(source, /function scheduleVolumeSync\(\)/, "AudioCard must expose a schedule helper for slider changes");
  assert.match(source, /onMoved:\s*\{[\s\S]*localOutputVolume = value[\s\S]*scheduleVolumeSync\(\)[\s\S]*\}/, "AudioCard output slider moves must schedule volume sync");
  assert.match(source, /onMoved:\s*\{[\s\S]*localInputVolume = value[\s\S]*scheduleVolumeSync\(\)[\s\S]*\}/, "AudioCard input slider moves must schedule volume sync");
  assert.match(source, /onPressedChanged:\s*\{[\s\S]*localOutputVolumeChanging = pressed[\s\S]*if \(!pressed\)[\s\S]*scheduleVolumeSync\(\)/, "AudioCard output slider release must flush volume sync");
  assert.match(source, /onPressedChanged:\s*\{[\s\S]*localInputVolumeChanging = pressed[\s\S]*if \(!pressed\)[\s\S]*scheduleVolumeSync\(\)/, "AudioCard input slider release must flush volume sync");
}

function testAudioPanelUsesOnDemandVolumeSync() {
  const source = readQml("Modules/Panels/Audio/AudioPanel.qml");

  assert.doesNotMatch(source, /Timer\s*\{[\s\S]*interval:\s*100[\s\S]*running:\s*true[\s\S]*repeat:\s*true[\s\S]*AudioService\.setVolume/, "AudioPanel must not run a permanent 100ms volume sync timer");
  assert.match(source, /Timer\s*\{[\s\S]*id:\s*volumeSyncTimer[\s\S]*interval:\s*100[\s\S]*running:\s*false[\s\S]*repeat:\s*false/, "AudioPanel must use an idle debounce timer for volume sync");
  assert.match(source, /function syncPendingVolumeChanges\(\)/, "AudioPanel must name the volume sync work");
  assert.match(source, /function scheduleVolumeSync\(\)/, "AudioPanel must expose a schedule helper for slider changes");
  assert.match(source, /onMoved:\s*value => \{[\s\S]*localOutputVolume = value[\s\S]*scheduleVolumeSync\(\)[\s\S]*\}/, "AudioPanel output slider moves must schedule volume sync");
  assert.match(source, /onMoved:\s*value => \{[\s\S]*localInputVolume = value[\s\S]*scheduleVolumeSync\(\)[\s\S]*\}/, "AudioPanel input slider moves must schedule volume sync");
  assert.match(source, /onPressedChanged:\s*\(pressed, value\) => \{[\s\S]*localOutputVolumeChanging = pressed[\s\S]*if \(!pressed\)[\s\S]*scheduleVolumeSync\(\)/, "AudioPanel output slider release must flush volume sync");
  assert.match(source, /onPressedChanged:\s*\(pressed, value\) => \{[\s\S]*localInputVolumeChanging = pressed[\s\S]*if \(!pressed\)[\s\S]*scheduleVolumeSync\(\)/, "AudioPanel input slider release must flush volume sync");
}

const tests = [
  testAudioCardUsesOnDemandVolumeSync,
  testAudioPanelUsesOnDemandVolumeSync,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
