#!/usr/bin/env python3
"""Targeted Clock lint and actual offscreen widget with fixed Time/UI services.

Reuse weather's isolated paths and basic production text/icon fixtures; no live
clock scheduling, settings bootstrap, panels, desktop input, or persistence.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Widgets/Clock.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


effects = load_helper("clock_fixtures", "weather-card-effects.test.py")
lint_fixture = load_helper("clock_lint", "media-mini-warnings.test.py")


def run_lint(directory):
    lint_fixture.stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
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
    print("CLOCK_LINT_COUNTS", dict(counts))
    assert not warnings, f"Clock warnings remain: {dict(counts)}"
    assert result.returncode == 0, f"qmllint failed: {result.returncode}"
    print("CLOCK_LINT_PASS")


def stage_runtime(directory):
    effects.stage_card(directory)
    for path in (TARGET, Path("Widgets/NPopupContextMenu.qml")):
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    commons = directory / "Commons"
    with (commons / "Style.qml").open("r+") as source:
        style = source.read()
        source.seek(0)
        source.write(
            style.rsplit("}", 1)[0]
            + """
property real capsuleHeight: 32
property color capsuleColor: "#202020"
property real radiusS: 4
property real fontSizeS: 10
property real animationNormal: 0
}\n"""
        )
        source.truncate()
    with (commons / "NColor.qml").open("r+") as source:
        colors = source.read()
        source.seek(0)
        source.write(
            colors.rsplit("}", 1)[0]
            + """
property color mSurface: "#202020"
property color mHover: "#404040"
property color mOnHover: "#ffffff"
}\n"""
        )
        source.truncate()
    effects.write_singleton(
        commons,
        "I18n",
        'property var locale: Qt.locale("en_US")\nfunction tr(key) { return key; }',
    )
    effects.write_singleton(
        commons,
        "Time",
        """property date now: new Date(2026, 9, 11, 14, 30, 45)
property int secondUpdateRefs: 0
function beginSecondUpdates() { secondUpdateRefs++; }
function endSecondUpdates() { secondUpdateRefs--; }
function formatRequiresSeconds(format) { return /(^|[^A-Za-z])s{1,2}([^A-Za-z]|$)/.test(format); }""",
    )
    extras = directory / "Modules/Bar/Extras"
    extras.mkdir(parents=True)
    effects.write_singleton(
        extras,
        "BarWidgetRegistry",
        """property var widgetMetadata: ({Clock: {
usePrimaryColor: false, useCustomFont: false, customFont: "",
formatHorizontal: "HH:mm", formatVertical: "HH mm"
}})""",
    )
    ui = directory / "Services/UI"
    ui.mkdir(parents=True)
    effects.write_singleton(
        ui,
        "PanelService",
        """function getPopupMenuWindow(screen) { return null; }
function getPanel(name, screen) { return null; }""",
    )
    effects.write_singleton(
        ui,
        "BarService",
        """function getTooltipDirection() { return "bottom"; }
function openWidgetSettings(...args) {}
function getContextMenuPosition(...args) { return {x: 0, y: 0}; }""",
    )
    effects.write_singleton(
        ui,
        "TooltipService",
        """function show(...args) {}
function hide() {}""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/ClockWarningsHarness.qml", directory / "shell.qml"
    )


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    try:
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            cwd=ROOT,
            env=effects.isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        assert settings.read_bytes() == original, "real settings changed"
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, f"Clock runtime failed: {result.returncode}"
    assert "CLOCK_BEHAVIOR_PASS" in output
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-clock-warnings-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint":
            run_lint(directory)
        else:
            run_behavior(directory)


if __name__ == "__main__":
    main()
