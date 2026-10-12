#!/usr/bin/env python3
"""Scoped color-picker lint and real-control offscreen lifecycle proof."""

import argparse
from collections import Counter
import json
import sys
import importlib.util
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load("grid-list-warnings")
config_guard = load("simple-widgets-warnings")


def run_lint(directory, environment):
    load("media-mini-warnings").stage_modules(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs/Widgets/NColorPickerDialog.qml"),
        ],
        "color-picker-lint",
    )
    counts = Counter(re.findall(r"^Warning:.*?\[([^]]+)\]", output, re.M | re.S))
    print("COLOR_PICKER_LINT_COUNTS", dict(counts))
    assert not counts, f"color-picker diagnostics remain: {dict(counts)}"
    assert code == 0, f"qmllint exit {code}"


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


def run_harness_lint(directory, environment, inject_warning=False):
    stage_runtime(directory)
    harness = directory / "tst_color_picker.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: scene",
                "id: scene\n  property int injectedWarning: scene.missingLintProbe",
                1,
            )
        )
    code, output = isolation.run_audited(
        directory,
        environment,
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
        "color-picker-harness-lint",
    )
    diagnostics = json.loads(output)
    counts = Counter(
        warning["id"]
        for file in diagnostics["files"]
        for warning in file["warnings"]
        if warning["type"] == "warning"
    )
    warnings = sum(counts.values())
    print(
        "COLOR_PICKER_HARNESS_LINT_COUNTS",
        dict(counts),
        "WARNINGS",
        warnings,
        "EXIT",
        code,
    )
    if inject_warning:
        assert counts["missing-property"] > 0, "injected semantic warning not diagnosed"
        assert code != 0, "injected warning accepted"
    assert not warnings or code != 0, "qmllint accepted harness warnings"
    return code


def run_runtime(directory, environment):
    stage_runtime(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_color_picker.qml"),
            "-import",
            str(directory),
        ],
        "color-picker-runtime",
    )
    assert code == 0, f"offscreen color-picker exit {code}"
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-color-picker-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        sys.addaudithook(config_guard.deny_real_config)
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint-harness":
            raise SystemExit(
                run_harness_lint(directory, environment, args.inject_warning)
            )
        (run_lint if args.mode == "lint" else run_runtime)(directory, environment)


if __name__ == "__main__":
    main()
