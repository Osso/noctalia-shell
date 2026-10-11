#!/usr/bin/env python3
"""Bounded production bar custom-button editor: offscreen controls and lint."""

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Bar/WidgetSettings/CustomButtonSettings.qml")
EXPECTED_HASH = "bc53e7cae6f456d443ba79ccee688802f18fb38abd6cbfc695ae331885b841e4"


def load_helper(filename):
    spec = importlib.util.spec_from_file_location("fixture", ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_helper("media-mini-warnings.test.py").stage_modules(directory)
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
    print("CUSTOM_BUTTON_BAR_SETTINGS_WARNINGS", len(warnings))
    assert not warnings and result.returncode == 0, output


def behavior(directory):
    helper = load_helper("setup-layout-geometry.test.py")
    source = directory / "source"
    source.mkdir()
    for relative in ("Commons", "Widgets", "Helpers", "Assets"):
        shutil.copytree(ROOT / relative, source / relative)
    target = source / TARGET
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / TARGET, target)
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["ui"].update(fontDefault="Sans Serif", fontFixed="monospace")
    helper.write_singleton(
        source, "Commons/Settings.qml", "property var data: " + json.dumps(defaults)
    )
    helper.write_singleton(
        source,
        "Commons/NColor.qml",
        "\n".join(
            f'property color {key}: "{value}"' for key, value in helper.PALETTE.items()
        ),
    )
    fixtures = {
        "Commons/I18n.qml": "function tr(key, text) { return text || key; }",
        "Commons/Logger.qml": "function i(...args) {}\nfunction d(...args) {}\nfunction w(...args) { console.warn(...args); }",
        "Services/UI/TooltipService.qml": "function show(...args) {}\nfunction hide() {}",
        "Services/Power/PowerProfileService.qml": "readonly property bool noctaliaPerformanceMode: false",
    }
    for path, body in fixtures.items():
        helper.write_singleton(source, path, body)
    load_helper("media-mini-warnings.test.py").stage_modules(directory, source)
    shutil.copytree(source / "Assets", directory / "qs/Assets")
    (directory / "qs/Commons/qmldir").write_text(
        "module qs.Commons\n"
        + "".join(
            f"singleton {name} 1.0 {name}.qml\n"
            for name in (
                "Settings",
                "Style",
                "NColor",
                "Icons",
                "IconsTabler",
                "I18n",
                "Logger",
            )
        )
    )
    quickshell = directory / "Quickshell"
    quickshell.mkdir()
    (quickshell / "qmldir").write_text(
        "module Quickshell\nSingleton 1.0 Singleton.qml\nsingleton Quickshell 1.0 Quickshell.qml\n"
    )
    widgets = quickshell / "Widgets"
    widgets.mkdir()
    (widgets / "qmldir").write_text(
        "module Quickshell.Widgets\nFixture 1.0 Fixture.qml\n"
    )
    (widgets / "Fixture.qml").write_text("import QtQuick\nQtObject {}\n")
    (quickshell / "Singleton.qml").write_text(
        "import QtQuick\nQtObject { default property list<QtObject> data }\n"
    )
    helper.write_singleton(
        directory,
        "Quickshell/Quickshell.qml",
        "readonly property string shellDir: "
        + json.dumps(str(directory / "qs"))
        + "\nsignal reloadCompleted()",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/CustomButtonBarSettingsHarness.qml",
        directory / "tst_editor.qml",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_editor.qml"),
            "-import",
            str(directory),
        ],
        cwd=directory,
        env=helper.isolated_environment(directory),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    assert hashlib.sha256(original).hexdigest() == EXPECTED_HASH
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-button-editor-") as temporary:
        directory = Path(temporary)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert backup.stat().st_mode & 0o777 == 0o600
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == EXPECTED_HASH
        try:
            (lint if args.mode == "lint" else behavior)(directory)
        finally:
            assert settings.read_bytes() == original, "Real settings bytes changed"
            assert hashlib.sha256(backup.read_bytes()).hexdigest() == EXPECTED_HASH


if __name__ == "__main__":
    main()
