#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/SystemMonitor.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testFanWidgetVisibilityAndSpeedTextHelpers() {
  assert.match(source, /function shouldShowFanSpeedMetric\(enabled: bool, fanAvailable: bool\): bool/, "fan visibility helper must type boolean inputs and output");
  assert.match(source, /function formatFanSpeedText\(maxRpm: int\): string/, "fan speed text helper must type max rpm input and output");
  const shouldShowFanSpeedMetric = qmlFunction("shouldShowFanSpeedMetric", "enabled", "fanAvailable");
  const formatFanSpeedText = qmlFunction("formatFanSpeedText", "maxRpm");
  const ctx = {
    FanService: {
      formatRpm(rpm) {
        return `${rpm} rpm formatted`;
      },
    },
  };

  assert.equal(shouldShowFanSpeedMetric(ctx, true, true), true);
  assert.equal(shouldShowFanSpeedMetric(ctx, true, false), false);
  assert.equal(shouldShowFanSpeedMetric(ctx, false, true), false);
  assert.equal(formatFanSpeedText(ctx, 2450), "2450 rpm formatted");
}

function testFanWidgetTooltipTextHelper() {
  assert.match(source, /function fanTooltipText\(fans\): string/, "fan tooltip helper must declare string output while keeping list input dynamic");
  const fanTooltipText = qmlFunction("fanTooltipText", "fans");

  assert.equal(fanTooltipText({}, []), "");
  assert.equal(fanTooltipText({}, [
    { label: "CPU Fan", rpm: 2100 },
    { label: "Chassis", rpm: 980 },
  ]), "CPU Fan: 2100 RPM\nChassis: 980 RPM");
}

function testFanWidgetUiUsesFanHelpers() {
  assert.match(source, /visible:\s*root\.shouldShowFanSpeedMetric\(showFanSpeed,\s*FanService\.available\)/, "fan widget visibility must use helper");
  assert.match(source, /text:\s*root\.formatFanSpeedText\(FanService\.getMaxRpm\(\)\)/, "fan widget text must format max fan RPM via helper");
  assert.match(source, /var tooltipText = root\.fanTooltipText\(FanService\.fans\)/, "fan hover tooltip must use helper");
}

const tests = [
  testFanWidgetVisibilityAndSpeedTextHelpers,
  testFanWidgetTooltipTextHelper,
  testFanWidgetUiUsesFanHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
