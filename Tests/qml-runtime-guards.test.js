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

  assert.match(source, /property var displayedUrgencyByWorkspace:/, "TaskbarGrouped badge cooldown state must survive delegate rebuilds");
  assert.match(source, /function workspaceUrgencyKey\(workspace\)/, "TaskbarGrouped badge cooldown must key state by workspace");
  assert.match(source, /function displayedUrgentForWorkspace\(workspace\)/, "TaskbarGrouped badge cooldown must restore displayed state after model refresh");
  assert.match(source, /id:\s*badgeUrgencyCooldown/, "TaskbarGrouped badge must define a cooldown timer");
  assert.match(source, /interval:\s*5000/, "TaskbarGrouped badge cooldown must be 5 seconds");
  assert.match(source, /root\.setDisplayedUrgency\(workspaceModel,\s*container\.badgeUrgent\)/, "TaskbarGrouped badge cooldown must settle persistent urgency state");
  assert.doesNotMatch(source, /if \(workspaceModel\.isUrgent\)\s+return Color\.mError/, "TaskbarGrouped badge color must use the cooled urgent state");
  assert.doesNotMatch(source, /if \(workspaceModel\.isUrgent\)\s+return Color\.mOnError/, "TaskbarGrouped badge text color must use the cooled urgent state");
}

function testWorkspaceUrgentBadgeHasCooldown() {
  const source = readQml("Modules/Bar/Widgets/Workspace.qml");

  assert.match(source, /property var displayedUrgencyByWorkspace:/, "Workspace badge cooldown state must survive delegate rebuilds");
  assert.match(source, /function workspaceUrgencyKey\(workspace\)/, "Workspace badge cooldown must key state by workspace");
  assert.match(source, /function displayedUrgentForWorkspace\(workspace\)/, "Workspace badge cooldown must restore displayed state after model refresh");
  assert.match(source, /id:\s*horizontalUrgencyCooldown/, "Workspace horizontal badge must define a cooldown timer");
  assert.match(source, /id:\s*verticalUrgencyCooldown/, "Workspace vertical badge must define a cooldown timer");
  assert.match(source, /interval:\s*5000/, "Workspace badge cooldown must be 5 seconds");
  assert.match(source, /root\.setDisplayedUrgency\(model,\s*workspacePillContainer\.urgent\)/, "Workspace horizontal badge cooldown must settle persistent urgency state");
  assert.match(source, /root\.setDisplayedUrgency\(model,\s*workspacePillContainerVertical\.urgent\)/, "Workspace vertical badge cooldown must settle persistent urgency state");
  assert.doesNotMatch(source, /if \(model\.isUrgent\)\s+return Color\.mError/, "Workspace badge color must use the cooled urgent state");
  assert.doesNotMatch(source, /if \(model\.isUrgent\)\s+return Color\.mOnError/, "Workspace badge text color must use the cooled urgent state");
}

function testFocusedWorkspaceBurstOnlyRunsOnFocusChange() {
  const workspaceSource = readQml("Modules/Bar/Widgets/Workspace.qml");
  const groupedSource = readQml("Modules/Bar/Widgets/TaskbarGrouped.qml");
  const workspaceBody = extractFunctionBody(workspaceSource, "updateWorkspaceFocus");
  const groupedBody = extractFunctionBody(groupedSource, "updateWorkspaceFocus");

  assert.match(workspaceSource, /property string focusedWorkspaceKey:/, "Workspace must remember the last focused workspace key");
  assert.match(groupedSource, /property string focusedWorkspaceKey:/, "TaskbarGrouped must remember the last focused workspace key");
  assert.match(workspaceBody, /if \(key === focusedWorkspaceKey\)\s+return;/, "Workspace must not restart focus burst for the same focused workspace");
  assert.match(groupedBody, /if \(key === focusedWorkspaceKey\)\s+return;/, "TaskbarGrouped must not restart focus burst for the same focused workspace");
  assert.match(workspaceBody, /focusedWorkspaceKey = key[\s\S]*root\.triggerUnifiedWave\(\)/, "Workspace must update focus key before running the burst");
  assert.match(groupedBody, /focusedWorkspaceKey = key[\s\S]*root\.triggerUnifiedWave\(\)/, "TaskbarGrouped must update focus key before running the burst");
}

function testTerminalBellNotificationsHaveCooldown() {
  const source = readQml("Services/System/NotificationService.qml");
  const handleBody = extractFunctionBody(source, "handleNotification");
  const cooldownIndex = handleBody.indexOf("shouldSuppressTerminalBellNotification(data)");
  const historyIndex = handleBody.indexOf("addToHistory(data)");
  const cooldownBody = extractFunctionBody(source, "shouldSuppressTerminalBellNotification");

  assert.match(source, /readonly property int terminalBellCooldownMs:\s*5000/, "terminal bell cooldown must be 5 seconds");
  assert.match(source, /property real lastTerminalBellNotificationMs:\s*0/, "terminal bell cooldown must track the last displayed bell");
  assert.notEqual(cooldownIndex, -1, "NotificationService must check terminal bell cooldown");
  assert.notEqual(historyIndex, -1, "NotificationService must still write normal notifications to history");
  assert.ok(cooldownIndex < historyIndex, "terminal bell cooldown must suppress repeated bells before history insertion");
  assert.match(cooldownBody, /isTerminalBellNotification\(data\)/, "cooldown must only apply to terminal bell notifications");
  assert.match(cooldownBody, /nowMs - lastTerminalBellNotificationMs < terminalBellCooldownMs/, "cooldown must suppress bells inside the 5 second window");
  assert.match(cooldownBody, /lastTerminalBellNotificationMs = nowMs/, "cooldown must record the displayed bell timestamp");
}

function testEmptyNotificationsAreSuppressedBeforeHistory() {
  const source = readQml("Services/System/NotificationService.qml");
  const handleBody = extractFunctionBody(source, "handleNotification");
  const emptyGuardIndex = handleBody.indexOf("shouldSuppressEmptyNotification(data)");
  const historyIndex = handleBody.indexOf("addToHistory(data)");
  const addNewIndex = handleBody.indexOf("addNewNotification(quickshellId, notification, data)");
  const guardBody = extractFunctionBody(source, "shouldSuppressEmptyNotification");
  const createDataBody = extractFunctionBody(source, "createData");

  assert.notEqual(emptyGuardIndex, -1, "NotificationService must check empty notification suppression");
  assert.notEqual(historyIndex, -1, "NotificationService must still write valid notifications to history");
  assert.notEqual(addNewIndex, -1, "NotificationService must still display valid notifications");
  assert.ok(emptyGuardIndex < historyIndex, "empty notifications must be suppressed before history insertion");
  assert.ok(emptyGuardIndex < addNewIndex, "empty notifications must be suppressed before display insertion");
  assert.match(guardBody, /isPlaceholderNotificationText\(data\.appName,\s*\["unknown",\s*"unknown app"\]\)/, "empty notification guard must require a missing or placeholder app name");
  assert.match(guardBody, /isPlaceholderNotificationText\(data\.summary,\s*\["no summary"\]\)/, "empty notification guard must require a missing or placeholder summary");
  assert.match(guardBody, /!\(data\.body \|\| ""\)\.trim\(\)/, "empty notification guard must require a missing body");
  assert.match(createDataBody, /const notificationAppName = n\.appName \|\| n\.desktopEntry \|\| ""/, "createData must keep the raw notification app name separate from display formatting");
  assert.match(createDataBody, /"appName":\s*notificationAppName\s*\?\s*getAppName\(notificationAppName\)\s*:\s*""/, "createData must keep missing app names empty so the guard can suppress placeholder notifications");
  assert.doesNotMatch(createDataBody, /"appName":\s*getAppName\(n\.appName \|\| n\.desktopEntry \|\| ""\)/, "createData must not turn missing app names into a display fallback before suppression");
}

function testPlaceholderNotificationsAreSuppressedBeforeHistory() {
  const source = readQml("Services/System/NotificationService.qml");
  const guardBody = extractFunctionBody(source, "shouldSuppressEmptyNotification");
  const placeholderBody = extractFunctionBody(source, "isPlaceholderNotificationText");

  assert.match(guardBody, /isPlaceholderNotificationText\(data\.appName,\s*\["unknown",\s*"unknown app"\]\)/, "empty notification guard must treat unknown app labels as missing app names");
  assert.match(guardBody, /isPlaceholderNotificationText\(data\.summary,\s*\["no summary"\]\)/, "empty notification guard must treat no-summary labels as missing summaries");
  assert.match(placeholderBody, /String\(value \|\| ""\)\.trim\(\)\.toLowerCase\(\)/, "placeholder normalization must ignore whitespace and casing");
  assert.match(placeholderBody, /placeholders\.indexOf\(normalized\) !== -1/, "placeholder normalization must match known fallback labels");
}

function testGithubServiceFollowsRedirectsAndValidatesResponses() {
  const source = readQml("Services/Noctalia/GitHubService.qml");

  assert.match(source, /command:\s*\["curl",\s*"-fsSL",\s*"https:\/\/api\.github\.com\/repos\/noctalia-dev\/noctalia-shell\/releases\/latest"\]/, "GitHub version fetch must follow redirects and fail on HTTP errors");
  assert.match(source, /command:\s*\["curl",\s*"-fsSL",\s*"https:\/\/api\.github\.com\/repos\/noctalia-dev\/noctalia-shell\/contributors\?per_page=100"\]/, "GitHub contributors fetch must follow redirects and fail on HTTP errors");
  assert.match(source, /Array\.isArray\(data\)/, "GitHub contributors response must be validated before storing contributors");
  assert.doesNotMatch(source, /root\.data\.contributors = data \|\| \[\]/, "GitHub contributors must not store non-array response objects");
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
  testWorkspaceUrgentBadgeHasCooldown,
  testFocusedWorkspaceBurstOnlyRunsOnFocusChange,
  testTerminalBellNotificationsHaveCooldown,
  testEmptyNotificationsAreSuppressedBeforeHistory,
  testPlaceholderNotificationsAreSuppressedBeforeHistory,
  testGithubServiceFollowsRedirectsAndValidatesResponses,
  testOsdDisconnectsBrightnessMonitorsOnDestruction,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
