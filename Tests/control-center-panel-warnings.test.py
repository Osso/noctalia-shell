#!/usr/bin/env python3
"""ControlCenterPanel-only static and offscreen owner/routing/layout proof.

Production panel is unchanged in staging; SmartPanel and leaf cards are inert
fixtures. Tests cover panel bindings, not real cards, compositor placement or
settings persistence. No desktop surfaces or service backends are available.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/ControlCenter/ControlCenterPanel.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
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
        "control-center-panel-lint",
    )
    (directory / "lint.log").write_text(output)
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("CONTROL_CENTER_PANEL_WARNINGS", len(warnings))
    assert not warnings and code == 0, output


def stage_behavior(directory):
    helpers = helper("about-tab-warnings.test.py")
    write, singleton = helpers.write_module, helpers.singleton
    write(
        directory,
        "qs.Modules.Panels.ControlCenter",
        {
            "ControlCenterPanel": (ROOT / TARGET).read_text(),
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "property real uiScaleRatio: 1\nproperty real marginL: 12"
            ),
            "Settings": singleton("""property var data: ({
  controlCenter: {position: "center", cards: [], shortcuts: {left: [], right: []}},
  bar: {monitors: []}, location: {weatherEnabled: true}
})"""),
        },
    )
    write(
        directory,
        "qs.Services.Media",
        {
            "MediaService": singleton("property bool autoSwitchingPaused: false"),
        },
    )
    write(
        directory,
        "qs.Services.Networking",
        {
            "VPNService": singleton("""property int pollingRefs: 0
property int starts: 0
property int stops: 0
function beginPolling() { pollingRefs++; starts++; }
function endPolling() { pollingRefs--; stops++; }"""),
        },
    )
    write(directory, "Quickshell", {"Inert": "import QtQuick\nQtObject {}"})
    write(directory, "qs.Services.UI", {"Inert": "import QtQuick\nQtObject {}"})
    write(directory, "qs.Widgets", {"Inert": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  id: host
  property QtObject screen
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool panelAnchorHorizontalCenter: false
  property bool panelAnchorVerticalCenter: false
  property bool panelAnchorTop: false
  property bool panelAnchorBottom: false
  property bool panelAnchorLeft: false
  property bool panelAnchorRight: false
  property bool isPanelOpen: false
  property alias contentItem: loader.item
  signal opened()
  signal closed()
  function open() { host.isPanelOpen = true; host.opened(); }
  function close() { host.isPanelOpen = false; host.closed(); }
  Loader { id: loader; anchors.fill: parent; sourceComponent: host.panelContent }
}""",
        },
    )
    cards = {}
    for name, card_id in (
        ("ProfileCard", "profile-card"),
        ("ShortcutsCard", "shortcuts-card"),
        ("AudioCard", "audio-card"),
        ("WeatherCard", "weather-card"),
        ("MediaCard", "media-sysmon-card"),
    ):
        weather_size = "height: 173" if name == "WeatherCard" else ""
        dependencies = {
            "ProfileCard": "required property QtObject screen",
            "ShortcutsCard": "required property QtObject controlCenter",
        }.get(name, "")
        cards[name] = f'''import QtQuick
Item {{
  readonly property string cardKind: "{card_id}"
  {dependencies}
  {weather_size}
}}'''
    write(directory, "qs.Modules.Cards", cards)
    (directory / "tst_control_center.qml").write_text(
        (ROOT / "Tests/Qml/ControlCenterPanelWarningsHarness.qml").read_text()
    )


def lint_harness(directory, environment, inject_warning):
    stage_behavior(directory)
    harness = directory / "tst_control_center.qml"
    if inject_warning:
        source = harness.read_text()
        marker = "id: testCase"
        assert source.count(marker) == 1, "injection owner must be unique"
        harness.write_text(
            source.replace(
                marker,
                marker
                + "\n    property int injectedWarning: testCase.missingLintProbe",
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
        "control-center-harness-lint",
    )
    (directory / "lint-harness.json").write_text(output)
    diagnostics = json.loads(output)
    warnings = sum(
        diagnostic["type"] == "warning"
        for entry in diagnostics["files"]
        for diagnostic in entry["warnings"]
    )
    print("CONTROL_CENTER_HARNESS_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0 and code != 0, "injected warning was accepted"
    else:
        assert warnings == 0 and code == 0, "strict harness lint failed"
    return code


def behavior(directory, environment):
    stage_behavior(directory)
    code, output = helper("grid-list-warnings.test.py").run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_control_center.qml"),
            "-import",
            str(directory),
        ],
        "control-center-behavior",
    )
    (directory / "behavior.log").write_text(output)
    assert code == 0 and "6 passed, 0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    isolation = helper("grid-list-warnings.test.py")
    isolation.install_settings_guard(args.artifacts)
    environment = isolation.isolated_environment(args.artifacts)
    if args.mode == "lint-harness":
        raise SystemExit(lint_harness(args.artifacts, environment, args.inject_warning))
    {"lint": lint, "behavior": behavior}[args.mode](args.artifacts, environment)


if __name__ == "__main__":
    main()
