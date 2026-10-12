#!/usr/bin/env python3
"""ControlCenterPanel-only static and offscreen owner/routing/layout proof.

Production panel is unchanged in staging; SmartPanel and leaf cards are inert
fixtures. Tests cover panel bindings, not real cards, compositor placement or
settings persistence. No desktop surfaces or service backends are available.
"""

import argparse
import importlib.util
from pathlib import Path
import re
import subprocess

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/ControlCenter/ControlCenterPanel.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
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
    (directory / "lint.log").write_text(output)
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("CONTROL_CENTER_PANEL_WARNINGS", len(warnings))
    assert not warnings and result.returncode == 0, output


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
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
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
    write(directory, "qs.Services.UI", {"Inert": "import QtQuick\nQtObject {}"})
    write(directory, "qs.Widgets", {"Inert": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
import Quickshell
Item {
  id: host
  property ShellScreen screen
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
        cards[name] = f'''import QtQuick
Item {{
  readonly property string cardKind: "{card_id}"
  {weather_size}
}}'''
    write(directory, "qs.Modules.Cards", cards)
    (directory / "tst_control_center.qml").write_text(
        (ROOT / "Tests/Qml/ControlCenterPanelWarningsHarness.qml").read_text()
    )


def behavior(directory):
    stage_behavior(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_control_center.qml"),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=helper("brightness-panel-warnings.test.py").isolated_environment(directory),
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    if args.mode == "lint-harness":
        stage_behavior(args.artifacts)
        raise SystemExit(
            check_harness(args.artifacts, args.artifacts / "tst_control_center.qml")
        )
    {"lint": lint, "behavior": behavior}[args.mode](args.artifacts)


if __name__ == "__main__":
    main()
