#!/usr/bin/env python3
"""Standalone BarContentWindow proof; no host settings or desktop access.

Runtime uses synthetic PanelWindow transport and Bar content, preserving the
production bindings. Installed Quickshell metadata remains real for source lint.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/MainScreen/BarContentWindow.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load_helper("bar_content_isolation", "grid-list-warnings.test.py")
fixtures = load_helper("bar_content_fixtures", "about-tab-warnings.test.py")


def stage_runtime(directory, mutation):
    write, singleton = fixtures.write_module, fixtures.singleton
    write(
        directory,
        "Quickshell",
        {
            "WindowAnchors": "import QtQuick\nQtObject { property bool top; property bool bottom; property bool left; property bool right }",
            "WindowMargins": "import QtQuick\nQtObject { property real top; property real bottom; property real left; property real right }",
            "PanelWindow": """import QtQuick
import Quickshell
QtObject {
  id: window
  default property alias children: content.data
  property QtObject screen
  property color color
  property real implicitWidth
  property real implicitHeight
  property WindowAnchors anchors: WindowAnchors {}
  property WindowMargins margins: WindowMargins {}
  property Item contentItem: Item {
    id: content
    width: window.implicitWidth
    height: window.implicitHeight
  }
}
""",
        },
    )
    write(
        directory,
        "Quickshell.Wayland",
        {
            "WlrLayershell": singleton(
                "property string namespace\nproperty int layer\nproperty int exclusionMode"
            ),
            "WlrLayer": "import QtQuick\nQtObject { enum Layer { Top } }",
            "ExclusionMode": "import QtQuick\nQtObject { enum Mode { Ignore } }",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                """component BarSettings: QtObject {
  property string position: "top"
  property bool floating: false
  property real marginHorizontal: 1.5
  property real marginVertical: 0.75
}
component SettingsData: QtObject {
  property BarSettings bar: BarSettings {}
}
property SettingsData data: SettingsData {}"""
            ),
            "Style": singleton(
                "property real marginXL: 12\nproperty real barHeight: 40"
            ),
            "NColor": singleton('property color transparent: "transparent"'),
            "Logger": singleton(
                "property var events: []\nfunction d(...args) { events = events.concat([args]); }"
            ),
        },
    )
    write(
        directory,
        "qs.Modules.Bar",
        {
            "Bar": 'import QtQuick\nItem { objectName: "fixtureBar"; property QtObject screen }'
        },
    )
    write(directory, "qs.Services.UI", {"Fixture": "import QtQuick\nQtObject {}"})
    source = (ROOT / TARGET).read_text()
    # Only layer-shell transport is replaced; namespace expression stays real.
    source = source.replace(
        "WlrLayershell.namespace:", "property string fixtureNamespace:"
    )
    source = source.replace("WlrLayershell.layer:", "property int fixtureLayer:")
    source = source.replace(
        "WlrLayershell.exclusionMode:", "property int fixtureExclusionMode:"
    )
    if mutation == "routing":
        source = source.replace("screen: barWindow.screen", "screen: null")
    elif mutation == "rotation":
        source = source.replace(
            'barPosition === "left" || barPosition === "right"', "false"
        )
    elif mutation == "margins":
        source = source.replace(
            "Settings.data.bar.marginHorizontal * Style.marginXL", "0"
        )
    write(directory, "qs.Modules.MainScreen", {"BarContentWindow": source})
    shutil.copyfile(
        ROOT / "Tests/Qml/BarContentWindowWarningsHarness.qml",
        directory / "tst_bar_content.qml",
    )


def lint_harness(directory, environment, inject_warning=False):
    stage_runtime(directory, None)
    harness = directory / "tst_bar_content.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: testCase",
                "id: testCase\n  property int injectedWarning: testCase.missingLintProbe",
                1,
            )
        )
    code, output = isolation.run_audited(
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
        "bar-content-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("BAR_CONTENT_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert code != 0, "injected warning accepted"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        code = lint_harness(staged, isolation.isolated_environment(staged), injected)
        assert (code != 0) if injected else (code == 0), code
    print("BAR_CONTENT_HARNESS_WARNING_REJECTED")


def execute(args, directory, environment):
    if args.mode == "lint":
        load_helper("bar_content_lint", "media-mini-warnings.test.py").stage_modules(
            directory
        )
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
    else:
        stage_runtime(directory, args.mutation)
        command = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_bar_content.qml"),
            "-import",
            str(directory),
        ]
    code, output = isolation.run_audited(
        directory, environment, command, "bar-content-" + args.mode
    )
    if args.mode == "lint":
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print("BAR_CONTENT_LINT_COUNTS", dict(counts), "EXIT", code)
        assert counts == {"uncreatable-type": 1, "missing-property": 7}, counts
        missing_margins = re.findall(r'Could not find property "([^"]+)"', output)
        missing_screen = re.findall(
            r'Member "([^"]+)" not found on type "QuickshellScreenInfo"', output
        )
        assert sorted(missing_margins) == ["bottom", "left", "right", "top"], (
            missing_margins
        )
        assert sorted(missing_screen) == ["height", "name", "width"], missing_screen
        assert code == 0, code
    else:
        assert code == 0, f"runtime exit {code}"
        assert "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "runtime", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--mutation", choices=("routing", "rotation", "margins"))
    args = parser.parse_args()
    if args.mutation and args.mode != "runtime":
        parser.error("--mutation requires runtime")
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-content-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        else:
            environment = isolation.isolated_environment(directory)
            if args.mode == "lint-harness":
                raise SystemExit(
                    lint_harness(directory, environment, args.inject_warning)
                )
            execute(args, directory, environment)


if __name__ == "__main__":
    main()
