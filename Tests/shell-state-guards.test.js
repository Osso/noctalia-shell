#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Commons/ShellState.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testShellStateSaveQueuesDebouncedWrite() {
  const save = qmlFunction("save");
  let restartCount = 0;
  const ctx = {
    saveQueued: false,
    saveTimer: {
      restart() {
        restartCount += 1;
      },
    },
  };

  save(ctx);

  assert.equal(ctx.saveQueued, true);
  assert.equal(restartCount, 1);
}

function testShellStateLoadHandlersPublishLoadedState() {
  assert.match(source, /function handleStateLoaded\(\)/, "ShellState must expose a tested load-success helper");
  assert.match(source, /function handleStateLoadFailed\(error: int\)/, "ShellState must type load-failure errors");
  assert.match(source, /onLoaded:\s*root\.handleStateLoaded\(\)/, "FileView load success must route through the helper");
  assert.match(source, /onLoadFailed:\s*error => root\.handleStateLoadFailed\(error\)/, "FileView load failure must route through the helper");

  const handleStateLoaded = qmlFunction("handleStateLoaded");
  const handleStateLoadFailed = qmlFunction("handleStateLoadFailed", "error");
  const logs = [];
  const ctx = {
    isLoaded: false,
    Logger: {
      d(...args) {
        logs.push(["debug", args]);
      },
      e(...args) {
        logs.push(["error", args]);
      },
    },
  };

  handleStateLoaded(ctx);

  assert.equal(ctx.isLoaded, true);
  assert.deepEqual(logs, [["debug", ["ShellState", "Loaded state file"]]]);

  ctx.isLoaded = false;
  logs.length = 0;
  handleStateLoadFailed(ctx, 2);

  assert.equal(ctx.isLoaded, true);
  assert.deepEqual(logs, [["debug", ["ShellState", "State file doesn't exist, will create on first write"]]]);

  ctx.isLoaded = false;
  logs.length = 0;
  handleStateLoadFailed(ctx, 13);

  assert.equal(ctx.isLoaded, true);
  assert.deepEqual(logs, [["error", ["ShellState", "Failed to load state file:", 13]]]);
}

function testShellStatePerformSaveGuardsAndWritesQueuedState() {
  const performSave = qmlFunction("performSave");
  const calls = [];
  const ctx = {
    saveQueued: false,
    stateFile: "/tmp/noctalia/shell-state.json",
    Settings: {
      cacheDir: "/tmp/noctalia/",
    },
    Quickshell: {
      execDetached(args) {
        calls.push(["execDetached", args]);
      },
    },
    Qt: {
      callLater(callback) {
        calls.push(["callLater"]);
        callback();
      },
    },
    stateFileView: {
      writeAdapter() {
        calls.push(["writeAdapter"]);
      },
    },
    Logger: {
      d(...args) {
        calls.push(["debug", args]);
      },
      e(...args) {
        calls.push(["error", args]);
      },
    },
  };

  performSave(ctx);

  assert.equal(ctx.saveQueued, false);
  assert.deepEqual(calls, []);

  ctx.saveQueued = true;
  ctx.stateFile = "";
  performSave(ctx);

  assert.equal(ctx.saveQueued, true);
  assert.deepEqual(calls, []);

  ctx.stateFile = "/tmp/noctalia/shell-state.json";
  performSave(ctx);

  assert.equal(ctx.saveQueued, false);
  assert.deepEqual(calls, [
    ["execDetached", ["mkdir", "-p", "/tmp/noctalia/"]],
    ["callLater"],
    ["writeAdapter"],
    ["debug", ["ShellState", "Saved state file"]],
  ]);
}

function testShellStateBuildSnapshotAggregatesSettingsAndCachedState() {
  const buildStateSnapshot = qmlFunction("buildStateSnapshot");
  const ctx = {
    Settings: {
      data: {
        theme: "ayu",
      },
    },
    ShellState: {
      data: {
        display: {
          HDMI: {
            scale: 1.25,
          },
        },
        notificationsState: {
          lastSeenTs: 123,
        },
        changelogState: {
          lastSeenVersion: "1.2.3",
        },
        colorSchemesList: {
          schemes: ["ayu"],
          timestamp: 456,
        },
      },
    },
    QtObj2JS: {
      qtObjectToPlainObject(value) {
        return { ...value };
      },
    },
    NotificationService: {
      doNotDisturb: true,
    },
    PowerProfileService: {
      noctaliaPerformanceMode: "balanced",
    },
    BarService: {
      isVisible: false,
    },
    WallpaperService: {
      currentWallpapers: {
        HDMI: "/wallpaper.png",
      },
    },
    Logger: {
      e() {},
    },
  };

  assert.deepEqual(buildStateSnapshot(ctx), {
    settings: {
      theme: "ayu",
    },
    state: {
      doNotDisturb: true,
      noctaliaPerformanceMode: "balanced",
      barVisible: false,
      wallpapers: {
        HDMI: "/wallpaper.png",
      },
      display: {
        HDMI: {
          scale: 1.25,
        },
      },
      notificationsState: {
        lastSeenTs: 123,
      },
      changelogState: {
        lastSeenVersion: "1.2.3",
      },
      colorSchemesList: {
        schemes: ["ayu"],
        timestamp: 456,
      },
    },
  });
}

function testShellStateBuildSnapshotFailsClosedOnConversionErrors() {
  const buildStateSnapshot = qmlFunction("buildStateSnapshot");
  const errors = [];
  const ctx = {
    Settings: {
      data: {},
    },
    ShellState: {
      data: {},
    },
    QtObj2JS: {
      qtObjectToPlainObject() {
        throw new Error("conversion failed");
      },
    },
    Logger: {
      e(...args) {
        errors.push(args);
      },
    },
  };

  assert.equal(buildStateSnapshot(ctx), null);
  assert.equal(errors.length, 1);
  assert.equal(errors[0][0], "Settings");
  assert.equal(errors[0][1], "Failed to build state snapshot:");
}

function testShellStateSettersSaveAndEmitMatchingSignals() {
  const cases = [
    {
      setter: qmlFunction("setDisplay", "displayData"),
      value: { HDMI: { scale: 1.25 } },
      adapterKey: "display",
      signalName: "displayStateChanged",
    },
    {
      setter: qmlFunction("setNotificationsState", "stateData"),
      value: { lastSeenTs: 123 },
      adapterKey: "notificationsState",
      signalName: "notificationsStateChanged",
    },
    {
      setter: qmlFunction("setChangelogState", "stateData"),
      value: { lastSeenVersion: "1.2.3" },
      adapterKey: "changelogState",
      signalName: "changelogStateChanged",
    },
    {
      setter: qmlFunction("setColorSchemesList", "listData"),
      value: { schemes: ["ayu"], timestamp: 456 },
      adapterKey: "colorSchemesList",
      signalName: "colorSchemesListChanged",
    },
  ];

  for (const testCase of cases) {
    const calls = [];
    const ctx = {
      adapter: {},
      save() {
        calls.push("save");
      },
      displayStateChanged() {
        calls.push("displayStateChanged");
      },
      notificationsStateChanged() {
        calls.push("notificationsStateChanged");
      },
      changelogStateChanged() {
        calls.push("changelogStateChanged");
      },
      colorSchemesListChanged() {
        calls.push("colorSchemesListChanged");
      },
    };

    testCase.setter(ctx, testCase.value);

    assert.deepEqual(ctx.adapter[testCase.adapterKey], testCase.value);
    assert.deepEqual(calls, ["save", testCase.signalName]);
  }
}

const tests = [
  testShellStateSaveQueuesDebouncedWrite,
  testShellStateLoadHandlersPublishLoadedState,
  testShellStatePerformSaveGuardsAndWritesQueuedState,
  testShellStateBuildSnapshotAggregatesSettingsAndCachedState,
  testShellStateBuildSnapshotFailsClosedOnConversionErrors,
  testShellStateSettersSaveAndEmitMatchingSignals,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
