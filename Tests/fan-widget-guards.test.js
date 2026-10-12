#!/usr/bin/env node

const assert = require("assert/strict");
const path = require("path");
const { spawnSync } = require("child_process");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/SystemMonitor.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function(
    "ctx",
    ...argNames,
    `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`,
  );
}

function testFanWidgetVisibilityAndSpeedTextHelpers() {
  const shouldShow = qmlFunction(
    "shouldShowFanSpeedMetric",
    "enabled",
    "fanAvailable",
    "sensorDetected",
  );
  const formatSpeed = qmlFunction("formatFanSpeedText", "maxRpm");
  const ctx = { FanService: { formatRpm: (rpm) => `${rpm} rpm formatted` } };
  for (const enabled of [true, false]) {
    for (const available of [true, false]) {
      for (const detected of [true, false]) {
        assert.equal(
          shouldShow(ctx, enabled, available, detected),
          enabled && (available || detected),
        );
      }
    }
  }
  assert.equal(formatSpeed(ctx, 2450), "2450 rpm formatted");
}

function testFanWidgetTooltipTextHelper() {
  const tooltip = qmlFunction("fanTooltipText", "fans");
  assert.equal(tooltip({}, []), "");
  assert.equal(
    tooltip({}, [
      { label: "CPU Fan", rpm: 2100 },
      { label: "Chassis", rpm: 980 },
    ]),
    "CPU Fan: 2100 RPM\nChassis: 980 RPM",
  );
}

function testFanWidgetPollingLifecycleGuards() {
  let refs = 0;
  const ctx = {
    fanPollingRegistered: false,
    visible: true,
    showFanSpeed: true,
    showCpuUsage: false,
    showCpuTemp: false,
    showMemoryUsage: false,
    showDiskUsage: false,
    showNetworkStats: false,
    FanService: {
      beginPolling() {
        refs += 1;
      },
      endPolling() {
        refs -= 1;
      },
      isPollingActive: () => refs > 0,
    },
    setSystemStatPolling() {},
  };
  const setPolling = qmlFunction("setFanPolling", "shouldPoll");
  ctx.setFanPolling = (enabled) => setPolling(ctx, enabled);
  const refresh = qmlFunction("refreshSystemStatPolling");
  const clear = qmlFunction("clearSystemStatPolling");
  refresh(ctx);
  assert.equal(refs, 1);
  assert.equal(ctx.fanPollingRegistered, true);
  refresh(ctx);
  assert.equal(refs, 1, "refresh must not acquire duplicate refs");
  refs = 0;
  refresh(ctx);
  assert.equal(
    refs,
    1,
    "service reset must reacquire ref despite registered flag",
  );
  ctx.showFanSpeed = false;
  refresh(ctx);
  assert.equal(refs, 0);
  assert.equal(ctx.fanPollingRegistered, false);
  ctx.showFanSpeed = true;
  ctx.visible = false;
  refresh(ctx);
  assert.equal(refs, 0);
  ctx.visible = true;
  refresh(ctx);
  assert.equal(refs, 1);
  clear(ctx);
  clear(ctx);
  assert.equal(refs, 0, "release must be idempotent");
  assert.equal(ctx.fanPollingRegistered, false);
}

function testFanWidgetUiUsesFanHelpers() {
  const result = spawnSync(
    "python3",
    [path.join(__dirname, "system-monitor-runtime.test.py"), "--fan-only"],
    {
      encoding: "utf8",
      timeout: 60000,
    },
  );
  assert.ifError(result.error);
  const output = result.stdout + result.stderr;
  process.stdout.write(output);
  assert.equal(result.status, 0, output);
  assert.match(
    output,
    /3 passed, 0 failed/,
    "fan UI, lifecycle and QtTest setup/cleanup must finish",
  );
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
