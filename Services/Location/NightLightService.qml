pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.UI

Singleton {
  id: root

  // Night Light properties - directly bound to settings
  readonly property var params: Settings.data.nightLight
  property var lastCommand: []
  property bool cleanupPending: false

  function apply() {
    if (!params.enabled) {
      runner.running = false;
      return;
    }

    // If using LocationService, wait for it to be ready
    if (!params.forced && params.autoSchedule && !LocationService.coordinatesReady) {
      return;
    }

    const command = buildCommand();
    const changed = JSON.stringify(command) !== JSON.stringify(lastCommand);
    if (changed) {
      lastCommand = command;
      runner.running = false;
    }

    if (cleanupPending || (!changed && runner.running)) {
      return;
    }

    cleanupPending = true;
    staleCleanup.command = buildStaleWlsunsetCleanupCommand();
    staleCleanup.running = true;
  }

  function buildStaleWlsunsetCleanupCommand() {
    const script = `
pids=$(pgrep -u "$(id -u)" -x wlsunset)
result=$?
if [ "$result" -gt 1 ]; then echo 'failed to enumerate wlsunset' >&2; exit "$result"; fi
for pid in $pids; do
  if ! kill "$pid" 2>/dev/null && kill -0 "$pid" 2>/dev/null; then echo "failed to stop wlsunset $pid" >&2; exit 1; fi
  attempts=0
  while kill -0 "$pid" 2>/dev/null; do
    state=$(ps -o stat= -p "$pid" 2>/dev/null)
    case "$state" in Z*|*' Z'*) break ;; esac
    if [ "$attempts" -ge 40 ]; then echo "timed out waiting for wlsunset $pid" >&2; exit 1; fi
    sleep 0.05
    attempts=$((attempts + 1))
  done
done`;

    return ["sh", "-c", script];
  }

  function stopNightLightRunner() {
    runner.running = false;
  }

  function buildCommand() {
    var cmd = ["wlsunset"];
    if (params.forced) {
      // Force immediate full night temperature regardless of time
      // Keep distinct day/night temps but set times so we're effectively always in "night"
      cmd.push("-t", `${params.nightTemp}`, "-T", `${params.dayTemp}`);
      // Night spans from sunset (00:00) to sunrise (23:59) covering almost the full day
      cmd.push("-S", "23:59"); // sunrise very late
      cmd.push("-s", "00:00"); // sunset at midnight
      // Near-instant transition
      cmd.push("-d", 1);
    } else {
      cmd.push("-t", `${params.nightTemp}`, "-T", `${params.dayTemp}`);
      if (params.autoSchedule) {
        cmd.push("-l", `${LocationService.stableLatitude}`, "-L", `${LocationService.stableLongitude}`);
      } else {
        cmd.push("-S", params.manualSunrise);
        cmd.push("-s", params.manualSunset);
      }
      cmd.push("-d", 60 * 15); // 15min progressive fade at sunset/sunrise
    }
    return cmd;
  }

  // Observe setting changes and location readiness
  Connections {
    target: Settings.data.nightLight
    function onEnabledChanged() {
      apply();
      // Toast: night light toggled
      const enabled = !!Settings.data.nightLight.enabled;
      ToastService.showNotice(I18n.tr("settings.display.night-light.section.label"), enabled ? I18n.tr("toast.night-light.enabled") : I18n.tr("toast.night-light.disabled"), enabled ? "nightlight-on" : "nightlight-off");
    }
    function onForcedChanged() {
      apply();
      if (Settings.data.nightLight.enabled) {
        ToastService.showNotice(I18n.tr("settings.display.night-light.section.label"), Settings.data.nightLight.forced ? I18n.tr("toast.night-light.forced") : I18n.tr("toast.night-light.normal"), Settings.data.nightLight.forced ? "nightlight-forced" : "nightlight-on");
      }
    }
    function onNightTempChanged() {
      apply();
    }
    function onDayTempChanged() {
      apply();
    }
  }

  Connections {
    target: LocationService
    function onCoordinatesReadyChanged() {
      if (LocationService.coordinatesReady) {
        apply();
      }
    }
  }

  Component.onDestruction: stopNightLightRunner()

  Process {
    id: staleCleanup
    running: false
    onStarted: {
      Logger.i("NightLight", "Stale wlsunset cleanup started");
    }
    stderr: StdioCollector {
      onStreamFinished: {
        if (text.trim())
          Logger.e("NightLight", "Stale wlsunset cleanup: " + text.trim());
      }
    }
    onExited: function (code, status) {
      root.cleanupPending = false;
      if (code !== 0 || status !== 0) {
        Logger.e("NightLight", "Stale wlsunset cleanup failed:", code, status);
        return;
      }
      Logger.i("NightLight", "Stale wlsunset cleanup exited:", code, status);
      if (root.params.enabled) {
        runner.command = root.lastCommand;
        runner.running = true;
      }
    }
  }

  // Foreground process runner
  Process {
    id: runner
    running: false
    onStarted: {
      Logger.i("NightLight", "Wlsunset started:", runner.command);
    }
    stderr: SplitParser {
      onRead: data => {
        if (data.includes("failed") || data.includes("error")) {
          Logger.e("NightLight", "Wlsunset stderr: " + data.trim());
        }
      }
    }
    onExited: function (code, status) {
      Logger.i("NightLight", "Wlsunset exited:", code, status);
    }
  }
}
