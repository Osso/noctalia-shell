#!/usr/bin/env python3
"""Bounded production grouped-taskbar lint and offscreen Niri/QtTest behavior.

Production Niri normalization and widget remain real. Desktop commands, icons,
settings, popup surfaces and compositor facade are inert boundary fixtures.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory):
    helper = load_helper("workspace-runtime")
    helper.stage_runtime(directory)
    (directory / "tst_workspace.qml").unlink()
    write = helper.write_module
    singleton = helper.singleton
    write(directory, "Quickshell.Wayland", {"Toplevel": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "Quickshell.Widgets",
        {
            "IconImage": "import QtQuick\nItem { property string source; property bool smooth; property bool asynchronous }",
        },
    )
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "\n}",
            """
property real marginM: 8
property real marginL: 12
property real radiusS: 4
property real radiusL: 12
property real radiusXXS: 2
property real fontSizeXS: 10
property real fontSizeXXS: 8
property real borderS: 1
property real opacityFull: 1
}\n""",
        )
    )
    colors = directory / "qs/Commons/NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "\n}", '\nproperty color mSurfaceVariant: "#777777"\n}\n'
        )
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "BarWidgetRegistry": singleton(
                'property var widgetMetadata: ({TaskbarGrouped: {hideUnoccupied: false, labelMode: "index", showLabelsOnlyWhenOccupied: false, colorizeIcons: false}})'
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "ThemeIcons": singleton("function iconForAppId(appId) { return appId; }"),
            "TooltipService": singleton(
                "function hide() {}\nfunction show(...args) {}"
            ),
            "PanelService": singleton("""property var events: []
property QtObject popup: QtObject {
  property var contentItem
  function open() { PanelService.events = PanelService.events.concat(["open"]); }
  function close() { PanelService.events = PanelService.events.concat(["close"]); }
}
function getPopupMenuWindow(screen) { return popup; }"""),
            "BarService": singleton("""property var settingsCalls: []
function getTooltipDirection() { return "bottom"; }
function openWidgetSettings(screen, section, index, id, settings) {
  settingsCalls = settingsCalls.concat([{screen: screen.name, section: section, index: index, id: id}]);
}"""),
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {
            "NiriService": (ROOT / "Services/Compositor/NiriService.qml").read_text(),
            "CompositorService": """pragma Singleton
import QtQuick
QtObject {
  id: facade
  property ListModel workspaces: ListModel {}
  signal windowListChanged()
  property NiriService backend: NiriService {
    onWorkspaceChanged: {
      facade.workspaces.clear();
      for (let i = 0; i < workspaces.count; i++)
        facade.workspaces.append(workspaces.get(i));
      facade.workspacesChanged();
    }
    onWindowListChanged: facade.windowListChanged()
  }
  function getWindowsForWorkspace(id) { return backend.windows.filter(win => win.workspaceId === id); }
  function switchToWorkspace(workspace) { backend.switchToWorkspace(workspace); }
  function focusWindow(window) { backend.focusWindow(window); }
  function closeWindow(window) { backend.closeWindow(window); }
  function getCleanAppName(appId, title) { return appId; }
}""",
        },
    )
    popup = directory / "qs/Widgets/NPopupContextMenu.qml"
    popup.write_text("""import QtQuick
Item {
  property var model: []
  property real itemHeight: 24
  implicitWidth: 180
  implicitHeight: model.length * itemHeight
  signal triggered(string action)
  function openAtItem(anchor, x, y) {}
}
""")
    write(
        directory,
        "qs.Modules.Bar.Widgets",
        {
            "TaskbarGrouped": (
                ROOT / "Modules/Bar/Widgets/TaskbarGrouped.qml"
            ).read_text(),
        },
    )
    (directory / "tst_taskbar_grouped.qml").write_text(
        (ROOT / "Tests/Qml/TaskbarGroupedHarness.qml").read_text()
    )


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    if original is not None:
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert (
            hashlib.sha256(backup.read_bytes()).digest()
            == hashlib.sha256(original).digest()
        )
    stage_runtime(directory)
    environment = load_helper("media-mini-warnings").isolate_environment(directory)
    for key in ("NIRI_SOCKET", "HYPRLAND_INSTANCE_SIGNATURE", "SWAYSOCK"):
        environment.pop(key, None)
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
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, (
            f"grouped taskbar runtime exit {result.returncode}"
        )
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert (settings.read_bytes() if settings.exists() else None) == original, (
            "real settings changed"
        )


def run_lint(directory):
    load_helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs/Modules/Bar/Widgets/TaskbarGrouped.qml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in warnings
    )
    print("TASKBAR_GROUPED_LINT_COUNTS", dict(counts))
    assert not counts, f"grouped taskbar warnings remain: {dict(counts)}"
    assert result.returncode == 0


def lint_harness(directory):
    stage_runtime(directory)
    return check_harness(directory, directory / "tst_taskbar_grouped.qml")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-taskbar-grouped-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        (run_lint if args.mode == "lint" else run_behavior)(directory)


if __name__ == "__main__":
    main()
