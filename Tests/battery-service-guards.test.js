#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Hardware/BatteryService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBatteryServiceIconSignatureIsTyped() {
  assert.match(source, /function getIcon\(percent, charging, isReady\)/, "getIcon must type percent, charging, and ready-state inputs");
}

function testBatteryServiceIconThresholdsAndReadiness() {
  const getIcon = qmlFunction("getIcon", "percent", "charging", "isReady");

  assert.equal(getIcon({}, 100, false, false), "battery-exclamation");
  assert.equal(getIcon({}, 5, true, true), "battery-charging");
  assert.equal(getIcon({}, 90, false, true), "battery-4");
  assert.equal(getIcon({}, 50, false, true), "battery-3");
  assert.equal(getIcon({}, 25, false, true), "battery-2");
  assert.equal(getIcon({}, 0, false, true), "battery-1");
  assert.equal(getIcon({}, -1, false, true), "battery");
}

const tests = [
  testBatteryServiceIconSignatureIsTyped,
  testBatteryServiceIconThresholdsAndReadiness,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
