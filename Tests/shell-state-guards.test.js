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
  assert.match(source, /function handleStateLoadFailed\(error\)/, "ShellState must type load-failure errors");
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

function testShellStateInitializesFileOnlyAfterSettingsDirectories() {
  const initializeStateFile = qmlFunction("initializeStateFile");
  const ctx = {
    stateFile: "",
    Settings: {
      cacheDir: "/tmp/noctalia/",
      directoriesCreated: false,
    },
    stateFileView: { path: "" },
  };
  ctx.root = ctx;

  initializeStateFile(ctx);
  assert.equal(ctx.stateFileView.path, "", "state load must wait for synchronized directory creation");

  ctx.Settings.directoriesCreated = true;
  initializeStateFile(ctx);
  assert.equal(ctx.stateFile, "/tmp/noctalia/shell-state.json");
  assert.equal(ctx.stateFileView.path, ctx.stateFile);
  assert.match(source, /target:\s*Settings[\s\S]*?onDirectoriesCreatedChanged[\s\S]*?initializeStateFile/);
}

function createSaveContext() {
  const calls = [];
  const ctx = {
    saveQueued: true,
    saveInProgress: false,
    stateFile: "/tmp/noctalia/shell-state.json",
    saveDirectoryProcess: { running: false },
    saveTimer: {
      restarts: 0,
      restart() {
        this.restarts += 1;
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
  ctx.root = ctx;
  ctx.calls = calls;
  return ctx;
}

function testShellStatePerformSaveWaitsForDirectoryProcess() {
  const performSave = qmlFunction("performSave");
  const ctx = createSaveContext();

  ctx.saveQueued = false;
  performSave(ctx);
  assert.equal(ctx.saveDirectoryProcess.running, false);

  ctx.saveQueued = true;
  ctx.stateFile = "";
  performSave(ctx);
  assert.equal(ctx.saveDirectoryProcess.running, false);
  assert.equal(ctx.saveQueued, true);

  ctx.stateFile = "/tmp/noctalia/shell-state.json";
  ctx.saveInProgress = true;
  performSave(ctx);
  assert.equal(ctx.saveDirectoryProcess.running, false, "in-flight adapter write must block another directory process");

  ctx.saveInProgress = false;
  performSave(ctx);

  assert.equal(ctx.saveDirectoryProcess.running, true);
  assert.equal(ctx.saveQueued, true, "queued state must remain claimed until the process exits");
  assert.deepEqual(ctx.calls, [], "adapter write must not run before directory process completion");

  ctx.saveDirectoryProcess.running = true;
  performSave(ctx);
  assert.deepEqual(ctx.calls, [], "concurrent save must coalesce behind the running process");
}

function testShellStateDirectoryExitWritesOnlyAfterSuccess() {
  const handleSaveDirectoryExit = qmlFunction("handleSaveDirectoryExit", "exitCode");

  const failed = createSaveContext();
  handleSaveDirectoryExit(failed, 1);
  assert.equal(failed.saveQueued, true, "directory failure must preserve pending state");
  assert.deepEqual(failed.calls, [["error", ["ShellState", "Failed to create cache directory, exit:", 1]]]);

  const succeeded = createSaveContext();
  handleSaveDirectoryExit(succeeded, 0);
  assert.equal(succeeded.saveQueued, false, "starting the write must claim the current queued state");
  assert.equal(succeeded.saveInProgress, true, "write must remain in flight until FileView reports completion");
  assert.deepEqual(succeeded.calls, [["writeAdapter"]], "success must not be logged before onSaved");
}

function testShellStateDirectoryStartFailureKeepsSaveQueued() {
  const handleSaveDirectoryStartFailure = qmlFunction("handleSaveDirectoryStartFailure", "exitObserved");
  const ctx = createSaveContext();

  handleSaveDirectoryStartFailure(ctx, false);
  assert.equal(ctx.saveQueued, true);
  assert.deepEqual(ctx.calls, [["error", ["ShellState", "Failed to start cache directory creation"]]]);

  ctx.calls.length = 0;
  handleSaveDirectoryStartFailure(ctx, true);
  assert.deepEqual(ctx.calls, [], "normal exit must not be reported as failed start");
  assert.match(source, /id:\s*saveDirectoryProcess[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?exitObserved = true[\s\S]*?handleSaveDirectoryExit/);
  assert.match(source, /id:\s*saveDirectoryProcess[\s\S]*?onRunningChanged:[\s\S]*?handleSaveDirectoryStartFailure/);
}

function testShellStateSaveCompletionTracksAsyncResult() {
  assert.match(source, /onSaved:\s*root\.handleStateSaved\(\)/);
  assert.match(source, /onSaveFailed:\s*error => root\.handleStateSaveFailed\(error\)/);
  const handleStateSaved = qmlFunction("handleStateSaved");
  const handleStateSaveFailed = qmlFunction("handleStateSaveFailed", "error");

  const succeeded = createSaveContext();
  succeeded.saveQueued = false;
  succeeded.saveInProgress = true;
  handleStateSaved(succeeded);
  assert.equal(succeeded.saveInProgress, false);
  assert.equal(succeeded.saveQueued, false);
  assert.deepEqual(succeeded.calls, [["debug", ["ShellState", "Saved state file"]]]);

  const coalesced = createSaveContext();
  coalesced.saveQueued = true;
  coalesced.saveInProgress = true;
  handleStateSaved(coalesced);
  assert.equal(coalesced.saveInProgress, false);
  assert.equal(coalesced.saveQueued, true, "state changed during write must remain queued");
  assert.equal(coalesced.saveTimer.restarts, 1, "pending state must schedule the next write");

  const failed = createSaveContext();
  failed.saveQueued = false;
  failed.saveInProgress = true;
  handleStateSaveFailed(failed, "disk full");
  assert.equal(failed.saveInProgress, false);
  assert.equal(failed.saveQueued, true, "asynchronous FileView failure must restore dirty state");
  assert.deepEqual(failed.calls, [["error", ["ShellState", "Failed to write state file:", "disk full"]]]);
}

function testShellStateSynchronousWriteFailureKeepsSaveQueued() {
  const handleSaveDirectoryExit = qmlFunction("handleSaveDirectoryExit", "exitCode");
  const ctx = createSaveContext();
  ctx.stateFileView.writeAdapter = () => {
    throw new Error("write failed");
  };

  handleSaveDirectoryExit(ctx, 0);

  assert.equal(ctx.saveInProgress, false);
  assert.equal(ctx.saveQueued, true);
  assert.equal(ctx.calls.length, 1);
  assert.equal(ctx.calls[0][0], "error");
  assert.equal(ctx.calls[0][1][1], "Failed to write state file:");
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
  testShellStateInitializesFileOnlyAfterSettingsDirectories,
  testShellStatePerformSaveWaitsForDirectoryProcess,
  testShellStateDirectoryExitWritesOnlyAfterSuccess,
  testShellStateDirectoryStartFailureKeepsSaveQueued,
  testShellStateSaveCompletionTracksAsyncResult,
  testShellStateSynchronousWriteFailureKeepsSaveQueued,
  testShellStateBuildSnapshotAggregatesSettingsAndCachedState,
  testShellStateBuildSnapshotFailsClosedOnConversionErrors,
  testShellStateSettersSaveAndEmitMatchingSignals,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
