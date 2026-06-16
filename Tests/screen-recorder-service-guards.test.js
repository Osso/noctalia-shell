#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Media/ScreenRecorderService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function settings(overrides = {}) {
  return {
    directory: "~/Videos",
    videoSource: "focused",
    frameRate: 60,
    audioCodec: "opus",
    videoCodec: "h264",
    audioSource: "both",
    quality: "high",
    showCursor: true,
    colorRange: "limited",
    ...overrides,
  };
}

function testScreenRecorderRefreshCaptureSourcesStartsBothQueries() {
  const refreshCaptureSources = qmlFunction("refreshCaptureSources");
  const ctx = {
    captureSourcesProcess: { command: [], running: false },
    monitorListProcess: { command: [], running: false },
  };

  refreshCaptureSources(ctx);

  assert.deepEqual(ctx.captureSourcesProcess.command, ["gpu-screen-recorder", "--list-capture-options"]);
  assert.equal(ctx.captureSourcesProcess.running, true);
  assert.deepEqual(ctx.monitorListProcess.command, ["gpu-screen-recorder", "--list-monitors"]);
  assert.equal(ctx.monitorListProcess.running, true);
}

function testScreenRecorderToggleDelegatesByState() {
  const toggleRecording = qmlFunction("toggleRecording");
  const calls = [];
  const ctx = {
    isRecording: false,
    isPending: false,
    startRecording() {
      calls.push("start");
    },
    stopRecording() {
      calls.push("stop");
    },
  };

  toggleRecording(ctx);
  ctx.isRecording = true;
  toggleRecording(ctx);
  ctx.isRecording = false;
  ctx.isPending = true;
  toggleRecording(ctx);

  assert.deepEqual(calls, ["start", "stop", "stop"]);
}

function testScreenRecorderStartRecordingGuardsAndPortalPath() {
  const startRecording = qmlFunction("startRecording");
  const closedPanels = [];
  const portalExecs = [];
  const ctx = {
    isAvailable: false,
    isRecording: false,
    isPending: false,
    hasActiveRecording: true,
    settings: settings({ videoSource: "portal" }),
    PanelService: {
      openedPanel: {
        isClosing: false,
        close() {
          closedPanels.push("closed");
        },
      },
    },
    portalCheckProcess: {
      exec(payload) {
        portalExecs.push(payload);
      },
    },
    launchRecorder() {
      throw new Error("launchRecorder should not run for unavailable or portal checks");
    },
  };

  startRecording(ctx);
  assert.equal(ctx.isPending, false);

  ctx.isAvailable = true;
  startRecording(ctx);

  assert.equal(ctx.isPending, true);
  assert.equal(ctx.hasActiveRecording, false);
  assert.deepEqual(closedPanels, ["closed"]);
  assert.deepEqual(portalExecs[0].command.slice(0, 2), ["sh", "-c"]);
  assert.match(portalExecs[0].command[2], /xdg-desktop-portal/);

  ctx.isPending = false;
  ctx.isRecording = true;
  startRecording(ctx);
  assert.equal(portalExecs.length, 1);
}

function testScreenRecorderStartRecordingDirectLaunchPath() {
  const startRecording = qmlFunction("startRecording");
  let launches = 0;
  const ctx = {
    isAvailable: true,
    isRecording: false,
    isPending: false,
    hasActiveRecording: true,
    settings: settings({ videoSource: "focused" }),
    PanelService: { openedPanel: null },
    portalCheckProcess: {
      exec() {
        throw new Error("portal check should not run for direct capture");
      },
    },
    launchRecorder() {
      launches++;
    },
  };

  startRecording(ctx);

  assert.equal(ctx.isPending, true);
  assert.equal(ctx.hasActiveRecording, false);
  assert.equal(launches, 1);
}

function testScreenRecorderLaunchRecorderBuildsCommandAndStartsPendingTimer() {
  const launchRecorder = qmlFunction("launchRecorder");
  const execs = [];
  const ctx = {
    settings: settings(),
    Time: {
      getFormattedTimestamp() {
        return "2026-06-16_120000";
      },
    },
    Settings: {
      preprocessPath(value) {
        assert.equal(value, "~/Videos");
        return "/home/alessio/Videos";
      },
    },
    primaryMonitorResolution: "3440x1440",
    outputPath: "",
    recorderProcess: {
      exec(payload) {
        execs.push(payload);
      },
    },
    pendingTimer: { running: false },
  };

  launchRecorder(ctx);

  assert.equal(ctx.outputPath, "/home/alessio/Videos/2026-06-16_120000.mp4");
  assert.equal(ctx.pendingTimer.running, true);
  assert.deepEqual(execs[0].command.slice(0, 2), ["sh", "-c"]);
  assert.match(execs[0].command[2], /gpu-screen-recorder/);
  assert.match(execs[0].command[2], /-w focused -s 3440x1440 -f 60/);
  assert.match(execs[0].command[2], /-a "default_output\|default_input"/);
  assert.match(execs[0].command[2], /-o "\/home\/alessio\/Videos\/2026-06-16_120000\.mp4"/);
}

function testScreenRecorderStopRecordingGuardsAndStopsState() {
  const stopRecording = qmlFunction("stopRecording");
  const toasts = [];
  const commands = [];
  const ctx = {
    isRecording: false,
    isPending: false,
    outputPath: "/tmp/out.mp4",
    ToastService: {
      showNotice(...args) {
        toasts.push(args);
      },
    },
    I18n: {
      tr(key) {
        return `tr:${key}`;
      },
    },
    Quickshell: {
      execDetached(command) {
        commands.push(command);
      },
    },
    pendingTimer: { running: true },
    monitorTimer: { running: true },
    killTimer: { running: false },
    hasActiveRecording: true,
  };

  stopRecording(ctx);
  assert.deepEqual(toasts, []);
  assert.deepEqual(commands, []);

  ctx.isPending = true;
  stopRecording(ctx);

  assert.equal(ctx.isRecording, false);
  assert.equal(ctx.isPending, false);
  assert.equal(ctx.pendingTimer.running, false);
  assert.equal(ctx.monitorTimer.running, false);
  assert.equal(ctx.killTimer.running, true);
  assert.equal(ctx.hasActiveRecording, false);
  assert.deepEqual(toasts[0], ["tr:toast.recording.stopping", "/tmp/out.mp4", "settings-screen-recorder"]);
  assert.deepEqual(commands[0].slice(0, 2), ["sh", "-c"]);
  assert.match(commands[0][2], /pkill -SIGINT -f 'gpu-screen-recorder'/);
}

const tests = [
  testScreenRecorderRefreshCaptureSourcesStartsBothQueries,
  testScreenRecorderToggleDelegatesByState,
  testScreenRecorderStartRecordingGuardsAndPortalPath,
  testScreenRecorderStartRecordingDirectLaunchPath,
  testScreenRecorderLaunchRecorderBuildsCommandAndStartsPendingTimer,
  testScreenRecorderStopRecordingGuardsAndStopsState,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
