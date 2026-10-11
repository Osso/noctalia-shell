#!/usr/bin/env python3
"""Bounded BarTab lint/behavior: production controls, inert registry, private settings.

Standalone only. Direct signals do not prove physical input or live persistence.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

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
  property QtObject data: QtObject {
    property var ui: UI_DEFAULTS
    property var general: GENERAL_DEFAULTS
    property QtObject bar: QtObject {
      BAR_FIELDS
      property QtObject widgets: QtObject {
        property var left: []
        property var center: []
        property var right: []
      }
    }
  }
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


def execute(mode, directory):
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
        argv = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_tab.qml"),
            "-import",
            str(directory),
        ]
    environment = helper("display-tab-warnings.test.py").isolated_environment(directory)
    environment["NOCTALIA_CONFIG_DIR"] = environment["XDG_CONFIG_HOME"]
    result = subprocess.run(
        argv, cwd=directory, env=environment, capture_output=True, text=True, timeout=60
    )
    output = result.stdout + result.stderr
    (directory / f"{mode}.log").write_text(output)
    print(output, end="")
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
    assert result.returncode == 0, result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    directory = args.artifacts.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = directory / "settings.backup.json"
    descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(original)
    assert backup.stat().st_mode & 0o777 == 0o600
    assert backup.read_bytes() == original
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    print("SETTINGS_BACKUP_VERIFIED", backup, digest)
    try:
        execute(args.mode, directory)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert backup.read_bytes() == original, "Backup changed"
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
