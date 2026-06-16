#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(readQml("Services/Media/AudioService.qml"), functionName);
  const args = argNames.join(", ");
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${args}) ${body}).call(ctx, ${args}); }`);
}

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

function testAudioServiceOsdSuppressionExecutesTimedWindows() {
  const suppressOutputOSD = qmlFunction("suppressOutputOSD", "durationMs");
  const suppressInputOSD = qmlFunction("suppressInputOSD", "durationMs");
  const consumeOutputOSDSuppression = qmlFunction("consumeOutputOSDSuppression");
  const consumeInputOSDSuppression = qmlFunction("consumeInputOSDSuppression");
  const clock = { now: 1000 };
  const ctx = {
    Date: { now: () => clock.now },
    inputOSDSuppressedUntilMs: 0,
    outputOSDSuppressedUntilMs: 0,
  };

  suppressOutputOSD(ctx, 400);
  suppressInputOSD(ctx, 250);

  assert.equal(ctx.outputOSDSuppressedUntilMs, 1400, "output suppression stores an absolute deadline");
  assert.equal(ctx.inputOSDSuppressedUntilMs, 1250, "input suppression stores an absolute deadline");
  assert.equal(consumeOutputOSDSuppression(ctx), true, "output suppression is active before its deadline");
  assert.equal(consumeInputOSDSuppression(ctx), true, "input suppression is active before its deadline");

  clock.now = 1100;
  suppressOutputOSD(ctx, 100);
  assert.equal(ctx.outputOSDSuppressedUntilMs, 1400, "shorter output suppression does not shrink the window");

  clock.now = 1300;
  assert.equal(consumeInputOSDSuppression(ctx), false, "input suppression expires after its deadline");
  assert.equal(consumeOutputOSDSuppression(ctx), true, "output suppression remains active until its own deadline");

  clock.now = 1400;
  assert.equal(consumeOutputOSDSuppression(ctx), false, "output suppression expires at the deadline");
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

function testAudioServiceIconHelpersExecuteThresholds() {
  const getOutputIcon = qmlFunction("getOutputIcon");
  const getInputIcon = qmlFunction("getInputIcon");
  const Settings = { data: { audio: { volumeOverdrive: false } } };
  const ctx = {
    Settings,
    inputMuted: false,
    inputVolume: 1,
    muted: false,
    root: { epsilon: 0.005 },
    volume: 1,
  };

  ctx.muted = true;
  assert.equal(getOutputIcon(ctx), "volume-mute", "muted output uses mute icon");

  ctx.muted = false;
  ctx.volume = 0.001;
  assert.equal(getOutputIcon(ctx), "volume-x", "near-zero output uses silent icon");

  ctx.volume = 0.5;
  assert.equal(getOutputIcon(ctx), "volume-low", "half-volume output uses low icon");

  ctx.volume = 0.75;
  assert.equal(getOutputIcon(ctx), "volume-high", "loud output uses high icon");

  ctx.inputMuted = true;
  assert.equal(getInputIcon(ctx), "microphone-mute", "muted input uses mute icon");

  ctx.inputMuted = false;
  ctx.inputVolume = 0;
  assert.equal(getInputIcon(ctx), "microphone-mute", "silent input uses mute icon");

  ctx.inputVolume = 0.25;
  assert.equal(getInputIcon(ctx), "microphone", "active input uses microphone icon");
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
  testAudioServiceOsdSuppressionExecutesTimedWindows,
  testAudioServiceOutputVolumeControlsClampAndFailClosed,
  testAudioServiceInputVolumeControlsClampAndFailClosed,
  testAudioServiceIconHelpersExecuteThresholds,
  testAudioServiceDeviceSelectionRequiresPipewireReadiness,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
