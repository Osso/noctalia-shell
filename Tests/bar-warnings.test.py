#!/usr/bin/env python3
"""Production Bar and BarWidgetLoader, fixture screens/services, offscreen only.

Static checks target Bar alone. Runtime exercises all six explicit-role delegates;
fixture widgets record registration state without desktop or real settings IO.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Bar.qml")


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def run_lint(directory):
    load_helper("media-mini-warnings").stage_modules(directory)
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
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("BAR_LINT_COUNTS", dict(counts))
    assert counts == {"missing-property": 2}, f"owner warnings remain: {dict(counts)}"
    assert result.returncode == 0, f"unexpected qmllint exit {result.returncode}"


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


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=load_helper("media-mini-warnings").isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"Bar behavior exit {result.returncode}"
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-warnings-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        (run_lint if args.mode == "lint" else run_behavior)(directory)


if __name__ == "__main__":
    main()
