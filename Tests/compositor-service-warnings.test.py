#!/usr/bin/env python3
"""Bounded compositor facade lint and offscreen event/lifecycle characterization.

Production facade, Loader, connections and timers remain real. Backend commands,
ShellState and session dispatch are inert fixtures; no Quickshell process starts.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/Compositor/CompositorService.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--json",
            "-",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    (directory / "lint.json").write_text(result.stdout)
    print(result.stderr, end="")
    warnings = json.loads(result.stdout)["files"][0]["warnings"]
    counts = Counter(w["id"] for w in warnings if w["type"] == "warning")
    for warning in warnings:
        print(warning["line"], warning["id"], warning["message"])
    print("COMPOSITOR_SERVICE_JSON_LINT", dict(counts))
    assert result.returncode == 0, result.returncode
    # Qt's text reporter deduplicates diagnostics; JSON exposes all locations.
    text = subprocess.run(
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
    output = text.stdout + text.stderr
    (directory / "lint-text.log").write_text(output)
    print(output, end="")
    text_counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("COMPOSITOR_SERVICE_TEXT_LINT", dict(text_counts))
    assert text.returncode == 0, text.returncode
    # Concrete backend methods are absent from their shared Item metadata.
    assert text_counts == {"missing-property": 7}, dict(text_counts)
    assert counts == {"missing-property": 19}, dict(counts)


def stage_runtime(directory, mutation):
    workspace = helper("workspace-runtime")
    write = workspace.write_module
    singleton = workspace.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem {}",
            "Quickshell": singleton("""property var environment: ({NIRI_SOCKET: "fixture"})
property var commands: []
function env(name) { return environment[name] || ""; }
function execDetached(argv) { commands = commands.concat([argv]); }"""),
        },
    )
    write(directory, "Quickshell.Io", {"Fixture": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Commons",
        {
            "Logger": singleton("""function i(...args) {}
function d(...args) {}
function w(...args) {}
function e(...args) { console.error(...args); }"""),
            "ShellState": singleton("""property bool isLoaded: false
property var display: ({})
property int writes: 0
function getDisplay() { return display; }
function setDisplay(value) { display = value; writes++; }"""),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("""component LockScreen: QtObject {
  property bool active: false
  property var item: null
}
property LockScreen lockScreen: LockScreen {}"""),
        },
    )
    backend = """import QtQuick
import Fixture
Item {
  id: backend
  property ListModel workspaces: ListModel {}
  property var windows: []
  property int focusedWindowIndex: -1
  property string kind: "KIND"
  property bool initialized: false
  signal workspaceChanged()
  signal activeWindowChanged()
  signal windowListChanged()
  function initialize() {
    workspaces.append({id: 7, isFocused: true, isActive: true});
    workspaceChanged();
    windows = [{id: 42, title: "Startup\\nwindow", workspaceId: 7}];
    focusedWindowIndex = 0;
    windowListChanged();
    activeWindowChanged();
    initialized = true;
  }
  function focusWindow(window) { FixtureBackend.actions = FixtureBackend.actions.concat([[kind, "focus", window.id]]); }
  function closeWindow(window) { FixtureBackend.actions = FixtureBackend.actions.concat([[kind, "close", window.id]]); }
  function switchToWorkspace(workspace) { FixtureBackend.actions = FixtureBackend.actions.concat([[kind, "workspace", workspace.id]]); }
  function logout() { FixtureBackend.actions = FixtureBackend.actions.concat([[kind, "logout"]]); }
  Component.onCompleted: FixtureBackend.live++
  Component.onDestruction: FixtureBackend.live--
}"""
    write(
        directory,
        "Fixture",
        {
            "FixtureBackend": singleton(
                "property int live: 0\nproperty var actions: []"
            ),
        },
    )
    source = (ROOT / TARGET).read_text()
    if mutation == "disconnect":
        source, count = re.subn(r"(?:root\.)?setupBackendConnections\(\);", "", source)
        assert count == 1
    elif mutation == "cache":
        source, count = re.subn(
            r"(?:root\.)?loadDisplayScalesFromState\(\);", "", source
        )
        assert count == 2
    elif mutation == "timer":
        prefix, timer = source.rsplit("  Timer {", 1)
        timer, count = re.subn(r"(?:root\.)?suspend\(\);", "", timer)
        assert count == 3
        source = prefix + "  Timer {" + timer
    write(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": source,
            **{
                name + "Service": backend.replace("KIND", name)
                for name in ("Niri", "Hyprland", "Sway", "Mango")
            },
        },
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/CompositorServiceHarness.qml", directory / "tst_service.qml"
    )


def runtime(directory, mutation):
    stage_runtime(directory, mutation)
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and k
        not in (
            "HOME",
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
        )
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
    )
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
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, result.returncode
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--mutation", choices=("disconnect", "cache", "timer"))
    args = parser.parse_args()
    assert args.mode == "runtime" or args.mutation is None
    directory = args.artifacts
    directory.mkdir(mode=0o700)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    try:
        if args.mode == "lint":
            lint(directory)
        else:
            runtime(directory, args.mutation)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest, (
            "backup changed"
        )
        print("SETTINGS_SHA256", digest)


if __name__ == "__main__":
    main()
