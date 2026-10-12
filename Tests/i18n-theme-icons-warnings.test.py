#!/usr/bin/env python3
"""Bounded production-singleton lint and private, inert-I/O QtTest."""

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path
import shutil
import subprocess
import tempfile

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
        [
            "/usr/lib/qt6/bin/qmllint",
            "--json",
            "-",
            "--max-warnings",
            "0",
            "-I",
            str(directory),
        ]
        + [str(directory / "qs" / target) for target in TARGETS],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=ROOT,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    files = json.loads(result.stdout)["files"]
    assert len(files) == len(TARGETS), files
    for target, report in zip(TARGETS, files):
        assert report["filename"] == str(directory / "qs" / target), report
        counts = Counter(warning["id"] for warning in report["warnings"])
        print(f"{target}: {dict(counts)}")
        assert not counts, counts
    assert result.returncode == 0, result.returncode
    print("Strict zero-warning lint PASS.")


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
    isolation = helper("grid-list-warnings")
    code, output = isolation.run_audited(
        directory,
        isolation.isolated_environment(directory),
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_i18n_icons.qml"),
            "-import",
            str(directory),
        ],
        "i18n-icons-runtime",
    )
    assert code == 0 and "0 failed" in output, (code, output)
    assert "QWARN" not in output and "FAIL!" not in output, output


def lint_harness(directory, inject_warning=False):
    stage_runtime(directory)
    harness = directory / "tst_i18n_icons.qml"
    if inject_warning:
        source = harness.read_text()
        harness.write_text(
            source.replace(
                "id: testCase",
                "id: testCase\n    property int injectedWarning: testCase.missingLintProbe",
                1,
            )
        )
    isolation = helper("grid-list-warnings")
    code, output = isolation.run_audited(
        directory,
        isolation.isolated_environment(directory),
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
        "i18n-icons-harness-lint",
    )
    reports = json.loads(output)["files"]
    assert len(reports) == 1 and reports[0]["filename"] == str(harness), reports
    counts = Counter(
        diagnostic["id"]
        for diagnostic in reports[0]["warnings"]
        if diagnostic["type"] == "warning"
    )
    total = sum(counts.values())
    print("HARNESS_LINT_COUNTS", dict(counts), "TOTAL", total, "EXIT", code)
    if inject_warning:
        assert counts["missing-property"] > 0, "injected warning not diagnosed"
    return int(code != 0 or total != 0 or not reports[0]["success"])


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        code = lint_harness(staged, injected)
        assert code == int(injected), (name, code)
    print("I18N_ICONS_HARNESS_WARNING_REJECTED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("lint", "runtime", "lint-harness", "lint-harness-regression"),
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-i18n-icons-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if arguments.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        elif arguments.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        else:
            globals()[arguments.mode](directory)
