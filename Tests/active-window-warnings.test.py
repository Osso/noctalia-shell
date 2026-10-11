#!/usr/bin/env python3
"""Bounded ActiveWindow lint and offscreen production-loader startup coverage."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Widgets/ActiveWindow.qml")


def load_fixture():
    spec = importlib.util.spec_from_file_location(
        "metadata_fixture", ROOT / "Tests/bar-widget-metadata-runtime.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_fixture().fixture.stage_modules(directory)
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
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "block-var"
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("ACTIVE_WINDOW_LINT_COUNTS", dict(counts))
    assert not counts, f"ActiveWindow diagnostics remain: {dict(counts)}"
    assert result.returncode == 0, result.returncode


def stage_widget(directory, focused_start, production_style):
    fixture = load_fixture()
    fixture.stage_widgets(directory)
    # No other widget is instantiated; retain production metadata and Loader.
    registry = directory / "Services/UI/BarWidgetRegistry.qml"
    registry.write_text(
        registry.read_text().replace(
            'property Component mediaComponent: Component {\n    MediaMini { Component.onCompleted: BarWidgetRegistry.capture(this, "MediaMini") }\n}',
            "property Component mediaComponent: null",
        )
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["bar"]["widgets"] = {"left": [], "center": [], "right": []}
    fixture.fixture.write_singleton(
        directory / "Commons",
        "Settings",
        "property bool ready: false\n"
        + f"property bool focusedStart: {str(focused_start).lower()}\n"
        + f"property int expectedHeight: {27 if production_style else 32}\n"
        + "property var data: "
        + json.dumps(defaults),
    )
    fixture.fixture.write_singleton(
        directory / "Services/UI",
        "PanelService",
        """
property var actions: []
property var popup: ({
    close: function() { PanelService.actions.push("close"); },
    showContextMenu: function(menu) { PanelService.actions.push("show"); }
})
function getPopupMenuWindow(screen) { return popup; }""",
    )
    bar_service = directory / "Services/UI/BarService.qml"
    bar_service.write_text(
        bar_service.read_text()
        .replace(
            "function openWidgetSettings(...args) {}",
            'property var settingsArgs: []\nfunction openWidgetSettings(...args) { settingsArgs = args; PanelService.actions.push("settings"); }',
        )
        .replace("import QtQuick", "import QtQuick\nimport qs.Services.UI")
    )
    if focused_start:
        compositor = directory / "Services/Compositor/CompositorService.qml"
        compositor.write_text(
            compositor.read_text().replace(
                "property var focusedWindow: null",
                'property var focusedWindow: ({title: "Concrete focused startup title exceeding the metadata width cap", appId: "fixture"})',
            )
        )
    if production_style:
        shutil.copyfile(ROOT / "Commons/Style.qml", directory / "Commons/Style.qml")
        fixture.fixture.write_singleton(
            directory / "Services/Power",
            "PowerProfileService",
            "property bool noctaliaPerformanceMode: false",
        )
        colors = directory / "Commons/NColor.qml"
        colors.write_text(
            colors.read_text().replace(
                "QtObject {",
                'QtObject {\nreadonly property color mSurfaceVariant: "#303030"',
            )
        )
    shutil.copyfile(
        ROOT / "Tests/Qml/ActiveWindowWarningsHarness.qml", directory / "shell.qml"
    )
    return fixture


def behavior(directory, focused_start, production_style):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    fixture = stage_widget(directory, focused_start, production_style)
    try:
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            cwd=ROOT,
            env=fixture.isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        assert settings.read_bytes() == original, "real settings changed"
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "ACTIVE_WINDOW_BEHAVIOR_PASS" in output, "scenario incomplete"
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )
    print("SETTINGS_SHA_UNCHANGED", hashlib.sha256(original).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--focused-start", action="store_true")
    parser.add_argument("--production-style", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-active-window-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint":
            lint(directory)
        else:
            behavior(directory, args.focused_start, args.production_style)


if __name__ == "__main__":
    main()
