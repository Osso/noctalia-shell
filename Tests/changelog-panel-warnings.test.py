#!/usr/bin/env python3
"""Bounded ChangelogPanel proof: offscreen QtTest, inert service and panel host.

Real panel content/layout/Text/Repeaters and stock ScrollView; no network,
settings persistence, canonical Quickshell, native input or whole-shell proof.
"""

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Changelog/ChangelogPanel.qml")


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
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("CHANGELOG_WARNINGS", len(warnings))
    assert not warnings and result.returncode == 0, warnings


def stage_runtime(directory):
    history = helper("notification-history-warnings.test.py")
    history.stage_runtime(directory)
    fixtures = helper("workspace-runtime.test.py")
    write, singleton = fixtures.write_module, fixtures.singleton
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "\n}",
            "\nproperty real fontSizeXL: 18\nproperty real radiusS: 4\nproperty real fontWeightSemiBold: 600\nproperty real fontWeightMedium: 500\n}",
        )
    )
    write(directory, "qs.Services.UI", {"Inert": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Services.Noctalia",
        {
            "UpdateService": singleton("""
property string currentVersion: "4.2"
property string changelogCurrentVersion: "4.2"
property string previousVersion: "4.1"
property var releaseHighlights: []
property string fetchError: ""
property string feedbackUrl: ""
property var seen: []
property var links: []
function markChangelogSeen(version) { seen = seen.concat([version]); }
function openDiscord() { links = links.concat(["discord"]); }
function openFeedbackForm() { links = links.concat(["feedback"]); }
""")
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  id: host
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool panelAnchorHorizontalCenter
  property bool panelAnchorVerticalCenter
  property bool isPanelOpen: false
  property alias contentItem: loader.item
  signal opened()
  signal closed()
  function open() { isPanelOpen = true; opened(); }
  function close() { isPanelOpen = false; closed(); }
  Loader { id: loader; anchors.fill: parent; active: host.isPanelOpen; sourceComponent: host.panelContent }
}"""
        },
    )
    widgets = directory / "qs/Widgets"
    (widgets / "NDivider.qml").write_text(
        "import QtQuick\nRectangle { implicitHeight: 1 }"
    )
    with (widgets / "qmldir").open("a") as declarations:
        declarations.write("NDivider 1.0 NDivider.qml\n")
    (widgets / "NScrollView.qml").write_text("""import QtQuick.Controls
ScrollView {
  property int horizontalPolicy: ScrollBar.AlwaysOff
  property int verticalPolicy: ScrollBar.AsNeeded
  ScrollBar.horizontal.policy: horizontalPolicy
  ScrollBar.vertical.policy: verticalPolicy
}""")
    text = widgets / "NText.qml"
    text.write_text(
        text.read_text().replace(
            "property real pointSize;", "property real pointSize: 12;"
        )
    )
    button = widgets / "NButton.qml"
    button.write_text(
        button.read_text().replace(
            "property string text;", "property string icon; property string text;"
        )
    )
    write(
        directory,
        "qs.Modules.Panels.Changelog",
        {"ChangelogPanel": (ROOT / TARGET).read_text()},
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/ChangelogPanelWarningsHarness.qml",
        directory / "tst_history.qml",
    )


def runtime(directory):
    # Reuse permission-locked settings backup, isolated HOME/XDG and timeout handling.
    history = helper("notification-history-warnings.test.py")
    history.stage_runtime = stage_runtime
    original_locale = os.environ.get("LC_ALL")
    os.environ["LC_ALL"] = "C"
    try:
        history.runtime(directory)
    finally:
        if original_locale is None:
            del os.environ["LC_ALL"]
        else:
            os.environ["LC_ALL"] = original_locale


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-changelog-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
