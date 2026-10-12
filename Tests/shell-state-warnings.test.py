#!/usr/bin/env python3
"""Bounded ShellState lint and offscreen behavior with inert I/O/services."""

import argparse
from collections import Counter
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Commons/ShellState.qml")


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
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=ROOT,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        (re.findall(r"\[([^]]+)\]", line) or ["unknown"])[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("SHELL_STATE_LINT_COUNTS", dict(counts))
    # Installed Quickshell metadata leaves FileViewAdapter incomplete.
    assert dict(counts) == {"unresolved-type": 1}, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    utilities = helper("workspace-runtime")
    write = utilities.write_module
    singleton = utilities.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nQtObject { default property list<QtObject> children }",
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton(
                "property int writes: 0\nproperty Process process\nproperty FileView file"
            ),
            "Process": """import QtQuick
QtObject {
  id: process
  property var command: []
  property bool running: false
  signal exited(int exitCode)
  function finish(code) { exited(code); running = false; }
  Component.onCompleted: FixtureIo.process = process
}""",
            "JsonAdapter": "import QtQuick\nQtObject {}",
            "FileView": """import QtQuick
QtObject {
  id: file
  property string path: ""
  property bool printErrors: false
  property bool watchChanges: false
  property JsonAdapter adapter
  signal loaded()
  signal loadFailed(int error)
  signal saved()
  signal saveFailed(int error)
  function writeAdapter() { FixtureIo.writes++; }
  Component.onCompleted: FixtureIo.file = file
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "ShellState": (ROOT / TARGET).read_text(),
            "Settings": singleton(
                'property bool directoriesCreated: false\nproperty string cacheDir: "/fixture/"\nproperty var data: ({screen: "DP-1"})'
            ),
            "Logger": singleton(
                "property var errors: []\nfunction d(...args) {}\nfunction e(...args) { errors = errors.concat([args]); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "NotificationService": singleton("property bool doNotDisturb: false"),
        },
    )
    write(
        directory,
        "qs.Services.Power",
        {
            "PowerProfileService": singleton(
                "property bool noctaliaPerformanceMode: false"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "BarService": singleton("property bool isVisible: true"),
            "WallpaperService": singleton(
                'property var currentWallpapers: ({"DP-1": "first.png"})'
            ),
        },
    )
    helpers = directory / "qs/Helpers"
    helpers.mkdir()
    shutil.copyfile(ROOT / "Helpers/QtObj2JS.js", helpers / "QtObj2JS.js")
    shutil.copyfile(
        ROOT / "Tests/Qml/ShellStateHarness.qml", directory / "tst_shellstate.qml"
    )


def runtime(directory):
    stage_runtime(directory)
    environment = {
        "PATH": os.environ["PATH"],
        "LANG": "C.UTF-8",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
    }
    for variable in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
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
        timeout=30,
        cwd=ROOT,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "QWARN" not in output and "FAIL!" not in output, output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-shell-state-") as temporary:
        globals()[arguments.mode](Path(temporary))
