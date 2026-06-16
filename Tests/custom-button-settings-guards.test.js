#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Bar/WidgetSettings/CustomButtonSettings.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testCustomButtonValueOrDefaultPreservesExplicitFalseyValues() {
  const valueOrDefault = qmlFunction("valueOrDefault", "source", "key", "defaultValue");

  assert.equal(valueOrDefault({}, { enabled: false }, "enabled", true), false);
  assert.equal(valueOrDefault({}, { count: 0 }, "count", 5), 0);
  assert.equal(valueOrDefault({}, { label: "" }, "label", "fallback"), "");
  assert.equal(valueOrDefault({}, {}, "missing", "fallback"), "fallback");
  assert.equal(valueOrDefault({}, null, "missing", "fallback"), "fallback");
}

function testCustomButtonSettingFallbacksPreferWidgetData() {
  const valueOrDefault = qmlFunction("valueOrDefault", "source", "key", "defaultValue");
  const settingValue = qmlFunction("settingValue", "key", "defaultValue");
  const textSettingValue = qmlFunction("textSettingValue", "key");
  const nestedSettingValue = qmlFunction("nestedSettingValue", "parentKey", "childKey", "defaultValue");
  const ctx = {
    widgetData: {
      leftClickUpdateText: false,
      leftClickExec: "",
      maxTextLength: { horizontal: 12 },
    },
    widgetMetadata: {
      leftClickUpdateText: true,
      leftClickExec: "echo metadata",
      rightClickExec: "echo right",
      maxTextLength: { horizontal: 20, vertical: 6 },
    },
    valueOrDefault(source, key, defaultValue) {
      return valueOrDefault(ctx, source, key, defaultValue);
    },
  };

  assert.equal(settingValue(ctx, "leftClickUpdateText", true), false);
  assert.equal(settingValue(ctx, "missing", "fallback"), "fallback");
  assert.equal(textSettingValue(ctx, "leftClickExec"), "echo metadata");
  assert.equal(textSettingValue(ctx, "rightClickExec"), "echo right");
  assert.equal(nestedSettingValue(ctx, "maxTextLength", "horizontal", 0), 12);
  assert.equal(nestedSettingValue(ctx, "maxTextLength", "vertical", 0), 6);
  assert.equal(nestedSettingValue(ctx, "maxTextLength", "missing", 99), 99);
}

function testCustomButtonSaveSettingsAggregatesUiState() {
  const saveSettings = qmlFunction("saveSettings");
  const ctx = {
    widgetData: {
      id: "CustomButton",
      keep: "existing",
    },
    valueIcon: "terminal",
    valueTextStream: true,
    valueParseJson: true,
    valueMaxTextLengthHorizontal: 24,
    valueMaxTextLengthVertical: 8,
    leftClickExecInput: { text: "left" },
    leftClickUpdateText: { checked: true },
    rightClickExecInput: { text: "right" },
    rightClickUpdateText: { checked: false },
    middleClickExecInput: { text: "middle" },
    middleClickUpdateText: { checked: true },
    separateWheelToggle: { internalChecked: true },
    wheelExecInput: { text: "wheel" },
    wheelUpExecInput: { text: "up" },
    wheelDownExecInput: { text: "down" },
    wheelUpdateText: { checked: false },
    wheelUpUpdateText: { checked: true },
    wheelDownUpdateText: { checked: false },
    textCommandInput: { text: "status" },
    textCollapseInput: { text: "collapse" },
    textIntervalInput: { text: "", placeholderText: "1500" },
  };

  const settings = saveSettings(ctx);

  assert.equal(settings.id, "CustomButton");
  assert.equal(settings.keep, "existing");
  assert.equal(settings.icon, "terminal");
  assert.equal(settings.leftClickExec, "left");
  assert.equal(settings.leftClickUpdateText, true);
  assert.equal(settings.rightClickExec, "right");
  assert.equal(settings.rightClickUpdateText, false);
  assert.equal(settings.middleClickExec, "middle");
  assert.equal(settings.middleClickUpdateText, true);
  assert.equal(settings.wheelMode, "separate");
  assert.equal(settings.wheelExec, "wheel");
  assert.equal(settings.wheelUpExec, "up");
  assert.equal(settings.wheelDownExec, "down");
  assert.equal(settings.wheelUpdateText, false);
  assert.equal(settings.wheelUpUpdateText, true);
  assert.equal(settings.wheelDownUpdateText, false);
  assert.equal(settings.textCommand, "status");
  assert.equal(settings.textCollapse, "collapse");
  assert.equal(settings.textStream, true);
  assert.equal(settings.parseJson, true);
  assert.deepEqual(settings.maxTextLength, { horizontal: 24, vertical: 8 });
  assert.equal(settings.textIntervalMs, 1500);
}

function testCustomButtonSaveSettingsUsesUnifiedWheelModeAndTextInterval() {
  const saveSettings = qmlFunction("saveSettings");
  const ctx = {
    widgetData: {},
    valueIcon: "",
    valueTextStream: false,
    valueParseJson: false,
    valueMaxTextLengthHorizontal: 0,
    valueMaxTextLengthVertical: 0,
    leftClickExecInput: { text: "" },
    leftClickUpdateText: { checked: false },
    rightClickExecInput: { text: "" },
    rightClickUpdateText: { checked: false },
    middleClickExecInput: { text: "" },
    middleClickUpdateText: { checked: false },
    separateWheelToggle: { internalChecked: false },
    wheelExecInput: { text: "wheel-any" },
    wheelUpExecInput: { text: "" },
    wheelDownExecInput: { text: "" },
    wheelUpdateText: { checked: true },
    wheelUpUpdateText: { checked: false },
    wheelDownUpdateText: { checked: false },
    textCommandInput: { text: "" },
    textCollapseInput: { text: "" },
    textIntervalInput: { text: "2500", placeholderText: "1500" },
  };

  const settings = saveSettings(ctx);

  assert.equal(settings.wheelMode, "unified");
  assert.equal(settings.wheelExec, "wheel-any");
  assert.equal(settings.textIntervalMs, 2500);
}

const tests = [
  testCustomButtonValueOrDefaultPreservesExplicitFalseyValues,
  testCustomButtonSettingFallbacksPreferWidgetData,
  testCustomButtonSaveSettingsAggregatesUiState,
  testCustomButtonSaveSettingsUsesUnifiedWheelModeAndTextInterval,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
