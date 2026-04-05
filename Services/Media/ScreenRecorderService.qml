pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.System
import qs.Services.UI

Singleton {
  id: root

  readonly property var settings: Settings.data.screenRecorder
  property bool isRecording: false
  property bool isPending: false
  // True only if the recorder actually started capturing at least once
  property bool hasActiveRecording: false
  property string outputPath: ""
  property bool isAvailable: ProgramCheckerService.gpuScreenRecorderAvailable

  // Available capture sources (populated from gpu-screen-recorder --list-capture-options)
  property var captureSources: []
  // Resolution of first detected monitor (e.g. "1920x1200"), used for -s flag with -w focused
  property string primaryMonitorResolution: ""

  // Update availability when ProgramCheckerService completes its checks
  Connections {
    target: ProgramCheckerService
    function onChecksCompleted() {
      if (ProgramCheckerService.gpuScreenRecorderAvailable)
        refreshCaptureSources();
    }
  }

  // Also query on startup in case checksCompleted already fired
  Component.onCompleted: {
    if (isAvailable)
      refreshCaptureSources();
  }

  function refreshCaptureSources() {
    captureSourcesProcess.command = ["gpu-screen-recorder", "--list-capture-options"];
    captureSourcesProcess.running = true;
    monitorListProcess.command = ["gpu-screen-recorder", "--list-monitors"];
    monitorListProcess.running = true;
  }

  // Query gpu-screen-recorder for available capture sources
  Process {
    id: captureSourcesProcess
    running: false
    stdout: StdioCollector {
      onStreamFinished: {
        var sources = [];
        var lines = this.text.trim().split("\n");
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i].trim();
          if (!line) continue;
          // Lines like "eDP-1|1920x1200" or "region" or "/dev/video0|..."
          var parts = line.split("|");
          var key = parts[0];
          // Skip v4l2 devices
          if (key.startsWith("/dev/")) continue;
          if (key === "region") {
            sources.push({ "key": "region", "name": "Select region", "label": "Select region" });
          } else {
            // Monitor: key is name, parts[1] is resolution
            var displayName = key;
            if (parts.length > 1) displayName += " (" + parts[1] + ")";
            sources.push({ "key": key, "name": displayName, "label": displayName, "resolution": parts.length > 1 ? parts[1] : "" });
          }
        }
        sources.push({ "key": "portal", "name": "Portal (window picker)", "label": "Portal (window picker)" });
        root.captureSources = sources;
      }
    }
    stderr: StdioCollector {}
  }

  // Query --list-monitors for primary monitor resolution (needed for -w focused)
  Process {
    id: monitorListProcess
    running: false
    stdout: StdioCollector {
      onStreamFinished: {
        var lines = this.text.trim().split("\n");
        var sources = root.captureSources.slice();
        // Insert monitors before the last entry (portal)
        var insertIdx = sources.length > 0 ? sources.length - 1 : 0;
        for (var i = 0; i < lines.length; i++) {
          var parts = lines[i].trim().split("|");
          if (parts.length > 1 && !parts[0].startsWith("/dev/")) {
            var key = parts[0];
            var res = parts[1];
            // Skip if already added by --list-capture-options
            var exists = false;
            for (var j = 0; j < sources.length; j++) {
              if (sources[j].key === key) { exists = true; break; }
            }
            if (!exists) {
              var displayName = key + " (" + res + ")";
              sources.splice(insertIdx, 0, { "key": key, "name": displayName, "label": displayName, "resolution": res });
              insertIdx++;
            }
            if (!root.primaryMonitorResolution)
              root.primaryMonitorResolution = res;
          }
        }
        root.captureSources = sources;
      }
    }
    stderr: StdioCollector {}
  }

  // Start or Stop recording
  function toggleRecording() {
    (isRecording || isPending) ? stopRecording() : startRecording();
  }

  // Start screen recording using Quickshell.execDetached
  function startRecording() {
    if (!isAvailable) {
      return;
    }
    if (isRecording || isPending) {
      return;
    }
    isPending = true;
    hasActiveRecording = false;

    // Close any opened panel
    if ((PanelService.openedPanel !== null) && !PanelService.openedPanel.isClosing) {
      PanelService.openedPanel.close();
    }

    // Portal check only needed when using portal capture mode
    if (settings.videoSource === "portal") {
      portalCheckProcess.exec({
                                "command": ["sh", "-c"
                                  , "pidof xdg-desktop-portal >/dev/null 2>&1 && (pidof xdg-desktop-portal-wlr >/dev/null 2>&1 || pidof xdg-desktop-portal-hyprland >/dev/null 2>&1 || pidof xdg-desktop-portal-gnome >/dev/null 2>&1 || pidof xdg-desktop-portal-kde >/dev/null 2>&1 || pidof xdg-desktop-portal-gtk >/dev/null 2>&1)"]
                              });
    } else {
      // Direct monitor/region capture - skip portal check
      launchRecorder();
    }
  }

  function launchRecorder() {
    var filename = Time.getFormattedTimestamp() + ".mp4";
    var videoDir = Settings.preprocessPath(settings.directory);
    if (videoDir && !videoDir.endsWith("/")) {
      videoDir += "/";
    }
    outputPath = videoDir + filename;

    var audioArg = (settings.audioSource === "both") ? `-a "default_output|default_input"` : `-a ${settings.audioSource}`;

    // -s WxH is required when using -w focused
    var sizeFlag = "";
    if (settings.videoSource === "focused" && primaryMonitorResolution)
      sizeFlag = `-s ${primaryMonitorResolution}`;

    var flags = `-w ${settings.videoSource} ${sizeFlag} -f ${settings.frameRate} -ac ${settings.audioCodec} -k ${settings.videoCodec} ${audioArg} -q ${settings.quality} -cursor ${settings.showCursor ? "yes" : "no"} -cr ${settings.colorRange} -o "${outputPath}"`;
    var command = `
    _gpuscreenrecorder_flatpak_installed() {
    flatpak list --app | grep -q "com.dec05eba.gpu_screen_recorder"
    }
    if command -v gpu-screen-recorder >/dev/null 2>&1; then
    gpu-screen-recorder ${flags}
    elif command -v flatpak >/dev/null 2>&1 && _gpuscreenrecorder_flatpak_installed; then
    flatpak run --command=gpu-screen-recorder --file-forwarding com.dec05eba.gpu_screen_recorder ${flags}
    else
    echo "GPU_SCREEN_RECORDER_NOT_INSTALLED"
    fi`;

    // Use Process instead of execDetached so we can monitor it and read stderr
    recorderProcess.exec({
                           "command": ["sh", "-c", command]
                         });

    // Start monitoring - if process ends quickly, it was likely cancelled
    pendingTimer.running = true;
  }

  // Stop recording using Quickshell.execDetached
  function stopRecording() {
    if (!isRecording && !isPending) {
      return;
    }

    ToastService.showNotice(I18n.tr("toast.recording.stopping"), outputPath, "settings-screen-recorder");

    Quickshell.execDetached(["sh", "-c", "pkill -SIGINT -f 'gpu-screen-recorder' || pkill -SIGINT -f 'com.dec05eba.gpu_screen_recorder'"]);

    isRecording = false;
    isPending = false;
    pendingTimer.running = false;
    monitorTimer.running = false;
    hasActiveRecording = false;

    // Just in case, force kill after 3 seconds
    killTimer.running = true;
  }

  // Process to run and monitor gpu-screen-recorder
  Process {
    id: recorderProcess
    stdout: StdioCollector {}
    stderr: StdioCollector {}
    onExited: function (exitCode, exitStatus) {
      if (isPending) {
        // Process ended while we were pending - likely cancelled or error
        isPending = false;
        pendingTimer.running = false;

        // Check if gpu-screen-recorder is not installed
        const stdout = String(recorderProcess.stdout.text || "").trim();
        if (stdout === "GPU_SCREEN_RECORDER_NOT_INSTALLED") {
          ToastService.showError(I18n.tr("toast.recording.not-installed"), I18n.tr("toast.recording.not-installed-desc"));
          return;
        }

        // If it failed to start, show a clear error toast with stderr
        if (exitCode !== 0) {
          const err = String(recorderProcess.stderr.text || "").trim();
          if (err.length > 0)
            ToastService.showError(I18n.tr("toast.recording.failed-start"), err);
          else
            ToastService.showError(I18n.tr("toast.recording.failed-start"), I18n.tr("toast.recording.failed-gpu"));
        }
      } else if (isRecording) {
        // Process ended normally while recording
        isRecording = false;
        monitorTimer.running = false;
        // Consider successful save if exitCode == 0
        if (exitCode === 0) {
          ToastService.showNotice(I18n.tr("toast.recording.saved"), outputPath, "settings-screen-recorder");
        } else {
          const err2 = String(recorderProcess.stderr.text || "").trim();
          if (err2.length > 0)
            ToastService.showError(I18n.tr("toast.recording.failed-start"), err2);
          else
            ToastService.showError(I18n.tr("toast.recording.failed-start"), I18n.tr("toast.recording.failed-general"));
        }
      }
    }
  }

  // Pre-flight check for xdg-desktop-portal
  Process {
    id: portalCheckProcess
    onExited: function (exitCode, exitStatus) {
      if (exitCode === 0) {
        // Portals available, proceed to launch
        launchRecorder();
      } else {
        isPending = false;
        hasActiveRecording = false;
        ToastService.showError(I18n.tr("toast.recording.no-portals"), I18n.tr("toast.recording.no-portals-desc"));
      }
    }
  }

  Timer {
    id: pendingTimer
    interval: 2000 // Wait 2 seconds to see if process stays alive
    running: false
    repeat: false
    onTriggered: {
      if (isPending && recorderProcess.running) {
        // Process is still running after 2 seconds - assume recording started successfully
        isPending = false;
        isRecording = true;
        hasActiveRecording = true;
        monitorTimer.running = true;
        // Don't show a toast when recording starts to avoid having the toast in every video.
      } else if (isPending) {
        // Process not running anymore - was cancelled or failed
        isPending = false;
      }
    }
  }

  // Monitor timer to periodically check if we're still recording
  Timer {
    id: monitorTimer
    interval: 2000
    running: false
    repeat: true
    onTriggered: {
      if (!recorderProcess.running && isRecording) {
        isRecording = false;
        running = false;
      }
    }
  }

  Timer {
    id: killTimer
    interval: 3000
    running: false
    repeat: false
    onTriggered: {
      Quickshell.execDetached(["sh", "-c", "pkill -9 -f 'gpu-screen-recorder' 2>/dev/null || pkill -9 -f 'com.dec05eba.gpu_screen_recorder' 2>/dev/null || true"]);
    }
  }
}
