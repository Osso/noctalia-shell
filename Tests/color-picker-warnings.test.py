#!/usr/bin/env python3
"""Scoped color-picker lint and real-control offscreen lifecycle proof."""

import argparse
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from qml_fixture_lint import check_harness

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
            str(directory / "qs/Widgets/NColorPickerDialog.qml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(re.findall(r"^Warning:.*?\[([^]]+)\]", output, re.M | re.S))
    print("COLOR_PICKER_LINT_COUNTS", dict(counts))
    assert not counts, f"color-picker diagnostics remain: {dict(counts)}"
    assert result.returncode == 0, f"qmllint exit {result.returncode}"


def stage_runtime(directory):
    load("simple-widgets-warnings").stage_runtime(directory)
    (directory / "tst_simple_widgets.qml").unlink()
    widgets = directory / "qs/Widgets"
    for name in (
        "NColorPickerDialog",
        "NColorSlider",
        "NCollapsible",
        "NScrollView",
        "NBox",
        "NTextInput",
        "NButton",
        "NDivider",
    ):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
        with (widgets / "qmldir").open("a") as file:
            file.write(f"{name} 1.0 {name}.qml\n")
    commons = directory / "qs/Commons"
    for name, properties in {
        "Style": "property real marginL: 12\nproperty real marginXL: 16\nproperty real marginXS: 2\nproperty real radiusM: 8\nproperty real radiusXXS: 1\nproperty real fontSizeXL: 18\nproperty real fontSizeXXL: 20\nproperty real barHeight: 32\nproperty int fontWeightRegular: 400",
        "NColor": 'property color mSecondary: "#fedcba"\nproperty color mOnSecondary: "#101010"\nproperty color mTertiary: "#aabbcc"\nproperty color mError: "#ff0000"\nproperty color white: "#ffffff"',
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
    helpers = directory / "qs/Helpers"
    helpers.mkdir()
    shutil.copyfile(ROOT / "Helpers/ColorList.js", helpers / "ColorList.js")
    shutil.copytree(ROOT / "Shaders/qsb", directory / "qs/Shaders/qsb")
    shutil.copyfile(
        ROOT / "Tests/Qml/ColorPickerWarningsHarness.qml",
        directory / "tst_color_picker.qml",
    )


def run_harness_lint(directory):
    stage_runtime(directory)
    assert check_harness(directory, directory / "tst_color_picker.qml") == 0


def run_runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    digest = hashlib.sha256(original).digest()
    assert hashlib.sha256(backup.read_bytes()).digest() == digest
    stage_runtime(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_color_picker.qml"),
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
        assert result.returncode == 0, (
            f"offscreen color-picker exit {result.returncode}"
        )
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-color-picker-") as temporary:
        modes = {
            "lint": run_lint,
            "lint-harness": run_harness_lint,
            "runtime": run_runtime,
        }
        modes[args.mode](Path(temporary))


if __name__ == "__main__":
    main()
