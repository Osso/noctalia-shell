#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/System/NotificationService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  const args = argNames.join(", ");
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${args}) ${body}).call(ctx, ${args}); }`);
}

function testNotificationServerAndImageQueueLifecycle() {
  const serverBody = extractFunctionBody(source, "updateNotificationServer");
  const processBody = extractFunctionBody(source, "processNextImage");
  const queueBody = extractFunctionBody(source, "queueImage");

  assert.match(serverBody, /if \(notificationServerLoader\)[\s\S]*notificationServerLoader\.destroy\(\)[\s\S]*notificationServerLoader = null/, "updateNotificationServer must destroy any old server before reloading");
  assert.match(serverBody, /Settings\.isLoaded && Settings\.data\.notifications\.enabled !== false/, "updateNotificationServer must only create the server when notifications are enabled");
  assert.match(serverBody, /notificationServerComponent\.createObject\(root\)/, "updateNotificationServer must create the notification server from its component");
  assert.match(processBody, /imageQueue\.shift\(\)/, "processNextImage must discard the completed image request");
  assert.match(processBody, /if \(imageQueue\.length > 0\)[\s\S]*source = imageQueue\[0\]\.src/, "processNextImage must continue with the next image request");
  assert.match(processBody, /else[\s\S]*source = ""/, "processNextImage must clear the image source when the queue is empty");
  assert.match(queueBody, /if \(!path \|\| !path\.startsWith\("image:\/\/"\) \|\| !imageId\)\s+return;/, "queueImage must only cache image-provider URLs with IDs");
  assert.match(queueBody, /const dest = Settings\.cacheDirImagesNotifications \+ imageId \+ "\.png"/, "queueImage must derive the notification cache path");
  assert.match(queueBody, /for \(const req of imageQueue\)[\s\S]*if \(req\.imageId === imageId\)\s+return;/, "queueImage must deduplicate queued image IDs");
  assert.match(queueBody, /imageQueue\.push\(\{[\s\S]*"src": path[\s\S]*"dest": dest[\s\S]*"imageId": imageId/, "queueImage must enqueue source, destination, and image id");
  assert.match(queueBody, /if \(imageQueue\.length === 1\)\s+cacher\.source = path/, "queueImage must start caching when the queue was empty");
}

function testNotificationReplacementAndObjectUpdatePreserveStableFields() {
  const refreshBody = extractFunctionBody(source, "refreshDuplicateNotification");
  const existingBody = extractFunctionBody(source, "updateExistingNotification");
  const objectBody = extractFunctionBody(source, "updateNotificationFromObject");
  const duplicateBody = extractFunctionBody(source, "findDuplicateNotification");

  assert.match(refreshBody, /const index = findNotificationIndex\(existingInternalId\)/, "refreshDuplicateNotification must locate the existing visible row");
  assert.match(refreshBody, /if \(index < 0\)[\s\S]*addNewNotification\(quickshellId,\s*notification,\s*data\)[\s\S]*return;/, "refreshDuplicateNotification must add a new notification when the old row is gone");
  assert.match(refreshBody, /activeList\.setProperty\(index,\s*"actionsJson",\s*data\.actionsJson\)/, "refreshDuplicateNotification must update only actions for exact duplicate content");
  assert.match(refreshBody, /notifData\.notification = notification/, "refreshDuplicateNotification must rebind stored notification object");
  assert.match(refreshBody, /if \(notifData\.watcher\)[\s\S]*notifData\.watcher\.destroy\(\)/, "refreshDuplicateNotification must destroy stale watchers");
  assert.match(refreshBody, /notification\.closed\.connect\(\(\) =>[\s\S]*activeNotifications\[existingInternalId\]\.notification === notification[\s\S]*removeNotification\(existingInternalId\)/, "refreshDuplicateNotification must ignore stale close signals");
  assert.match(refreshBody, /quickshellIdToInternalId\[quickshellId\] = existingInternalId/, "refreshDuplicateNotification must map the new quickshell id to the existing internal id");
  assert.match(existingBody, /const oldTimestamp = existing\.timestamp[\s\S]*const oldProgress = existing\.progress/, "updateExistingNotification must preserve timestamp and progress");
  assert.match(existingBody, /activeList\.setProperty\(index,\s*"summary",\s*data\.summary\)/, "updateExistingNotification must update display fields");
  assert.match(existingBody, /activeList\.setProperty\(index,\s*"timestamp",\s*oldTimestamp\)/, "updateExistingNotification must restore the old timestamp");
  assert.match(existingBody, /activeList\.setProperty\(index,\s*"progress",\s*oldProgress\)/, "updateExistingNotification must restore the old progress");
  assert.match(existingBody, /notificationWatcherComponent\.createObject\(root,\s*\{[\s\S]*"targetNotification": notification[\s\S]*"targetDataId": internalId/, "updateExistingNotification must create a fresh watcher");
  assert.match(existingBody, /notifData\.metadata\.duration = calculateDuration\(data\)/, "updateExistingNotification must update timeout metadata");
  assert.match(objectBody, /const notifData = activeNotifications\[internalId\][\s\S]*if \(!notifData\)\s+return;/, "updateNotificationFromObject must ignore missing active notifications");
  assert.match(objectBody, /const data = createData\(notifData\.notification\)/, "updateNotificationFromObject must recreate data from the live object");
  assert.match(objectBody, /activeList\.setProperty\(index,\s*"actionsJson",\s*data\.actionsJson\)/, "updateNotificationFromObject must update action data");
  assert.match(objectBody, /notifData\.metadata\.duration = calculateDuration\(data\)/, "updateNotificationFromObject must refresh timeout metadata");
  assert.match(duplicateBody, /const contentId = getContentId\(data\.summary,\s*data\.body,\s*data\.appName\)/, "findDuplicateNotification must compare stable content ids");
  assert.match(duplicateBody, /for \(var i = 0; i < activeList\.count; i\+\+\)/, "findDuplicateNotification must scan visible notifications");
  assert.match(duplicateBody, /if \(existingContentId === contentId\)[\s\S]*return existing\.id/, "findDuplicateNotification must return the matching internal id");
}

function testNotificationCleanupAndProgressGuards() {
  const cleanupBody = extractFunctionBody(source, "cleanupNotification");
  const progressBody = extractFunctionBody(source, "updateAllProgress");

  assert.match(cleanupBody, /const notifData = activeNotifications\[id\]/, "cleanupNotification must look up active notification data");
  assert.match(cleanupBody, /if \(notifData\.watcher\)\s+notifData\.watcher\.destroy\(\)/, "cleanupNotification must destroy active watchers");
  assert.match(cleanupBody, /delete activeNotifications\[id\]/, "cleanupNotification must delete active notification state");
  assert.match(cleanupBody, /for \(const qsId in quickshellIdToInternalId\)/, "cleanupNotification must scan all quickshell id mappings");
  assert.match(cleanupBody, /if \(quickshellIdToInternalId\[qsId\] === id\)[\s\S]*delete quickshellIdToInternalId\[qsId\]/, "cleanupNotification must remove every mapping to the internal id");
  assert.match(progressBody, /const now = Date\.now\(\)/, "updateAllProgress must compute progress from current time");
  assert.match(progressBody, /const toRemove = \[\]/, "updateAllProgress must collect expired ids");
  assert.match(progressBody, /if \(meta\.duration === -1 \|\| meta\.paused\)\s+continue;/, "updateAllProgress must skip persistent and paused notifications");
  assert.match(progressBody, /const progress = Math\.max\(1\.0 - \(elapsed \/ meta\.duration\),\s*0\.0\)/, "updateAllProgress must clamp progress at zero");
  assert.match(progressBody, /if \(progress <= 0\)[\s\S]*toRemove\.push\(notif\.id\)/, "updateAllProgress must queue expired notifications for removal");
  assert.match(progressBody, /Math\.abs\(notif\.progress - progress\) > 0\.005[\s\S]*activeList\.setProperty\(i,\s*"progress",\s*progress\)/, "updateAllProgress must avoid tiny progress updates");
  assert.match(progressBody, /if \(toRemove\.length > 0\)[\s\S]*animateAndRemove\(toRemove\[0\]\)/, "updateAllProgress must animate the oldest expired notification");
}

function testNotificationHistoryAndStatePersistence() {
  const performSaveBody = extractFunctionBody(source, "performSaveHistory");
  const loadHistoryBody = extractFunctionBody(source, "loadHistory");
  const loadStateBody = extractFunctionBody(source, "loadState");
  const saveStateBody = extractFunctionBody(source, "saveState");
  const seenBody = extractFunctionBody(source, "updateLastSeenTs");

  assert.match(performSaveBody, /const items = \[\]/, "performSaveHistory must serialize a fresh item list");
  assert.match(performSaveBody, /for \(var i = 0; i < historyList\.count; i\+\+\)/, "performSaveHistory must scan history rows");
  assert.match(performSaveBody, /const copy = Object\.assign\(\{\},\s*n\)/, "performSaveHistory must copy rows before serializing");
  assert.match(performSaveBody, /copy\.timestamp = n\.timestamp\.getTime\(\)/, "performSaveHistory must serialize timestamps as milliseconds");
  assert.match(performSaveBody, /adapter\.notifications = items[\s\S]*historyFileView\.writeAdapter\(\)/, "performSaveHistory must write the JSON adapter");
  assert.match(performSaveBody, /Logger\.e\("Notifications",\s*"Save history failed:",\s*e\)/, "performSaveHistory must log save failures");
  assert.match(loadHistoryBody, /historyList\.clear\(\)/, "loadHistory must clear stale history rows");
  assert.match(loadHistoryBody, /for \(const item of adapter\.notifications \|\| \[\]\)/, "loadHistory must tolerate missing adapter notifications");
  assert.match(loadHistoryBody, /const time = new Date\(item\.timestamp\)/, "loadHistory must restore Date timestamps");
  assert.match(loadHistoryBody, /if \(item\.originalImage && item\.originalImage\.startsWith\("image:\/\/"\) && !cachedImage\)/, "loadHistory must derive cache paths for provider images");
  assert.match(loadHistoryBody, /cachedImage = Settings\.cacheDirImagesNotifications \+ imageId \+ "\.png"/, "loadHistory must rebuild cached image paths from generated ids");
  assert.match(loadHistoryBody, /"urgency": item\.urgency < 0 \|\| item\.urgency > 2 \? 1 : item\.urgency/, "loadHistory must clamp invalid urgency to normal");
  assert.match(loadHistoryBody, /Logger\.e\("Notifications",\s*"Load failed:",\s*e\)/, "loadHistory must log load failures");
  assert.match(loadStateBody, /const notifState = ShellState\.getNotificationsState\(\)/, "loadState must read persisted notification state");
  assert.match(loadStateBody, /root\.lastSeenTs = notifState\.lastSeenTs \|\| 0/, "loadState must restore last seen timestamp");
  assert.match(loadStateBody, /Logger\.e\("Notifications",\s*"Load state failed:",\s*e\)/, "loadState must log state load failures");
  assert.match(saveStateBody, /ShellState\.setNotificationsState\(\{[\s\S]*lastSeenTs: root\.lastSeenTs[\s\S]*\}\)/, "saveState must persist last seen timestamp");
  assert.match(saveStateBody, /Logger\.e\("Notifications",\s*"Save state failed:",\s*e\)/, "saveState must log state save failures");
  assert.match(seenBody, /root\.lastSeenTs = Time\.timestamp \* 1000/, "updateLastSeenTs must convert current timestamp to milliseconds");
  assert.match(seenBody, /saveState\(\)/, "updateLastSeenTs must persist the new timestamp");
}

function testNotificationEmptySuppressionExecutesPlaceholderMatching() {
  const isPlaceholderNotificationText = qmlFunction("isPlaceholderNotificationText", "value", "placeholders");
  const shouldSuppressEmptyNotification = qmlFunction("shouldSuppressEmptyNotification", "data");
  const ctx = {};
  ctx.isPlaceholderNotificationText = (value, placeholders) => isPlaceholderNotificationText(ctx, value, placeholders);

  assert.equal(isPlaceholderNotificationText(ctx, "", ["unknown"]), true, "blank placeholder text matches");
  assert.equal(isPlaceholderNotificationText(ctx, " Unknown App ", ["unknown app"]), true, "placeholder matching trims and lowercases");
  assert.equal(isPlaceholderNotificationText(ctx, "Firefox", ["unknown"]), false, "real text does not match placeholders");
  assert.equal(shouldSuppressEmptyNotification(ctx, {
    appName: "Unknown App",
    body: "",
    summary: "No summary",
  }), true, "unknown app/no summary/blank body is suppressed");
  assert.equal(shouldSuppressEmptyNotification(ctx, {
    appName: "Unknown App",
    body: "real body",
    summary: "No summary",
  }), false, "non-empty body is not suppressed");
  assert.equal(shouldSuppressEmptyNotification(ctx, {
    appName: "Firefox",
    body: "",
    summary: "No summary",
  }), false, "known app is not suppressed");
}

function testNotificationTerminalBellCooldownExecutes() {
  const isTerminalBellNotification = qmlFunction("isTerminalBellNotification", "data");
  const shouldSuppressTerminalBellNotification = qmlFunction("shouldSuppressTerminalBellNotification", "data");
  const clock = { now: 10000 };
  const ctx = {
    Date: { now: () => clock.now },
    lastTerminalBellNotificationMs: 0,
    terminalBellCooldownMs: 5000,
  };
  ctx.isTerminalBellNotification = data => isTerminalBellNotification(ctx, data);

  assert.equal(isTerminalBellNotification(ctx, {
    appName: "Ghostty",
    body: "",
    summary: "Bell",
  }), true, "terminal app plus bell content is a terminal bell");
  assert.equal(isTerminalBellNotification(ctx, {
    appName: "Unknown App",
    body: "terminal bell",
    summary: "",
  }), true, "content mentioning terminal bell is a terminal bell");
  assert.equal(isTerminalBellNotification(ctx, {
    appName: "Ghostty",
    body: "",
    summary: "Build finished",
  }), false, "terminal notification without bell content is not a terminal bell");
  assert.equal(shouldSuppressTerminalBellNotification(ctx, {
    appName: "Ghostty",
    body: "",
    summary: "Bell",
  }), false, "first terminal bell is allowed");
  assert.equal(ctx.lastTerminalBellNotificationMs, 10000, "first terminal bell updates cooldown timestamp");

  clock.now = 12000;
  assert.equal(shouldSuppressTerminalBellNotification(ctx, {
    appName: "Ghostty",
    body: "",
    summary: "Bell",
  }), true, "terminal bell inside cooldown is suppressed");
  assert.equal(ctx.lastTerminalBellNotificationMs, 10000, "suppressed terminal bell does not extend cooldown");

  clock.now = 16000;
  assert.equal(shouldSuppressTerminalBellNotification(ctx, {
    appName: "Ghostty",
    body: "",
    summary: "Bell",
  }), false, "terminal bell after cooldown is allowed");
  assert.equal(ctx.lastTerminalBellNotificationMs, 16000, "allowed terminal bell refreshes cooldown timestamp");

  clock.now = 17000;
  assert.equal(shouldSuppressTerminalBellNotification(ctx, {
    appName: "Firefox",
    body: "",
    summary: "Download finished",
  }), false, "non-terminal-bell notifications are not suppressed");
  assert.equal(ctx.lastTerminalBellNotificationMs, 16000, "non-terminal-bell notifications do not affect cooldown");
}

const tests = [
  testNotificationServerAndImageQueueLifecycle,
  testNotificationReplacementAndObjectUpdatePreserveStableFields,
  testNotificationCleanupAndProgressGuards,
  testNotificationHistoryAndStatePersistence,
  testNotificationEmptySuppressionExecutesPlaceholderMatching,
  testNotificationTerminalBellCooldownExecutes,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
