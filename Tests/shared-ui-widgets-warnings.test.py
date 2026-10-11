#!/usr/bin/env python3
"""Targeted shared selector/checklist lint and real offscreen interaction proof."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("NReorderCheckboxes", "NSearchableComboBox", "NComboBox")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_behavior(directory):
    load("simple-widgets-warnings").stage_runtime(directory)
    widgets = directory / "qs/Widgets"
    for name in (*NAMES, "NListView", "NTextInput"):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
        with (widgets / "qmldir").open("a") as file:
            file.write(f"{name} 1.0 {name}.qml\n")
    helpers = directory / "qs/Helpers"
    helpers.mkdir()
    shutil.copyfile(ROOT / "Helpers/FuzzySort.js", helpers / "FuzzySort.js")
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {",
            "QtObject {\nproperty real marginL: 12\nproperty real radiusM: 8\nproperty real fontSizeXXS: 6\nproperty int fontWeightRegular: 400",
        )
    )
    colors = directory / "qs/Commons/NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "QtObject {",
            'QtObject {\nproperty color mSecondary: "#fedcba"\nproperty color mError: "#ff0000"',
        )
    )
    commons = directory / "qs/Commons"
    (commons / "I18n.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject { function tr(key) { return key; } }\n"
    )
    with (commons / "qmldir").open("a") as file:
        file.write("singleton I18n 1.0 I18n.qml\n")
    (directory / "tst_simple_widgets.qml").unlink()
    shutil.copyfile(
        ROOT / "Tests/Qml/SharedUiWidgetsWarningsHarness.qml",
        directory / "tst_shared_ui.qml",
    )


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_behavior(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
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
        assert result.returncode == 0, f"behavior exit {result.returncode}"
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"


def run_lint(directory):
    load("media-mini-warnings").stage_modules(directory)
    for name in NAMES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / f"qs/Widgets/{name}.qml"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
        print(name, "LINT_COUNTS", json.dumps(dict(counts), sort_keys=True))
        # Cross-component IDs remain intentionally unbound; never blanket Bound.
        actionable = [
            block
            for block in output.split("Warning:")[1:]
            if "pragma ComponentBehavior: Bound" not in block
        ]
        assert not actionable, f"{name}: same-component/role diagnostics remain"
        assert result.returncode == 0, f"{name}: lint exit {result.returncode}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-shared-ui-proof-") as temporary:
        directory = Path(temporary)
        (run_lint if args.mode == "lint" else run_behavior)(directory)


if __name__ == "__main__":
    main()
