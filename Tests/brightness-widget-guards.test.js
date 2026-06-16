#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/Brightness.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext(monitor) {
  const calls = [];
  const screen = { name: "HDMI-A-1" };
  return {
    calls,
    screen,
    BrightnessService: {
      getMonitorForScreen(requestedScreen) {
        calls.push(requestedScreen);
        return monitor;
      },
    },
  };
}

function testBrightnessWidgetGetMonitorDelegatesToServiceWithScreen() {
  const getMonitor = qmlFunction("getMonitor");
  const monitor = { brightness: 0.75 };
  const ctx = createContext(monitor);

  assert.equal(getMonitor(ctx), monitor);
  assert.deepEqual(ctx.calls, [ctx.screen]);
}

function testBrightnessWidgetGetMonitorReturnsNullWhenServiceHasNoDisplay() {
  const getMonitor = qmlFunction("getMonitor");
  const ctx = createContext(undefined);

  assert.equal(getMonitor(ctx), null);
  assert.deepEqual(ctx.calls, [ctx.screen]);
}

function testBrightnessWidgetGetIconMapsMissingOrOffBrightness() {
  const getIcon = qmlFunction("getIcon");
  const ctx = {
    getMonitor() {
      return null;
    },
  };

  assert.equal(getIcon(ctx), "sun-off");

  ctx.getMonitor = () => ({ brightness: 0 });
  assert.equal(getIcon(ctx), "sun-off");

  ctx.getMonitor = () => ({ brightness: 0.001 });
  assert.equal(getIcon(ctx), "sun-off");
}

function testBrightnessWidgetGetIconMapsLowAndHighBrightness() {
  const getIcon = qmlFunction("getIcon");
  const ctx = {
    getMonitor() {
      return { brightness: 0.5 };
    },
  };

  assert.equal(getIcon(ctx), "brightness-low");

  ctx.getMonitor = () => ({ brightness: 0.5001 });
  assert.equal(getIcon(ctx), "brightness-high");
}

const tests = [
  testBrightnessWidgetGetMonitorDelegatesToServiceWithScreen,
  testBrightnessWidgetGetMonitorReturnsNullWhenServiceHasNoDisplay,
  testBrightnessWidgetGetIconMapsMissingOrOffBrightness,
  testBrightnessWidgetGetIconMapsLowAndHighBrightness,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
