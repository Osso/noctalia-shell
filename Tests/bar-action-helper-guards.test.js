#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const customButtonSource = readQml("Modules/Bar/Widgets/CustomButton.qml");
const microphoneSource = readQml("Modules/Bar/Widgets/Microphone.qml");
const screenRecorderSource = readQml("Modules/Bar/Widgets/ScreenRecorder.qml");
const taskbarSource = readQml("Modules/Bar/Widgets/Taskbar.qml");
const trayDrawerSource = readQml("Modules/Panels/Tray/TrayDrawerPanel.qml");
const volumeSource = readQml("Modules/Bar/Widgets/Volume.qml");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testCustomButtonRunTextCommandGuardsEmptyAndRunningCommands() {
  const runTextCommand = qmlFunction(customButtonSource, "runTextCommand");
  const textProc = { running: false, command: null };

  runTextCommand({ textCommand: "", textProc });
  assert.equal(textProc.running, false);
  assert.equal(textProc.command, null);

  const runningProc = { running: true, command: ["old"] };
  runTextCommand({ textCommand: "date", textProc: runningProc });
  assert.deepEqual(runningProc.command, ["old"]);
  assert.equal(runningProc.running, true);
}

function testCustomButtonRunTextCommandStartsShellCommand() {
  const runTextCommand = qmlFunction(customButtonSource, "runTextCommand");
  const textProc = { running: false, command: null };

  runTextCommand({ textCommand: "notify-send hello", textProc });

  assert.deepEqual(textProc.command, ["sh", "-lc", "notify-send hello"]);
  assert.equal(textProc.running, true);
}

function testAudioWidgetsOpenConfiguredExternalMixer() {
  const microphoneOpenExternalMixer = qmlFunction(microphoneSource, "openExternalMixer");
  const volumeOpenExternalMixer = qmlFunction(volumeSource, "openExternalMixer");
  const calls = [];
  const ctx = {
    Settings: {
      data: {
        audio: {
          externalMixer: "pavucontrol",
        },
      },
    },
    Quickshell: {
      execDetached(command) {
        calls.push(command);
      },
    },
  };

  microphoneOpenExternalMixer(ctx);
  volumeOpenExternalMixer(ctx);

  assert.deepEqual(calls, [
    ["sh", "-c", "pavucontrol"],
    ["sh", "-c", "pavucontrol"],
  ]);
}

function testScreenRecorderHandleClickShowsInstallErrorWhenUnavailable() {
  const handleClick = qmlFunction(screenRecorderSource, "handleClick");
  const errors = [];
  const ctx = {
    ScreenRecorderService: {
      isAvailable: false,
    },
    ToastService: {
      showError(summary, body) {
        errors.push([summary, body]);
      },
    },
    I18n: {
      tr(key) {
        return key;
      },
    },
  };

  handleClick(ctx);

  assert.deepEqual(errors, [["toast.recording.not-installed", "toast.recording.not-installed-desc"]]);
}

function testScreenRecorderHandleClickStopsActiveOrPendingRecording() {
  const handleClick = qmlFunction(screenRecorderSource, "handleClick");
  let stopCount = 0;
  const ctx = {
    ScreenRecorderService: {
      isAvailable: true,
      isRecording: false,
      isPending: true,
      stopRecording() {
        stopCount++;
      },
    },
  };

  handleClick(ctx);

  assert.equal(stopCount, 1);
}

function testScreenRecorderHandleClickOpensSourceMenuWhenIdle() {
  const handleClick = qmlFunction(screenRecorderSource, "handleClick");
  const calls = [];
  const sourceMenu = {
    implicitWidth: 320,
    implicitHeight: 180,
    model: null,
    openAtItem(item, x, y) {
      calls.push(["openAtItem", item, x, y]);
    },
  };
  const root = { id: "root" };
  const ctx = {
    root,
    screen: { name: "HDMI-A-1" },
    sourceMenu,
    ScreenRecorderService: {
      isAvailable: true,
      isRecording: false,
      isPending: false,
      captureSources: ["screen", "window"],
    },
    PanelService: {
      getPopupMenuWindow(screen) {
        calls.push(["getPopupMenuWindow", screen.name]);
        return {
          showContextMenu(menu) {
            calls.push(["showContextMenu", menu]);
          },
        };
      },
    },
    BarService: {
      getContextMenuPosition(item, width, height) {
        calls.push(["getContextMenuPosition", item, width, height]);
        return { x: 12, y: 34 };
      },
    },
  };

  handleClick(ctx);

  assert.deepEqual(sourceMenu.model, ["screen", "window"]);
  assert.deepEqual(calls, [
    ["getPopupMenuWindow", "HDMI-A-1"],
    ["showContextMenu", sourceMenu],
    ["getContextMenuPosition", root, 320, 180],
    ["openAtItem", root, 12, 34],
  ]);
}

function testTaskbarUpdateHasWindowFiltersOutputAndWorkspace() {
  const updateHasWindow = qmlFunction(taskbarSource, "updateHasWindow");
  const windows = [
    { output: "DP-1", workspaceId: 1 },
    { output: "HDMI-A-1", workspaceId: 2 },
  ];
  const ctx = {
    hasWindow: false,
    onlySameOutput: true,
    onlyActiveWorkspaces: true,
    screen: { name: "HDMI-A-1" },
    CompositorService: {
      windows: {
        count: windows.length,
        get(index) {
          return windows[index];
        },
      },
      getActiveWorkspaces() {
        return [{ id: 2 }];
      },
    },
  };

  updateHasWindow(ctx);

  assert.equal(ctx.hasWindow, true);
}

function testTaskbarUpdateHasWindowFailsClosedOnErrors() {
  const updateHasWindow = qmlFunction(taskbarSource, "updateHasWindow");
  const ctx = {
    hasWindow: true,
    onlySameOutput: false,
    onlyActiveWorkspaces: false,
    screen: { name: "HDMI-A-1" },
    CompositorService: {
      windows: {
        get count() {
          throw new Error("unavailable");
        },
      },
    },
  };

  updateHasWindow(ctx);

  assert.equal(ctx.hasWindow, false);
}

function createDrawerContext(pinnedList) {
  const root = { pinnedList };
  const ctx = { root };
  const wildCardMatch = qmlFunction(trayDrawerSource, "wildCardMatch", "str", "rule");
  root.wildCardMatch = (str, rule) => wildCardMatch(ctx, str, rule);
  return ctx;
}

function testTrayDrawerIsPinnedMatchesTitleNameAndId() {
  const isPinned = qmlFunction(trayDrawerSource, "isPinned", "item");
  const ctx = createDrawerContext(["Bluetooth*", "Network", "fallback-id"]);

  assert.equal(isPinned(ctx, { tooltipTitle: "Bluetooth Manager" }), true);
  assert.equal(isPinned(ctx, { name: "Network" }), true);
  assert.equal(isPinned(ctx, { id: "fallback-id" }), true);
  assert.equal(isPinned(ctx, { tooltipTitle: "Power" }), false);
  assert.equal(isPinned(createDrawerContext([]), { tooltipTitle: "Bluetooth Manager" }), false);
  assert.equal(isPinned(ctx, null), false);
}

function testTrayDrawerIsPinnedTracksPinAndUnpin() {
  const isPinned = qmlFunction(trayDrawerSource, "isPinned", "item");
  const ctx = createDrawerContext([]);
  const item = { tooltipTitle: "Bluetooth Manager" };

  assert.equal(isPinned(ctx, item), false);
  ctx.root.pinnedList = ["Bluetooth*"];
  assert.equal(isPinned(ctx, item), true);
  ctx.root.pinnedList = [];
  assert.equal(isPinned(ctx, item), false);
}

function testTrayDrawerIsPinnedWithoutOwnerPinsNothing() {
  const isPinned = qmlFunction(trayDrawerSource, "isPinned", "item");
  const ctx = createDrawerContext(undefined);

  assert.equal(isPinned(ctx, { name: "Network" }), false);
  assert.equal(isPinned(ctx, { id: "fallback-id" }), false);
  assert.equal(isPinned(ctx, null), false);
}

function testTrayDrawerIsPinnedKeepsTwoOwnersIndependent() {
  const isPinned = qmlFunction(trayDrawerSource, "isPinned", "item");
  const first = createDrawerContext(["Bluetooth*"]);
  const second = createDrawerContext(["Network"]);
  const bluetooth = { tooltipTitle: "Bluetooth Manager" };
  const network = { name: "Network" };

  assert.equal(isPinned(first, bluetooth), true);
  assert.equal(isPinned(second, bluetooth), false);
  assert.equal(isPinned(first, network), false);
  assert.equal(isPinned(second, network), true);
  first.root.pinnedList = ["Network"];
  assert.equal(isPinned(first, bluetooth), false);
  assert.equal(isPinned(first, network), true);
  assert.equal(isPinned(second, bluetooth), false);
  assert.equal(isPinned(second, network), true);
  second.root.pinnedList = [];
  assert.equal(isPinned(second, network), false);
  assert.equal(isPinned(first, network), true);
}

const tests = [
  testCustomButtonRunTextCommandGuardsEmptyAndRunningCommands,
  testCustomButtonRunTextCommandStartsShellCommand,
  testAudioWidgetsOpenConfiguredExternalMixer,
  testScreenRecorderHandleClickShowsInstallErrorWhenUnavailable,
  testScreenRecorderHandleClickStopsActiveOrPendingRecording,
  testScreenRecorderHandleClickOpensSourceMenuWhenIdle,
  testTaskbarUpdateHasWindowFiltersOutputAndWorkspace,
  testTaskbarUpdateHasWindowFailsClosedOnErrors,
  testTrayDrawerIsPinnedMatchesTitleNameAndId,
  testTrayDrawerIsPinnedTracksPinAndUnpin,
  testTrayDrawerIsPinnedWithoutOwnerPinsNothing,
  testTrayDrawerIsPinnedKeepsTwoOwnersIndependent,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
