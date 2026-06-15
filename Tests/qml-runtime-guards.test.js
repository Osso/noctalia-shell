#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function extractFunctionBody(source, functionName) {
  const marker = `function ${functionName}(`;
  const markerIndex = source.indexOf(marker);
  assert.notEqual(markerIndex, -1, `missing function: ${functionName}`);

  const blockStart = source.indexOf("{", markerIndex);
  let depth = 0;

  for (let index = blockStart; index < source.length; index++) {
    const char = source[index];

    if (char === "{") {
      depth++;
    } else if (char === "}") {
      depth--;
      if (depth === 0) {
        return source.slice(blockStart, index + 1);
      }
    }
  }

  throw new Error(`unterminated function: ${functionName}`);
}

function testOsdBrightnessHandlerRejectsInvalidValues() {
  const source = readQml("Modules/OSD/OSD.qml");
  const body = extractFunctionBody(source, "onBrightnessChanged");

  assert.match(body, /BrightnessParsing\.isValidBrightnessRatio\(normalizedBrightness\)/);
  assert.match(body, /newBrightness === null \|\| newBrightness === undefined/);
  assert.match(body, /const normalizedBrightness = Number\(newBrightness\)/);
  assert.match(body, /return;/);
  assert.match(body, /root\.currentBrightness = normalizedBrightness/);
}

function testOsdShowRequiresScreenBeforeActivatingLoader() {
  const source = readQml("Modules/OSD/OSD.qml");
  const body = extractFunctionBody(source, "showOSD");
  const screenGuard = body.indexOf("if (!modelData)");
  const activation = body.indexOf("root.active = true");

  assert.notEqual(screenGuard, -1, "showOSD must guard missing screen model data");
  assert.notEqual(activation, -1, "showOSD must still activate the loader for valid screens");
  assert.ok(screenGuard < activation, "showOSD must guard missing screen model data before activating the loader");
}

function testTaskbarGroupedUrgentBadgeHasCooldown() {
  const source = readQml("Modules/Bar/Widgets/TaskbarGrouped.qml");

  assert.match(source, /property bool displayedBadgeUrgent:/, "TaskbarGrouped badge must keep a displayed urgent state");
  assert.match(source, /id:\s*badgeUrgencyCooldown/, "TaskbarGrouped badge must define a cooldown timer");
  assert.match(source, /interval:\s*5000/, "TaskbarGrouped badge cooldown must be 5 seconds");
  assert.match(source, /displayedBadgeUrgent = container\.badgeUrgent/, "TaskbarGrouped badge cooldown must settle to current urgency");
  assert.doesNotMatch(source, /if \(workspaceModel\.isUrgent\)\s+return Color\.mError/, "TaskbarGrouped badge color must use the cooled urgent state");
  assert.doesNotMatch(source, /if \(workspaceModel\.isUrgent\)\s+return Color\.mOnError/, "TaskbarGrouped badge text color must use the cooled urgent state");
}

function testOsdDisconnectsBrightnessMonitorsOnDestruction() {
  const source = readQml("Modules/OSD/OSD.qml");

  assert.match(source, /function disconnectBrightnessMonitors\(\)/, "OSD must define brightness monitor disconnect cleanup");
  assert.match(source, /monitor\.brightnessUpdated\.disconnect\(onBrightnessChanged\)/, "OSD cleanup must disconnect brightness monitor signals");
  assert.match(source, /Component\.onDestruction:\s*disconnectBrightnessMonitors\(\)/, "OSD must disconnect brightness monitors when its delegate is destroyed");
}

const tests = [
  testOsdBrightnessHandlerRejectsInvalidValues,
  testOsdShowRequiresScreenBeforeActivatingLoader,
  testTaskbarGroupedUrgentBadgeHasCooldown,
  testOsdDisconnectsBrightnessMonitorsOnDestruction,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
