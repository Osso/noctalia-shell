#!/usr/bin/env python3
"""Targeted MediaMini lint and actual-widget offscreen regression.

Fixture services prevent settings bootstrap, MPRIS/DBus and desktop access.
Production MediaMini, text/icons, art, popup delegates and spectra remain real.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WIDGET = Path("Modules/Bar/Widgets/MediaMini.qml")


def write_singleton(directory, name, body):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"
    )


def stage_modules(directory):
    result = subprocess.run(
        ["rg", "--files", "-g", "*.qml", "-g", "*.js", "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    modules = {}
    for relative in sorted(result.stdout.splitlines()):
        path = Path(relative)
        target = directory / "qs" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
        if path.suffix != ".qml":
            continue
        for parent in (path.parent, *path.parent.parents):
            modules.setdefault(parent, [])
        singleton = bool(
            re.search(r"^\s*pragma\s+Singleton\b", target.read_text(), re.M)
        )
        prefix = "singleton " if singleton else ""
        modules[path.parent].append(f"{prefix}{path.stem} 1.0 {path.name}\n")
    for path, declarations in modules.items():
        (directory / "qs" / path / "qmldir").write_text(
            f"module {'.'.join(('qs', *path.parts))}\n" + "".join(declarations)
        )


def run_lint(directory):
    stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / WIDGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in warnings
    )
    print(output, end="")
    print("MEDIA_MINI_LINT_COUNTS", dict(counts))
    # Five outer mainContainer ID reads inside Loader source components remain
    # unbound. Do not change delegate context injection just to satisfy lint.
    assert counts == {"unqualified": 5}, (
        f"actionable MediaMini warnings remain: {dict(counts)}"
    )
    blocks = re.split(r"(?=Warning:)", output)[1:]
    assert all(
        "mainContainer." in block and "ComponentBehavior: Bound" in block
        for block in blocks
    )
    assert result.returncode in (0, 255), f"unexpected qmllint exit {result.returncode}"
    print("MEDIA_MINI_LINT_PASS (5 documented unbound component ID reads)")


def stage_widget(directory):
    files = [
        WIDGET,
        Path("Widgets/NText.qml"),
        Path("Widgets/NIcon.qml"),
        Path("Widgets/NImageRounded.qml"),
        Path("Widgets/NPopupContextMenu.qml"),
    ]
    files += sorted(
        Path("Widgets/AudioSpectrum") / name
        for name in (
            "NLinearSpectrum.qml",
            "NMirroredSpectrum.qml",
            "NWaveSpectrum.qml",
        )
    )
    for path in files:
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    shutil.copytree(ROOT / "Shaders/qsb", directory / "Shaders/qsb")
    commons = directory / "Commons"
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["bar"]["position"] = "top"
    write_singleton(commons, "Settings", "property var data: " + json.dumps(defaults))
    style = {
        "uiScaleRatio": 1,
        "marginM": 8,
        "marginS": 4,
        "marginXXS": 2,
        "radiusS": 4,
        "radiusM": 8,
        "radiusL": 12,
        "borderS": 1,
        "baseWidgetSize": 32,
        "capsuleHeight": 32,
        "animationNormal": 0,
        "animationFast": 0,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXXL": 20,
        "fontWeightMedium": 500,
    }
    write_singleton(
        commons,
        "Style",
        "\n".join(
            f"readonly property real {key}: {value}" for key, value in style.items()
        )
        + '\nreadonly property color capsuleColor: "#202020"',
    )
    colors = {
        "mSurface": "#202020",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#dddddd",
        "mPrimary": "#abcdef",
        "mOutline": "#808080",
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
        """readonly property string defaultIcon: "disc"
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
        directory / "Modules/Bar/Extras",
        "BarWidgetRegistry",
        "property var widgetMetadata: ({})",
    )
    write_singleton(
        directory / "Services/Media",
        "MediaService",
        """property var currentPlayer: null
property bool isPlaying: false
property bool canPlay: true
property bool canGoNext: true
property bool canGoPrevious: true
property string trackArtist: "Artist"
property string trackTitle: "Title"
property string trackArtUrl: ""
property real trackLength: 100
property real currentPosition: 25
property int positionConsumers: 0
property int previousCount: 0
property int nextCount: 0
function beginPositionUpdates(detailed) { positionConsumers++; }
function endPositionUpdates(detailed) { positionConsumers--; }
function playPause() { isPlaying = !isPlaying; }
function previous() { previousCount++; }
function next() { nextCount++; }""",
    )
    write_singleton(
        directory / "Services/Media",
        "CavaService",
        "property var values: [0.2, 0.6, 0.9]",
    )
    ui = directory / "Services/UI"
    write_singleton(
        ui, "PanelService", "function getPopupMenuWindow(screen) { return null; }"
    )
    write_singleton(
        ui,
        "BarService",
        """function getTooltipDirection() { return "bottom"; }
function openWidgetSettings(...args) {}
function getContextMenuPosition(...args) { return {x: 0, y: 0}; }""",
    )
    write_singleton(
        ui,
        "TooltipService",
        """property string lastText: ""
function show(item, text, direction) { lastText = text; }
function hide() { lastText = ""; }""",
    )
    (directory / "cover.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><rect width="24" height="24" fill="red"/></svg>'
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/MediaMiniWarningsHarness.qml", directory / "shell.qml"
    )


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


def run_widget(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    if original is not None:
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert (
            hashlib.sha256(backup.read_bytes()).digest()
            == hashlib.sha256(original).digest()
        )
    stage_widget(directory)
    try:
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            cwd=ROOT,
            env=isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=15,
        )
    finally:
        assert (settings.read_bytes() if settings.exists() else None) == original, (
            "real settings changed"
        )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, f"MediaMini runtime failed: {result.returncode}"
    assert "MEDIA_MINI_BEHAVIOR_PASS" in output, "widget assertions did not finish"
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-media-mini-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint":
            run_lint(directory)
        else:
            run_widget(directory)


if __name__ == "__main__":
    main()
