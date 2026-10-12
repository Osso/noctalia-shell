#!/usr/bin/env python3
"""Bounded production lint and offscreen IPC/inhibitor behavior; inert transports."""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("Services/Control/IPCService.qml", "Services/Power/IdleInhibitorService.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    expected = ({"missing-property": 7}, {})
    for target, wanted in zip(TARGETS, expected):
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / (Path(target).stem + ".lint.log")).write_text(output)
        print(output, end="")
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print(target, dict(counts))
        assert result.returncode == 0 and counts == wanted, (
            result.returncode,
            dict(counts),
            wanted,
        )


def stage_runtime(directory, mutation):
    workspace = helper("workspace-runtime")
    write, singleton = workspace.write_module, workspace.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem {}",
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Quickshell": singleton(
                'property var screens: []\nfunction execDetached(argv) { throw new Error("Unexpected command"); }'
            ),
            "PanelWindow": """import QtQuick
import Quickshell
Item {
  property ShellScreen screen: Quickshell.screens[1]
  property color color
  property QtObject mask
}""",
            "Region": "import QtQuick\nQtObject {}",
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "IpcHandler": "import QtQuick\nItem { property string target }",
            "FixtureIo": singleton(
                "property var commands: []\nproperty var signals: []\nproperty var process: null"
            ),
            "Process": """import QtQuick
Item {
  id: process
  property bool running: false
  property var command: []
  signal exited(int exitCode, int exitStatus)
  signal started()
  onRunningChanged: {
    if (running) {
      FixtureIo.commands = FixtureIo.commands.concat([command]);
      started();
    }
  }
  function signal(number) {
    FixtureIo.signals = FixtureIo.signals.concat([number]);
    running = false;
    exited(0, 0);
  }
  Component.onCompleted: FixtureIo.process = process
}""",
        },
    )
    write(
        directory,
        "Quickshell.Wayland",
        {
            "WlrLayershell": singleton("property int exclusionMode: 0"),
            "ExclusionMode": "import QtQuick\nQtObject { enum Mode { Ignore } }",
        },
    )
    write(directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Commons",
        {
            "Logger": singleton(
                "property var warnings: []\nproperty var errors: []\nfunction i(...args) {}\nfunction d(...args) {}\nfunction w(...args) { warnings = warnings.concat([args]); }\nfunction e(...args) { errors = errors.concat([args]); }"
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Settings": singleton(
                "property var data: ({general: {allowPanelsOnScreenWithoutBar: true}, bar: {monitors: []}})"
            ),
            "NColor": singleton('property color transparent: "transparent"'),
            "ShellState": singleton(
                "property var snapshot: ({bar: {visible: true}, count: 2})\nfunction buildStateSnapshot() { return snapshot; }"
            ),
        },
    )
    modules = {
        "Compositor": ["CompositorService"],
        "Hardware": ["BrightnessService", "AudioService", "BatteryService"],
        "Media": ["MediaService"],
        "Power": ["PowerProfileService"],
        "System": ["ScreenRecorderService", "NotificationService"],
        "Theming": ["ColorSchemeService", "WallpaperService"],
        "UI": ["PanelService", "BarService", "ToastService"],
    }
    for module, names in modules.items():
        write(
            directory, f"qs.Services.{module}", {name: singleton("") for name in names}
        )
    write(
        directory,
        "qs.Services.Media",
        {
            "MediaService": singleton(
                "property var seeks: []\nfunction seekRelative(value) { seeks = seeks.concat([{relative: value}]); }\nfunction seekByRatio(value) { seeks = seeks.concat([{ratio: value}]); }"
            )
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton(""),
            "BarService": singleton(""),
            "ToastService": singleton(
                "property var notices: []\nfunction showNotice(...args) { notices = notices.concat([args]); }"
            ),
        },
    )
    idle = (ROOT / TARGETS[1]).read_text()
    # Attached native layer-shell transport has no QML-only fixture equivalent.
    # Remove only its exclusion-mode assignment on this disposable runtime copy.
    ipc = (
        (ROOT / TARGETS[0])
        .read_text()
        .replace("      WlrLayershell.exclusionMode: ExclusionMode.Ignore\n", "")
    )
    if mutation == "parse":
        ipc = ipc.replace(
            "MediaService.seekRelative(offsetVal);", "MediaService.seekRelative(0);"
        )
    elif mutation == "exit":
        idle = re.sub(r"(?:root\.)?isInhibited = false;", "", idle)
    elif mutation == "capture":
        ipc = ipc.replace(
            "root.pendingCallback(root.detectedScreen);",
            "root.pendingCallback(Quickshell.screens[0]);",
        )
    write(
        directory,
        "qs.Services.Power",
        {"PowerProfileService": singleton(""), "IdleInhibitorService": idle},
    )
    write(directory, "qs.Services.Control", {"IPCService": ipc})
    shutil.copyfile(
        ROOT / "Tests/Qml/IpcIdleServicesHarness.qml", directory / "tst_services.qml"
    )


def private_environment(directory):
    environment = {
        "PATH": os.environ["PATH"],
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent",
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700, exist_ok=True)
        environment[key] = str(path)
    return environment


def lint_harness(directory, max_warnings):
    stage_runtime(directory, None)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            str(directory),
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            str(max_warnings),
            "--json",
            "-",
            str(directory / "tst_services.qml"),
        ],
        env=private_environment(directory),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "harness.lint.log").write_text(output)
    print(output, end="")
    report = json.loads(result.stdout)
    counts = Counter(
        warning["id"]
        for file in report["files"]
        for warning in file["warnings"]
        if warning["type"] == "warning"
    )
    total = sum(counts.values())
    print("HARNESS_LINT_COUNTS", dict(counts), "TOTAL", total)
    return int(result.returncode != 0 or total > max_warnings)


def runtime(directory, mutation):
    stage_runtime(directory, mutation)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory),
            "-import",
            str(directory),
        ],
        env=private_environment(directory),
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, result.returncode
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime", "lint-harness"))
    parser.add_argument("--max-warnings", type=int, default=0)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--mutation", choices=("parse", "exit", "capture"))
    args = parser.parse_args()
    assert args.mode == "runtime" or args.mutation is None
    if args.max_warnings < 0:
        parser.error("--max-warnings must be nonnegative")
    directory = args.artifacts.resolve()
    directory.mkdir(mode=0o700)
    if args.mode == "lint":
        lint(directory)
    elif args.mode == "lint-harness":
        return lint_harness(directory, args.max_warnings)
    else:
        runtime(directory, args.mutation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
