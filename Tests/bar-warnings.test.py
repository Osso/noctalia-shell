#!/usr/bin/env python3
"""Production Bar and BarWidgetLoader, fixture screens/services, offscreen only.

Production lint targets Bar; fixture lint uses the exact runtime modules.
Runtime exercises all six explicit-role delegates in a masked-config sandbox.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Bar.qml")


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def run_lint(directory, environment):
    load_helper("media-mini-warnings").stage_modules(directory)
    code, output = load_helper("grid-list-warnings").run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "bar-production-lint",
    )
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("BAR_LINT_COUNTS", dict(counts))
    assert not counts, f"Bar warnings remain: {dict(counts)}"
    assert code == 0, f"unexpected qmllint exit {code}"


def stage_runtime(directory):
    helper = load_helper("workspace-runtime")
    write = helper.write_module
    singleton = helper.singleton
    write(
        directory,
        "Quickshell",
        {"ShellScreen": "import QtQuick\nQtObject { property string name }"},
    )
    for uri in (
        "Quickshell.Services.UPower",
        "Quickshell.Wayland",
        "qs.Modules.Notification",
        "qs.Widgets",
    ):
        write(directory, uri, {"UnusedFixture": "import QtQuick\nQtObject {}"})
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["bar"].update(
        position="top", monitors=[], floating=False, outerCorners=False
    )
    defaults["bar"]["widgets"] = {
        "left": [{"id": "leftA"}, {"id": "leftB"}],
        "center": [{"id": "centerA"}, {"id": "hidden"}, {"id": "centerB"}],
        "right": [{"id": "rightA"}, {"id": "rightB"}],
    }
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "property real barHeight: 40\nproperty real marginM: 8\nproperty real marginS: 4"
            ),
            "Logger": singleton(
                "function d(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "BarService": singleton("""property var readyScreens: []
property var widgets: ({})
function registerBar(name) {
  if (!readyScreens.includes(name)) readyScreens = readyScreens.concat([name]);
}
function registerWidget(screen, section, widget, index, item) {
  const next = Object.assign({}, widgets);
  next[[screen, section, widget, index].join("|")] = {
    screen: screen, section: section, widget: widget, index: index, item: item,
    initialVisible: item.visible, initialWidth: item.implicitWidth,
    assignedScreen: item.screen, count: item.sectionWidgetsCount
  };
  widgets = next;
}
function unregisterWidget(screen, section, widget, index) {
  const next = Object.assign({}, widgets);
  delete next[[screen, section, widget, index].join("|")];
  widgets = next;
}"""),
            "PanelService": singleton("""property var requestedScreens: []
property bool available: true
property var toggles: []
function getPanel(name, screen) {
  requestedScreens = requestedScreens.concat([screen.name]);
  return available ? this : null;
}
function toggle(anchor, hint) { toggles = toggles.concat([hint || "default"]); }"""),
            "BarWidgetRegistry": """pragma Singleton
import QtQuick
import Quickshell
QtObject {
  property Component fixtureWidget: Component {
    Rectangle {
      property string widgetId: ""
      property string section: ""
      property int sectionWidgetIndex: -1
      property int sectionWidgetsCount: -1
      property ShellScreen screen: null
      property real scaling: 1
      implicitWidth: widgetId.endsWith("B") ? 30 : 20
      implicitHeight: widgetId.endsWith("B") ? 16 : 12
      visible: widgetId !== "hidden"
      opacity: widgetId !== "hidden" ? 1 : 0
    }
  }
  function getWidget(id) { return fixtureWidget; }
  function hasWidget(id) { return true; }
}""",
        },
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "BarWidgetLoader": (
                ROOT / "Modules/Bar/Extras/BarWidgetLoader.qml"
            ).read_text(),
        },
    )
    write(directory, "qs.Modules.Bar", {"Bar": (ROOT / TARGET).read_text()})
    (directory / "tst_bar.qml").write_text(
        (ROOT / "Tests/Qml/BarWarningsHarness.qml").read_text()
    )


def run_behavior(directory, environment):
    stage_runtime(directory)
    code, output = load_helper("grid-list-warnings").run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_bar.qml"),
            "-import",
            str(directory),
        ],
        "bar-behavior",
    )
    assert code == 0, f"Bar behavior exit {code}"
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def lint_harness(directory, environment, inject_warning=False):
    stage_runtime(directory)
    harness = directory / "tst_bar.qml"
    if inject_warning:
        source = harness.read_text()
        harness.write_text(
            source.replace(
                "id: tests",
                "id: tests\n        property int injectedWarning: tests.missingLintProbe",
                1,
            )
        )
    code, output = load_helper("grid-list-warnings").run_audited(
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
        "bar-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("BAR_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
    return code


def lint_harness_regression(directory):
    isolation = load_helper("grid-list-warnings")
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        code = lint_harness(staged, isolation.isolated_environment(staged), injected)
        if injected:
            assert code != 0, "genuine harness warning accepted"
        else:
            assert code == 0, "clean harness lint failed"
    print("BAR_HARNESS_WARNING_REJECTED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-warnings-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = load_helper("grid-list-warnings")
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
            (run_lint if args.mode == "lint" else run_behavior)(directory, environment)


if __name__ == "__main__":
    main()
