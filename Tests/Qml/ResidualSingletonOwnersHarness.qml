import QtQuick
import Quickshell
import qs.Commons
import qs.Services.System

ShellRoot {
  id: harness

  property string mode: Quickshell.env("OWNER_CASE")
  property int phase: 0
  property int loads: 0
  property int saves: 0
  property double previousClock: 0
  property int previousVersion: 0
  property double saveRequestedAt: 0
  property bool clockAdvanced: false

  function check(condition, message) {
    if (!condition) {
      console.error("OWNER_FAIL", message)
      Qt.exit(1)
      throw new Error(message)
    }
  }

  Connections {
    target: Settings
    function onSettingsLoaded() {
      harness.loads++
    }
    function onSettingsSaved() {
      harness.saves++
    }
  }

  Timer {
    interval: 20
    repeat: true
    running: true
    onTriggered: {
      if (harness.phase === 0 && Settings.ready && Icons.fontFamily !== "") {
        harness.check(harness.loads === 1 && Settings.isLoaded, "singleton bootstrap readiness")
        harness.check(Settings.shouldOpenSetupWizard === (harness.mode === "create"), "first-run initialization")
        harness.check(Icons.get("check") === Icons.icons["check"], "icon lookup")
        const date = new Date(2026, 9, 11, 12, 34, 56, 250)
        harness.check(Time.nextUpdateInterval(date) === 3760, "minute boundary")
        Time.beginSecondUpdates()
        harness.check(Time.secondUpdateRefs === 1 && Time.nextUpdateInterval(date) === 760, "second boundary")
        Time.endSecondUpdates()
        Time.endSecondUpdates()
        harness.check(Time.secondUpdateRefs === 0, "second refcount floor")
        harness.check(Time.getFormattedTimestamp(date) === "20261011-123456", "timestamp format")
        Time.timerStopwatchMode = true
        Time.timerStart()
        harness.check(Time.timerRunning && Time.secondUpdatesRequired, "stopwatch start")
        harness.previousClock = Time.now.getTime()
        harness.previousVersion = Icons.fontVersion
        harness.phase = 1
        Quickshell.reloadCompleted()
        if (harness.mode === "create") {
          harness.saveRequestedAt = Date.now()
          Settings.data.audio.volumeStep = 17
          Settings.data.ui.fontDefault = "Owner Fixture Sans"
        } else {
          harness.check(Settings.data.audio.volumeStep === 17 && Settings.data.ui.fontDefault === "Owner Fixture Sans", "fresh process hydration")
        }
      }

      if (harness.phase === 1) {
        if (Time.now.getTime() > harness.previousClock) {
          harness.clockAdvanced = true
        }
        if (harness.mode === "create" && harness.saves > 0) {
          harness.check(Date.now() - harness.saveRequestedAt >= 450, "adapter update bypassed deferred save")
        }
        const persistenceComplete = harness.mode === "reload" || (harness.saves > 0 && !Settings.saveInProgress)
        const fontReady = Icons.currentFontLoader.status === FontLoader.Ready && Icons.fontVersion === harness.previousVersion + 1
        if (harness.clockAdvanced && fontReady && persistenceComplete) {
          harness.check(Icons.fontVersion === harness.previousVersion + 1, "reload callback owner")
          Time.timerPause()
          harness.check(!Time.timerRunning && !Time.secondUpdatesRequired && SoundService.stops === 1, "pause semantics")
          Time.timerReset()
          harness.check(Time.timerElapsedSeconds === 0 && Time.timerPausedAt === 0 && SoundService.stops === 2, "reset semantics")
          console.log("OWNER_PASS", harness.mode, harness.loads, harness.saves)
          Qt.quit()
        }
      }
    }
  }

  Timer {
    interval: 8000
    running: true
    onTriggered: {
      console.error("OWNER_FAIL timeout", harness.phase, Settings.bootstrapState, harness.clockAdvanced, Icons.fontVersion, harness.saves)
      Qt.exit(1)
    }
  }
}
