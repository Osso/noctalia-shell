#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { extractFunctionBody, findComponentBlock, readQml } = require("./qml-test-utils");

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
    killTimer: { running: true },
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
    discoveryInProgress: false,
    captureSourcesProcess: { command: [], running: false },
    monitorListProcess: { command: [], running: false },
  };

  refreshCaptureSources(ctx);

  assert.deepEqual(ctx.captureSourcesProcess.command, ["gpu-screen-recorder", "--list-capture-options"]);
  assert.equal(ctx.captureSourcesProcess.running, true);
  assert.deepEqual(ctx.monitorListProcess.command, ["gpu-screen-recorder", "--list-monitors"]);
  assert.equal(ctx.monitorListProcess.running, true);
}

function testScreenRecorderDiscoveryPublishesLatestCompleteSnapshot() {
  const refresh = qmlFunction("refreshCaptureSources");
  const publish = qmlFunction("publishDiscoveryIfComplete");
  const ctx = {
    discoveryInProgress: false,
    discoveryQueued: false,
    pendingCaptureOptions: null,
    pendingMonitorOutput: null,
    captureSources: [],
    primaryMonitorResolution: "",
    captureSourcesProcess: { running: false },
    monitorListProcess: { running: false },
  };
  const parseSources = qmlFunction("parseCaptureSources", "output");
  const parseMonitors = qmlFunction("parseMonitorList", "output", "existingSources");
  ctx.parseCaptureSources = output => parseSources(ctx, output);
  ctx.parseMonitorList = (output, sources) => parseMonitors(ctx, output, sources);
  ctx.refreshCaptureSources = () => refresh(ctx);

  refresh(ctx);
  ctx.pendingMonitorOutput = "DP-4|2560x1440";
  publish(ctx);
  assert.deepEqual(ctx.captureSources, []);
  ctx.pendingCaptureOptions = "DP-4|2560x1440\nregion";
  publish(ctx);
  assert.equal(ctx.primaryMonitorResolution, "2560x1440");

  refresh(ctx);
  ctx.pendingMonitorOutput = "eDP-1|1920x1200";
  publish(ctx);
  assert.equal(ctx.primaryMonitorResolution, "2560x1440", "partial refresh must not overwrite resolution");
  refresh(ctx);
  assert.equal(ctx.discoveryQueued, true, "hotplug during active query must request another snapshot");
  ctx.pendingCaptureOptions = "eDP-1|1920x1200\nregion";
  publish(ctx);
  assert.equal(ctx.primaryMonitorResolution, "1920x1200");
  assert.deepEqual(ctx.captureSources.filter(source => source.resolution).map(source => source.key), ["eDP-1"]);
  assert.equal(ctx.discoveryInProgress, true, "queued hotplug must start a new query");
  ctx.pendingCaptureOptions = "eDP-1|1920x1200\nregion";
  ctx.pendingMonitorOutput = "";
  publish(ctx);
  assert.equal(ctx.primaryMonitorResolution, "", "missing monitor result clears stale focused-capture size");
}

function testScreenRecorderParsesCaptureSourcesAndMonitorList() {
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
  assert.equal(ctx.killTimer.running, false, "launch must disarm a force-kill left by the previous recording");
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

function recorderLifecycleContext() {
  const notices = [];
  const errors = [];
  const ctx = {
    isPending: true,
    isRecording: false,
    hasActiveRecording: false,
    outputPath: "/tmp/out.mp4",
    pendingTimer: { running: true },
    monitorTimer: { running: false },
    ToastService: {
      showNotice(...args) { notices.push(args); },
      showError(...args) { errors.push(args); },
    },
    I18n: { tr(key) { return `tr:${key}`; } },
  };
  ctx.root = ctx;
  ctx.notices = notices;
  ctx.errors = errors;
  return ctx;
}

function testRecorderProcessExitTransitions() {
  const finishRecorderProcess = qmlFunction("finishRecorderProcess", "exitCode", "stdout", "stderr");
  const pendingFailure = recorderLifecycleContext();
  finishRecorderProcess(pendingFailure, 1, "", "device failed");
  assert.equal(pendingFailure.isPending, false);
  assert.equal(pendingFailure.pendingTimer.running, false);
  assert.deepEqual(pendingFailure.errors, [["tr:toast.recording.failed-start", "device failed"]]);
  assert.deepEqual(pendingFailure.notices, []);

  const pendingFallback = recorderLifecycleContext();
  finishRecorderProcess(pendingFallback, 1, "", "");
  assert.deepEqual(pendingFallback.errors, [["tr:toast.recording.failed-start", "tr:toast.recording.failed-gpu"]]);
  assert.deepEqual(pendingFallback.notices, []);

  const missing = recorderLifecycleContext();
  finishRecorderProcess(missing, 0, "GPU_SCREEN_RECORDER_NOT_INSTALLED", "");
  assert.deepEqual(missing.errors, [["tr:toast.recording.not-installed", "tr:toast.recording.not-installed-desc"]]);
  assert.deepEqual(missing.notices, []);

  const completed = recorderLifecycleContext();
  completed.isPending = false;
  completed.isRecording = true;
  completed.hasActiveRecording = true;
  completed.monitorTimer.running = true;
  finishRecorderProcess(completed, 0, "", "");
  assert.equal(completed.isRecording, false);
  assert.equal(completed.hasActiveRecording, false);
  assert.equal(completed.monitorTimer.running, false);
  assert.deepEqual(completed.notices, [["tr:toast.recording.saved", "/tmp/out.mp4", "settings-screen-recorder"]]);
  assert.deepEqual(completed.errors, []);

  const activeFailure = recorderLifecycleContext();
  activeFailure.isPending = false;
  activeFailure.isRecording = true;
  activeFailure.hasActiveRecording = true;
  activeFailure.monitorTimer.running = false;
  finishRecorderProcess(activeFailure, 2, "", "");
  assert.deepEqual(activeFailure.notices, []);
  assert.deepEqual(activeFailure.errors, [["tr:toast.recording.failed-start", "tr:toast.recording.failed-general"]]);
}

function testRecorderPendingAndMonitorTimerTransitions() {
  const handlePendingTimer = qmlFunction("handlePendingTimer", "processRunning");
  const handleMonitorTimer = qmlFunction("handleMonitorTimer", "processRunning");
  const started = recorderLifecycleContext();
  handlePendingTimer(started, true);
  assert.equal(started.isPending, false);
  assert.equal(started.isRecording, true);
  assert.equal(started.hasActiveRecording, true);
  assert.equal(started.monitorTimer.running, true);
  assert.deepEqual(started.notices, []);
  assert.deepEqual(started.errors, []);

  const cancelled = recorderLifecycleContext();
  handlePendingTimer(cancelled, false);
  assert.equal(cancelled.isPending, false);
  assert.equal(cancelled.isRecording, false);
  assert.deepEqual(cancelled.notices, []);
  assert.deepEqual(cancelled.errors, []);

  const ended = recorderLifecycleContext();
  ended.isPending = false;
  ended.isRecording = true;
  ended.hasActiveRecording = true;
  ended.monitorTimer.running = true;
  handleMonitorTimer(ended, false);
  assert.equal(ended.isRecording, true, "monitor must leave terminal state for authoritative process exit");
  assert.equal(ended.hasActiveRecording, true);
  assert.equal(ended.monitorTimer.running, false);

  const qml = readQml("Services/Media/ScreenRecorderService.qml");
  const recorder = findComponentBlock(qml, "Process", "id: recorderProcess");
  const pending = findComponentBlock(qml, "Timer", "id: pendingTimer");
  const monitor = findComponentBlock(qml, "Timer", "id: monitorTimer");
  assert.match(recorder, /onExited:[\s\S]*?root\.finishRecorderProcess\(exitCode/);
  assert.match(pending, /onTriggered:\s*root\.handlePendingTimer\(recorderProcess\.running\)/);
  assert.match(monitor, /onTriggered:\s*root\.handleMonitorTimer\(recorderProcess\.running\)/);
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

function screenRecorderWidgetFixture() {
  return {
    "Widgets/NIconButtonHot.qml": `import QtQuick

Item {
  property string icon
  property bool hot
  property string tooltipText
  signal clicked
}`,
    "Commons/I18n.qml": `pragma Singleton
import QtQuick

QtObject {
  function tr(key) {
    return key;
  }
}`,
    "Services/System/ProgramCheckerService.qml": `pragma Singleton
import QtQuick

QtObject {
  readonly property bool gpuScreenRecorderAvailable: true
}`,
    "Services/Media/ScreenRecorderService.qml": `pragma Singleton
import QtQuick

QtObject {
  property bool isRecording: true
  property int toggles: 0
  function toggleRecording() {
    toggles++;
    isRecording = !isRecording;
  }
}`,
    "Services/UI/PanelService.qml": `pragma Singleton
import QtQuick

QtObject {
  property int lookups: 0
  property bool available: true
  property QtObject panel: QtObject {
    property bool isOpen: true
    property int closeCount: 0
    function close() {
      isOpen = false;
      closeCount++;
    }
  }
  function getPanel(name, screen) {
    if (name !== "controlCenterPanel" || screen !== null)
      throw new Error("incorrect panel routing");
    lookups++;
    return available ? panel : null;
  }
}`,
    "ScreenRecorder.qml": readQml("Modules/Panels/ControlCenter/Widgets/ScreenRecorder.qml"),
    "shell.qml": `import QtQuick
import Quickshell
import qs.Services.Media
import qs.Services.UI

ShellRoot {
  ScreenRecorder {
    id: widget
  }
  function requireCondition(condition, message) {
    if (!condition) {
      console.error("SCREEN_RECORDER_WIDGET_FAIL: " + message);
      Qt.exit(1);
      return false;
    }
    return true;
  }
  Timer {
    interval: 1
    running: true
    onTriggered: {
      widget.clicked();
      if (!requireCondition(!ScreenRecorderService.isRecording && ScreenRecorderService.toggles === 1, "stop must toggle recording off"))
        return;
      if (!requireCondition(!PanelService.panel.isOpen && PanelService.panel.closeCount === 1, "stop must close control-center panel"))
        return;
      if (!requireCondition(PanelService.lookups === 1, "stop must route to control-center panel"))
        return;
      PanelService.panel.isOpen = true;
      widget.clicked();
      if (!requireCondition(ScreenRecorderService.isRecording && ScreenRecorderService.toggles === 2, "start must toggle recording on"))
        return;
      if (!requireCondition(PanelService.panel.isOpen && PanelService.panel.closeCount === 1 && PanelService.lookups === 1, "start must not close or look up a panel"))
        return;
      PanelService.available = false;
      widget.clicked();
      if (!requireCondition(!ScreenRecorderService.isRecording && ScreenRecorderService.toggles === 3 && PanelService.lookups === 2, "stop without panel must finish"))
        return;
      if (!requireCondition(PanelService.panel.isOpen && PanelService.panel.closeCount === 1, "missing panel must not close another panel"))
        return;
      console.log("SCREEN_RECORDER_WIDGET_PASS");
      Qt.quit();
    }
  }
}`,
  };
}

function isolatedWidgetEnvironment(directory) {
  const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    !/^(XDG_|WAYLAND_|QT_|QML_|NOCTALIA_)/.test(key) &&
    !["DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME"].includes(key)));
  for (const [variable, name] of Object.entries({
    HOME: "home", XDG_CONFIG_HOME: "config", XDG_CACHE_HOME: "cache",
    XDG_DATA_HOME: "data", XDG_STATE_HOME: "state", XDG_RUNTIME_DIR: "runtime",
  })) {
    const location = path.join(directory, name);
    fs.mkdirSync(location, { mode: 0o700 });
    environment[variable] = location;
  }
  return { ...environment, QT_QPA_PLATFORM: "offscreen", QT_QUICK_BACKEND: "software" };
}

function testControlCenterScreenRecorderClickClosesOnlyOnStop() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "noctalia-recorder-widget-"));
  const shell = path.join(directory, "shell.qml");
  let environment;
  try {
    environment = isolatedWidgetEnvironment(directory);
    for (const [relativePath, contents] of Object.entries(screenRecorderWidgetFixture())) {
      const destination = path.join(directory, relativePath);
      fs.mkdirSync(path.dirname(destination), { recursive: true, mode: 0o700 });
      fs.writeFileSync(destination, contents);
    }
    const result = spawnSync("timeout", ["--kill-after=2s", "10s", "quickshell", "--no-color", "-p", shell], {
      env: environment, encoding: "utf8", timeout: 15000,
    });
    const output = (result.stdout || "") + (result.stderr || "");
    assert.ifError(result.error);
    assert.equal(result.status, 0, output);
    assert.match(output, /SCREEN_RECORDER_WIDGET_PASS/, output);
    assert.doesNotMatch(output, / WARN | ERROR /, output);
  } finally {
    try {
      if (environment) {
        spawnSync("quickshell", ["kill", "--any-display", "-p", shell], { env: environment, timeout: 5000 });
        const registry = spawnSync("quickshell", ["list", "--all"], { env: environment, encoding: "utf8", timeout: 5000 });
        assert.ifError(registry.error);
        assert.equal(registry.status, 0, registry.stderr);
        assert.ok(!registry.stdout.includes(shell), "experimental widget shell must not remain registered");
      }
    } finally {
      fs.rmSync(directory, { recursive: true, force: true });
    }
  }
}

const tests = [
  testControlCenterScreenRecorderClickClosesOnlyOnStop,
  testScreenRecorderRefreshCaptureSourcesStartsBothQueries,
  testScreenRecorderDiscoveryPublishesLatestCompleteSnapshot,
  testScreenRecorderParsesCaptureSourcesAndMonitorList,
  testScreenRecorderToggleDelegatesByState,
  testScreenRecorderStartRecordingGuardsAndPortalPath,
  testScreenRecorderStartRecordingDirectLaunchPath,
  testScreenRecorderLaunchRecorderBuildsCommandAndStartsPendingTimer,
  testScreenRecorderLaunchRecorderBuildsAudioSourceVariants,
  testScreenRecorderLaunchRecorderHandlesDirectoryAndFocusSizeVariants,
  testRecorderProcessExitTransitions,
  testRecorderPendingAndMonitorTimerTransitions,
  testScreenRecorderStopRecordingGuardsAndStopsState,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
