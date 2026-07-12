#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createShellState() {
  const source = readQml("Commons/ShellState.qml");
  const shellState = {
    adapter: {
      display: {},
      notificationsState: { lastSeenTs: 0 },
      changelogState: { lastSeenVersion: "" },
      colorSchemesList: { schemes: [], timestamp: 0 },
    },
    save() {},
    displayStateChanged() {},
    notificationsStateChanged() {},
    changelogStateChanged() {},
    colorSchemesListChanged() {},
  };
  shellState.data = shellState.adapter;
  for (const [name, args] of [
    ["getDisplay", []],
    ["setDisplay", ["displayData"]],
    ["getNotificationsState", []],
    ["setNotificationsState", ["stateData"]],
    ["getChangelogState", []],
    ["setChangelogState", ["stateData"]],
    ["getColorSchemesList", []],
    ["setColorSchemesList", ["listData"]],
  ]) {
    const fn = qmlFunction(source, name, ...args);
    shellState[name] = (...values) => fn(shellState, ...values);
  }
  return shellState;
}

const Logger = { d() {}, e() {} };

function testCompositorDisplayStateRoundTripsThroughShellState() {
  const source = readQml("Services/Compositor/CompositorService.qml");
  const save = qmlFunction(source, "saveDisplayScalesToCache");
  const load = qmlFunction(source, "loadDisplayScalesFromState");
  const shellState = createShellState();
  const expected = { "DP-1": { scale: 1.25, width: 2560, height: 1440 } };
  const ctx = { ShellState: shellState, Logger, displayScales: expected, displayScalesLoaded: false };

  save(ctx);
  ctx.displayScales = {};
  load(ctx);

  assert.deepEqual(ctx.displayScales, expected);
  assert.equal(ctx.displayScalesLoaded, true);
  assert.deepEqual(shellState.data.display, expected);
}

function testNotificationStateRoundTripsThroughShellState() {
  const source = readQml("Services/System/NotificationService.qml");
  const save = qmlFunction(source, "saveState");
  const load = qmlFunction(source, "loadState");
  const shellState = createShellState();
  const ctx = { ShellState: shellState, Logger, lastSeenTs: 123456 };
  ctx.root = ctx;

  save(ctx);
  ctx.lastSeenTs = 0;
  load(ctx);

  assert.equal(ctx.lastSeenTs, 123456);
  assert.deepEqual(shellState.data.notificationsState, { lastSeenTs: 123456 });
}

function testChangelogStateRoundTripsThroughShellState() {
  const source = readQml("Services/Noctalia/UpdateService.qml");
  const save = qmlFunction(source, "executeSave");
  const load = qmlFunction(source, "loadChangelogState");
  const shellState = createShellState();
  const ctx = {
    ShellState: shellState,
    Logger,
    Qt: { callLater(callback) { callback(); } },
    changelogLastSeenVersion: "v5.2.1",
    changelogStateLoaded: false,
    pendingSave: true,
    pendingShowRequest: false,
    saveInProgress: false,
    showLatestChangelog() {},
  };
  ctx.root = ctx;

  save(ctx);
  ctx.changelogLastSeenVersion = "";
  load(ctx);

  assert.equal(ctx.changelogLastSeenVersion, "v5.2.1");
  assert.equal(ctx.changelogStateLoaded, true);
  assert.deepEqual(shellState.data.changelogState, { lastSeenVersion: "v5.2.1" });
}

function testChangelogSaveFailureRetainsPendingState() {
  const source = readQml("Services/Noctalia/UpdateService.qml");
  const save = qmlFunction(source, "executeSave");
  const errors = [];
  const ctx = {
    ShellState: {
      setChangelogState() {
        throw new Error("persistence unavailable");
      },
    },
    Logger: { d() {}, e(...args) { errors.push(args); } },
    Qt: { callLater() {} },
    changelogLastSeenVersion: "v5.2.1",
    pendingSave: true,
    saveInProgress: false,
  };

  save(ctx);

  assert.equal(ctx.pendingSave, true, "failed persistence must retain the dirty state");
  assert.equal(ctx.saveInProgress, false, "failed persistence must release the in-progress guard");
  assert.equal(errors.length, 1);
}

function testColorSchemeListRoundTripsThroughShellState() {
  const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml");
  const save = qmlFunction(source, "saveSchemesToCache");
  const load = qmlFunction(source, "loadSchemesFromCache");
  const shellState = createShellState();
  const expected = [{ name: "Ayu", path: "ayu" }];
  const ctx = {
    ShellState: shellState,
    Logger,
    Time: { timestamp: 1000 },
    availableSchemes: expected,
    fetching: true,
    hasInitialData: false,
    lastApiFetchTime: 0,
    minApiFetchInterval: 60,
    schemesCacheUpdateFrequency: 3600,
    fetchAvailableSchemesFromAPI() {
      throw new Error("fresh round-trip cache must not fetch from API");
    },
  };

  save(ctx);
  ctx.availableSchemes = [];
  load(ctx);

  assert.deepEqual(ctx.availableSchemes, expected);
  assert.equal(ctx.hasInitialData, true);
  assert.equal(ctx.fetching, false);
  assert.deepEqual(shellState.data.colorSchemesList, { schemes: expected, timestamp: 1000 });
}

const tests = [
  testCompositorDisplayStateRoundTripsThroughShellState,
  testNotificationStateRoundTripsThroughShellState,
  testChangelogStateRoundTripsThroughShellState,
  testChangelogSaveFailureRetainsPendingState,
  testColorSchemeListRoundTripsThroughShellState,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
