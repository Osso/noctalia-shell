#!/usr/bin/env python3
"""Exercise the unchanged production singleton with real offscreen Quickshell I/O.

Only Settings/Logger and backend script outputs are fixtures. FileView,
JsonAdapter, Timer, Process and StdioCollector remain production Qt objects.
Run directly; no desktop, real settings, or calendar provider is accessed.
"""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CACHED_EVENTS = [{"title": "Cached standup", "start": 1700000000}]
CACHED_CALENDARS = [{"name": "Cached work"}]
EVENTS = [{"title": "Fixture meeting", "start": 1800000000}]
CALENDARS = [{"name": "Fixture work"}]
SETTINGS = """pragma Singleton
import QtQuick
QtObject {
  property string cacheDir: CACHE_DIR
  property var data: ({location: {showCalendarEvents: ENABLED}})
}
"""
LOGGER = """pragma Singleton
import QtQuick
QtObject {
  property var messages: []
  function record(args) { messages = messages.concat([args.join(" ")]); }
  function i(...args) { record(args); }
  function d(...args) { record(args); }
  function w(...args) { record(args); }
}
"""
HARNESS = """import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.Location

Scope {
  id: harness
  property var service: CalendarService
  property int elapsed: 0
  property bool inspectedCache: false
  property bool inspectedLoading: false
  property bool finished: false
  property int finishedAt: 0
  property var initialEvents: INITIAL_EVENTS
  property var initialCalendars: INITIAL_CALENDARS
  property var finalEvents: FINAL_EVENTS
  property var finalCalendars: FINAL_CALENDARS
  property string terminalLog: TERMINAL_LOG
  property string expectedError: EXPECTED_ERROR
  property bool expectedAvailable: EXPECTED_AVAILABLE
  property bool enabled: ENABLED
  property bool savesCache: SAVES_CACHE

  function normalized(value) {
    if (Array.isArray(value))
      return value.map(normalized);
    if (value && typeof value === "object") {
      const result = {};
      Object.keys(value).sort().forEach(key => { result[key] = normalized(value[key]); });
      return result;
    }
    return value;
  }

  function equal(actual, expected, label) {
    const actualJson = JSON.parse(JSON.stringify(actual));
    const expectedJson = JSON.parse(JSON.stringify(expected));
    if (JSON.stringify(normalized(actualJson)) !== JSON.stringify(normalized(expectedJson)))
      throw new Error(label + ": " + JSON.stringify(actual) + " != " + JSON.stringify(expected));
  }

  FileView {
    id: diskCache
    path: Settings.cacheDir + "calendar.json"
    blockLoading: true
    blockAllReads: true
    printErrors: false
  }

  Timer {
    interval: 20
    running: true
    repeat: true
    onTriggered: {
      try {
        harness.elapsed += 20;
        if (!harness.inspectedCache && harness.elapsed >= 100) {
          harness.equal(harness.service.events, harness.initialEvents, "FileView loaded events");
          harness.equal(harness.service.calendars, harness.initialCalendars, "FileView loaded calendars");
          harness.inspectedCache = true;
          if (!harness.enabled) {
            harness.equal(harness.service.available, false, "disabled availability");
            harness.service.checkAvailability();
            harness.service.beginPolling();
            harness.service.beginPolling();
            harness.equal(harness.service.pollingRefs, 2, "polling acquisition");
            harness.equal(harness.service.isPollingActive(), true, "polling active");
            harness.equal(harness.service.events, [], "disabled load clears events");
            harness.equal(harness.service.loading, false, "disabled load completes");
            harness.service.endPolling();
            harness.service.endPolling();
            harness.service.endPolling();
            harness.equal(harness.service.pollingRefs, 0, "polling clamp");
            harness.equal(harness.service.isPollingActive(), false, "polling stopped");
            harness.service.loadFromCache();
          }
        }
        if (harness.service.loading && !harness.inspectedLoading) {
          harness.equal(harness.service.lastError, "", "load clears stale error");
          harness.service.loadEvents(2, 1);
          harness.inspectedLoading = true;
        }
        const terminal = !harness.enabled || Logger.messages.some(message => message.indexOf(harness.terminalLog) !== -1);
        if (harness.inspectedCache && terminal && !harness.finished) {
          harness.equal(harness.service.available, harness.expectedAvailable, "availability callback");
          harness.equal(harness.service.events, harness.finalEvents, "events callback");
          harness.equal(harness.service.calendars, harness.finalCalendars, "calendars callback");
          harness.equal(harness.service.loading, false, "load finished");
          harness.equal(harness.service.lastError, harness.expectedError, "callback error");
          if (harness.savesCache) {
            diskCache.reload();
            harness.equal(JSON.parse(diskCache.text()).cachedEvents, harness.initialEvents, "debounce leaves disk unchanged initially");
          }
          harness.finishedAt = harness.elapsed;
          harness.finished = true;
        }
        // Measure debounce waiting from callback completion, not engine startup.
        if (harness.finished && harness.elapsed - harness.finishedAt >= 1300) {
          if (harness.savesCache) {
            diskCache.reload();
            const saved = JSON.parse(diskCache.text());
            harness.equal(saved.cachedEvents, harness.finalEvents, "debounced event write");
            harness.equal(saved.cachedCalendars, harness.finalCalendars, "debounced calendar write");
            if (!saved.lastUpdate || isNaN(Date.parse(saved.lastUpdate)))
              throw new Error("missing saved timestamp");
            harness.service.events = [];
            harness.service.calendars = [];
            harness.service.loadFromCache();
            harness.equal(harness.service.events, harness.finalEvents, "cache reload events");
            harness.equal(harness.service.calendars, harness.finalCalendars, "cache reload calendars");
          }
          console.log("CALENDAR_RUNTIME_PASS");
          Qt.quit();
        }
        if (harness.elapsed > 5000)
          throw new Error("callback timeout: " + JSON.stringify(Logger.messages));
      } catch (error) {
        console.error("CALENDAR_RUNTIME_FAIL: " + error);
        Qt.exit(1);
      }
    }
  }
}
"""


def isolated_environment(directory):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_", "QS_"))
        and key not in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME")
    }
    for variable, name in {
        "HOME": "home",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "XDG_DATA_HOME": "data",
        "XDG_STATE_HOME": "state",
        "XDG_RUNTIME_DIR": "runtime",
    }.items():
        path = directory / name
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    return environment


def write_backend(directory, name, stdout, stderr="", arguments=False):
    script = "import json, os, pathlib, sys, time\ntime.sleep(0.25)\n"
    script += f"path = pathlib.Path({str(directory / 'calls.jsonl')!r})\n"
    script += f"with path.open('a') as file: file.write(json.dumps([{name!r}, sys.argv[1:]]) + '\\n')\n"
    if arguments:
        script += "assert len(sys.argv) == 3 and int(sys.argv[1]) < int(sys.argv[2])\n"
    script += f"print({stdout!r}, flush=True)\n"
    if stderr:
        # Close stdout first so the two real stream callbacks have a fixed order.
        script += "os.close(1)\ntime.sleep(0.1)\n"
    script += f"print({stderr!r}, file=sys.stderr)\n"
    (directory / "Bin" / name).write_text(script)


def run_harness(directory, environment, values):
    source = HARNESS
    for key, value in values.items():
        source = source.replace(key, json.dumps(value))
    (directory / "shell.qml").write_text(source)
    process = subprocess.Popen(
        ["/usr/bin/quickshell", "--no-color", "-p", str(directory / "shell.qml")],
        cwd=directory,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=12)
        output = stdout + stderr
        if (
            process.returncode
            or "CALENDAR_RUNTIME_PASS" not in output
            or " WARN " in output
            or "CALENDAR_RUNTIME_FAIL" in output
        ):
            raise AssertionError(f"exit {process.returncode}\n{output}")
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Successful runs have already exited with their backend children.
        process.wait()


def run_case(
    name,
    *,
    enabled=True,
    missing=False,
    availability="available",
    availability_error="",
    calendars=None,
    calendars_error="",
    events=None,
    events_error="",
    terminal="Loaded 1 event(s)",
    error="",
    expected_available=True,
):
    calendars = json.dumps(CALENDARS) if calendars is None else calendars
    events = json.dumps(EVENTS) if events is None else events
    receives_calendars = (
        enabled
        and availability == "available"
        and not availability_error
        and not calendars_error
        and calendars.startswith("[")
    )
    receives_events = receives_calendars and events.startswith("[") and not events_error
    initial_events = [] if missing else CACHED_EVENTS
    initial_calendars = [] if missing else CACHED_CALENDARS
    final_events = EVENTS if receives_events else initial_events
    final_calendars = CALENDARS if receives_calendars else initial_calendars
    with tempfile.TemporaryDirectory(prefix="noctalia-calendar-runtime-") as temporary:
        directory = Path(temporary)
        environment = isolated_environment(directory)
        for relative in ("Commons", "Services/Location", "Bin"):
            (directory / relative).mkdir(mode=0o700, parents=True)
        shutil.copyfile(
            ROOT / "Services/Location/CalendarService.qml",
            directory / "Services/Location/CalendarService.qml",
        )
        settings = SETTINGS.replace(
            "CACHE_DIR", json.dumps(str(directory / "cache") + "/")
        )
        (directory / "Commons/Settings.qml").write_text(
            settings.replace("ENABLED", json.dumps(enabled))
        )
        (directory / "Commons/Logger.qml").write_text(LOGGER)
        cache = directory / "cache/calendar.json"
        if not missing:
            cache.write_text(
                json.dumps(
                    {
                        "cachedEvents": initial_events,
                        "cachedCalendars": initial_calendars,
                        "lastUpdate": "2026-10-01T12:00:00Z",
                    }
                )
            )
        write_backend(directory, "check-calendar.py", availability, availability_error)
        write_backend(directory, "list-calendars.py", calendars, calendars_error)
        write_backend(
            directory, "calendar-events.py", events, events_error, arguments=True
        )
        values = {
            "INITIAL_EVENTS": initial_events,
            "INITIAL_CALENDARS": initial_calendars,
            "FINAL_EVENTS": final_events,
            "FINAL_CALENDARS": final_calendars,
            "TERMINAL_LOG": terminal,
            "EXPECTED_ERROR": error,
            "EXPECTED_AVAILABLE": expected_available,
            "ENABLED": enabled,
            "SAVES_CACHE": receives_events and not missing,
        }
        try:
            run_harness(directory, environment, values)
        except AssertionError as failure:
            disk = cache.read_text() if cache.exists() else "<missing>"
            raise AssertionError(f"{failure}\nCache bytes on disk: {disk}") from failure
        calls_path = directory / "calls.jsonl"
        calls = (
            [json.loads(line) for line in calls_path.read_text().splitlines()]
            if calls_path.exists()
            else []
        )
        expected_scripts = [] if not enabled else ["check-calendar.py"]
        if enabled and availability == "available" and not availability_error:
            expected_scripts.append("list-calendars.py")
        if receives_calendars:
            expected_scripts.append("calendar-events.py")
        assert [call[0] for call in calls] == expected_scripts, calls
        if receives_events:
            saved = json.loads(cache.read_text())
            assert (
                saved["cachedEvents"] == EVENTS
                and saved["cachedCalendars"] == CALENDARS
            ), saved
            start, end = map(int, calls[-1][1])
            assert end - start == 45 * 86400, calls
            # A fresh engine must reload the bytes written by the real debounce timer.
            (directory / "Commons/Settings.qml").write_text(
                settings.replace("ENABLED", "false")
            )
            values.update(
                INITIAL_EVENTS=EVENTS,
                INITIAL_CALENDARS=CALENDARS,
                ENABLED=False,
                EXPECTED_AVAILABLE=False,
                SAVES_CACHE=False,
            )
            run_harness(directory, environment, values)
            assert len(calls_path.read_text().splitlines()) == len(calls)
        print(f"ok {name}")


def main():
    run_case("disabled cache load and polling", enabled=False, expected_available=False)
    run_case(
        "missing cache defaults", enabled=False, missing=True, expected_available=False
    )
    run_case(
        "availability/list/events callbacks, duplicate guard, debounce and fresh reload"
    )
    run_case(
        "unavailable stdout",
        availability="unavailable: fixture",
        terminal="EDS libraries not available",
        error="Evolution Data Server libraries not installed",
        expected_available=False,
    )
    run_case(
        "availability stderr",
        availability="unavailable: fixture",
        availability_error="fixture failure",
        terminal="Availability check error",
        error="Failed to check library availability",
        expected_available=False,
    )
    run_case(
        "invalid calendar stdout",
        calendars="not json",
        terminal="Failed to parse calendars",
        error="Failed to parse calendar list",
    )
    run_case(
        "calendar stderr",
        calendars="not json",
        calendars_error="calendar fixture failed",
        terminal="List calendars error",
        error="calendar fixture failed",
    )
    run_case(
        "invalid event stdout restores cache",
        events="not json",
        terminal="Using cached events",
        error="Failed to parse events",
    )
    run_case(
        "event stderr restores cache",
        events="not json",
        events_error="event fixture failed",
        terminal="Using cached events due to error",
        error="event fixture failed",
    )


if __name__ == "__main__":
    main()
