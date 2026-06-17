#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/UI/BarWidgetRegistry.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBarWidgetRegistryLookupAndPresenceHelpers() {
  const getWidget = qmlFunction("getWidget", "id");
  const hasWidget = qmlFunction("hasWidget", "id");
  const clockComponent = { name: "ClockComponent" };

  assert.match(source, /function getWidget\(id: string\)/, "getWidget must type the widget id input");
  assert.match(source, /function hasWidget\(id: string\)/, "hasWidget must type the widget id input");

  const ctx = {
    widgets: {
      Clock: clockComponent,
      MissingComponent: null,
    },
  };

  assert.equal(getWidget(ctx, "Clock"), clockComponent);
  assert.equal(getWidget(ctx, "MissingComponent"), null);
  assert.equal(getWidget(ctx, "Unknown"), null);
  assert.equal(hasWidget(ctx, "Clock"), true);
  assert.equal(hasWidget(ctx, "MissingComponent"), true);
  assert.equal(hasWidget(ctx, "Unknown"), false);
}

function testBarWidgetRegistryAvailableWidgetsReflectsRegistryKeys() {
  const getAvailableWidgets = qmlFunction("getAvailableWidgets");
  const ctx = {
    widgets: {
      Clock: {},
      Tray: {},
      CustomButton: {},
    },
  };

  assert.deepEqual(getAvailableWidgets(ctx), ["Clock", "Tray", "CustomButton"]);
}

function testBarWidgetRegistryUserSettingsRequiresExplicitTrue() {
  const widgetHasUserSettings = qmlFunction("widgetHasUserSettings", "id");

  assert.match(source, /function widgetHasUserSettings\(id: string\)/, "widgetHasUserSettings must type the widget id input");

  const ctx = {
    widgetMetadata: {
      Clock: { allowUserSettings: false },
      Tray: { allowUserSettings: true },
      CustomButton: {},
    },
  };

  assert.equal(widgetHasUserSettings(ctx, "Tray"), true);
  assert.equal(widgetHasUserSettings(ctx, "Clock"), false);
  assert.equal(widgetHasUserSettings(ctx, "CustomButton"), false);
  assert.equal(widgetHasUserSettings(ctx, "Unknown"), false);
}

const tests = [
  testBarWidgetRegistryLookupAndPresenceHelpers,
  testBarWidgetRegistryAvailableWidgetsReflectsRegistryKeys,
  testBarWidgetRegistryUserSettingsRequiresExplicitTrue,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
