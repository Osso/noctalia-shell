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
  const processNextImage = qmlFunction("processNextImage");
  const queueImage = qmlFunction("queueImage", "path", "imageId");

  assert.match(serverBody, /if \(notificationServerLoader\)[\s\S]*notificationServerLoader\.destroy\(\)[\s\S]*notificationServerLoader = null/, "updateNotificationServer must destroy any old server before reloading");
  assert.match(serverBody, /Settings\.isLoaded && Settings\.data\.notifications\.enabled !== false/, "updateNotificationServer must only create the server when notifications are enabled");
  assert.match(serverBody, /notificationServerComponent\.createObject\(root\)/, "updateNotificationServer must create the notification server from its component");
  const owner = {
    imageQueue: [],
    Settings: { cacheDirImagesNotifications: "/cache/notifications/" },
  };
  const decoyQueue = [{ src: "image://other/untouched" }];
  const cacher = { root: owner, source: "", imageQueue: decoyQueue };
  owner.cacher = cacher;
  for (const [path, id] of [["", "empty"], ["/plain.png", "plain"], ["image://provider/no-id", ""]]) {
    queueImage(owner, path, id);
  }
  assert.deepEqual(owner.imageQueue, []);
  assert.equal(cacher.source, "");

  queueImage(owner, "image://provider/first", "first");
  queueImage(owner, "image://provider/duplicate", "first");
  queueImage(owner, "image://provider/second", "second");
  assert.deepEqual(owner.imageQueue, [
    { src: "image://provider/first", dest: "/cache/notifications/first.png", imageId: "first" },
    { src: "image://provider/second", dest: "/cache/notifications/second.png", imageId: "second" },
  ]);
  assert.equal(cacher.source, "image://provider/first", "enqueue must not interrupt current image");
  processNextImage(cacher);
  assert.equal(owner.imageQueue.length, 1);
  assert.equal(owner.imageQueue[0].imageId, "second");
  assert.equal(cacher.source, "image://provider/second");
  processNextImage(cacher);
  assert.deepEqual(owner.imageQueue, []);
  assert.equal(cacher.source, "");
  assert.deepEqual(decoyQueue, [{ src: "image://other/untouched" }], "advancement must mutate root queue, not cacher-local state");
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
  const findDuplicateNotification = qmlFunction("findDuplicateNotification", "data");
  const rows = [
    { id: "first", summary: "unrelated", body: "body", appName: "Firefox" },
    { id: "second", summary: "match", body: "body", appName: "Terminal" },
  ];
  const ctx = {
    activeList: { count: rows.length, get: index => rows[index] },
    getContentId: (...fields) => JSON.stringify(fields),
  };
  assert.equal(findDuplicateNotification(ctx, rows[1]), "second", "duplicate search must reach later rows");
  assert.equal(findDuplicateNotification(ctx, { ...rows[1], body: "different" }), null);
  ctx.activeList.count = 0;
  assert.equal(findDuplicateNotification(ctx, rows[1]), null);
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
  const performSaveHistory = qmlFunction("performSaveHistory");
  const rows = [
    { id: "first", timestamp: new Date(1710000000000), summary: "First" },
    { id: "second", timestamp: new Date(1710000001000), summary: "Second" },
  ];
  let writes = 0;
  const errors = [];
  const ctx = {
    historyList: { count: rows.length, get: index => rows[index] },
    adapter: { notifications: [] },
    historyFileView: { writeAdapter() { writes++; } },
    Logger: { e: (...args) => errors.push(args) },
  };
  performSaveHistory(ctx);
  assert.deepEqual(ctx.adapter.notifications, rows.map(row => ({ ...row, timestamp: row.timestamp.getTime() })));
  assert.equal(writes, 1);
  assert.ok(rows.every(row => row.timestamp instanceof Date), "serialization must not mutate model timestamps");
  assert.notEqual(ctx.adapter.notifications[0], rows[0]);
  const failure = new Error("write failed");
  ctx.historyFileView.writeAdapter = () => { throw failure; };
  performSaveHistory(ctx);
  assert.deepEqual(errors, [["Notifications", "Save history failed:", failure]]);
  assert.match(performSaveBody, /const copy = Object\.assign\(\{\},\s*n\)/, "performSaveHistory must copy rows before serializing");
  assert.match(performSaveBody, /copy\.timestamp = n\.timestamp\.getTime\(\)/, "performSaveHistory must serialize timestamps as milliseconds");
  assert.match(performSaveBody, /adapter\.notifications = items[\s\S]*historyFileView\.writeAdapter\(\)/, "performSaveHistory must write the JSON adapter");
  assert.match(performSaveBody, /Logger\.e\("Notifications",\s*"Save history failed:",\s*e\)/, "performSaveHistory must log save failures");
  assert.match(loadHistoryBody, /historyList\.clear\(\)/, "loadHistory must clear stale history rows");
  assert.match(loadHistoryBody, /for \(const item of adapter\.notifications \|\| \[\]\)/, "loadHistory must tolerate missing adapter notifications");
  assert.match(loadHistoryBody, /const time = new Date\(item\.timestamp\)/, "loadHistory must restore Date timestamps");
  assert.match(loadHistoryBody, /resolveCachedImageForHistory\(item\)/, "loadHistory must normalize cached history images before appending rows");
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

function testNotificationHistoryCachedImagesResolveIconProviderFallbacks() {
  const loadHistory = qmlFunction("loadHistory");
  const resolveCachedImageForHistory = qmlFunction("resolveCachedImageForHistory", "item");
  const cacheDir = "/tmp/noctalia-cache/images/notifications/";
  const cachedIconImage = cacheDir + "icon.png";
  const cachedProviderImage = cacheDir + "provider.png";
  const historyRows = [];
  const ctx = {
    Settings: { cacheDirImagesNotifications: cacheDir },
    generateImageId: () => "generated",
    adapter: { notifications: [] },
    historyList: {
      clear: () => { historyRows.length = 0; },
      append: row => historyRows.push(row),
    },
    Logger: { e: () => {} },
  };
  ctx.resolveCachedImageForHistory = item => resolveCachedImageForHistory(ctx, item);

  assert.equal(resolveCachedImageForHistory(ctx, {
    originalImage: "image://icon/com.mitchellh.ghostty",
    cachedImage: cachedIconImage,
  }), "", "stable icon-provider images should bypass stale generated cache files");
  assert.equal(resolveCachedImageForHistory(ctx, {
    originalImage: "image://qsimage/transient-id",
    cachedImage: cachedProviderImage,
  }), cachedProviderImage, "transient image-provider rows keep persisted cache paths");
  assert.equal(resolveCachedImageForHistory(ctx, {
    originalImage: "image://qsimage/transient-id",
    cachedImage: "",
  }), cacheDir + "generated.png", "transient image-provider rows derive cache paths when missing");
  assert.equal(resolveCachedImageForHistory(ctx, {
    originalImage: "/tmp/plain.png",
    cachedImage: "",
  }), "", "plain images do not derive notification cache paths");

  ctx.adapter.notifications = [{
    id: "ghostty-1",
    timestamp: 1710000000000,
    originalImage: "image://icon/com.mitchellh.ghostty",
    cachedImage: cachedIconImage,
  }];
  loadHistory(ctx);

  assert.equal(historyRows.length, 1, "history load appends persisted notification");
  assert.equal(historyRows[0].cachedImage, "", "history model lets stable original icon provider win over stale cache path");
  assert.equal(historyRows[0].originalImage, "image://icon/com.mitchellh.ghostty", "history model keeps original image for delegate fallback");
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
  testNotificationHistoryCachedImagesResolveIconProviderFallbacks,
  testNotificationEmptySuppressionExecutesPlaceholderMatching,
  testNotificationTerminalBellCooldownExecutes,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
