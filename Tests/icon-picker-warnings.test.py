#!/usr/bin/env python3
"""Targeted icon-picker lint and production controls in an isolated offscreen scene."""

import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lint(directory):
    load("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs/Widgets/NIconPicker.qml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("ICON_PICKER_LINT_COUNTS", dict(counts))
    assert not counts, f"icon-picker diagnostics remain: {dict(counts)}"
    assert result.returncode == 0, f"qmllint exit {result.returncode}"


def stage_runtime(directory):
    # Reuse inert service fixtures, not their settings-reading test entry point.
    load("simple-widgets-warnings").stage_runtime(directory)
    (directory / "tst_simple_widgets.qml").unlink()
    widgets = directory / "qs/Widgets"
    for name in ("NIconPicker", "NGridView", "NTextInput", "NButton", "NDivider"):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
        with (widgets / "qmldir").open("a") as file:
            file.write(f"{name} 1.0 {name}.qml\n")
    commons = directory / "qs/Commons"
    for name, properties in {
        "Style": "property real marginL: 12\nproperty real marginXL: 16\nproperty real marginXS: 2\nproperty real radiusM: 8\nproperty int fontWeightRegular: 400",
        "NColor": 'property color mSecondary: "#fedcba"\nproperty color mError: "#ff0000"',
        "Icons": 'property var icons: ({ "alpha": "a", "beta": "b", "beta-outline": "c", "gamma": "d" })',
    }.items():
        path = commons / f"{name}.qml"
        path.write_text(
            path.read_text().replace("QtObject {", "QtObject {\n" + properties)
        )
    (commons / "I18n.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject { function tr(key) { return key; } }\n"
    )
    with (commons / "qmldir").open("a") as file:
        file.write("singleton I18n 1.0 I18n.qml\n")
    shutil.copyfile(
        ROOT / "Tests/Qml/IconPickerWarningsHarness.qml",
        directory / "tst_icon_picker.qml",
    )


def run_runtime(directory):
    stage_runtime(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_icon_picker.qml"),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=load("media-mini-warnings").isolate_environment(directory),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, f"offscreen icon-picker exit {result.returncode}"
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-icon-picker-") as temporary:
        (run_lint if args.mode == "lint" else run_runtime)(Path(temporary))


if __name__ == "__main__":
    main()
