#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testAudioServiceOsdSuppressionUsesTimedWindows() {
  const source = readQml("Services/Media/AudioService.qml");
  const suppressOutputBody = extractFunctionBody(source, "suppressOutputOSD");
  const suppressInputBody = extractFunctionBody(source, "suppressInputOSD");
  const consumeOutputBody = extractFunctionBody(source, "consumeOutputOSDSuppression");
  const consumeInputBody = extractFunctionBody(source, "consumeInputOSDSuppression");

  assert.match(suppressOutputBody, /const target = Date\.now\(\) \+ durationMs/, "suppressOutputOSD must build an absolute suppression deadline");
  assert.match(suppressOutputBody, /outputOSDSuppressedUntilMs = Math\.max\(outputOSDSuppressedUntilMs,\s*target\)/, "suppressOutputOSD must not shorten an existing suppression window");
  assert.match(suppressInputBody, /const target = Date\.now\(\) \+ durationMs/, "suppressInputOSD must build an absolute suppression deadline");
  assert.match(suppressInputBody, /inputOSDSuppressedUntilMs = Math\.max\(inputOSDSuppressedUntilMs,\s*target\)/, "suppressInputOSD must not shorten an existing suppression window");
  assert.match(consumeOutputBody, /return Date\.now\(\) < outputOSDSuppressedUntilMs/, "consumeOutputOSDSuppression must report whether the output window is still active");
  assert.match(consumeInputBody, /return Date\.now\(\) < inputOSDSuppressedUntilMs/, "consumeInputOSDSuppression must report whether the input window is still active");
}

function testAudioServiceOutputVolumeControlsClampAndFailClosed() {
  const source = readQml("Services/Media/AudioService.qml");
  const increaseBody = extractFunctionBody(source, "increaseVolume");
  const decreaseBody = extractFunctionBody(source, "decreaseVolume");
  const setBody = extractFunctionBody(source, "setVolume");
  const muteBody = extractFunctionBody(source, "setOutputMuted");
  const iconBody = extractFunctionBody(source, "getOutputIcon");

  assert.match(increaseBody, /if \(!Pipewire\.ready \|\| !sinkAudio\)[\s\S]*return;/, "increaseVolume must fail closed without Pipewire output audio");
  assert.match(increaseBody, /const maxVolume = Settings\.data\.audio\.volumeOverdrive \? 1\.5 : 1\.0/, "increaseVolume must respect overdrive maximum");
  assert.match(increaseBody, /if \(volume >= maxVolume\)[\s\S]*return;/, "increaseVolume must avoid exceeding the maximum volume");
  assert.match(increaseBody, /setVolume\(Math\.min\(maxVolume,\s*volume \+ stepVolume\)\)/, "increaseVolume must clamp the stepped volume");
  assert.match(decreaseBody, /if \(!Pipewire\.ready \|\| !sinkAudio\)[\s\S]*return;/, "decreaseVolume must fail closed without Pipewire output audio");
  assert.match(decreaseBody, /if \(volume <= 0\)[\s\S]*return;/, "decreaseVolume must avoid negative output volume work");
  assert.match(decreaseBody, /setVolume\(Math\.max\(0,\s*volume - stepVolume\)\)/, "decreaseVolume must clamp the stepped volume to zero");
  assert.match(setBody, /if \(!Pipewire\.ready \|\| !sink \|\| !sink\.ready \|\| !sinkAudio\)[\s\S]*Logger\.w\("AudioService",\s*"No sink available or not ready"\)[\s\S]*return;/, "setVolume must fail closed when the sink is unavailable");
  assert.match(setBody, /const clampedVolume = Math\.max\(0,\s*Math\.min\(maxVolume,\s*newVolume\)\)/, "setVolume must clamp requested output volume");
  assert.match(setBody, /const delta = Math\.abs\(clampedVolume - sinkAudio\.volume\)/, "setVolume must compare against current output volume");
  assert.match(setBody, /if \(delta < root\.epsilon\)[\s\S]*return;/, "setVolume must skip tiny output changes");
  assert.match(setBody, /isSettingOutputVolume = true[\s\S]*sinkAudio\.muted = false[\s\S]*sinkAudio\.volume = clampedVolume/, "setVolume must unmute and apply output volume under feedback-loop guard");
  assert.match(setBody, /Qt\.callLater\(\(\) =>[\s\S]*isSettingOutputVolume = false/, "setVolume must clear the output feedback-loop guard later");
  assert.match(muteBody, /if \(!Pipewire\.ready \|\| !sinkAudio\)[\s\S]*Logger\.w\("AudioService",\s*"No sink available or Pipewire not ready"\)[\s\S]*return;/, "setOutputMuted must fail closed when output audio is unavailable");
  assert.match(muteBody, /sinkAudio\.muted = muted/, "setOutputMuted must apply the requested mute state");
  assert.match(iconBody, /if \(muted\)\s+return "volume-mute"/, "getOutputIcon must show mute icon first");
  assert.match(iconBody, /const clampedVolume = Math\.max\(0,\s*Math\.min\(volume,\s*maxVolume\)\)/, "getOutputIcon must classify a clamped output volume");
  assert.match(iconBody, /if \(clampedVolume < root\.epsilon\)[\s\S]*return "volume-x"/, "getOutputIcon must show zero-volume icon near silence");
  assert.match(iconBody, /if \(clampedVolume <= 0\.5\)[\s\S]*return "volume-low"/, "getOutputIcon must show low-volume icon below half");
  assert.match(iconBody, /return "volume-high"/, "getOutputIcon must fall back to high-volume icon");
}

function testAudioServiceInputVolumeControlsClampAndFailClosed() {
  const source = readQml("Services/Media/AudioService.qml");
  const increaseBody = extractFunctionBody(source, "increaseInputVolume");
  const decreaseBody = extractFunctionBody(source, "decreaseInputVolume");
  const setBody = extractFunctionBody(source, "setInputVolume");
  const muteBody = extractFunctionBody(source, "setInputMuted");
  const iconBody = extractFunctionBody(source, "getInputIcon");

  assert.match(increaseBody, /if \(!Pipewire\.ready \|\| !sourceAudio\)[\s\S]*return;/, "increaseInputVolume must fail closed without Pipewire input audio");
  assert.match(increaseBody, /const maxVolume = Settings\.data\.audio\.volumeOverdrive \? 1\.5 : 1\.0/, "increaseInputVolume must respect overdrive maximum");
  assert.match(increaseBody, /if \(inputVolume >= maxVolume\)[\s\S]*return;/, "increaseInputVolume must avoid exceeding the maximum input volume");
  assert.match(increaseBody, /setInputVolume\(Math\.min\(maxVolume,\s*inputVolume \+ stepVolume\)\)/, "increaseInputVolume must clamp the stepped volume");
  assert.match(decreaseBody, /if \(!Pipewire\.ready \|\| !sourceAudio\)[\s\S]*return;/, "decreaseInputVolume must fail closed without Pipewire input audio");
  assert.match(decreaseBody, /setInputVolume\(Math\.max\(0,\s*inputVolume - stepVolume\)\)/, "decreaseInputVolume must clamp the stepped volume to zero");
  assert.match(setBody, /if \(!Pipewire\.ready \|\| !source \|\| !source\.ready \|\| !sourceAudio\)[\s\S]*Logger\.w\("AudioService",\s*"No source available or not ready"\)[\s\S]*return;/, "setInputVolume must fail closed when the source is unavailable");
  assert.match(setBody, /const clampedVolume = Math\.max\(0,\s*Math\.min\(maxVolume,\s*newVolume\)\)/, "setInputVolume must clamp requested input volume");
  assert.match(setBody, /const delta = Math\.abs\(clampedVolume - sourceAudio\.volume\)/, "setInputVolume must compare against current input volume");
  assert.match(setBody, /if \(delta < root\.epsilon\)[\s\S]*return;/, "setInputVolume must skip tiny input changes");
  assert.match(setBody, /isSettingInputVolume = true[\s\S]*sourceAudio\.muted = false[\s\S]*sourceAudio\.volume = clampedVolume/, "setInputVolume must unmute and apply input volume under feedback-loop guard");
  assert.match(setBody, /Qt\.callLater\(\(\) =>[\s\S]*isSettingInputVolume = false/, "setInputVolume must clear the input feedback-loop guard later");
  assert.match(muteBody, /if \(!Pipewire\.ready \|\| !sourceAudio\)[\s\S]*Logger\.w\("AudioService",\s*"No source available or Pipewire not ready"\)[\s\S]*return;/, "setInputMuted must fail closed when input audio is unavailable");
  assert.match(muteBody, /sourceAudio\.muted = muted/, "setInputMuted must apply the requested mute state");
  assert.match(iconBody, /if \(inputMuted \|\| inputVolume <= Number\.EPSILON\)[\s\S]*return "microphone-mute"/, "getInputIcon must show mute icon when muted or silent");
  assert.match(iconBody, /return "microphone"/, "getInputIcon must show microphone icon for active input");
}

function testAudioServiceDeviceSelectionRequiresPipewireReadiness() {
  const source = readQml("Services/Media/AudioService.qml");
  const sinkBody = extractFunctionBody(source, "setAudioSink");
  const sourceBody = extractFunctionBody(source, "setAudioSource");

  assert.match(sinkBody, /if \(!Pipewire\.ready\)[\s\S]*Logger\.w\("AudioService",\s*"Pipewire not ready"\)[\s\S]*return;/, "setAudioSink must fail closed until Pipewire is ready");
  assert.match(sinkBody, /Pipewire\.preferredDefaultAudioSink = newSink/, "setAudioSink must update the preferred default sink");
  assert.match(sourceBody, /if \(!Pipewire\.ready\)[\s\S]*Logger\.w\("AudioService",\s*"Pipewire not ready"\)[\s\S]*return;/, "setAudioSource must fail closed until Pipewire is ready");
  assert.match(sourceBody, /Pipewire\.preferredDefaultAudioSource = newSource/, "setAudioSource must update the preferred default source");
}

const tests = [
  testAudioServiceOsdSuppressionUsesTimedWindows,
  testAudioServiceOutputVolumeControlsClampAndFailClosed,
  testAudioServiceInputVolumeControlsClampAndFailClosed,
  testAudioServiceDeviceSelectionRequiresPipewireReadiness,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
