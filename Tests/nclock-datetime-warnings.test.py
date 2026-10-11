#!/usr/bin/env python3
"""Bounded clock/token lint and production widgets offscreen; no real settings access."""

import argparse
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tests"))


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lint(directory):
    helper = load_helper("clock_lint", "media-mini-warnings.test.py")
    helper.stage_modules(directory)
    for name in ("NClock", "NDateTimeTokens"):
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs/Widgets" / f"{name}.qml"),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=ROOT,
        )
        output = result.stdout + result.stderr
        (directory / f"{name}.lint.log").write_text(output)
        print(output, end="")
        warnings = re.findall(r"^Warning:.*$", output, re.M)
        print(name, "warnings:", len(warnings), "exit:", result.returncode)
        assert not warnings and result.returncode == 0, output


def run_behavior(directory):
    helper = load_helper("clock_runtime", "datetime-tokens-layout-runtime.test.py")
    helper.stage_harness(directory)
    widgets = directory / "qs/Widgets"
    shutil.copyfile(ROOT / "Widgets/NClock.qml", widgets / "NClock.qml")
    with (widgets / "qmldir").open("a") as stream:
        stream.write("NClock 1.0 NClock.qml\n")
    shutil.copytree(ROOT / "Helpers", directory / "qs/Helpers")
    commons = directory / "qs/Commons"
    # Fixture sizes needed by the production clock, absent from the token fixture.
    (commons / "Style.qml").write_text(
        (commons / "Style.qml")
        .read_text()
        .replace(
            "QtObject {",
            "QtObject {\nproperty real fontSizeXXS: 8\nproperty real fontSizeXXXL: 32\nproperty real marginXXS: 2",
            1,
        )
    )
    helper.write_singleton(
        commons,
        "Settings",
        'property var data: ({location: {use12hourFormat: false}, ui: {fontDefault: "DejaVu Sans", fontFixed: "DejaVu Sans Mono", fontDefaultScale: 1, fontFixedScale: 1}})',
    )
    helper.write_singleton(
        commons,
        "Time",
        """property date now: new Date(2023, 11, 25, 14, 30, 0)
property int consumers: 0
function beginSecondUpdates() { consumers++; }
function endSecondUpdates() { consumers--; }""",
    )
    with (commons / "qmldir").open("a") as stream:
        stream.write("singleton Time 1.0 Time.qml\n")
    quickshell = directory / "Quickshell"
    quickshell.mkdir()
    (quickshell / "Fixture.qml").write_text("import QtQuick\nQtObject {}\n")
    (quickshell / "qmldir").write_text("module Quickshell\nFixture 1.0 Fixture.qml\n")
    shutil.copyfile(
        ROOT / "Tests/Qml/NClockDateTimeWarningsHarness.qml",
        directory / "tst_geometry.qml",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_geometry.qml"),
            "-import",
            str(directory),
        ],
        capture_output=True,
        text=True,
        timeout=45,
        cwd=directory,
        env=helper.isolate_environment(directory),
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0, output
    assert not re.search(
        r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    (run_lint if args.mode == "lint" else run_behavior)(args.artifacts)


if __name__ == "__main__":
    main()
