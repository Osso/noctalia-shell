#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Tabs/BatteryTab.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext() {
  return {
    writeThresholdProcess: {
      thresholdType: "",
      thresholdValue: 0,
      running: false,
    },
  };
}

function testBatteryTabSetStartThresholdStartsWriteProcess() {
  const setStartThreshold = qmlFunction("setStartThreshold", "value");
  const ctx = createContext();

  setStartThreshold(ctx, 35);

  assert.deepEqual(ctx.writeThresholdProcess, {
    thresholdType: "start",
    thresholdValue: 35,
    running: true,
  });
}

function testBatteryTabSetStopThresholdStartsWriteProcess() {
  const setStopThreshold = qmlFunction("setStopThreshold", "value");
  const ctx = createContext();

  setStopThreshold(ctx, 80);

  assert.deepEqual(ctx.writeThresholdProcess, {
    thresholdType: "end",
    thresholdValue: 80,
    running: true,
  });
}

const tests = [
  testBatteryTabSetStartThresholdStartsWriteProcess,
  testBatteryTabSetStopThresholdStartsWriteProcess,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
