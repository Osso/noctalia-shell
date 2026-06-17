#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/UI/ControlCenterWidgetRegistry.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testControlCenterWidgetRegistryLookupAndPresenceHelpers() {
  const getWidget = qmlFunction("getWidget", "id");
  const hasWidget = qmlFunction("hasWidget", "id");
  const notificationsComponent = { name: "NotificationsComponent" };

  assert.match(source, /function getWidget\(id: string\)/, "getWidget must type the widget id input");
  assert.match(source, /function hasWidget\(id: string\)/, "hasWidget must type the widget id input");

  const ctx = {
    widgets: {
      Notifications: notificationsComponent,
      MissingComponent: null,
    },
  };

  assert.equal(getWidget(ctx, "Notifications"), notificationsComponent);
  assert.equal(getWidget(ctx, "MissingComponent"), null);
  assert.equal(getWidget(ctx, "Unknown"), null);
  assert.equal(hasWidget(ctx, "Notifications"), true);
  assert.equal(hasWidget(ctx, "MissingComponent"), true);
  assert.equal(hasWidget(ctx, "Unknown"), false);
}

function testControlCenterWidgetRegistryAvailableWidgetsReflectsRegistryKeys() {
  const getAvailableWidgets = qmlFunction("getAvailableWidgets");
  const ctx = {
    widgets: {
      Notifications: {},
      WiFi: {},
      CustomButton: {},
    },
  };

  assert.deepEqual(getAvailableWidgets(ctx), ["Notifications", "WiFi", "CustomButton"]);
}

function testControlCenterWidgetRegistryUserSettingsRequiresExplicitTrue() {
  const widgetHasUserSettings = qmlFunction("widgetHasUserSettings", "id");

  assert.match(source, /function widgetHasUserSettings\(id: string\)/, "widgetHasUserSettings must type the widget id input");

  const ctx = {
    widgetMetadata: {
      CustomButton: { allowUserSettings: true },
      Notifications: { allowUserSettings: false },
      WiFi: {},
    },
  };

  assert.equal(widgetHasUserSettings(ctx, "CustomButton"), true);
  assert.equal(widgetHasUserSettings(ctx, "Notifications"), false);
  assert.equal(widgetHasUserSettings(ctx, "WiFi"), false);
  assert.equal(widgetHasUserSettings(ctx, "Unknown"), false);
}

const tests = [
  testControlCenterWidgetRegistryLookupAndPresenceHelpers,
  testControlCenterWidgetRegistryAvailableWidgetsReflectsRegistryKeys,
  testControlCenterWidgetRegistryUserSettingsRequiresExplicitTrue,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
