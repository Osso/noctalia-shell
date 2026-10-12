#!/usr/bin/env python3
"""Bounded BarTab lint/behavior: production controls, inert registry, private settings.

Standalone only. Direct signals do not prove physical input or live persistence.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/BarTab.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_behavior(directory):
    geometry = helper("setup-layout-geometry.test.py")
    source = directory / "source"
    source.mkdir()
    for relative in ("Commons", "Widgets", "Helpers", "Assets"):
        shutil.copytree(ROOT / relative, source / relative)
    for relative in (
        TARGET,
        Path("Modules/Panels/Settings/Bar/BarWidgetSettingsDialog.qml"),
    ):
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["ui"].update(fontDefault="Sans Serif", fontFixed="monospace")
    bar = defaults["bar"].copy()
    bar.pop("widgets")
    fields = "\n".join(
        f"property var {key}: {json.dumps(value)}" for key, value in bar.items()
    )
    geometry.write_singleton(
        source,
        "Commons/Settings.qml",
        """
  property int saveRequests: 0
  component BarWidgets: QtObject {
    property var left: []
    property var center: []
    property var right: []
  }
  component BarSettings: QtObject {
    BAR_FIELDS
    property BarWidgets widgets: BarWidgets {}
  }
  component SettingsData: QtObject {
    property var ui: UI_DEFAULTS
    property var general: GENERAL_DEFAULTS
    property BarSettings bar: BarSettings {}
  }
  property SettingsData data: SettingsData {}
  function saveImmediate() { saveRequests++; }
""".replace("UI_DEFAULTS", json.dumps(defaults["ui"]))
        .replace("GENERAL_DEFAULTS", json.dumps(defaults["general"]))
        .replace("BAR_FIELDS", fields),
    )
    fixtures = {
        "Commons/Logger.qml": "function i(...args) {}\nfunction d(...args) {}\nfunction w(...args) { console.warn(...args); }",
        "Commons/I18n.qml": """function tr(key, values) {
  if (key === 'system.monitor-description')
    return values.model + ':' + values.width + 'x' + values.height + '@' + values.scale;
  return key;
}""",
        "Services/UI/TooltipService.qml": "function show(...args) {}\nfunction hide() {}",
        "Services/UI/ToastService.qml": "property var warnings: []\nfunction showWarning(...args) { warnings = warnings.concat([args]); }",
        "Services/Power/PowerProfileService.qml": "readonly property bool noctaliaPerformanceMode: false",
        "Services/Compositor/CompositorService.qml": "function getDisplayScale(name) { return name === 'DP-1' ? 1.5 : 1; }",
        "Services/UI/BarWidgetRegistry.qml": """property var widgetMetadata: ({CustomButton: {allowUserSettings: true, icon: 'terminal', command: 'never-run'}})
property var widgetSettingsMap: ({CustomButton: Qt.resolvedUrl('../../Modules/Panels/Settings/Bar/WidgetSettings/CustomButtonSettings.qml')})
function getAvailableWidgets() { return ['Clock', 'CustomButton', 'ControlCenter']; }
function widgetHasUserSettings(id) { return id === 'CustomButton'; }""",
        "Services/UI/BarService.qml": """signal activeWidgetsChanged()
property var instances: [{widgetId: 'Clock', section: 'left'}, {widgetId: 'Clock', section: 'right'}]
function getAllRegisteredWidgets() { return instances; }
function lookupWidget(id) { return instances.find(item => item.widgetId === id); }""",
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
        source / "Modules/Panels/Settings/Bar/WidgetSettings/CustomButtonSettings.qml"
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
    module = helper("about-tab-warnings.test.py")
    module.write_module(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nQtObject { default property list<QtObject> data }",
            "ShellScreen": "import QtQuick\nQtObject { property string name; property string model; property int width; property int height }",
            "Quickshell": "pragma Singleton\nimport QtQuick\nQtObject {\n"
            + "readonly property string shellDir: "
            + json.dumps(str(directory / "qs"))
            + """
  signal reloadCompleted()
  property ShellScreen laptop: ShellScreen { name: 'eDP-1'; model: 'Laptop'; width: 1920; height: 1080 }
  property ShellScreen external: ShellScreen { name: 'DP-1'; model: 'External'; width: 2560; height: 1440 }
  property var screens: [laptop, external]
}
""",
        },
    )
    module.write_module(
        directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"}
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/BarTabWarningsHarness.qml", directory / "tst_tab.qml"
    )


def execute(mode, directory, environment, inject_warning=False):
    if mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        argv = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
    else:
        stage_behavior(directory)
        if mode == "lint-harness":
            return lint_staged_harness(directory, environment, inject_warning)
        argv = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_tab.qml"),
            "-import",
            str(directory),
        ]
    code, output = helper("grid-list-warnings.test.py").run_audited(
        directory, environment, argv, f"bar-tab-{mode}"
    )
    (directory / f"{mode}.log").write_text(output)
    if mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        print("BAR_TAB_WARNINGS", len(warnings))
        assert not warnings, warnings
    else:
        assert "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
            output,
        ), output
    assert code == 0, code


def lint_staged_harness(directory, environment, inject_warning):
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
        "bar-tab-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("BAR_TAB_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
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
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-tab-") as temporary:
        directory = args.artifacts.resolve() if args.artifacts else Path(temporary)
        if args.artifacts:
            directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        isolation = helper("grid-list-warnings.test.py")
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        environment = isolation.isolated_environment(directory)
        environment["NOCTALIA_CONFIG_DIR"] = environment["XDG_CONFIG_HOME"]
        code = execute(args.mode, directory, environment, args.inject_warning)
        if args.mode == "lint-harness":
            raise SystemExit(code)


if __name__ == "__main__":
    main()
