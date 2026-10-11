import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.Theming
import qs.Services.UI

Scope {
  id: harness
  property string mode: "@MODE@"
  property string rose: "@ROSE@"
  property string zebra: "@ZEBRA@"
  property int phase: 0
  property int elapsed: 0
  property bool sawPendingExit: false
  property bool mutationDone: false
  property var service: ColorSchemeService

  function equal(actual, expected, label) {
    if (JSON.stringify(actual) !== JSON.stringify(expected))
      throw new Error(label + ": " + JSON.stringify(actual) + " != " + JSON.stringify(expected));
  }

  function saved(color) {
    disk.reload();
    const palette = JSON.parse(disk.text());
    return Object.keys(palette).length === 16 && Object.values(palette).every(value => value === color);
  }

  function pass() {
    console.log("COLOR_SCHEME_RUNTIME_PASS " + mode);
    Qt.quit();
  }

  Component.onCompleted: {
    service.schemesDirectory = "@BUNDLED@";
    service.init();
    equal(service.scanning, true, "discovery begins pending");
    equal(service.schemes, [], "discovery resets list");
  }

  FileView {
    id: disk
    path: Settings.configDir + "colors.json"
    blockLoading: true
    blockAllReads: true
    printErrors: false
  }

  Process {
    command: ["/usr/bin/python3", "@MUTATOR@"]
    running: harness.phase === 3 && !harness.mutationDone
    onExited: function (exitCode) {
      harness.equal(exitCode, 0, "fixture mutation exit");
      harness.mutationDone = true;
    }
  }

  Timer {
    interval: 20
    running: true
    repeat: true
    onTriggered: {
      try {
        harness.elapsed += 20;
        if (harness.elapsed > 10000)
          throw new Error("phase timeout " + harness.phase + ": " + JSON.stringify(Logger.messages));
        if (harness.phase === 0) {
          if (harness.mode !== "normal" && harness.elapsed >= 300 && harness.elapsed < 500) {
            harness.equal(harness.service.scanning, true, "stdout EOF must not finish discovery");
            harness.equal(harness.service.schemes, [], "stdout EOF must not publish files");
            harness.equal(Settings.data.colorSchemes.predefinedScheme, harness.rose, "stdout EOF must not normalize settings");
            harness.sawPendingExit = true;
          }
          if (harness.service.scanning)
            return;
          if (harness.mode !== "normal") {
            harness.equal(harness.sawPendingExit, true, "observed stdout/exit gap");
            if (harness.mode === "error") {
              harness.equal(harness.service.schemes, [], "nonzero exit discards stdout");
              harness.equal(Settings.data.colorSchemes.predefinedScheme, harness.rose, "error leaves selection unchanged");
              harness.equal(AppThemeService.generations, 0, "error never applies stdout scheme");
              harness.equal(harness.saved("#123456"), true, "error leaves disk palette unchanged");
              harness.equal(Logger.messages.filter(message => message.includes("Failed to find")).length, 1, "one discovery error");
              harness.pass();
              return;
            }
            harness.equal(harness.service.schemes, [harness.rose], "successful delayed exit publishes stdout");
          } else {
            harness.equal(harness.service.schemes, [harness.rose, harness.zebra], "sorted bundled/downloaded discovery");
          }
          harness.equal(Settings.data.colorSchemes.predefinedScheme, "Rose Pine", "stored path normalization");
          harness.phase = 1;
        }
        if (harness.phase === 1 && AppThemeService.generations === 1 && harness.saved("#123456")) {
          if (harness.mode === "early") {
            harness.pass();
            return;
          }
          Settings.data.colorSchemes.darkMode = false;
          harness.phase = 2;
        }
        if (harness.phase === 2 && AppThemeService.generations === 2 && harness.saved("#abcdef")) {
          harness.equal(ToastService.notices, 1, "dark mode watcher toast");
          harness.phase = 3;
        }
        if (harness.phase === 3 && harness.mutationDone) {
          // No production FileView watchChanges: refresh is explicitly requested.
          harness.equal(AppThemeService.generations, 2, "file mutation does not auto-apply");
          harness.service.loadColorSchemes();
          harness.equal(harness.service.scanning, true, "refresh pending");
          harness.equal(harness.service.schemes, [], "refresh resets discovery");
          harness.phase = 4;
        }
        if (harness.phase === 4 && !harness.service.scanning && AppThemeService.generations === 3) {
          harness.equal(harness.service.schemes.map(path => harness.service.getBasename(path)), ["Amber", "Rose Pine", "Zebra"], "refresh discovers added file");
          Settings.data.colorSchemes.darkMode = true;
          harness.phase = 5;
        }
        if (harness.phase === 5 && AppThemeService.generations === 4 && harness.saved("#654321")) {
          harness.equal(ToastService.notices, 2, "watcher reapplies refreshed dark variant");
          harness.service.setPredefinedScheme("Zebra");
          harness.phase = 6;
        }
        if (harness.phase === 6 && AppThemeService.generations === 5 && harness.saved("#789abc")) {
          harness.equal(Settings.data.colorSchemes.predefinedScheme, "Zebra", "switch persists fixture selection");
          harness.equal(ToastService.notices, 3, "switch notice");
          harness.service.setPredefinedScheme("Missing");
          harness.equal(Settings.data.colorSchemes.predefinedScheme, "Zebra", "missing selection preserved");
          harness.equal(ToastService.errors, 1, "missing selection error");
          harness.pass();
        }
      } catch (error) {
        console.error("COLOR_SCHEME_RUNTIME_FAIL " + error);
        Qt.exit(1);
      }
    }
  }
}
