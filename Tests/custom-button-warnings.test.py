#!/usr/bin/env python3
"""Bounded production Control Center button lint/behavior; no command execution."""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDGET = Path("Modules/Panels/ControlCenter/Widgets/CustomButton.qml")


def helper():
    spec = importlib.util.spec_from_file_location(
        "media_fixture", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_module(directory, uri, files):
    target = directory.joinpath(*uri.split("."))
    target.mkdir(parents=True, exist_ok=True)
    declarations = [f"module {uri}\n"]
    for name, source in files.items():
        (target / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml\n")
    (target / "qmldir").write_text("".join(declarations))


def run_lint(directory):
    helper().stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / WIDGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("CUSTOM_BUTTON_WARNINGS", len(warnings))
    # One pre-existing block-scoped var is not an observed hoisting bug.
    assert len(warnings) == 1 and "block scope is hoisted" in warnings[0], output
    assert result.returncode == 0, result.returncode


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
    write_module(
        directory,
        "qs.Modules.Panels.ControlCenter.Widgets",
        {
            "CustomButton": (ROOT / WIDGET).read_text(),
        },
    )
    write_module(
        directory,
        "qs.Commons",
        {"Fixture": "pragma Singleton\nimport QtQuick\nQtObject {}"},
    )
    write_module(directory, "qs.Widgets", {"NIconButtonHot": BUTTON})
    write_module(directory, "Quickshell", {"Quickshell": QUICK, "Driver": DRIVER})
    write_module(directory, "Quickshell.Io", {"Process": PROCESS})
    config = directory / "widget-settings.json"
    config.write_text(
        json.dumps(
            {
                "icon": "base",
                "onClicked": "left",
                "onRightClicked": "right",
                "onMiddleClicked": "middle",
                "generalTooltipText": "Launch",
            }
        )
    )
    harness = HARNESS.replace("SETTINGS_JSON", config.read_text())
    (directory / "tst_custom_button.qml").write_text(harness)
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
            env=helper().isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0 and "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
        errors = [line for line in output.splitlines() if "QCRITICAL" in line]
        assert len(errors) == 3 and all(
            "CustomButton: Failed to parse stateChecksJson:" in line for line in errors
        ), errors
    finally:
        assert settings.read_bytes() == original, "real settings changed"


BUTTON = """import QtQuick
Item {
  implicitWidth: 32
  implicitHeight: 32
  property string icon: ""
  property bool hot: false
  property string tooltipText: ""
  signal clicked()
  signal rightClicked()
  signal middleClicked()
}
"""
QUICK = """pragma Singleton
import QtQuick
QtObject {
  function execDetached(command) { Driver.detached = Driver.detached.concat([command]); }
}
"""
DRIVER = """pragma Singleton
import QtQuick
QtObject {
  property var launches: []
  property var detached: []
  property var active: null
  function finish(code) {
    const process = active;
    active = null;
    process.running = false;
    process.exited(code, 0);
  }
}
"""
PROCESS = """import QtQuick
import Quickshell
QtObject {
  id: process
  property bool running: false
  property var command: []
  signal exited(int exitCode, int exitStatus)
  onRunningChanged: {
    if (running) {
      if (Driver.active !== null)
        throw new Error("Concurrent synthetic state process");
      Driver.active = process;
      Driver.launches = Driver.launches.concat([command.slice()]);
    }
  }
  Component.onDestruction: {
    if (Driver.active === process)
      Driver.active = null;
  }
}
"""
HARNESS = """import QtQuick
import QtTest
import Quickshell
import qs.Modules.Panels.ControlCenter.Widgets
Item {
  id: scene
  Component { id: factory; CustomButton {} }
  TestCase {
    name: "ControlCenterCustomButton"
    when: windowShown
    property var widget
    function init() {
      Driver.launches = [];
      Driver.detached = [];
      widget = createTemporaryObject(factory, scene);
      verify(widget !== null);
      widget.widgetSettings = SETTINGS_JSON;
    }
    function settings(checks, enabled = true, icon = "base") {
      widget.widgetSettings = {icon: icon, enableOnStateLogic: enabled,
        stateChecksJson: JSON.stringify(checks)};
    }
    function button() { return widget.children[0]; }
    function test_settings_clicks_and_missing() {
      compare(widget.onClickedCommand, "left");
      compare(widget.onRightClickedCommand, "right");
      compare(widget.onMiddleClickedCommand, "middle");
      compare(button().tooltipText, "Launch\\nLeft click: left\\nRight click: right\\nMiddle click: middle");
      compare(widget.implicitWidth, 32);
      compare(widget.implicitHeight, 32);
      button().clicked(); button().rightClicked(); button().middleClicked();
      compare(Driver.detached, [["sh", "-c", "left"], ["sh", "-c", "right"], ["sh", "-c", "middle"]]);
      widget.widgetSettings = null;
      compare(widget.onClickedCommand, "left");
      compare(button().icon, "base");
    }
    function test_ordered_checks() {
      settings([null, {}, {command: "fail", icon: "bad"}, {command: "pass", icon: "winner"}]);
      tryCompare(Driver, "launches", [["sh", "-c", "fail"]]);
      Driver.finish(1);
      compare(Driver.launches, [["sh", "-c", "fail"], ["sh", "-c", "pass"]]);
      Driver.finish(0);
      compare(button().hot, true);
      compare(button().icon, "winner");
    }
    function test_all_fail_and_missing_icon() {
      settings([{command: "fail"}]);
      tryCompare(Driver, "launches", [["sh", "-c", "fail"]]);
      Driver.finish(1);
      compare(button().hot, false);
      compare(button().icon, "base");
      settings([{command: "pass"}]);
      tryCompare(Driver, "launches", [["sh", "-c", "fail"], ["sh", "-c", "pass"]]);
      Driver.finish(0);
      compare(button().hot, true);
      compare(button().icon, "base");
    }
    function test_disable_while_running() {
      settings([{command: "old", icon: "old-icon"}]);
      tryCompare(Driver, "launches", [["sh", "-c", "old"]]);
      settings([], false, "disabled");
      Driver.finish(0);
      compare(button().hot, false);
      compare(button().icon, "disabled");
      wait(250);
      compare(Driver.launches.length, 1);
    }
    function test_replace_while_running_data() {
      return [{tag: "before-debounce", delay: 0}, {tag: "after-debounce", delay: 250}];
    }
    function test_replace_while_running(row) {
      settings([{command: "old", icon: "old-icon"}]);
      tryCompare(Driver, "launches", [["sh", "-c", "old"]]);
      settings([{command: "new", icon: "new-icon"}]);
      wait(row.delay);
      compare(Driver.launches.length, 1);
      Driver.finish(0);
      compare(button().hot, false);
      tryCompare(Driver, "launches", [["sh", "-c", "old"], ["sh", "-c", "new"]]);
      Driver.finish(0);
      compare(button().hot, true);
      compare(button().icon, "new-icon");
    }
    function test_debounce_uses_latest_settings() {
      settings([{command: "first"}]);
      settings([{command: "latest", icon: "latest-icon"}]);
      tryCompare(Driver, "launches", [["sh", "-c", "latest"]]);
      Driver.finish(0);
      compare(button().icon, "latest-icon");
    }
    function test_invalid_json_data() {
      return [{tag: "syntax", json: "["}, {tag: "null", json: "null"},
              {tag: "object", json: "{}"}];
    }
    function test_invalid_json(row) {
      widget.widgetSettings = {icon: "invalid", stateChecksJson: row.json, enableOnStateLogic: true};
      compare(widget._parsedStateChecks, []);
      compare(button().hot, false);
      compare(button().icon, "invalid");
      wait(250);
      compare(Driver.launches.length, 0);
    }
  }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-custom-button-") as temporary:
        directory = Path(temporary)
        (run_lint if args.mode == "lint" else run_behavior)(directory)


if __name__ == "__main__":
    main()
