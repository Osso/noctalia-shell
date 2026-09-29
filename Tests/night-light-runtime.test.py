#!/usr/bin/env python3
"""Isolated Quickshell Process + real wlsunset against a private gamma-control server.

Test-only dependencies: quickshell, /usr/bin/wlsunset, wayland-scanner, cc,
libwayland-server development headers/pkg-config, Python 3. No desktop access.
"""
import hashlib
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "Tests/fixtures/night-light"
WLSUNSET = Path("/usr/bin/wlsunset")
SETTINGS = '''pragma Singleton
import QtQuick
QtObject {
  property QtObject data: QtObject {
    property QtObject nightLight: QtObject {
      property bool enabled: true
      property bool forced: true
      property bool autoSchedule: false
      property int nightTemp: 3800
      property int dayTemp: 6500
      property string manualSunrise: "07:30"
      property string manualSunset: "19:45"
    }
  }
}
'''
LOCATION = '''pragma Singleton
import QtQuick
QtObject {
  property bool coordinatesReady: true
  property real stableLatitude: 32.78
  property real stableLongitude: -96.8
}
'''
LOGGER = '''pragma Singleton
import QtQuick
QtObject {
  function i(...args) { console.log("NightLightLogger", ...args); }
  function e(...args) { console.error("NightLightError", ...args); }
}
'''
TOAST = '''pragma Singleton
import QtQuick
QtObject { function showNotice(...args) {} }
'''
I18N = '''pragma Singleton
import QtQuick
QtObject { function tr(text) { return text; } }
'''


def execute(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def wait_for(label, predicate, processes, seconds=6):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        for name, process in processes.items():
            if process.poll() is not None:
                raise AssertionError(f"{label}: {name} exited with {process.returncode}")
        time.sleep(0.025)
    raise AssertionError(f"timeout waiting for {label}")


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def text(path):
    return path.read_text() if path.exists() else ""


def module(path, entries):
    path.mkdir(parents=True, exist_ok=True)
    (path / "qmldir").write_text("\n".join(f"singleton {name} 1.0 {name}.qml" for name in entries) + "\n")
    for name, contents in entries.items():
        (path / f"{name}.qml").write_text(contents)


def compile_server(directory):
    xml = FIXTURE / "wlr-gamma-control-unstable-v1.xml"
    execute(["wayland-scanner", "server-header", str(xml), str(directory / "gamma-server.h")])
    execute(["wayland-scanner", "private-code", str(xml), str(directory / "gamma-protocol.c")])
    flags = subprocess.check_output(["pkg-config", "--cflags", "--libs", "wayland-server"], text=True).split()
    execute(["cc", "-std=c11", "-Wall", "-Wextra", "-o", str(directory / "server"),
             "-I", str(directory), str(FIXTURE / "server.c"), str(directory / "gamma-protocol.c"), *flags])


def run_case(mode, root):
    directory = root / mode
    directory.mkdir(mode=0o700)
    compile_server(directory)
    server_log = directory / "server.log"
    old_log = directory / "old.log"
    shell_log = directory / "shell.log"
    processes = {}
    try:
        # The old client and cleanup fixture are strictly test-owned; no real settings
        # or compositor connection and no signal ever sent to canonical wlsunset.
        base_env = os.environ.copy()
        for key in list(base_env):
            if key.startswith("WAYLAND_") or key.startswith("XDG_"):
                del base_env[key]
        base_env.update(XDG_RUNTIME_DIR=str(directory / "runtime"), WAYLAND_DISPLAY="repro-gamma")
        (directory / "runtime").mkdir(mode=0o700)
        with server_log.open("w") as server_output, old_log.open("w") as old_output, shell_log.open("w") as shell_output:
            processes["server"] = subprocess.Popen([str(directory / "server")], env=base_env,
                                                    stdout=server_output, stderr=subprocess.STDOUT)
            wait_for("private server", lambda: "READY" in text(server_log), processes)
            isolated_wlsunset = copy_wlsunset(directory)
            processes["old"] = subprocess.Popen([str(isolated_wlsunset), "-t", "3800", "-T", "6500", "-S", "23:59",
                                                "-s", "00:00", "-d", "1"], env=base_env,
                                               stdout=old_output, stderr=subprocess.STDOUT)
            wait_for("old ramp", lambda: "RAMP count=1 " in text(server_log), processes)
            assert Path(f"/proc/{processes['old'].pid}/comm").read_text().strip() == "nl-test-client"
            (directory / "old.pid").write_text(str(processes["old"].pid))
            env = prepare_for_shell(directory, mode)
            processes["shell"] = subprocess.Popen(["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                                                   env=env, stdout=shell_output,
                                                   stderr=subprocess.STDOUT)
            if mode == "gamma-failure":
                wait_for("failed gamma acquisition", lambda: "FAILED count=1" in text(server_log), processes)
                wait_for("live gamma stderr", lambda: "gamma control of output" in text(shell_log), processes)
                assert processes["shell"].poll() is None
            elif mode == "failure":
                wait_for("cleanup failure", lambda: "NightLightError" in text(shell_log), processes)
                time.sleep(0.35)
                assert "RELEASE" not in text(server_log), text(server_log)
                assert "FAILED" not in text(server_log), text(server_log)
                assert "Wlsunset started" not in text(shell_log), text(shell_log)
            elif mode == "disabled":
                time.sleep(1.2)
                assert "RELEASE" in text(server_log), text(server_log)
                assert "RAMP count=2" not in text(server_log), text(server_log)
                assert "Wlsunset started" not in text(shell_log), text(shell_log)
            else:
                wait_for("new ramp", lambda: "RAMP count=2 " in text(server_log),
                         {name: processes[name] for name in ("server", "shell")}, seconds=3)
                assert "FAILED" not in text(server_log), text(server_log)
                assert "RELEASE count=1 restored=neutral" in text(server_log), text(server_log)
                assert "NightLightError NightLight Wlsunset stderr" not in text(shell_log), text(shell_log)
                assert processes["shell"].poll() is None
                if mode == "latest":
                    assert '3200' in text(shell_log), text(shell_log)
                    assert '4200' not in text(shell_log), text(shell_log)
                    ramps = re.findall(r"RAMP count=\d+ red_last=\d+ green_last=(\d+) blue_last=(\d+)", text(server_log))
                    assert len(ramps) == 2 and ramps[1] != ramps[0], text(server_log)
                if mode == "unchanged":
                    time.sleep(1.1)
                    assert text(server_log).count("ACQUIRE ") == 2, text(server_log)
                    assert text(shell_log).count("Stale wlsunset cleanup started") == 1, text(shell_log)
            print(f"PASS {mode}: server={text(server_log)!r} shell={text(shell_log)!r}")
    except Exception:
        print(f"FAIL {mode}: server={text(server_log)} old={text(old_log)} shell={text(shell_log)}")
        raise
    finally:
        for process in reversed(list(processes.values())):
            stop(process)
        assert all(process.poll() is not None for process in processes.values())


def copy_wlsunset(directory):
    binary = directory / "bin/nl-test-client"
    binary.parent.mkdir(mode=0o700)
    shutil.copy2(WLSUNSET, binary)
    checksum = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert checksum(binary) == checksum(WLSUNSET), "fixture must execute byte-for-byte installed wlsunset"
    wrapper = directory / "bin/wlsunset"
    wrapper.write_text(f"#!/bin/sh\nexec '{binary}' \"$@\"\n")
    wrapper.chmod(0o700)
    return binary


def prepare_for_shell(directory, mode):
    for name in ("config", "cache", "data"):
        path = directory / name
        path.mkdir(mode=0o700)
    module(directory / "Commons", {"Settings": SETTINGS, "Logger": LOGGER, "I18n": I18N})
    module(directory / "Services/UI", {"ToastService": TOAST})
    service = directory / "Services/Location"
    module(service, {"LocationService": LOCATION})
    shutil.copyfile(ROOT / "Services/Location/NightLightService.qml", service / "NightLightService.qml")
    with (service / "qmldir").open("a") as qmldir:
        qmldir.write("singleton NightLightService 1.0 NightLightService.qml\n")
    shell = (FIXTURE / "shell.qml").read_text().replace("TEST_MODE", mode)
    (directory / "shell.qml").write_text(shell)
    # No system process enumeration: pgrep returns exclusively our old child.
    pgrep = directory / "bin/pgrep"
    pgrep.write_text("#!/bin/sh\n/usr/bin/sleep 0.45\n" +
                     ("exit 23\n" if mode == "failure" else
                      "exit 1\n" if mode == "gamma-failure" else
                      f"printf '%s\\n' '{(directory / 'old.pid').read_text().strip()}'\n"))
    pgrep.chmod(0o700)
    env = base_shell_env(directory)
    return env


def base_shell_env(directory):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("WAYLAND_") or key.startswith("XDG_") or key.startswith("QS_"):
            del env[key]
    env.update(XDG_RUNTIME_DIR=str(directory / "runtime"), XDG_CONFIG_HOME=str(directory / "config"),
               XDG_CACHE_HOME=str(directory / "cache"), XDG_DATA_HOME=str(directory / "data"),
               WAYLAND_DISPLAY="repro-gamma", QT_QPA_PLATFORM="offscreen",
               PATH=f"{directory / 'bin'}:{os.environ['PATH']}")
    return env


def main():
    with tempfile.TemporaryDirectory(prefix="night-light-runtime-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        for mode in ("overlap", "failure", "disabled", "latest", "unchanged", "gamma-failure"):
            run_case(mode, root)


if __name__ == "__main__":
    main()
