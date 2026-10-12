#!/usr/bin/env python3
"""ActiveWindow editor only: audited config denial and sandboxed offscreen Qt."""

import argparse
from collections import Counter
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/Panels/Settings/Bar/WidgetSettings/ActiveWindowSettings.qml")


def deny_host_path(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    name = os.path.abspath(os.fsdecode(path))
    host_home = name == "/home" or name.startswith("/home/")
    host_sync = name.startswith("/syncthing/") and not name.startswith(str(ROOT) + "/")
    if host_home or host_sync:
        raise PermissionError(f"CONFIG_ACCESS_DENIED {name}")


def audit(event, arguments):
    if event in ("open", "os.listdir", "os.scandir"):
        deny_host_path(arguments[0])


def guard_metadata(function):
    def guarded(path, *arguments, **keywords):
        deny_host_path(path)
        return function(path, *arguments, **keywords)

    return guarded


def prove_denial():
    protected = "/home/osso/.config/noctalia/settings.json"
    for operation in (open, os.stat, os.lstat, os.readlink):
        try:
            operation(protected)
        except PermissionError:
            print("CONFIG_ACCESS_DENIED", operation.__name__, flush=True)
        else:
            raise AssertionError(f"Host access accepted: {operation.__name__}")


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def stage_behavior(directory):
    # Staging only: the helper's real-settings CLI main is never called.
    helper = load_helper("clock-settings-warnings.test.py")
    helper.stage_runtime(directory)
    (directory / "tst_clock.qml").unlink()
    helper.write_module(
        directory,
        "qs.Modules.Panels.Settings.Bar.WidgetSettings",
        {"ActiveWindowSettings": (ROOT / TARGET).read_text()},
    )
    helper.write_module(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": helper.singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
            "BarWidgetRegistry": helper.singleton("""
property var widgetSettingsMap: ({ActiveWindow: "WidgetSettings/ActiveWindowSettings.qml"})
property var widgetMetadata: ({ActiveWindow: {showIcon: true, hideMode: "hidden", scrollingMode: "hover", maxWidth: 240, useFixedWidth: false, colorizeIcons: false}})
"""),
        },
    )
    harness = directory / "tst_active_window_settings.qml"
    harness.write_text(
        (ROOT / "Tests/Qml/ActiveWindowSettingsWarningsHarness.qml").read_text()
    )
    return harness


def isolated_environment(directory):
    environment = {"PATH": "/usr/bin", "LANG": "C.UTF-8"}
    for variable in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / variable
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/active-window-settings",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/active-window-settings-system",
    )
    return environment


def run_child(command, directory, environment):
    result = subprocess.run(
        command,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="", flush=True)
    return result.returncode, output


def run_sandboxed(mode, directory):
    mounts = Path("/proc/self/mountinfo").read_text()
    for path in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == path and " - tmpfs " in line
            for line in mounts.splitlines()
        ), path
    environment = isolated_environment(directory)
    if mode == "lint":
        load_helper("media-mini-warnings.test.py").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
    else:
        harness = stage_behavior(directory)
        if mode == "lint-harness":
            command = [
                "/usr/lib/qt6/bin/qmllint",
                "--bare",
                "-I",
                str(directory),
                "-I",
                "/usr/lib/qt6/qml",
                "--max-warnings",
                "0",
                str(harness),
            ]
        else:
            command = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(harness),
                "-import",
                str(directory),
            ]
    code, output = run_child(command, directory, environment)
    (directory / f"{mode}.log").write_text(output)
    if mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
        print(
            "ACTIVE_WINDOW_SETTINGS_WARNINGS",
            dict(counts),
            "TOTAL",
            len(warnings),
            "EXIT",
            code,
        )
        assert not warnings, output
    elif mode == "behavior":
        assert "6 passed, 0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
    assert code == 0, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.addaudithook(audit)
    with (
        patch("os.stat", guard_metadata(os.stat)),
        patch("os.lstat", guard_metadata(os.lstat)),
        patch("os.readlink", guard_metadata(os.readlink)),
    ):
        prove_denial()
        if args.sandbox:
            run_sandboxed(args.mode, args.sandbox)
            return
        with tempfile.TemporaryDirectory(
            prefix="noctalia-active-window-settings-"
        ) as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            command = [
                "bwrap",
                "--die-with-parent",
                "--unshare-all",
                "--new-session",
                "--ro-bind",
                "/",
                "/",
                "--perms",
                "000",
                "--tmpfs",
                "/home",
                "--tmpfs",
                "/syncthing",
                "--ro-bind",
                str(ROOT),
                str(ROOT),
                "--tmpfs",
                "/tmp",
                "--tmpfs",
                "/run",
                "--bind",
                temporary,
                temporary,
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                temporary,
                "--",
                "/usr/bin/python3",
                str(Path(__file__).absolute()),
                args.mode,
                "--sandbox",
                temporary,
            ]
            code, _ = run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


if __name__ == "__main__":
    main()
