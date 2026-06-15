#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testUpdateServiceInitializationAndChangelogRequestGuards() {
  const source = readQml("Services/Noctalia/UpdateService.qml");
  const initBody = extractFunctionBody(source, "init");
  const requestBody = extractFunctionBody(source, "handleChangelogRequest");
  const fetchBody = extractFunctionBody(source, "fetchUpgradeLog");

  assert.match(initBody, /if \(initialized\)\s+return;/, "init must be idempotent");
  assert.match(initBody, /initialized = true/, "init must mark service initialized");
  assert.match(initBody, /Qt\.callLater\(\(\) =>[\s\S]*ShellState\.isLoaded[\s\S]*loadChangelogState\(\)/, "init must defer ShellState loading until available");
  assert.match(requestBody, /Settings\.shouldOpenSetupWizard[\s\S]*markChangelogSeen\(toVersion\)[\s\S]*return;/, "handleChangelogRequest must suppress changelog during setup wizard");
  assert.match(requestBody, /if \(!toVersion\)\s+return;/, "handleChangelogRequest must ignore empty target versions");
  assert.match(requestBody, /popupScheduled && changelogCurrentVersion === toVersion/, "handleChangelogRequest must not duplicate scheduled popups");
  assert.match(requestBody, /!popupScheduled && lastShownVersion === toVersion/, "handleChangelogRequest must not reopen already shown versions");
  assert.match(requestBody, /previousVersion = fromVersion/, "handleChangelogRequest must store previous version");
  assert.match(requestBody, /changelogCurrentVersion = toVersion/, "handleChangelogRequest must store current changelog version");
  assert.match(requestBody, /fetchUpgradeLog\(fromVersion,\s*toVersion\)/, "handleChangelogRequest must fetch upgrade log");
  assert.match(requestBody, /root\.popupQueued\(previousVersion,\s*changelogCurrentVersion\)/, "handleChangelogRequest must emit popupQueued");
  assert.match(requestBody, /clearChangelogRequest\(\)/, "handleChangelogRequest must clear pending request state");
  assert.match(fetchBody, /let from = fromVersion \|\| changelogLastSeenVersion \|\| "v3\.0\.0"/, "fetchUpgradeLog must choose a stable fallback source version");
  assert.match(fetchBody, /from = from\.replace\("-dev",\s*""\)/, "fetchUpgradeLog must strip legacy dev suffix from source version");
  assert.match(fetchBody, /to = to\.replace\("-dev",\s*""\)/, "fetchUpgradeLog must strip legacy dev suffix from target version");
  assert.match(fetchBody, /if \(from >= to\)[\s\S]*from = "v3\.0\.0"/, "fetchUpgradeLog must reset inverted version ranges");
  assert.match(fetchBody, /from = "v3\.0\.0"/, "fetchUpgradeLog must reset inverted version ranges");
  assert.match(fetchBody, /const url = `\$\{upgradeLogBaseUrl\}\/\$\{from\}\/\$\{to\}`/, "fetchUpgradeLog must build upgrade log URL from normalized range");
  assert.match(fetchBody, /request\.open\("GET",\s*url\)/, "fetchUpgradeLog must use GET");
  assert.match(fetchBody, /request\.send\(\)/, "fetchUpgradeLog must send the request");
}

function testUpdateServiceVersionAndReleaseNoteParsing() {
  const source = readQml("Services/Noctalia/UpdateService.qml");
  const normalizeBody = extractFunctionBody(source, "normalizeVersion");
  const partsBody = extractFunctionBody(source, "parseVersionParts");
  const compareBody = extractFunctionBody(source, "compareVersions");
  const notesBody = extractFunctionBody(source, "parseReleaseNotes");
  const versionLineBody = extractFunctionBody(source, "isVersionLine");
  const cleanBody = extractFunctionBody(source, "cleanEntry");
  const ignoredBody = extractFunctionBody(source, "isIgnoredEntry");

  assert.match(normalizeBody, /if \(!version\)\s+return ""/, "normalizeVersion must handle empty values");
  assert.match(normalizeBody, /version\.startsWith\("v"\) \? version\.substring\(1\) : version/, "normalizeVersion must strip leading v");
  assert.match(partsBody, /const clean = normalizeVersion\(version\)/, "parseVersionParts must normalize first");
  assert.match(partsBody, /clean\.split\(\/\[\^0-9\]\+\/\)\.filter/, "parseVersionParts must split on non-numeric separators");
  assert.match(partsBody, /map\(part => parseInt\(part\)\)/, "parseVersionParts must parse integers");
  assert.match(compareBody, /if \(a === b\)\s+return 0;/, "compareVersions must fast-path equal strings");
  assert.match(compareBody, /Math\.max\(partsA\.length,\s*partsB\.length\)/, "compareVersions must compare all version parts");
  assert.match(compareBody, /const valA = partsA\[i\] \|\| 0/, "compareVersions must default missing A parts to zero");
  assert.match(compareBody, /const valB = partsB\[i\] \|\| 0/, "compareVersions must default missing B parts to zero");
  assert.match(compareBody, /if \(valA > valB\)\s+return 1;/, "compareVersions must report greater versions");
  assert.match(compareBody, /if \(valA < valB\)\s+return -1;/, "compareVersions must report lesser versions");
  assert.match(notesBody, /if \(!body\)\s+return \[\]/, "parseReleaseNotes must handle empty body");
  assert.match(notesBody, /body\.split\(\/\\r\?\\n\/\)/, "parseReleaseNotes must split on platform line endings");
  assert.match(notesBody, /entries\.push\(line\)/, "parseReleaseNotes must preserve release note lines");
  assert.match(notesBody, /while \(entries\.length > 0 && entries\[entries\.length - 1\]\.trim\(\)\.length === 0\)/, "parseReleaseNotes must trim trailing blank lines");
  assert.match(versionLineBody, /return \/\^v\?\\d\/i\.test\(text\)/, "isVersionLine must detect numeric version headings");
  assert.match(cleanBody, /cleaned\.replace\(\/\\\[\(\[\^\\\]\]\+\)\\\]\\\(\(\[\^\)\]\+\)\\\)\/g,\s*"\$1"\)/, "cleanEntry must strip markdown links");
  assert.match(cleanBody, /cleaned\.replace\(\/\\\(\(https\?:\\\/\\\/\[\^\)\]\+\)\\\)\/gi,\s*""\)/, "cleanEntry must drop parenthesized URLs");
  assert.match(cleanBody, /cleaned\.replace\(\/\\\(\[0-9a-f\]\{7,\}\\\)\/gi,\s*""\)/, "cleanEntry must drop commit hashes");
  assert.match(cleanBody, /cleaned\.replace\(\/\\s\+by\\s\+\[A-Za-z0-9_-\]\+\$\/i,\s*""\)/, "cleanEntry must drop trailing author names");
  assert.match(cleanBody, /cleaned\.toLowerCase\(\)\.startsWith\("merge branch"\)/, "cleanEntry must special-case merge branch entries");
  assert.match(ignoredBody, /lower\.startsWith\("release v"\)/, "isIgnoredEntry must ignore release headings");
  assert.match(ignoredBody, /lower\.includes\("autoformat"\) \|\| lower\.includes\("auto-formatting"\)/, "isIgnoredEntry must ignore autoformat entries");
  assert.match(ignoredBody, /lower\.includes\("qmlfmt"\)/, "isIgnoredEntry must ignore qmlfmt entries");
}

function testUpdateServiceOpenAndStateTransitionGuards() {
  const source = readQml("Services/Noctalia/UpdateService.qml");
  const openBody = extractFunctionBody(source, "openWhenReady");
  const discordBody = extractFunctionBody(source, "openDiscord");
  const feedbackBody = extractFunctionBody(source, "openFeedbackForm");
  const latestBody = extractFunctionBody(source, "showLatestChangelog");
  const clearBody = extractFunctionBody(source, "clearChangelogRequest");
  const markBody = extractFunctionBody(source, "markChangelogSeen");

  assert.match(openBody, /if \(!popupScheduled\)\s+return;/, "openWhenReady must only run for scheduled popups");
  assert.match(openBody, /!Quickshell\.screens \|\| Quickshell\.screens\.length === 0[\s\S]*Qt\.callLater\(openWhenReady\)/, "openWhenReady must wait for screens");
  assert.match(openBody, /PanelService\.getPanel\("changelogPanel",\s*targetScreen\)/, "openWhenReady must target changelog panel");
  assert.match(openBody, /if \(!panel\)[\s\S]*Qt\.callLater\(openWhenReady\)/, "openWhenReady must wait for panel registration");
  assert.match(openBody, /panel\.open\(\)/, "openWhenReady must open the panel");
  assert.match(openBody, /popupScheduled = false/, "openWhenReady must clear scheduled flag");
  assert.match(openBody, /lastShownVersion = changelogCurrentVersion/, "openWhenReady must remember shown version");
  assert.match(discordBody, /if \(!discordUrl\)\s+return;/, "openDiscord must guard empty URL");
  assert.match(discordBody, /Quickshell\.execDetached\(\["xdg-open",\s*discordUrl\]\)/, "openDiscord must open the Discord URL");
  assert.match(feedbackBody, /if \(!feedbackUrl\)\s+return;/, "openFeedbackForm must guard empty URL");
  assert.match(feedbackBody, /Quickshell\.execDetached\(\["xdg-open",\s*feedbackUrl\]\)/, "openFeedbackForm must open feedback URL");
  assert.match(latestBody, /if \(!currentVersion\)\s+return;/, "showLatestChangelog must guard empty current version");
  assert.match(latestBody, /if \(!changelogStateLoaded\)[\s\S]*pendingShowRequest = true[\s\S]*return;/, "showLatestChangelog must defer until state loads");
  assert.match(latestBody, /if \(lastSeen === currentVersion\)\s+return;/, "showLatestChangelog must skip already seen version");
  assert.match(latestBody, /changelogFromVersion = lastSeen/, "showLatestChangelog must set source version");
  assert.match(latestBody, /changelogToVersion = currentVersion/, "showLatestChangelog must set target version");
  assert.match(latestBody, /changelogPending = true/, "showLatestChangelog must mark a request pending");
  assert.match(latestBody, /handleChangelogRequest\(\)/, "showLatestChangelog must dispatch the request");
  assert.match(clearBody, /changelogPending = false/, "clearChangelogRequest must clear pending flag");
  assert.match(clearBody, /changelogFromVersion = ""/, "clearChangelogRequest must clear source version");
  assert.match(clearBody, /changelogToVersion = ""/, "clearChangelogRequest must clear target version");
  assert.match(markBody, /if \(!version\)\s+return;/, "markChangelogSeen must ignore empty versions");
  assert.match(markBody, /changelogLastSeenVersion = version/, "markChangelogSeen must store seen version");
  assert.match(markBody, /debouncedSaveChangelogState\(\)/, "markChangelogSeen must persist state");
}

function testUpdateServiceChangelogStatePersistenceGuards() {
  const source = readQml("Services/Noctalia/UpdateService.qml");
  const loadBody = extractFunctionBody(source, "loadChangelogState");
  const debounceBody = extractFunctionBody(source, "debouncedSaveChangelogState");
  const executeBody = extractFunctionBody(source, "executeSave");
  const saveBody = extractFunctionBody(source, "saveChangelogState");

  assert.match(loadBody, /const changelog = ShellState\.getChangelogState\(\)/, "loadChangelogState must read ShellState changelog state");
  assert.match(loadBody, /changelogLastSeenVersion = changelog\.lastSeenVersion \|\| ""/, "loadChangelogState must restore last seen version");
  assert.match(loadBody, /Logger\.e\("UpdateService",\s*"Failed to load changelog state:",\s*error\)/, "loadChangelogState must log load failures");
  assert.match(loadBody, /changelogStateLoaded = true/, "loadChangelogState must mark state loaded even after failure");
  assert.match(loadBody, /if \(pendingShowRequest\)[\s\S]*pendingShowRequest = false[\s\S]*Qt\.callLater\(root\.showLatestChangelog\)/, "loadChangelogState must replay deferred show requests");
  assert.match(debounceBody, /pendingSave = true/, "debouncedSaveChangelogState must queue a save");
  assert.match(debounceBody, /saveDebouncer\.restart\(\)/, "debouncedSaveChangelogState must debounce saves");
  assert.match(executeBody, /if \(!pendingSave\)\s+return;/, "executeSave must no-op with no pending save");
  assert.match(executeBody, /if \(saveInProgress\)[\s\S]*saveDebouncer\.start\(\)[\s\S]*return;/, "executeSave must retry when a save is already running");
  assert.match(executeBody, /pendingSave = false[\s\S]*saveInProgress = true/, "executeSave must claim the pending save");
  assert.match(executeBody, /ShellState\.setChangelogState\(\{[\s\S]*lastSeenVersion: changelogLastSeenVersion \|\| ""[\s\S]*\}\)/, "executeSave must persist last seen version");
  assert.match(executeBody, /saveInProgress = false/, "executeSave must clear save-in-progress flag");
  assert.match(executeBody, /if \(pendingSave\)[\s\S]*Qt\.callLater\(executeSave\)/, "executeSave must handle saves queued during save");
  assert.match(executeBody, /Logger\.e\("UpdateService",\s*"Failed to save changelog state:",\s*error\)/, "executeSave must log save failures");
  assert.match(saveBody, /debouncedSaveChangelogState\(\)/, "saveChangelogState must preserve immediate-save compatibility through debounce path");
}

const tests = [
  testUpdateServiceInitializationAndChangelogRequestGuards,
  testUpdateServiceVersionAndReleaseNoteParsing,
  testUpdateServiceOpenAndStateTransitionGuards,
  testUpdateServiceChangelogStatePersistenceGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
