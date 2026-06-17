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

function launchRecorderContext(overrides = {}) {
  const execs = [];
  const ctx = {
    settings: settings(overrides.settings),
    Time: {
      getFormattedTimestamp() {
        return "2026-06-16_120000";
      },
    },
    Settings: {
      preprocessPath(value) {
        assert.equal(value, overrides.expectedDirectory || ctx.settings.directory);
        return overrides.videoDir === undefined ? "/home/alessio/Videos" : overrides.videoDir;
      },
    },
    primaryMonitorResolution: overrides.primaryMonitorResolution === undefined ? "3440x1440" : overrides.primaryMonitorResolution,
    outputPath: "",
    recorderProcess: {
      exec(payload) {
        execs.push(payload);
      },
    },
    pendingTimer: { running: false },
  };

  return { ctx, execs };
}

function launchRecorderCommand(overrides = {}) {
  const launchRecorder = qmlFunction("launchRecorder");
  const { ctx, execs } = launchRecorderContext(overrides);
  launchRecorder(ctx);
  return { command: execs[0].command[2], ctx, execs };
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

function testScreenRecorderParsesCaptureSourcesAndMonitorList() {
  assert.match(source, /function parseCaptureSources\(output: string\)/, "capture source parser must type raw output");
  assert.match(source, /function parseMonitorList\(output: string, existingSources\)/, "monitor list parser must type raw output and accept dynamic existing sources");
  assert.match(source, /root\.captureSources = root\.parseCaptureSources\(this\.text\)/, "capture options collector must use parser helper");
  assert.match(source, /const monitorResult = root\.parseMonitorList\(this\.text, root\.captureSources\)/, "monitor collector must use parser helper");

  const parseCaptureSources = qmlFunction("parseCaptureSources", "output");
  const parseMonitorList = qmlFunction("parseMonitorList", "output", "existingSources");

  const parsedSources = parseCaptureSources({}, [
    "eDP-1|1920x1200",
    "region",
    "/dev/video0|Camera",
    "HDMI-A-1|3440x1440",
    "",
  ].join("\n"));

  assert.deepEqual(parsedSources, [
    { key: "eDP-1", name: "eDP-1 (1920x1200)", label: "eDP-1 (1920x1200)", resolution: "1920x1200" },
    { key: "region", name: "Select region", label: "Select region" },
    { key: "HDMI-A-1", name: "HDMI-A-1 (3440x1440)", label: "HDMI-A-1 (3440x1440)", resolution: "3440x1440" },
    { key: "portal", name: "Portal (window picker)", label: "Portal (window picker)" },
  ]);

  const monitorResult = parseMonitorList({}, [
    "eDP-1|1920x1200",
    "/dev/video0|Camera",
    "DP-2|2560x1440",
    "HDMI-A-1|3440x1440",
  ].join("\n"), parsedSources);

  assert.equal(monitorResult.primaryMonitorResolution, "1920x1200");
  assert.deepEqual(monitorResult.sources, [
    { key: "eDP-1", name: "eDP-1 (1920x1200)", label: "eDP-1 (1920x1200)", resolution: "1920x1200" },
    { key: "region", name: "Select region", label: "Select region" },
    { key: "HDMI-A-1", name: "HDMI-A-1 (3440x1440)", label: "HDMI-A-1 (3440x1440)", resolution: "3440x1440" },
    { key: "DP-2", name: "DP-2 (2560x1440)", label: "DP-2 (2560x1440)", resolution: "2560x1440" },
    { key: "portal", name: "Portal (window picker)", label: "Portal (window picker)" },
  ]);
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
  const { command, ctx, execs } = launchRecorderCommand();

  assert.equal(ctx.outputPath, "/home/alessio/Videos/2026-06-16_120000.mp4");
  assert.equal(ctx.pendingTimer.running, true);
  assert.deepEqual(execs[0].command.slice(0, 2), ["sh", "-c"]);
  assert.match(command, /gpu-screen-recorder/);
  assert.match(command, /-w focused -s 3440x1440 -f 60/);
  assert.match(command, /-a "default_output\|default_input"/);
  assert.match(command, /-o "\/home\/alessio\/Videos\/2026-06-16_120000\.mp4"/);
}

function testScreenRecorderLaunchRecorderBuildsAudioSourceVariants() {
  assert.match(launchRecorderCommand({
    settings: { audioSource: "default_output" },
  }).command, /-a default_output/, "system output audio source must be passed directly");

  assert.match(launchRecorderCommand({
    settings: { audioSource: "default_input" },
  }).command, /-a default_input/, "microphone audio source must be passed directly");
}

function testScreenRecorderLaunchRecorderHandlesDirectoryAndFocusSizeVariants() {
  const emptyDirectory = launchRecorderCommand({
    expectedDirectory: "",
    primaryMonitorResolution: "",
    settings: {
      directory: "",
      videoSource: "screen",
    },
    videoDir: "",
  });

  assert.equal(emptyDirectory.ctx.outputPath, "2026-06-16_120000.mp4", "empty output directory keeps filename relative");
  assert.match(emptyDirectory.command, /-w screen  -f 60/, "non-focused capture does not add focused size flag");
  assert.doesNotMatch(emptyDirectory.command, /-s 3440x1440/, "non-focused capture omits primary monitor size");
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
  testScreenRecorderParsesCaptureSourcesAndMonitorList,
  testScreenRecorderToggleDelegatesByState,
  testScreenRecorderStartRecordingGuardsAndPortalPath,
  testScreenRecorderStartRecordingDirectLaunchPath,
  testScreenRecorderLaunchRecorderBuildsCommandAndStartsPendingTimer,
  testScreenRecorderLaunchRecorderBuildsAudioSourceVariants,
  testScreenRecorderLaunchRecorderHandlesDirectoryAndFocusSizeVariants,
  testScreenRecorderStopRecordingGuardsAndStopsState,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
