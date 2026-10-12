#!/usr/bin/env python3
"""Bounded ChangelogPanel proof: offscreen QtTest, inert service and panel host.

Real panel content/layout/Text/Repeaters and stock ScrollView; no network,
settings persistence, canonical Quickshell, native input or whole-shell proof.
"""

import argparse
import importlib.util
import json
import re
import sys
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


def run_isolated(directory, command, label):
    isolation = helper("grid-list-warnings.test.py")
    environment = isolation.isolated_environment(directory)
    environment["LC_ALL"] = "C"
    trace = directory / f"{label}.trace"
    sandbox = [
        "bwrap",
        "--die-with-parent",
        "--unshare-net",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--ro-bind",
        "/etc/fonts",
        "/etc/fonts",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(directory),
        str(directory),
        "--chdir",
        str(directory),
        "--",
    ]
    result = subprocess.run(
        [
            "strace",
            "-f",
            "-qq",
            "-e",
            "trace=%file",
            "-o",
            str(trace),
            *sandbox,
            *command,
        ],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "settings.json" not in trace.read_text(), (
        "SETTINGS_AUDIT_DENIED: child settings access attempted"
    )
    print(
        f"CHILD_SETTINGS_AUDIT: {label} zero settings attempts; host home/config not mounted"
    )
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result


def lint_harness(directory, inject_warning=False):
    stage_runtime(directory)
    harness = directory / "tst_history.qml"
    if inject_warning:
        source = harness.read_text()
        harness.write_text(
            source.replace(
                "id: tests",
                "id: tests\n    property int injectedWarning: tests.missingLintProbe",
                1,
            )
        )
    result = run_isolated(
        directory,
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
        "changelog-harness-lint",
    )
    diagnostics = json.loads(result.stdout)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    failed = not diagnostics["files"] or any(
        not entry["success"]
        or any(warning["type"] in ("warning", "error") for warning in entry["warnings"])
        for entry in diagnostics["files"]
    )
    code = result.returncode or int(failed)
    print("CHANGELOG_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected diagnostic not detected"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        code = lint_harness(staged, injected)
        if injected:
            assert code != 0, "genuine harness diagnostic accepted"
        else:
            assert code == 0, "clean harness lint failed"
    print("CHANGELOG_HARNESS_WARNING_REJECTED")


def runtime(directory):
    stage_runtime(directory)
    result = run_isolated(
        directory,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_history.qml"),
            "-import",
            str(directory),
        ],
        "changelog-runtime",
    )
    assert result.returncode == 0, f"runtime exit {result.returncode}"
    output = result.stdout + result.stderr
    assert "7 passed, 0 failed" in output, output
    assert not re.search(r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError", output), (
        output
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "runtime", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-changelog-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = helper("grid-list-warnings.test.py")
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode == "lint-harness":
            sys.exit(lint_harness(directory, args.inject_warning))
        {
            "lint": lint,
            "runtime": runtime,
            "lint-harness-regression": lint_harness_regression,
        }[args.mode](directory)
