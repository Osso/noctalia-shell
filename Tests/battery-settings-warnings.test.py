#!/usr/bin/env python3
"""Battery editor only: production controls, fixture UPower, isolated offscreen.

Positive changeRate magnitudes in charging/discharging fixtures; this editor
only selects devices and has no watt display. No real persistence or hardware.
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

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Bar/WidgetSettings/BatterySettings.qml")


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(
        "battery_settings_helper", ROOT / "Tests" / filename
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def lint(directory):
    load_helper("media-mini-warnings.test.py").stage_modules(directory)
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
    print("BATTERY_SETTINGS_LINT_COUNTS", dict(counts), "EXIT", result.returncode)
    assert not counts and result.returncode == 0, output


def stage_runtime(directory):
    helper = load_helper("clock-settings-warnings.test.py")
    helper.stage_runtime(directory)
    helper.write_module(
        directory,
        "qs.Modules.Panels.Settings.Bar.WidgetSettings",
        {
            "BatterySettings": (ROOT / TARGET).read_text(),
        },
    )
    helper.write_module(
        directory,
        "Quickshell.Services.UPower",
        {
            "UPowerDeviceType": helper.singleton(
                "enum Type { LinePower, Battery, Mouse }"
            ),
            "UPowerDeviceState": helper.singleton(
                "enum State { Charging, Discharging }"
            ),
            "UPower": helper.singleton("""component DeviceList: QtObject {
  property var values: []
}
property DeviceList devices: DeviceList {}"""),
        },
    )
    (directory / "tst_clock.qml").unlink()
    harness = directory / "tst_battery_settings.qml"
    shutil.copyfile(ROOT / "Tests/Qml/BatterySettingsWarningsHarness.qml", harness)
    return harness


def lint_harness(directory):
    harness = stage_runtime(directory)
    return check_harness(directory, harness)


def check_harness(directory, harness):
    result = subprocess.run(
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
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint-harness.log").write_text(output)
    print(output, end="")
    diagnostics = json.loads(result.stdout)
    warnings = sum(
        warning["type"] == "warning"
        for item in diagnostics["files"]
        for warning in item["warnings"]
    )
    print("BATTERY_SETTINGS_HARNESS_WARNINGS", warnings, "EXIT", result.returncode)
    passed = (
        result.returncode == 0
        and warnings == 0
        and all(item["success"] for item in diagnostics["files"])
    )
    return 0 if passed else result.returncode or 1


def lint_harness_regression(directory):
    clean = directory / "clean"
    clean.mkdir()
    assert lint_harness(clean) == 0, "clean harness lint failed"
    injected = directory / "injected"
    injected.mkdir()
    harness = stage_runtime(injected)
    source = harness.read_text()
    marker = "id: suite"
    assert source.count(marker) == 1, "injection owner must be unique"
    harness.write_text(
        source.replace(
            marker,
            marker + "\n  property int injectedWarning: suite.missingLintProbe",
            1,
        )
    )
    assert check_harness(injected, harness) != 0, "genuine warning was accepted"
    assert "missingLintProbe" in (injected / "lint-harness.log").read_text(), (
        "expected injected missing-property diagnostic"
    )
    print("BATTERY_SETTINGS_HARNESS_WARNING_REJECTED")


def behavior(directory):
    harness = stage_runtime(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ],
        cwd=directory,
        env=load_helper("datetime-tokens-layout-runtime.test.py").isolate_environment(
            directory
        ),
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "8 passed, 0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
        output,
    ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    if args.mode == "lint-harness":
        assert lint_harness(args.artifacts) == 0, "harness lint failed"
        return
    if args.mode == "lint-harness-regression":
        lint_harness_regression(args.artifacts)
        return
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(original)
    digest = hashlib.sha256(original).digest()
    assert backup.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(backup.read_bytes()).digest() == digest
    try:
        (lint if args.mode == "lint" else behavior)(args.artifacts)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest, "Backup changed"
    print("Real settings/backup unchanged; bounded offscreen runner exited.")


if __name__ == "__main__":
    main()
