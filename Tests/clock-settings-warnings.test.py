#!/usr/bin/env python3
"""Bounded ClockSettings lint and real-control behavior, isolated offscreen.

Production dialog/ClockSettings/widgets; inert settings/bootstrap services.
No desktop connection, real settings writes, or whole-shell proof.
"""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

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


def lint_staged_harness(directory, harness, marker, inject_warning=False):
    if inject_warning:
        source = harness.read_text()
        assert source.count(marker) == 1, "Injection marker must identify one object"
        owner = marker.removeprefix("id: ")
        harness.write_text(
            source.replace(
                marker,
                marker + f"\n  property int injectedWarning: {owner}.missingLintProbe",
                1,
            )
        )
    command = [
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
    ]
    print("HARNESS_CLI", json.dumps(command), flush=True)
    result = subprocess.run(
        command,
        cwd=directory,
        env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": str(directory)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint-harness.log").write_text(output)
    print(output, end="", flush=True)
    files = json.loads(result.stdout)["files"]
    assert len(files) == 1 and Path(files[0]["filename"]) == harness
    warnings = [
        entry for entry in files[0]["warnings"] if entry["type"] in ("warning", "error")
    ]
    counts = Counter(entry["id"] for entry in warnings)
    print(
        "HARNESS_FILE",
        harness.name,
        "FILE_COUNT",
        len(files),
        "WARNINGS",
        len(warnings),
        "COUNTS",
        dict(counts),
        "EXIT",
        result.returncode,
        flush=True,
    )
    if inject_warning:
        assert counts["missing-property"] > 0 and "missingLintProbe" in output, (
            "Semantic injection not diagnosed"
        )
        assert result.returncode != 0, "Injected warning accepted"
    assert not warnings or result.returncode != 0, "Warnings accepted"
    assert result.returncode != 0 or not warnings, output
    return result.returncode


def run_harness_lint(directory, inject_warning=False):
    stage_runtime(directory)
    return lint_staged_harness(
        directory, directory / "tst_clock.qml", "id: suite", inject_warning
    )


def run_fixture_cli(actions, default_mode=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=tuple(actions),
        **({"nargs": "?", "default": default_mode} if default_mode else {}),
    )
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    isolation = load_helper(
        "fixture_isolation", ROOT / "Tests/audio-notification-settings-warnings.test.py"
    )
    sys.addaudithook(isolation.audit)
    with (
        patch("os.stat", isolation.guard_metadata(os.stat)),
        patch("os.lstat", isolation.guard_metadata(os.lstat)),
        patch("os.readlink", isolation.guard_metadata(os.readlink)),
    ):
        isolation.prove_denial()
        if args.sandbox:
            mounts = Path("/proc/self/mountinfo").read_text().splitlines()
            for path in ("/home", "/syncthing", "/run"):
                assert any(
                    line.split()[4] == path and " - tmpfs " in line for line in mounts
                ), path
            if args.mode == "lint-harness":
                raise SystemExit(actions[args.mode](args.sandbox, args.inject_warning))
            actions[args.mode](args.sandbox)
            return
        with tempfile.TemporaryDirectory(prefix="noctalia-fixture-") as temporary:
            directory = args.artifacts.absolute() if args.artifacts else Path(temporary)
            if args.artifacts:
                directory.mkdir(mode=0o700, parents=True, exist_ok=False)
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
                str(directory),
                str(directory),
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                str(directory),
                "--",
                "/usr/bin/python3",
                str(Path(sys.argv[0]).absolute()),
                args.mode,
                "--sandbox",
                str(directory),
                "--max-warnings",
                "0",
            ]
            if args.inject_warning:
                command.append("--inject-warning")
            result = subprocess.run(
                command,
                env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": str(directory)},
                timeout=120,
            )
            raise SystemExit(result.returncode)


def main():
    run_fixture_cli(
        {"lint": run_lint, "behavior": run_behavior, "lint-harness": run_harness_lint}
    )


if __name__ == "__main__":
    main()
