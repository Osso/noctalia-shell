#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testPowerProfileNameAndIconGuards() {
  const source = readQml("Services/Power/PowerProfileService.qml");
  const nameBody = extractFunctionBody(source, "getName");
  const iconBody = extractFunctionBody(source, "getIcon");

  assert.match(nameBody, /if \(!available\)\s+return "Unknown"/, "getName must fail closed when power profiles are unavailable");
  assert.match(nameBody, /const prof = \(p !== undefined\) \? p : profile/, "getName must default to the active profile");
  assert.match(nameBody, /case PowerProfile\.Performance:[\s\S]*return "Performance"/, "getName must map performance profile");
  assert.match(nameBody, /case PowerProfile\.Balanced:[\s\S]*return "Balanced"/, "getName must map balanced profile");
  assert.match(nameBody, /case PowerProfile\.PowerSaver:[\s\S]*return "Power saver"/, "getName must map power saver profile");
  assert.match(nameBody, /default:[\s\S]*return "Unknown"/, "getName must label unknown profile values");
  assert.match(iconBody, /if \(!available\)\s+return "balanced"/, "getIcon must default to a safe icon when unavailable");
  assert.match(iconBody, /const prof = \(p !== undefined\) \? p : profile/, "getIcon must default to the active profile");
  assert.match(iconBody, /case PowerProfile\.Performance:[\s\S]*return "performance"/, "getIcon must map performance profile");
  assert.match(iconBody, /case PowerProfile\.Balanced:[\s\S]*return "balanced"/, "getIcon must map balanced profile");
  assert.match(iconBody, /case PowerProfile\.PowerSaver:[\s\S]*return "powersaver"/, "getIcon must map power saver profile");
  assert.match(iconBody, /default:[\s\S]*return "balanced"/, "getIcon must fallback to balanced for unknown profile values");
}

function testPowerProfileMutationGuards() {
  const source = readQml("Services/Power/PowerProfileService.qml");
  const initBody = extractFunctionBody(source, "init");
  const setBody = extractFunctionBody(source, "setProfile");
  const cycleBody = extractFunctionBody(source, "cycleProfile");
  const defaultBody = extractFunctionBody(source, "isDefault");

  assert.match(initBody, /Logger\.d\("PowerProfileService", "Service started"\)/, "init must log service startup");
  assert.match(setBody, /if \(!available\)\s+return;/, "setProfile must no-op when unavailable");
  assert.match(setBody, /try \{[\s\S]*powerProfiles\.profile = p[\s\S]*\} catch \(e\) \{[\s\S]*Logger\.e\("PowerProfileService", "Failed to set profile:", e\)/, "setProfile must log assignment failures");
  assert.match(cycleBody, /if \(!available\)\s+return;/, "cycleProfile must no-op when unavailable");
  assert.match(cycleBody, /const current = powerProfiles\.profile/, "cycleProfile must read the live UPower profile");
  assert.match(cycleBody, /current === PowerProfile\.Performance[\s\S]*setProfile\(PowerProfile\.PowerSaver\)/, "cycleProfile must cycle performance to power saver");
  assert.match(cycleBody, /current === PowerProfile\.Balanced[\s\S]*setProfile\(PowerProfile\.Performance\)/, "cycleProfile must cycle balanced to performance");
  assert.match(cycleBody, /current === PowerProfile\.PowerSaver[\s\S]*setProfile\(PowerProfile\.Balanced\)/, "cycleProfile must cycle power saver to balanced");
  assert.match(defaultBody, /if \(!available\)\s+return true;/, "isDefault must treat unavailable profiles as default");
  assert.match(defaultBody, /return \(profile === PowerProfile\.Balanced\)/, "isDefault must consider balanced the default profile");
}

function testPowerProfileMutationInputsAreTyped() {
  const source = readQml("Services/Power/PowerProfileService.qml");

  assert.match(source, /function setProfile\(p\)/, "setProfile must type the requested profile value");
  assert.match(source, /function setNoctaliaPerformance\(value\)/, "setNoctaliaPerformance must type the requested performance mode");
}

function testNoctaliaPerformanceGuards() {
  const source = readQml("Services/Power/PowerProfileService.qml");
  const toggleBody = extractFunctionBody(source, "toggleNoctaliaPerformance");
  const setPerfBody = extractFunctionBody(source, "setNoctaliaPerformance");

  assert.match(toggleBody, /noctaliaPerformanceMode = !noctaliaPerformanceMode/, "toggleNoctaliaPerformance must invert the mode");
  assert.match(setPerfBody, /noctaliaPerformanceMode = value/, "setNoctaliaPerformance must assign the requested mode");
  assert.match(source, /onNoctaliaPerformanceModeChanged:[\s\S]*ToastService\.showNotice\(I18n\.tr\("toast\.noctalia-performance\.label"\), I18n\.tr\("toast\.noctalia-performance\.enabled"\), "rocket"\)/, "performance mode enable must show a rocket toast");
  assert.match(source, /onNoctaliaPerformanceModeChanged:[\s\S]*ToastService\.showNotice\(I18n\.tr\("toast\.noctalia-performance\.label"\), I18n\.tr\("toast\.noctalia-performance\.disabled"\), "rocket-off"\)/, "performance mode disable must show a rocket-off toast");
}

const tests = [
  testPowerProfileNameAndIconGuards,
  testPowerProfileMutationGuards,
  testPowerProfileMutationInputsAreTyped,
  testNoctaliaPerformanceGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
