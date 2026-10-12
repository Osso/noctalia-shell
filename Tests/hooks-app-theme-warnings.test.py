#!/usr/bin/env python3
"""Bounded owner lint and inert signal/template QtTest in a masked private HOME."""

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
TARGETS = ("Services/Control/HooksService.qml", "Services/Theming/AppThemeService.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory, shadow):
    utilities = helper("workspace-runtime.test.py")
    write = utilities.write_module

    def singleton(body):
        return utilities.singleton(body).replace(
            "import QtQuick", "import QtQuick\nimport qs.Commons"
        )

    quickshell = {
        "Singleton": "import QtQuick\nQtObject { default property list<QtObject> children }",
        "Quickshell": singleton("""property string shellDir: "/fixture"
property bool rejectCommand: false
function execDetached(argv) {
  if (rejectCommand) throw new Error("fixture spawn rejected");
  Recorder.append(["hook", argv]);
}"""),
    }
    if shadow:
        # Adversarial dynamic scope, not a claimed production Connections API.
        # Unchanged service handlers must still select their lexical singleton.
        quickshell["Connections"] = """import QtQml as Qml
Qml.Connections {
  function executeWallpaperHook(path, screen) { throw new Error("WRONG_OWNER wallpaper"); }
  function executeDarkModeHook(dark) { throw new Error("WRONG_OWNER dark"); }
  function generateFromWallpaper() { throw new Error("WRONG_OWNER wallpaper templates"); }
  function generate() { throw new Error("WRONG_OWNER templates"); }
}"""
    write(directory, "Quickshell", quickshell)
    write(
        directory,
        "qs.Commons",
        {
            "Recorder": singleton("""property var events: []
function append(event) { events = events.concat([event]); }"""),
            "Settings": singleton("property SettingsData data: SettingsData {}"),
            "SettingsData": """import QtQuick
QtObject {
  property ColorSchemes colorSchemes: ColorSchemes {}
  property var hooks: ({enabled: true, wallpaperChange: "wall $1 $2 $1", darkModeChange: "dark $1"})
}""",
            "ColorSchemes": """import QtQuick
QtObject {
  property bool darkMode: false
  property bool useWallpaperColors: false
  property string predefinedScheme: "fixture-day"
}""",
            "Logger": singleton("""property var errors: []
function i(...args) {}
function d(...args) {}
function e(...args) { errors = errors.concat([args]); }"""),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "WallpaperService": singleton("""property string currentWallpaper: "/fixture/a.png"
signal wallpaperChanged(string screenName, string path)
function getWallpaper(screen) {
  Recorder.append(["readWallpaper", screen]);
  return currentWallpaper;
}"""),
        },
    )
    write(
        directory,
        "qs.Services.Control",
        {
            "HooksService": (ROOT / TARGETS[0]).read_text(),
        },
    )
    write(
        directory,
        "qs.Services.Theming",
        {
            "AppThemeService": (ROOT / TARGETS[1]).read_text(),
            "ColorSchemeService": singleton("""property var pending: null
function applyScheme(name) {
  Recorder.append(["applyScheme", name]);
  pending = {name: name, primary: "#123456"};
}
function deliver() {
  const scheme = pending;
  pending = null;
  AppThemeService.generateFromPredefinedScheme(scheme);
}"""),
            "TemplateProcessor": singleton("""function processWallpaperColors(path, mode) {
  Recorder.append(["wallpaperTemplates", path, mode]);
}
function processPredefinedScheme(scheme, mode) {
  Recorder.append(["schemeTemplates", scheme, mode]);
}"""),
        },
    )
    harness = directory / "tst_hooks_app_theme.qml"
    harness.write_text(
        (ROOT / "Tests/Qml/HooksAppThemeWarningsHarness.qml").read_text()
    )
    return harness


def lint_harness(directory, environment, isolation, inject_warning=False):
    harness = stage_runtime(directory, False)
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: testCase",
                "id: testCase\n    property int injectedWarning: testCase.missingLintProbe",
                1,
            )
        )
    command = [
        "/usr/lib/qt6/bin/qmllint",
        "--bare",
        "--max-warnings",
        "0",
        "--json",
        "-",
        "-I",
        str(directory),
        "-I",
        "/usr/lib/qt6/qml",
        str(harness),
    ]
    code, output = isolation.run_child(command, directory, environment)
    (directory / "lint-harness.log").write_text(output)
    reports = json.loads(output)["files"]
    assert len(reports) == 1 and reports[0]["filename"] == str(harness), reports
    counts = Counter(warning["id"] for warning in reports[0]["warnings"])
    print(
        "HOOKS_APP_THEME_HARNESS_LINT",
        dict(counts),
        "TOTAL",
        sum(counts.values()),
        "EXIT",
        code,
        flush=True,
    )
    if inject_warning:
        assert any(
            warning["type"] == "warning"
            and warning["id"] == "missing-property"
            and "missingLintProbe" in warning["message"]
            for warning in reports[0]["warnings"]
        ), reports
        assert code != 0, "injected diagnostic accepted"
    else:
        assert not counts and reports[0]["success"], reports
    return code


def run_sandboxed(mode, directory, isolation):
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for path in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == path and " - tmpfs " in line for line in mounts
        ), path
    environment = isolation.isolated_environment(directory)
    if mode == "lint-harness":
        raise SystemExit(lint_harness(directory, environment, isolation))
    if mode == "lint-harness-regression":
        for name, injected in (("clean", False), ("injected", True)):
            staged = directory / name
            staged.mkdir(mode=0o700)
            staged_environment = isolation.isolated_environment(staged)
            code = lint_harness(staged, staged_environment, isolation, injected)
            assert (code != 0) if injected else (code == 0), code
        print("HOOKS_APP_THEME_HARNESS_WARNING_REJECTED", flush=True)
        return
    if mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "--json",
            "-",
            "--max-warnings",
            "0",
            "-I",
            str(directory),
        ]
        command += [str(directory / "qs" / target) for target in TARGETS]
    else:
        harness = stage_runtime(directory, mode == "owner-probe")
        command = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ]
    code, output = isolation.run_child(command, directory, environment)
    (directory / f"{mode}.log").write_text(output)
    if mode == "lint":
        reports = json.loads(output)["files"]
        assert len(reports) == len(TARGETS), reports
        for target, report in zip(TARGETS, reports):
            assert report["filename"] == str(directory / "qs" / target), report
            counts = Counter(warning["id"] for warning in report["warnings"])
            print(target, dict(counts), "TOTAL", sum(counts.values()), flush=True)
        assert all(
            not report["warnings"] and report["success"] for report in reports
        ), reports
    else:
        assert "7 passed, 0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
    assert code == 0, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=(
            "lint",
            "behavior",
            "owner-probe",
            "lint-harness",
            "lint-harness-regression",
        ),
    )
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    isolation = helper("notifications-hooks-warnings.test.py")
    sys.addaudithook(isolation.audit)
    with (
        patch("os.stat", isolation.guard_metadata(os.stat)),
        patch("os.lstat", isolation.guard_metadata(os.lstat)),
        patch("os.readlink", isolation.guard_metadata(os.readlink)),
    ):
        isolation.prove_denial()
        if args.sandbox:
            run_sandboxed(args.mode, args.sandbox, isolation)
            return
        with tempfile.TemporaryDirectory(
            prefix="noctalia-hooks-app-theme-"
        ) as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            command = [
                "bwrap",
                "--die-with-parent",
                "--unshare-all",
                "--new-session",
                "--ro-bind",
                "/",
                "/",
                "--perms",
                "000",
                "--tmpfs",
                "/home",
                "--tmpfs",
                "/syncthing",
                "--ro-bind",
                str(ROOT),
                str(ROOT),
                "--tmpfs",
                "/tmp",
                "--tmpfs",
                "/run",
                "--bind",
                temporary,
                temporary,
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                temporary,
                "--",
                "/usr/bin/python3",
                str(Path(__file__).absolute()),
                args.mode,
                "--sandbox",
                temporary,
            ]
            code, _ = isolation.run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


if __name__ == "__main__":
    main()
