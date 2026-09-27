import QtQuick
import Quickshell
import Quickshell.Io
import qs.Services.Media
import qs.Services.System

ShellRoot {
  id: testRoot
  property int exitCode: 0
  property int phase: 0

  function verify(condition, message) {
    if (!condition) {
      console.error("FAIL ScreenRecorderDiscovery:", message);
      exitCode = 1;
    }
  }

  function checkSources(expectedKey, expectedResolution) {
    const recorder = ScreenRecorderService;
    const monitors = recorder.captureSources.filter(source => source.resolution);
    verify(monitors.length === 1 && monitors[0].key === expectedKey && monitors[0].resolution === expectedResolution,
           "expected only " + expectedKey + " (" + expectedResolution + "), got " + JSON.stringify(recorder.captureSources));
    verify(recorder.primaryMonitorResolution === expectedResolution,
           "expected primary resolution " + expectedResolution + ", got " + recorder.primaryMonitorResolution);
    verify(recorder.settings.videoSource === "DP-4", "source selection was changed by discovery");
  }

  function advance() {
    if (phase === 0) {
      checkSources("DP-4", "2560x1440");
      if (exitCode !== 0) {
        Qt.exit(exitCode);
        return;
      }
      phase = 1;
      changeOutput.exec({ "command": ["sh", "-c", "printf 'new\\n' > \"$DISCOVERY_PHASE_FILE\""] });
    } else {
      checkSources("eDP-1", "1920x1200");
      if (exitCode === 0) console.log("PASS ScreenRecorderDiscovery");
      Qt.exit(exitCode);
    }
  }

  Connections {
    target: ScreenRecorderService
    function onCaptureSourcesChanged() {
      if (ScreenRecorderService.captureSources.length === 0) return;
      const expected = testRoot.phase === 0 ? "2560x1440" : "1920x1200";
      testRoot.verify(ScreenRecorderService.primaryMonitorResolution === expected,
                      "published sources before corresponding primary resolution");
    }
  }

  Connections {
    target: ScreenRecorderService
    function onDiscoveryInProgressChanged() {
      Qt.callLater(() => {
        if (!ScreenRecorderService.discoveryInProgress && ScreenRecorderService.captureSources.length > 0)
          testRoot.advance();
      });
    }
  }

  Process {
    id: changeOutput
    onExited: function(exitCode) {
      testRoot.verify(exitCode === 0, "failed to switch test output");
      if (exitCode === 0) Quickshell.screensChanged();
      else Qt.exit(testRoot.exitCode);
    }
  }

  Timer {
    interval: 8000
    running: true
    onTriggered: {
      testRoot.verify(false, "timed out waiting for a complete discovery snapshot");
      Qt.exit(testRoot.exitCode);
    }
  }

  Component.onCompleted: {
    ScreenRecorderService.settings.videoSource = "DP-4";
    ProgramCheckerService.gpuScreenRecorderAvailable = true;
    ProgramCheckerService.checksCompleted();
  }
}
