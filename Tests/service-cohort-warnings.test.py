#!/usr/bin/env python3
"""Four-service warning slice: real QML, inert desktop/I/O boundaries."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERVICES = [Path("Services/Keyboard/LockKeysService.qml")] + [
    Path(f"Services/Compositor/{name}Service.qml")
    for name in ("Niri", "Sway", "Hyprland")
]


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_helper("media-mini-warnings").stage_modules(directory)
    failures = []
    for service in SERVICES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / service),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        counts = Counter(
            (re.findall(r"\[([^]]+)\]", line) or ["block-scope-var"])[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print(service, "LINT_COUNTS", dict(counts))
        if counts or result.returncode:
            failures.append((str(service), dict(counts), result.returncode))
    assert not failures, failures


def stage_runtime(directory):
    helper = load_helper("workspace-runtime")
    write = helper.write_module
    singleton = helper.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem {}",
            "Quickshell": singleton(
                'function env(name) { return "fixture.sock"; }\nfunction execDetached(argv) {}'
            ),
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton("""property var files: ({})
property var writes: []
property var reloads: []
property int liveSockets: 0"""),
            "Socket": """import QtQuick
QtObject {
  id: socket
  property string path
  property bool connected: false
  property QtObject parser
  function write(value) {
    FixtureIo.writes = FixtureIo.writes.concat([{path: socket.path, value: value, connected: socket.connected}]);
  }
  function flush() {}
  Component.onCompleted: FixtureIo.liveSockets++
  Component.onDestruction: FixtureIo.liveSockets--
}""",
            "SplitParser": "import QtQuick\nQtObject { signal read(string line) }",
            "Process": """import QtQuick
QtObject {
  property bool running: false
  property var command: []
  property QtObject stdout
  signal exited(int exitCode)
}""",
            "FileView": """import QtQuick
QtObject {
  id: file
  property string path
  property bool printErrors: false
  signal loaded()
  function text() { return FixtureIo.files[file.path] || "0"; }
  function reload() {
    FixtureIo.reloads = FixtureIo.reloads.concat([file.path]);
    Qt.callLater(function() { file.loaded(); });
  }
}""",
        },
    )
    write(
        directory,
        "Qt.labs.folderlistmodel",
        {
            "FolderListModel": """import QtQuick
QtObject {
  enum Status { Null, Ready }
  property url folder
  property bool showDirs
  property bool showFiles
  property bool showDotAndDotDot
  property int status: FolderListModel.Null
  property var entries: []
  readonly property int count: entries.length
  function get(index, role) { return entries[index]; }
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Logger": singleton("""function i(...args) {}
function d(...args) {}
function e(...args) { console.error(...args); }"""),
            "Settings": singleton(
                'property var data: ({bar: {floating: true, outerCorners: true, position: "top"}})'
            ),
            "Style": singleton("property int barHeight: 40"),
        },
    )
    write(
        directory,
        "qs.Services.Keyboard",
        {
            "LockKeysService": (ROOT / SERVICES[0]).read_text(),
            "KeyboardLayoutService": singleton(
                'property string currentLayout: ""\nfunction setCurrentLayout(name) { currentLayout = name; }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {
            **{p.stem: (ROOT / p).read_text() for p in SERVICES[1:]},
            "CompositorService": singleton("""property var scales: ({})
function onDisplayScalesUpdated(value) { scales = value; }
function getDisplayInfo(name) { return scales[name]; }"""),
        },
    )
    write(
        directory,
        "Fixture",
        {
            "EventModel": "import QtQuick\nQtObject { property var values: [] }",
        },
    )
    for uri, name, extra in [
        ("Quickshell.I3", "I3", "function dispatch(command) {}"),
        (
            "Quickshell.Hyprland",
            "Hyprland",
            "property EventModel toplevels: EventModel {}\nfunction refreshToplevels() {}\nfunction dispatch(command) {}",
        ),
        (
            "Quickshell.Wayland",
            "ToplevelManager",
            "property EventModel toplevels: EventModel {}\nsignal activeToplevelChanged()",
        ),
    ]:
        write(
            directory,
            uri,
            {
                name: "pragma Singleton\nimport QtQuick\nimport Fixture\nQtObject {\n"
                + (
                    "property EventModel workspaces: EventModel {}\nsignal rawEvent(var event)\nfunction refreshWorkspaces() {}\n"
                    if name != "ToplevelManager"
                    else ""
                )
                + extra
                + "\n}"
            },
        )
    shutil.copyfile(
        ROOT / "Tests/Qml/ServiceCohortHarness.qml", directory / "tst_services.qml"
    )


def behavior(directory):
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
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key
        not in (
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "HOME",
            "NIRI_SOCKET",
            "SWAYSOCK",
            "HYPRLAND_INSTANCE_SIGNATURE",
        )
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
                "-import",
                str(directory),
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0 and "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-service-cohort-") as temporary:
        globals()[args.mode](Path(temporary))


if __name__ == "__main__":
    main()
