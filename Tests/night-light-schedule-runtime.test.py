#!/usr/bin/env python3
"""Live schedule mutations with production Quickshell Process and private fake clients.

No real settings or compositor access. Reuses the runtime test's isolated modules.
"""

import importlib.util
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

RUNTIME_PATH = Path(__file__).with_name("night-light-runtime.test.py")
SPEC = importlib.util.spec_from_file_location("night_light_runtime", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)

SHELL = """import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.Location
ShellRoot {
  Component.onCompleted: NightLightService.apply()
  Timer {
    interval: 25
    running: true
    repeat: true
    onTriggered: mutations.running = true
  }
  Process {
    id: mutations
    command: ["read-mutation"]
    stdout: StdioCollector {
      onStreamFinished: {
        if (!text.trim()) return;
        const change = JSON.parse(text);
        Settings.data.nightLight[change.key] = change.value;
        console.log("Mutation applied", change.key, Settings.data.nightLight[change.key]);
      }
    }
  }
}
"""


def write_executable(path, body):
    path.write_text("#!/usr/bin/python3\n" + body)
    path.chmod(0o700)


def read_events(directory):
    return [
        json.loads(line) for line in runtime.text(directory / "events").splitlines()
    ]


def starts(directory):
    return [event for event in read_events(directory) if event[0] == "start"]


def mutate(directory, key, value):
    pending = directory / "pending"
    pending.write_text(json.dumps({"key": key, "value": value}))
    pending.replace(directory / "mutation")


def run_case(directory):
    for name in ("runtime", "config", "cache", "data", "bin"):
        (directory / name).mkdir(mode=0o700)
    settings = (
        runtime.SETTINGS.replace("forced: true", "forced: false")
        .replace("autoSchedule: false", "autoSchedule: true")
        .replace('manualSunrise: "07:30"', 'manualSunrise: "06:30"')
    )
    runtime.module(
        directory / "Commons",
        {
            "Settings": settings,
            "Logger": runtime.LOGGER,
            "I18n": runtime.I18N,
        },
    )
    runtime.module(directory / "Services/UI", {"ToastService": runtime.TOAST})
    runtime.module(
        directory / "Services/Location",
        {
            "LocationService": runtime.LOCATION,
            "NightLightService": (
                runtime.ROOT / "Services/Location/NightLightService.qml"
            ).read_text(),
        },
    )
    (directory / "shell.qml").write_text(SHELL)
    event_writer = f"""import json, os, signal, sys, time
from pathlib import Path
log = Path({str(directory / "events")!r})
def record(event):
    with log.open("a") as output:
        output.write(json.dumps(event) + "\\n")
"""
    write_executable(
        directory / "bin/wlsunset",
        event_writer
        + """
def terminate(signum, frame):
    record(["stop", os.getpid()])
    sys.exit(0)
signal.signal(signal.SIGTERM, terminate)
record(["start", os.getpid(), sys.argv[1:]])
while True:
    time.sleep(0.025)
""",
    )
    # Production cleanup runs unchanged, but enumeration is private and empty.
    write_executable(
        directory / "bin/pgrep",
        event_writer
        + """
record(["cleanup-start"])
time.sleep(0.3)
record(["cleanup-end"])
sys.exit(1)
""",
    )
    write_executable(
        directory / "bin/read-mutation",
        f"""from pathlib import Path
path = Path({str(directory / "mutation")!r})
if path.exists():
    print(path.read_text())
    path.unlink()
""",
    )
    env = runtime.base_shell_env(directory)
    env.pop("WAYLAND_DISPLAY", None)
    process = None
    try:
        with (directory / "shell.log").open("w") as output:
            process = subprocess.Popen(
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            processes = {"shell": process}
            runtime.wait_for(
                "initial automatic runner",
                lambda: len(starts(directory)) == 1,
                processes,
            )
            automatic = [
                "-t",
                "3800",
                "-T",
                "6500",
                "-l",
                "32.78",
                "-L",
                "-96.8",
                "-d",
                "900",
            ]
            assert starts(directory)[0][2] == automatic, read_events(directory)
            mutate(directory, "autoSchedule", False)
            runtime.wait_for(
                "autoSchedule mutation applied",
                lambda: (
                    "Mutation applied autoSchedule false"
                    in runtime.text(directory / "shell.log")
                ),
                processes,
            )
            runtime.wait_for(
                "manual cleanup after autoSchedule mutation",
                lambda: (
                    sum(e[0] == "cleanup-start" for e in read_events(directory)) == 2
                ),
                processes,
            )
            # Same object changes while cleanup is still running must select latest command.
            mutate(directory, "manualSunset", "22:00")
            runtime.wait_for(
                "manual 22:00 runner", lambda: len(starts(directory)) == 2, processes
            )
            manual = [
                "-t",
                "3800",
                "-T",
                "6500",
                "-S",
                "06:30",
                "-s",
                "22:00",
                "-d",
                "900",
            ]
            assert starts(directory)[1][2] == manual, read_events(directory)
            mutate(directory, "manualSunset", "22:30")
            runtime.wait_for(
                "changed sunset runner", lambda: len(starts(directory)) == 3, processes
            )
            manual[7] = "22:30"
            assert starts(directory)[2][2] == manual, read_events(directory)
            mutate(directory, "manualSunrise", "07:00")
            runtime.wait_for(
                "changed sunrise runner", lambda: len(starts(directory)) == 4, processes
            )
            manual[5] = "07:00"
            assert starts(directory)[3][2] == manual, read_events(directory)
            # All mutations above occurred in this still-live Quickshell instance.
            assert process.poll() is None
            mutate(directory, "enabled", False)
            runtime.wait_for(
                "disabled final runner",
                lambda: sum(e[0] == "stop" for e in read_events(directory)) == 4,
                processes,
            )
            events = read_events(directory)
            expected = ["cleanup-start", "cleanup-end", "start"]
            expected += ["stop", "cleanup-start", "cleanup-end", "start"] * 3
            expected += ["stop"]
            assert [e[0] for e in events] == expected, events
            assert len({e[1] for e in starts(directory)}) == 4, events
            assert "NightLightError" not in runtime.text(directory / "shell.log")
            print(
                f"PASS live scheduling: auto→manual, pending 22:00, sunset 22:30, sunrise 07:00; events={events}"
            )
    except Exception:
        print(
            f"FAIL live scheduling: events={read_events(directory)} shell={runtime.text(directory / 'shell.log')}"
        )
        raise
    finally:
        if process is not None:
            runtime.stop(process)
        # Only children recorded by our private fake executable may be signalled.
        for event in starts(directory):
            try:
                os.kill(event[1], 15)
            except ProcessLookupError:
                continue
            deadline = time.monotonic() + 2
            while Path(f"/proc/{event[1]}").exists() and time.monotonic() < deadline:
                time.sleep(0.025)
            assert not Path(f"/proc/{event[1]}").exists(), (
                f"fake child survived: {event[1]}"
            )


def main():
    with tempfile.TemporaryDirectory(prefix="night-light-schedule-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        run_case(directory)


if __name__ == "__main__":
    main()
