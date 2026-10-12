#!/usr/bin/env python3
"""Bounded ControlCenterTab production controls/dialog, offscreen and isolated."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/ControlCenterTab.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location("fixture", ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory, environment):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    code, output = helper("grid-list-warnings.test.py").run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "control-center-tab-production-lint",
    )
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("CONTROL_CENTER_TAB_WARNINGS", len(warnings))
    assert not warnings and code == 0, output


def stage_behavior(directory):
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
  component LocationSettings: QtObject {
    property bool weatherEnabled: false
  }
  component Shortcuts: QtObject {
    property var left: []
    property var right: []
  }
  component ControlCenterSettings: QtObject {
    property string position: "center"
    property var cards: []
    property Shortcuts shortcuts: Shortcuts {}
  }
  component SettingsData: QtObject {
    property LocationSettings location: LocationSettings {}
    property ControlCenterSettings controlCenter: ControlCenterSettings {}
    property var ui: UI_DEFAULTS
    property var general: GENERAL_DEFAULTS
    property var bar: BAR_DEFAULTS
  }
  property SettingsData data: SettingsData {}
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


def behavior(directory, environment):
    stage_behavior(directory)
    code, output = helper("grid-list-warnings.test.py").run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_tab.qml"),
            "-import",
            str(directory),
        ],
        "control-center-tab-behavior",
    )
    assert code == 0 and "0 failed" in output, output
    diagnostics = [
        line
        for line in output.splitlines()
        if re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
            line,
        )
    ]
    print("CONTROL_CENTER_RUNTIME_DIAGNOSTICS", json.dumps(diagnostics))
    assert not diagnostics, diagnostics


def lint_harness(directory, environment, inject_warning):
    stage_behavior(directory)
    harness = directory / "tst_tab.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: scene",
                "id: scene\n  property int injectedWarning: scene.missingLintProbe",
                1,
            )
        )
    code, output = helper("grid-list-warnings.test.py").run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            str(directory),
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            "0",
            "--json",
            "-",
            str(harness),
        ],
        "control-center-tab-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("CONTROL_CENTER_TAB_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0 and code != 0, "semantic warning accepted or hidden"
    else:
        assert warnings == 0 and code == 0, "harness lint failed"
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(
        prefix="noctalia-control-center-tab-"
    ) as temporary:
        directory = args.artifacts.resolve() if args.artifacts else Path(temporary)
        if args.artifacts:
            directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        isolation = helper("grid-list-warnings.test.py")
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        environment = isolation.isolated_environment(directory)
        environment["NOCTALIA_CONFIG_DIR"] = environment["XDG_CONFIG_HOME"]
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory, environment, args.inject_warning))
        (lint if args.mode == "lint" else behavior)(directory, environment)


if __name__ == "__main__":
    main()
