#!/usr/bin/env python3
"""Grouped taskbar/OSD editors only: audited config denial and sandboxed offscreen Qt."""

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
TARGETS = (
    Path("Modules/Panels/Settings/Bar/WidgetSettings/TaskbarGroupedSettings.qml"),
    Path("Modules/Panels/Settings/Tabs/OsdTab.qml"),
)


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


def stage_behavior(directory, owner_shadow=False):
    # Only fixture staging; never call helpers' real-settings CLI entry points.
    helper = load_helper("clock-settings-warnings.test.py")
    helper.stage_runtime(directory)
    (directory / "tst_clock.qml").unlink()
    helper.write_module(
        directory,
        "qs.Modules.Panels.Settings.Bar.WidgetSettings",
        {
            "TaskbarGroupedSettings": (ROOT / TARGETS[0]).read_text(),
        },
    )
    helper.write_module(
        directory,
        "qs.Modules.Panels.Settings.Tabs",
        {
            "OsdTab": (ROOT / TARGETS[1]).read_text(),
        },
    )
    # Production enum values without loading the OSD surface/backends.
    enum = re.search(
        r"enum Type\s*\{[^}]+\}", (ROOT / "Modules/OSD/OSD.qml").read_text()
    ).group()
    helper.write_module(
        directory,
        "qs.Modules.OSD",
        {"OSD": "import QtQuick\nQtObject { " + enum + " }"},
    )
    helper.write_module(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name; property string model; property int width; property int height }",
            "Quickshell": helper.singleton("""
property list<ShellScreen> screens: [
    ShellScreen { name: "TEST-A"; model: "Fixture A"; width: 1920; height: 1080 },
    ShellScreen { name: "TEST-B"; model: "Fixture B"; width: 2560; height: 1440 }
]
"""),
        },
    )
    helper.write_module(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": helper.singleton(
                'function getDisplayScale(name) { return name === "TEST-B" ? 1.5 : 1; }'
            ),
        },
    )
    if owner_shadow:
        # Real controls with colliding local names prove editor ownership.
        shadows = {
            "NToggle": "property bool valueHideUnoccupied: true\n",
            "NComboBox": 'property var widgetData: ({labelMode: "none"})\nproperty string valueLabelMode: "shadow"\n',
            "NCheckbox": "\n".join(
                f'function {name}(list, value) {{ throw new Error("WRONG_OWNER {name}"); }}'
                for name in ("addType", "removeType", "addMonitor", "removeMonitor")
            ),
        }
        for name, declarations in shadows.items():
            path = directory / "qs/Widgets" / f"{name}.qml"
            path.write_text(
                path.read_text().replace("id: root", "id: root\n" + declarations, 1)
            )
    harness = directory / "tst_grouped_osd_settings.qml"
    harness.write_text(
        (ROOT / "Tests/Qml/GroupedOsdSettingsWarningsHarness.qml").read_text()
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
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/grouped-osd-settings",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/grouped-osd-settings-system",
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
            *[str(directory / "qs" / target) for target in TARGETS],
        ]
    else:
        harness = stage_behavior(directory, mode == "behavior-shadow")
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
            "GROUPED_OSD_SETTINGS_WARNINGS",
            dict(counts),
            "TOTAL",
            len(warnings),
            "EXIT",
            code,
        )
        assert not warnings, output
    elif mode in ("behavior", "behavior-shadow"):
        assert "7 passed, 0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
    assert code == 0, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("lint", "behavior", "behavior-shadow", "lint-harness")
    )
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
            prefix="noctalia-grouped-osd-settings-"
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
