#!/usr/bin/env python3
"""Bounded ControlCenterTab production controls/dialog, offscreen and isolated."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/ControlCenterTab.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location("fixture", ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings.test.py").stage_modules(directory)
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
    print("CONTROL_CENTER_TAB_WARNINGS", len(warnings))
    assert not warnings and result.returncode == 0, output


def behavior(directory):
    geometry = helper("setup-layout-geometry.test.py")
    source = directory / "source"
    source.mkdir()
    for relative in ("Commons", "Widgets", "Helpers", "Assets"):
        shutil.copytree(ROOT / relative, source / relative)
    for relative in (
        TARGET,
        Path(
            "Modules/Panels/Settings/ControlCenter/ControlCenterWidgetSettingsDialog.qml"
        ),
    ):
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["ui"].update(fontDefault="Sans Serif", fontFixed="monospace")
    settings = source / "Commons/Settings.qml"
    settings.write_text(
        """pragma Singleton
import QtQuick
QtObject {
  id: settings
  property int saveRequests: 0
  property QtObject data: QtObject {
    property QtObject location: QtObject { property bool weatherEnabled: false }
    property QtObject controlCenter: QtObject {
      property string position: "center"
      property var cards: []
      property QtObject shortcuts: QtObject {
        property var left: []
        property var right: []
      }
    }
    property var ui: UI_DEFAULTS
    property var general: GENERAL_DEFAULTS
    property var bar: BAR_DEFAULTS
  }
  function saveImmediate() { settings.saveRequests++; }
}
""".replace("UI_DEFAULTS", json.dumps(defaults["ui"]))
        .replace("GENERAL_DEFAULTS", json.dumps(defaults["general"]))
        .replace("BAR_DEFAULTS", json.dumps(defaults["bar"]))
    )
    fixtures = {
        "Commons/Logger.qml": "function i(...args) {}\nfunction d(...args) {}\nfunction w(...args) { console.warn(...args); }",
        "Commons/I18n.qml": "function tr(key, values) { return typeof values === 'string' ? values : key; }",
        "Services/UI/TooltipService.qml": "function show(...args) {}\nfunction hide() {}",
        "Services/Power/PowerProfileService.qml": "readonly property bool noctaliaPerformanceMode: false",
        "Services/UI/ControlCenterWidgetRegistry.qml": """property var widgetMetadata: ({CustomButton: {allowUserSettings: true, icon: "terminal", command: "fixture-never-run"}})
function getAvailableWidgets() { return ["WiFi", "CustomButton", "Bluetooth"]; }
function widgetHasUserSettings(id) { return id === "CustomButton"; }""",
    }
    for path, body in fixtures.items():
        geometry.write_singleton(source, path, body)
    palette = dict(
        geometry.PALETTE,
        mOnSecondary="#ffffff",
        mOnTertiary="#ffffff",
        mOnError="#ffffff",
    )
    geometry.write_singleton(
        source,
        "Commons/NColor.qml",
        "\n".join(f'property color {key}: "{value}"' for key, value in palette.items()),
    )
    editor = (
        source
        / "Modules/Panels/Settings/ControlCenter/WidgetSettings/CustomButtonSettings.qml"
    )
    editor.parent.mkdir(parents=True)
    editor.write_text("""import QtQuick
Item {
  property var widgetData
  property var widgetMetadata
  property string draftIcon: widgetData.icon
  implicitWidth: 420
  implicitHeight: 80
  function saveSettings() { return {id: widgetData.id, icon: draftIcon}; }
}
""")
    helper("media-mini-warnings.test.py").stage_modules(directory, source)
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
    (quickshell / "Singleton.qml").write_text(
        "import QtQuick\nQtObject { default property list<QtObject> data }\n"
    )
    geometry.write_singleton(
        directory,
        "Quickshell/Quickshell.qml",
        "readonly property string shellDir: "
        + json.dumps(str(directory / "qs"))
        + "\nsignal reloadCompleted()",
    )
    widgets = quickshell / "Widgets"
    widgets.mkdir()
    (widgets / "qmldir").write_text(
        "module Quickshell.Widgets\nFixture 1.0 Fixture.qml\n"
    )
    (widgets / "Fixture.qml").write_text("import QtQuick\nQtObject {}\n")
    shutil.copyfile(
        ROOT / "Tests/Qml/ControlCenterTabWarningsHarness.qml",
        directory / "tst_tab.qml",
    )
    environment = geometry.isolated_environment(directory)
    environment["NOCTALIA_CONFIG_DIR"] = str(directory / "XDG_CONFIG_HOME")
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_tab.qml"),
            "-import",
            str(directory),
        ],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    diagnostics = [
        line
        for line in output.splitlines()
        if re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", line
        )
    ]
    print("CONTROL_CENTER_RUNTIME_DIAGNOSTICS", json.dumps(diagnostics))
    assert not diagnostics, diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-control-center-tab-"
    ) as temporary:
        directory = Path(temporary)
        backup = directory / "settings.backup.json"
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(original)
        assert backup.stat().st_mode & 0o777 == 0o600
        assert backup.read_bytes() == original
        print("SETTINGS_BACKUP_VERIFIED", backup, digest)
        try:
            (lint if args.mode == "lint" else behavior)(directory)
        finally:
            assert settings.read_bytes() == original, "Real settings changed"
            assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
            print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
