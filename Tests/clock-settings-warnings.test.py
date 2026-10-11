#!/usr/bin/env python3
"""Bounded ClockSettings lint and real-control behavior, isolated offscreen.

Production dialog/ClockSettings/widgets; inert settings/bootstrap services.
No desktop connection, real settings writes, or whole-shell proof.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml")
HARNESS = ROOT / "Tests/Qml/ClockSettingsWarningsHarness.qml"


def load_helper(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def write_module(directory, name, sources):
    path = directory.joinpath(*name.split("."))
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for type_name, source in sources.items():
        (path / f"{type_name}.qml").write_text(source)
        prefix = "singleton " if "pragma Singleton" in source else ""
        declarations.append(f"{prefix}{type_name} 1.0 {type_name}.qml\n")
    (path / "qmldir").write_text(f"module {name}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def stage_runtime(directory):
    # Keep production controls and their relative JS imports intact.
    shutil.copytree(ROOT / "Widgets", directory / "qs/Widgets")
    shutil.copytree(ROOT / "Helpers", directory / "qs/Helpers")
    widgets = {path.stem: path.read_text() for path in (ROOT / "Widgets").glob("*.qml")}
    write_module(directory, "qs.Widgets", widgets)
    write_module(
        directory,
        "qs.Modules.Panels.Settings.Bar.WidgetSettings",
        {"ClockSettings": (ROOT / TARGET).read_text()},
    )
    write_module(
        directory,
        "qs.Modules.Panels.Settings.Bar",
        {
            "BarWidgetSettingsDialog": (
                ROOT / "Modules/Panels/Settings/Bar/BarWidgetSettingsDialog.qml"
            ).read_text()
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["general"]["animationDisabled"] = True
    defaults["ui"].update(fontDefault="DejaVu Sans", fontFixed="DejaVu Sans Mono")
    style = (
        (ROOT / "Commons/Style.qml")
        .read_text()
        .replace("import Quickshell\n", "")
        .replace("Singleton {", "QtObject {")
    )
    palette_helper = load_helper(
        "clock_palette", ROOT / "Tests/setup-layout-geometry.test.py"
    )
    palette = dict(
        palette_helper.PALETTE,
        mOnSecondary="#1a151f",
        mOnTertiary="#1a151f",
        mOnError="#1a151f",
    )
    write_module(
        directory,
        "qs.Commons",
        {
            "Style": style,
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "NColor": singleton(
                "\n".join(
                    f'property color {key}: "{value}"' for key, value in palette.items()
                )
            ),
            "I18n": singleton(
                'property var locale: Qt.locale("en_US")\nfunction tr(key) { return key; }'
            ),
            "Time": singleton(
                "readonly property date now: new Date(2023, 11, 25, 14, 30, 45)"
            ),
            "Icons": singleton(
                'property string fontFamily: "DejaVu Sans"\nfunction get(key) { return ""; }'
            ),
        },
    )
    write_module(
        directory,
        "qs.Services.Power",
        {
            "PowerProfileService": singleton(
                "property bool noctaliaPerformanceMode: false"
            )
        },
    )
    write_module(
        directory,
        "qs.Services.System",
        {
            "FontService": singleton(
                'property ListModel availableFonts: ListModel { ListElement { key: "DejaVu Sans"; name: "DejaVu Sans" } }'
            )
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
            "BarWidgetRegistry": singleton(
                'property var widgetSettingsMap: ({Clock: "WidgetSettings/ClockSettings.qml"})\nproperty var widgetMetadata: ({Clock: {usePrimaryColor: true, useCustomFont: false, customFont: "", formatHorizontal: "HH:mm ddd, MMM dd", formatVertical: "HH mm dd MM"}})'
            ),
        },
    )
    for name in ("Quickshell", "Quickshell.Widgets"):
        write_module(directory, name, {"Fixture": "import QtQuick\nQtObject {}"})
    shutil.copyfile(HARNESS, directory / "tst_clock.qml")


def run_lint(directory):
    helper = load_helper(
        "clock_lint_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    helper.stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint.log").write_text(output)
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("CLOCK_SETTINGS_LINT_COUNTS", dict(counts))
    assert not counts and result.returncode == 0, (
        f"ClockSettings lint failed: {dict(counts)}, exit {result.returncode}"
    )


def run_behavior(directory):
    stage_runtime(directory)
    helper = load_helper(
        "clock_isolation", ROOT / "Tests/datetime-tokens-layout-runtime.test.py"
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_clock.qml"),
            "-import",
            str(directory),
        ],
        cwd=directory,
        env=helper.isolate_environment(directory),
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0, (
        f"ClockSettings behavior failed: exit {result.returncode}"
    )
    assert "9 passed, 0 failed" in output, (
        "Expected seven behavior cases plus init/cleanup"
    )
    assert not re.search(
        r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
    ), output
    print("CLOCK_SETTINGS_BEHAVIOR_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(original)
    digest = hashlib.sha256(original).digest()
    assert hashlib.sha256(backup.read_bytes()).digest() == digest
    try:
        if args.mode == "lint":
            run_lint(args.artifacts)
        else:
            run_behavior(args.artifacts)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest, "Backup changed"
    print("Real settings/backup bytes unchanged; bounded runner exited.")


if __name__ == "__main__":
    main()
