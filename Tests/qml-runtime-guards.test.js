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

function testNotificationContentIdentityUsesStableFields() {
  const source = readQml("Services/System/NotificationService.qml");
  const contentIdBody = extractFunctionBody(source, "getContentId");
  const compareBody = extractFunctionBody(source, "hasSameNotificationContent");

  assert.match(contentIdBody, /Checksum\.sha256\(JSON\.stringify/, "getContentId must hash stable notification content");
  assert.match(contentIdBody, /"summary":\s*summary \|\| ""/, "getContentId must normalize missing summaries");
  assert.match(contentIdBody, /"body":\s*body \|\| ""/, "getContentId must normalize missing bodies");
  assert.match(contentIdBody, /"app":\s*appName \|\| ""/, "getContentId must normalize missing app names");
  assert.match(compareBody, /getContentId\(existing\.summary,\s*existing\.body,\s*existing\.appName\)/, "hasSameNotificationContent must hash existing notification content");
  assert.match(compareBody, /getContentId\(data\.summary,\s*data\.body,\s*data\.appName\)/, "hasSameNotificationContent must hash incoming notification content");
  assert.match(compareBody, /return existingContentId === dataContentId/, "hasSameNotificationContent must compare hashes");
}

function testNotificationDurationsRespectSettingsAndExpireTimeout() {
  const source = readQml("Services/System/NotificationService.qml");
  const body = extractFunctionBody(source, "calculateDuration");

  assert.match(body, /Settings\.data\.notifications/, "calculateDuration must read notification duration settings");
  assert.match(body, /lowUrgencyDuration \? notificationSettings\.lowUrgencyDuration \* 1000 : 3000/, "calculateDuration must default low urgency to 3 seconds");
  assert.match(body, /normalUrgencyDuration \? notificationSettings\.normalUrgencyDuration \* 1000 : 8000/, "calculateDuration must default normal urgency to 8 seconds");
  assert.match(body, /criticalUrgencyDuration \? notificationSettings\.criticalUrgencyDuration \* 1000 : 15000/, "calculateDuration must default critical urgency to 15 seconds");
  assert.match(body, /notificationSettings && notificationSettings\.respectExpireTimeout/, "calculateDuration must respect explicit notification timeouts when enabled");
  assert.match(body, /if \(data\.expireTimeout === 0\)\s+return -1/, "calculateDuration must keep zero expire timeout notifications persistent");
  assert.match(body, /if \(data\.expireTimeout > 0\)\s+return data\.expireTimeout/, "calculateDuration must use positive expire timeouts directly");
  assert.match(body, /return durations\[data\.urgency\]/, "calculateDuration must select duration by urgency");
}

function testNotificationImageHelpersKeepOnlyCacheableImageIds() {
  const source = readQml("Services/System/NotificationService.qml");
  const iconBody = extractFunctionBody(source, "getIcon");
  const imageIdBody = extractFunctionBody(source, "generateImageId");

  assert.match(iconBody, /if \(!icon\)\s+return ""/, "getIcon must preserve missing icons as empty strings");
  assert.match(iconBody, /icon\.startsWith\("\/"\) \|\| icon\.startsWith\("file:\/\/"\)/, "getIcon must keep absolute image paths unchanged");
  assert.match(iconBody, /return ThemeIcons\.iconFromName\(icon\)/, "getIcon must resolve named icons through ThemeIcons");
  assert.match(imageIdBody, /image && image\.startsWith\("image:\/\/"\)/, "generateImageId must only cache image provider URLs");
  assert.match(imageIdBody, /image\.startsWith\("image:\/\/qsimage\/"\)/, "generateImageId must handle transient qsimage URLs specially");
  assert.match(imageIdBody, /const key = \(notification\.appName \|\| ""\) \+ "\|" \+ \(notification\.summary \|\| ""\)/, "generateImageId must make qsimage IDs stable for duplicate content");
  assert.match(imageIdBody, /return Checksum\.sha256\(image\)/, "generateImageId must hash other image provider URLs");
  assert.match(imageIdBody, /return ""/, "generateImageId must skip non-provider paths");
}

function testNotificationTextHelpersNormalizeInput() {
  const source = readQml("Services/System/NotificationService.qml");
  const appNameBody = extractFunctionBody(source, "getAppName");
  const stripTagsBody = extractFunctionBody(source, "stripTags");

  assert.match(appNameBody, /if \(!name \|\| name\.trim\(\) === ""\)\s+return "Unknown"/, "getAppName must label missing app names");
  assert.match(appNameBody, /name = name\.trim\(\)/, "getAppName must trim raw names before formatting");
  assert.match(appNameBody, /name\.startsWith\("com\."\) \|\| name\.startsWith\("org\."\) \|\| name\.startsWith\("io\."\) \|\| name\.startsWith\("net\."\)/, "getAppName must unwrap reverse-DNS app names");
  assert.match(appNameBody, /displayName\.replace\(\/\(\[a-z\]\)\(\[A-Z\]\)\/g, '\$1 \$2'\)/, "getAppName must split camel-case app names");
  assert.match(appNameBody, /displayName\.replace\(\/app\$\/i, ''\)\.trim\(\)/, "getAppName must drop generic app suffixes");
  assert.match(stripTagsBody, /return text\.replace\(\/<\[\^>\]\*>\?\/gm, ''\)/, "stripTags must remove simple markup tags");
}

function testNotificationModelUpdatesTargetMatchingRows() {
  const source = readQml("Services/System/NotificationService.qml");
  const findBody = extractFunctionBody(source, "findNotificationIndex");
  const updateBody = extractFunctionBody(source, "updateModel");
  const imagePathBody = extractFunctionBody(source, "updateImagePath");

  assert.match(findBody, /for \(var i = 0; i < activeList\.count; i\+\+\)/, "findNotificationIndex must scan the active list");
  assert.match(findBody, /activeList\.get\(i\)\.id === internalId/, "findNotificationIndex must match by notification id");
  assert.match(findBody, /return -1/, "findNotificationIndex must report missing notifications");
  assert.match(updateBody, /for \(var i = 0; i < model\.count; i\+\+\)/, "updateModel must scan the provided model");
  assert.match(updateBody, /model\.get\(i\)\.id === id/, "updateModel must update only the matching row");
  assert.match(updateBody, /model\.setProperty\(i,\s*prop,\s*value\)/, "updateModel must write the requested property value");
  assert.match(updateBody, /break;/, "updateModel must stop after the first matching row");
  assert.match(imagePathBody, /updateModel\(activeList,\s*id,\s*"cachedImage",\s*path\)/, "updateImagePath must update active notification images");
  assert.match(imagePathBody, /updateModel\(historyList,\s*id,\s*"cachedImage",\s*path\)/, "updateImagePath must update history notification images");
  assert.match(imagePathBody, /saveHistory\(\)/, "updateImagePath must persist history image changes");
}

function testNotificationTimeoutPauseAndResumeTrackElapsedTime() {
  const source = readQml("Services/System/NotificationService.qml");
  const pauseBody = extractFunctionBody(source, "pauseTimeout");
  const resumeBody = extractFunctionBody(source, "resumeTimeout");

  assert.match(pauseBody, /const notifData = activeNotifications\[id\]/, "pauseTimeout must read active notification metadata");
  assert.match(pauseBody, /notifData && !notifData\.metadata\.paused/, "pauseTimeout must ignore missing or already paused notifications");
  assert.match(pauseBody, /notifData\.metadata\.paused = true/, "pauseTimeout must mark the timeout paused");
  assert.match(pauseBody, /notifData\.metadata\.pauseTime = Date\.now\(\)/, "pauseTimeout must store the pause timestamp");
  assert.match(resumeBody, /notifData && notifData\.metadata\.paused/, "resumeTimeout must only resume paused notifications");
  assert.match(resumeBody, /notifData\.metadata\.timestamp \+= Date\.now\(\) - notifData\.metadata\.pauseTime/, "resumeTimeout must shift the original timestamp by paused time");
  assert.match(resumeBody, /notifData\.metadata\.paused = false/, "resumeTimeout must clear the paused flag");
}

function testNotificationDismissAndActionFunctionsFailClosed() {
  const source = readQml("Services/System/NotificationService.qml");
  const dismissActiveBody = extractFunctionBody(source, "dismissActiveNotification");
  const dismissOldestBody = extractFunctionBody(source, "dismissOldestActive");
  const dismissAllBody = extractFunctionBody(source, "dismissAllActive");
  const invokeBody = extractFunctionBody(source, "invokeAction");

  assert.match(dismissActiveBody, /activeNotifications\[id\] && activeNotifications\[id\]\.notification/, "dismissActiveNotification must check notification existence before dismissing");
  assert.match(dismissActiveBody, /activeNotifications\[id\]\.notification\.dismiss\(\)/, "dismissActiveNotification must dismiss the backing notification");
  assert.match(dismissActiveBody, /removeNotification\(id\)/, "dismissActiveNotification must remove local state");
  assert.match(dismissOldestBody, /if \(activeList\.count > 0\)/, "dismissOldestActive must tolerate an empty active list");
  assert.match(dismissOldestBody, /activeList\.get\(activeList\.count - 1\)/, "dismissOldestActive must select the oldest visible active notification");
  assert.match(dismissOldestBody, /dismissActiveNotification\(lastNotif\.id\)/, "dismissOldestActive must reuse active dismissal");
  assert.match(dismissAllBody, /for \(const id in activeNotifications\)/, "dismissAllActive must visit all active notifications");
  assert.match(dismissAllBody, /activeList\.clear\(\)/, "dismissAllActive must clear the visible model");
  assert.match(dismissAllBody, /activeNotifications = \{\}/, "dismissAllActive must reset active notification state");
  assert.match(dismissAllBody, /quickshellIdToInternalId = \{\}/, "dismissAllActive must reset quickshell id mappings");
  assert.match(invokeBody, /if \(!notifData \|\| !notifData\.notification \|\| !notifData\.notification\.actions\)\s+return false/, "invokeAction must fail closed when action data is missing");
  assert.match(invokeBody, /action\.identifier === actionId && action\.invoke/, "invokeAction must call only the selected invokable action");
  assert.match(invokeBody, /action\.invoke\(\)/, "invokeAction must invoke matching actions");
  assert.match(invokeBody, /return true/, "invokeAction must report successful invocation");
  assert.match(invokeBody, /return false/, "invokeAction must report missing actions");
}

function testNotificationHistoryRemovalOnlyDeletesOwnedCachedImages() {
  const source = readQml("Services/System/NotificationService.qml");
  const removeBody = extractFunctionBody(source, "removeFromHistory");
  const oldestBody = extractFunctionBody(source, "removeOldestHistory");
  const clearBody = extractFunctionBody(source, "clearHistory");

  assert.match(removeBody, /for \(var i = 0; i < historyList\.count; i\+\+\)/, "removeFromHistory must scan history entries");
  assert.match(removeBody, /notif\.id === notificationId/, "removeFromHistory must match the requested history id");
  assert.match(removeBody, /notif\.cachedImage && notif\.cachedImage\.startsWith\(Settings\.cacheDirImagesNotifications\)/, "removeFromHistory must delete only owned cached images");
  assert.match(removeBody, /Quickshell\.execDetached\(\["rm",\s*"-f",\s*notif\.cachedImage\]\)/, "removeFromHistory must remove the matching cached image");
  assert.match(removeBody, /historyList\.remove\(i\)/, "removeFromHistory must remove the matching history row");
  assert.match(removeBody, /saveHistory\(\)/, "removeFromHistory must persist the removal");
  assert.match(removeBody, /return false/, "removeFromHistory must report missing history rows");
  assert.match(oldestBody, /if \(historyList\.count > 0\)/, "removeOldestHistory must tolerate empty history");
  assert.match(oldestBody, /historyList\.get\(historyList\.count - 1\)/, "removeOldestHistory must select the oldest history row");
  assert.match(oldestBody, /oldest\.cachedImage && oldest\.cachedImage\.startsWith\(Settings\.cacheDirImagesNotifications\)/, "removeOldestHistory must delete only owned cached images");
  assert.match(oldestBody, /historyList\.remove\(historyList\.count - 1\)/, "removeOldestHistory must remove the oldest row");
  assert.match(oldestBody, /return true/, "removeOldestHistory must report successful removal");
  assert.match(oldestBody, /return false/, "removeOldestHistory must report empty history");
  assert.match(clearBody, /Quickshell\.execDetached\(\["sh",\s*"-c",\s*`rm -rf "\$\{Settings\.cacheDirImagesNotifications\}"\*`\]\)/, "clearHistory must only clear the notification image cache directory");
  assert.match(clearBody, /Logger\.e\("Notifications",\s*"Failed to clear cache directory:",\s*e\)/, "clearHistory must log cache cleanup failures");
  assert.match(clearBody, /historyList\.clear\(\)/, "clearHistory must clear history rows");
  assert.match(clearBody, /saveHistory\(\)/, "clearHistory must persist the cleared history");
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
  testNotificationContentIdentityUsesStableFields,
  testNotificationDurationsRespectSettingsAndExpireTimeout,
  testNotificationImageHelpersKeepOnlyCacheableImageIds,
  testNotificationTextHelpersNormalizeInput,
  testNotificationModelUpdatesTargetMatchingRows,
  testNotificationTimeoutPauseAndResumeTrackElapsedTime,
  testNotificationDismissAndActionFunctionsFailClosed,
  testNotificationHistoryRemovalOnlyDeletesOwnedCachedImages,
  testGithubServiceFollowsRedirectsAndValidatesResponses,
  testOsdDisconnectsBrightnessMonitorsOnDestruction,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
