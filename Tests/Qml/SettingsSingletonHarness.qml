import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import "Helpers/QtObj2JS.js" as QtObj2JS

ShellRoot {
  id: harness

  property string mode: Quickshell.env("SETTINGS_SINGLETON_MODE")
  property int phase: 0
  property int loadCount: 0
  property int saveCount: 0

  function finish() {
    console.log("SETTINGS_SINGLETON_PASS", mode, loadCount, saveCount);
    Qt.quit();
  }

  function check(condition, message) {
    if (!condition) {
      throw new Error(message);
    }
  }

  Connections {
    target: Settings

    function onSettingsLoaded() {
      harness.loadCount += 1;
    }

    function onSettingsSaved() {
      harness.saveCount += 1;
    }
  }

  Timer {
    interval: 20
    running: true
    repeat: true
    onTriggered: {
      if (harness.mode === "malformed") {
        if (Settings.bootstrapState === Settings.Error) {
          harness.check(!Settings.isLoaded && !Settings.ready, "Malformed settings published readiness");
          harness.check(Settings.errorMessage.includes("Invalid settings JSON"), "Missing validation error");
          harness.check(harness.loadCount === 0 && harness.saveCount === 0, "Malformed settings emitted success");
          harness.finish();
        }
        return;
      }

      if (Settings.ready && harness.phase === 0) {
        harness.check(Settings.isLoaded && Settings.hasLoadedOnce, "Readiness missing loaded flags");
        harness.check(harness.loadCount === 1, "Expected one initial load");
        harness.check(Settings.shouldOpenSetupWizard === (harness.mode === "defaults"), "First-run flag mismatch");
        console.log("SETTINGS_INITIAL", JSON.stringify(QtObj2JS.qtObjectToPlainObject(Settings.data)));
        harness.phase = 1;
        if (harness.mode === "valid") {
          harness.check(Settings.data.ui.fontDefault === "Fixture Sans", "Validated font not hydrated");
          Settings.data.ui.fontDefault = "Saved Sans";
          Settings.saveImmediate();
          Settings.data.audio.volumeStep = 7;
          Settings.saveImmediate();
        } else {
          Settings.saveImmediate();
        }
      }

      if (harness.phase === 1 && Settings.ready && !Settings.saveInProgress && harness.saveCount > 0) {
        harness.check(Settings.persistedSettingsText === Settings.canonicalizeSettingsValue(QtObj2JS.qtObjectToPlainObject(Settings.data)), "Read-back differs from adapter");
        if (harness.mode === "defaults") {
          harness.finish();
        } else if (Settings.data.audio.volumeStep === 7 && harness.saveCount >= 2) {
          harness.phase = 2;
          console.log("SETTINGS_AWAIT_EXTERNAL");
        }
      }

      if (harness.phase === 2 && Settings.ready && Settings.data.ui.fontDefault === "External Sans") {
        harness.check(harness.loadCount === 2, "External valid change did not reload");
        harness.phase = 3;
        console.log("SETTINGS_AWAIT_MALFORMED");
      }

      if (harness.phase === 3 && Settings.bootstrapState === Settings.Error) {
        harness.check(!Settings.ready && !Settings.isLoaded, "Malformed watcher change kept readiness");
        harness.phase = 4;
        console.log("SETTINGS_AWAIT_REPAIR");
      }

      if (harness.phase === 5 && Settings.ready) {
        harness.check(harness.loadCount === 3, "Retry did not publish repaired settings");
        harness.check(Settings.data.ui.fontDefault === "Repaired Sans", "Retry hydrated wrong bytes");
        harness.finish();
      }
    }
  }

  FileView {
    path: Quickshell.env("SETTINGS_SINGLETON_REPAIR_MARKER")
    preload: false
    watchChanges: true
    onFileChanged: {
      if (harness.phase === 4) {
        harness.phase = 5;
        Settings.retryBootstrap();
      }
    }
  }

  Component.onCompleted: console.log("SETTINGS_HARNESS_STARTED", Settings.settingsFile)

  Timer {
    interval: 10000
    running: true
    onTriggered: {
      console.error("SETTINGS_SINGLETON_TIMEOUT", harness.phase, Settings.bootstrapState, Settings.errorMessage);
      Qt.quit();
    }
  }
}
