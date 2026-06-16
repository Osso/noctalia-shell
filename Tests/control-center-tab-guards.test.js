#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Tabs/ControlCenterTab.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function settingsWithShortcuts(shortcuts = {}) {
  return {
    data: {
      controlCenter: {
        cards: [],
        shortcuts: {
          left: shortcuts.left || [],
          right: shortcuts.right || [],
        },
      },
    },
    saved: 0,
    saveImmediate() {
      this.saved++;
    },
  };
}

function testControlCenterTabSaveCards() {
  const saveCards = qmlFunction("saveCards");
  const Settings = settingsWithShortcuts();
  const ctx = {
    Settings,
    cardsModel: [
      { id: "profile-card", enabled: true, text: "Profile" },
      { id: "weather-card", enabled: false, text: "Weather" },
    ],
  };

  saveCards(ctx);

  assert.deepEqual(Settings.data.controlCenter.cards, [
    { id: "profile-card", enabled: true },
    { id: "weather-card", enabled: false },
  ]);
}

function testControlCenterTabAddWidgetGuards() {
  const addWidget = qmlFunction("_addWidgetToSection", "widgetId", "section");
  const Settings = settingsWithShortcuts({ left: [] });
  const ctx = {
    Settings,
    ControlCenterWidgetRegistry: {
      widgetMetadata: {
        "toggle-wifi": {
          allowUserSettings: true,
          icon: "network-wireless",
          label: "Wi-Fi",
        },
      },
      widgetHasUserSettings(widgetId) {
        return widgetId === "toggle-wifi";
      },
    },
  };

  addWidget(ctx, "toggle-wifi", "left");
  addWidget(ctx, "plain-toggle", "left");

  assert.deepEqual(Settings.data.controlCenter.shortcuts.left, [
    { id: "toggle-wifi", icon: "network-wireless", label: "Wi-Fi" },
    { id: "plain-toggle" },
  ]);
}

function testControlCenterTabRemoveAndReorderGuards() {
  const removeWidget = qmlFunction("_removeWidgetFromSection", "section", "index");
  const reorderWidget = qmlFunction("_reorderWidgetInSection", "section", "fromIndex", "toIndex");
  const Settings = settingsWithShortcuts({
    left: [{ id: "one" }, { id: "two" }, { id: "three" }],
  });
  const ctx = { Settings };

  removeWidget(ctx, "left", -1);
  assert.deepEqual(Settings.data.controlCenter.shortcuts.left.map(widget => widget.id), ["one", "two", "three"]);

  removeWidget(ctx, "left", 1);
  assert.deepEqual(Settings.data.controlCenter.shortcuts.left.map(widget => widget.id), ["one", "three"]);

  reorderWidget(ctx, "left", 1, 0);
  assert.deepEqual(Settings.data.controlCenter.shortcuts.left.map(widget => widget.id), ["three", "one"]);

  reorderWidget(ctx, "left", 5, 0);
  assert.deepEqual(Settings.data.controlCenter.shortcuts.left.map(widget => widget.id), ["three", "one"]);
}

function testControlCenterTabMoveAndUpdateGuards() {
  const moveWidget = qmlFunction("_moveWidgetBetweenSections", "fromSection", "index", "toSection");
  const updateWidget = qmlFunction("_updateWidgetSettingsInSection", "section", "index", "settings");
  const Settings = settingsWithShortcuts({
    left: [{ id: "one" }, { id: "two" }],
    right: [{ id: "three" }],
  });
  const ctx = { Settings };

  moveWidget(ctx, "left", 1, "right");
  assert.deepEqual(Settings.data.controlCenter.shortcuts.left.map(widget => widget.id), ["one"]);
  assert.deepEqual(Settings.data.controlCenter.shortcuts.right.map(widget => widget.id), ["three", "two"]);

  moveWidget(ctx, "left", 5, "right");
  assert.deepEqual(Settings.data.controlCenter.shortcuts.left.map(widget => widget.id), ["one"]);
  assert.deepEqual(Settings.data.controlCenter.shortcuts.right.map(widget => widget.id), ["three", "two"]);

  updateWidget(ctx, "right", 1, { id: "two", enabled: false });
  assert.deepEqual(Settings.data.controlCenter.shortcuts.right, [{ id: "three" }, { id: "two", enabled: false }]);
  assert.equal(Settings.saved, 1);
}

const tests = [
  testControlCenterTabSaveCards,
  testControlCenterTabAddWidgetGuards,
  testControlCenterTabRemoveAndReorderGuards,
  testControlCenterTabMoveAndUpdateGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
