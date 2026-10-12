#!/usr/bin/env python3
"""Targeted lint and offscreen production TimerCard/Time behavior regression."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CARD = Path("Modules/Cards/TimerCard.qml")


def write_singleton(directory, name, body):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"
    )


def run_lint(directory):
    sources = subprocess.run(
        ["rg", "--files", "-g", "*.qml", "-g", "*.js", "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    modules = {}
    for name in sorted(sources.stdout.splitlines()):
        path = Path(name)
        target = directory / "qs" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
        if path.suffix != ".qml":
            continue
        for parent in (path.parent, *path.parent.parents):
            modules.setdefault(parent, [])
        singleton = (
            "singleton "
            if re.search(r"^\s*pragma\s+Singleton\b", target.read_text(), re.M)
            else ""
        )
        modules[path.parent].append(f"{singleton}{path.stem} 1.0 {path.name}\n")
    for path, declarations in modules.items():
        (directory / "qs" / path / "qmldir").write_text(
            f"module {'.'.join(('qs', *path.parts))}\n" + "".join(declarations)
        )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / CARD),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in warnings
    )
    print("TIMER_CARD_LINT_COUNTS", dict(counts))
    assert not warnings, f"TimerCard warnings remain: {dict(counts)}"
    assert result.returncode == 0, f"qmllint failed: {result.returncode}"
    print("TIMER_CARD_LINT_PASS")


def stage_runtime(directory):
    sources = [CARD, Path("Commons/Time.qml"), Path("Helpers/TimerDigits.js")]
    sources += [
        Path(f"Widgets/{name}.qml")
        for name in ("NBox", "NButton", "NText", "NIcon", "NTabBar", "NTabButton")
    ]
    for path in sources:
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    commons = directory / "Commons"
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    write_singleton(commons, "Settings", "property var data: " + json.dumps(defaults))
    style = {
        "uiScaleRatio": 1,
        "marginM": 8,
        "marginS": 4,
        "marginXS": 3,
        "marginL": 12,
        "radiusM": 12,
        "radiusS": 6,
        "radiusXS": 3,
        "borderS": 1,
        "baseWidgetSize": 32,
        "animationFast": 0,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXXL": 22,
        "fontSizeXXXL": 26,
        "fontWeightRegular": 400,
        "fontWeightMedium": 500,
        "fontWeightSemiBold": 600,
        "fontWeightBold": 700,
    }
    write_singleton(
        commons,
        "Style",
        "\n".join(
            f"readonly property real {key}: {value}" for key, value in style.items()
        ),
    )
    colors = {
        "mSurfaceVariant": "#202020",
        "mSurface": "#303030",
        "mOutline": "#808080",
        "mPrimary": "#abcdef",
        "mOnPrimary": "#000000",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#dddddd",
        "mHover": "#404040",
        "mOnHover": "#ffffff",
        "transparent": "transparent",
    }
    write_singleton(
        commons,
        "NColor",
        "\n".join(
            f"readonly property color {key}: {json.dumps(value)}"
            for key, value in colors.items()
        ),
    )
    write_singleton(
        commons,
        "Icons",
        """readonly property string defaultIcon: "clock"
readonly property string fontFamily: "sans-serif"
function get(name) { return "*"; }""",
    )
    write_singleton(commons, "I18n", "function tr(key) { return key; }")
    write_singleton(
        commons,
        "Logger",
        """function w(...args) { console.warn(...args); }
function callStack() { console.trace(); }""",
    )
    write_singleton(
        directory / "Services/System",
        "SoundService",
        """property int plays: 0
property int stops: 0
property string lastSound: ""
property var lastOptions
function playSound(name, options) { plays++; lastSound = name; lastOptions = options; }
function stopSound(name) { stops++; lastSound = name; }""",
    )
    write_singleton(
        directory / "Services/UI",
        "TooltipService",
        """function show(...args) {}
function hide() {}""",
    )
    shutil.copyfile(ROOT / "Tests/Qml/TimerCardHarness.qml", directory / "shell.qml")


def isolate_environment(directory):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key not in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME")
    }
    for variable in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    return environment


def run_behavior(directory):
    environment = isolate_environment(directory)
    settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
    settings.parent.mkdir(mode=0o700, parents=True)
    original = (ROOT / "Assets/settings-default.json").read_bytes()
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        path.touch(mode=0o600)
        path.write_bytes(original)
        assert path.read_bytes() == original, "fixture bytes differ"
        assert path.stat().st_mode & 0o777 == 0o600, "fixture mode differs"
    try:
        stage_runtime(directory)
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"
        assert settings.stat().st_mode & 0o777 == 0o600, "fixture settings mode changed"
        assert backup.stat().st_mode & 0o777 == 0o600, "fixture backup mode changed"
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, f"TimerCard runtime failed: {result.returncode}"
    assert "TIMER_CARD_BEHAVIOR_PASS" in output, "timer assertions did not finish"
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-timer-card-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint":
            run_lint(directory)
        else:
            run_behavior(directory)


if __name__ == "__main__":
    main()
