#!/usr/bin/env python3
"""Bounded actual Taskbar lint and offscreen Niri/ListModel behavior.

Production Taskbar and Niri normalization stay real. Desktop commands, settings,
icons and popup surfaces are inert fixtures; no live shell is launched.
"""

import argparse
import hashlib
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]


def load_helper(name):
    spec = spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory):
    grouped = load_helper("taskbar-grouped-warnings")
    grouped.stage_runtime(directory)
    (directory / "tst_taskbar_grouped.qml").unlink()
    helper = load_helper("workspace-runtime")
    helper.write_module(
        directory,
        "qs.Modules.Bar.Widgets",
        {
            "Taskbar": (ROOT / "Modules/Bar/Widgets/Taskbar.qml").read_text(),
        },
    )
    ui = directory / "qs/Services/UI"
    (ui / "BarWidgetRegistry.qml").write_text(
        helper.singleton(
            'property var widgetMetadata: ({Taskbar: {hideMode: "visible", onlySameOutput: true, onlyActiveWorkspaces: true, colorizeIcons: false}})'
        )
    )
    with (ui / "qmldir").open("a") as declarations:
        declarations.write("singleton BarWidgetRegistry 1.0 BarWidgetRegistry.qml\n")
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace("\n}", "\nproperty real marginXXS: 2\n}\n")
    )
    # Copy production model synchronization and active-workspace selection, not
    # an array substitute: delegate role/modelData injection is the boundary.
    source = (ROOT / "Services/Compositor/CompositorService.qml").read_text()
    functions = []
    for name in ("syncWindows", "getActiveWorkspaces"):
        match = re.search(
            r"^  function " + name + r"\([^\n]*\n.*?^  }", source, re.M | re.S
        )
        assert match, name
        functions.append(match.group())
    helper.write_module(
        directory,
        "qs.Services.Compositor",
        {
            "NiriService": (ROOT / "Services/Compositor/NiriService.qml").read_text(),
            "CompositorService": """pragma Singleton
import QtQuick
QtObject {
  id: facade
  property ListModel windows: ListModel {}
  property ListModel workspaces: ListModel {}
  signal windowListChanged()
  signal workspaceChanged()
  property NiriService backend: NiriService {
    onWindowListChanged: facade.syncWindows()
    onWorkspaceChanged: {
      facade.workspaces.clear();
      for (let i = 0; i < workspaces.count; i++)
        facade.workspaces.append(workspaces.get(i));
      facade.workspaceChanged();
    }
  }
  function focusWindow(window) { backend.focusWindow(window); }
  function closeWindow(window) { backend.closeWindow(window); }
  function getCleanAppName(appId, title) { return appId; }
"""
            + "\n".join(functions)
            + "\n}\n",
        },
    )
    (directory / "tst_taskbar.qml").write_text(
        (ROOT / "Tests/Qml/TaskbarHarness.qml").read_text()
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
        assert result.returncode == 0, f"Taskbar runtime exit {result.returncode}"
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
            str(directory / "qs/Modules/Bar/Widgets/Taskbar.qml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("TASKBAR_LINT_COUNTS", dict(counts))
    assert not counts, f"Taskbar warnings remain: {dict(counts)}"
    assert result.returncode == 0


def lint_harness(directory):
    stage_runtime(directory)
    return check_harness(directory, directory / "tst_taskbar.qml")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-taskbar-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        (run_lint if args.mode == "lint" else run_behavior)(directory)


if __name__ == "__main__":
    main()
