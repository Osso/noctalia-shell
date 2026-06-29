#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/SystemMonitor.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testFanWidgetVisibilityAndSpeedTextHelpers() {
  assert.match(source, /function shouldShowFanSpeedMetric\(enabled, fanAvailable, sensorDetected\)/, "fan visibility helper must type boolean inputs and output");
  assert.match(source, /function formatFanSpeedText\(maxRpm\)/, "fan speed text helper must type max rpm input and output");
  const shouldShowFanSpeedMetric = qmlFunction("shouldShowFanSpeedMetric", "enabled", "fanAvailable", "sensorDetected");
  const formatFanSpeedText = qmlFunction("formatFanSpeedText", "maxRpm");
  const ctx = {
    FanService: {
      formatRpm(rpm) {
        return `${rpm} rpm formatted`;
      },
    },
  };

  assert.equal(shouldShowFanSpeedMetric(ctx, true, true, false), true);
  assert.equal(shouldShowFanSpeedMetric(ctx, true, false, true), true);
  assert.equal(shouldShowFanSpeedMetric(ctx, true, false, false), false);
  assert.equal(shouldShowFanSpeedMetric(ctx, false, true, true), false);
  assert.equal(formatFanSpeedText(ctx, 2450), "2450 rpm formatted");
}

function testFanWidgetTooltipTextHelper() {
  assert.match(source, /function fanTooltipText\(fans\)/, "fan tooltip helper must declare string output while keeping list input dynamic");
  const fanTooltipText = qmlFunction("fanTooltipText", "fans");

  assert.equal(fanTooltipText({}, []), "");
  assert.equal(fanTooltipText({}, [
    { label: "CPU Fan", rpm: 2100 },
    { label: "Chassis", rpm: 980 },
  ]), "CPU Fan: 2100 RPM\nChassis: 980 RPM");
}

function testFanWidgetPollingLifecycleGuards() {
  assert.match(source, /property bool fanPollingRegistered: false/, "SystemMonitor must track FanService polling ownership");
  assert.match(source, /function setFanPolling\(shouldPoll\)/, "SystemMonitor must expose a fan polling ref helper");
  assert.match(source, /FanService\.beginPolling\(\)/, "SystemMonitor must begin fan polling when fan speed display is enabled");
  assert.match(source, /shouldPoll && \(!fanPollingRegistered \|\| !FanService\.isPollingActive\(\)\)/, "SystemMonitor must re-register fan polling if FanService refs reset during hot reload");
  assert.match(source, /FanService\.endPolling\(\)/, "SystemMonitor must end fan polling when fan speed display is disabled or destroyed");
  assert.match(source, /setFanPolling\(widgetVisible && showFanSpeed\)/, "fan polling must depend on widget visibility and configured fan display, not current fan availability");
  assert.match(source, /Connections\s*\{[\s\S]*target:\s*FanService[\s\S]*function onSensorDetectedChanged\(\)[\s\S]*refreshSystemStatPolling\(\)/, "SystemMonitor must resync fan polling when FanService redetects sensors");
  assert.match(source, /function clearSystemStatPolling\(\)[\s\S]*setFanPolling\(false\)/, "SystemMonitor clear helper must release fan polling");
  assert.match(source, /Component\.onDestruction: clearSystemStatPolling\(\)/, "SystemMonitor must release fan polling on destruction through the clear helper");
}

function testFanWidgetUiUsesFanHelpers() {
  assert.match(source, /visible:\s*root\.shouldShowFanSpeedMetric\(showFanSpeed,\s*FanService\.available,\s*FanService\.sensorDetected\)/, "fan widget visibility must use helper with sensor detection");
  assert.match(source, /text:\s*root\.formatFanSpeedText\(FanService\.getMaxRpm\(\)\)/, "fan widget text must format max fan RPM via helper");
  assert.match(source, /var tooltipText = root\.fanTooltipText\(FanService\.fans\)/, "fan hover tooltip must use helper");
}

const tests = [
  testFanWidgetVisibilityAndSpeedTextHelpers,
  testFanWidgetTooltipTextHelper,
  testFanWidgetPollingLifecycleGuards,
  testFanWidgetUiUsesFanHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
