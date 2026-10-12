#!/usr/bin/env python3
"""Bounded production-singleton lint and private, inert-I/O QtTest."""

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("Commons/I18n.qml", "Commons/ThemeIcons.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        ["/usr/lib/qt6/bin/qmllint", "--max-warnings", "0", "-I", str(directory)]
        + [str(directory / "qs" / target) for target in TARGETS],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=ROOT,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    for target in TARGETS:
        count = sum(
            line.startswith("Warning:") and target in line
            for line in output.splitlines()
        )
        print(f"{target}: {count} warnings")
    assert result.returncode == 0, result.returncode
    assert "Warning:" not in output, output


def stage_runtime(directory):
    utilities = helper("workspace-runtime")
    write = utilities.write_module
    singleton = utilities.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nQtObject { default property list<QtObject> children }",
            "Quickshell": singleton("""property string shellDir: "/private-fixture"
property string iconTheme: "day"
function hasThemeIcon(name) { return name === "firefox" || name === "application-x-executable"; }
function iconPath(name, check) { return "/private-icons/" + iconTheme + "/" + name + ".svg"; }"""),
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "Process": """import QtQuick
QtObject {
  property var command: []
  property bool running: false
  property StdioCollector stdout
  signal exited(int exitCode, int exitStatus)
}""",
            "StdioCollector": 'import QtQuick\nQtObject { property string text: "" }',
            "FileView": """import QtQuick
QtObject {
  id: file
  property string path: ""
  property bool watchChanges: false
  property string contents: ""
  property int reloadCount: 0
  signal fileChanged()
  signal loaded()
  signal loadFailed(int error)
  function text() { return file.contents; }
  function reload() { file.reloadCount++; }
  function deliver(value) { file.contents = value; file.loaded(); }
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "I18n": (ROOT / TARGETS[0]).read_text(),
            "ThemeIcons": (ROOT / TARGETS[1]).read_text(),
            "Settings": singleton('property var data: ({general: {language: "it"}})'),
            "Logger": singleton("""property var errors: []
function d(...args) {}
function i(...args) {}
function w(...args) {}
function e(...args) { errors = errors.concat([args]); }"""),
        },
    )
    helpers = directory / "qs/Helpers"
    helpers.mkdir()
    shutil.copyfile(
        ROOT / "Helpers/ThemeIconResolver.js", helpers / "ThemeIconResolver.js"
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/I18nThemeIconsHarness.qml", directory / "tst_i18n_icons.qml"
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
        cwd=directory,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "QWARN" not in output and "FAIL!" not in output, output


def lint_harness(directory):
    stage_runtime(directory)
    return check_harness(directory, directory / "tst_i18n_icons.qml")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime", "lint-harness"))
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-i18n-icons-") as temporary:
        directory = Path(temporary)
        if arguments.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        globals()[arguments.mode](directory)
