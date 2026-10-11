#!/usr/bin/env python3
"""Bounded WeatherCard lint/display proof; reuse existing offscreen effect fixtures.

No provider requests, settings bootstrap, desktop connection, or GPU pixel proof.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Cards/WeatherCard.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


effects = load_helper("weather_effects", "weather-card-effects.test.py")
lint_fixture = load_helper("weather_lint", "media-mini-warnings.test.py")


def run_lint(directory):
    lint_fixture.stage_modules(directory)
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
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in warnings
    )
    # Shader Loader retains its creation context: Bound would alter that contract.
    # Accept only Qt's explicit cross-component ID diagnostics, never ordinary
    # unqualified member access or other warning categories.
    blocks = re.split(r"(?=^Warning:)", output, flags=re.M)[1:]
    residuals = [
        block
        for block in blocks
        if "[unqualified]" in block.splitlines()[0]
        and 'Info: Set "pragma ComponentBehavior: Bound"' in block
    ]
    print("WEATHER_CARD_LINT_COUNTS", dict(counts), "CONTEXT_BOUNDARY", len(residuals))
    assert len(warnings) == len(residuals) == 9, (
        "unexpected/actionable WeatherCard warnings"
    )
    assert result.returncode == 0, f"qmllint failed: {result.returncode}"
    print("WEATHER_CARD_ACTIONABLE_LINT_PASS")


def stage_runtime(directory):
    effects.stage_card(directory)
    effects.write_singleton(
        directory / "Services/Location",
        "LocationService",
        """property var data: ({weather: null})
function weatherSymbolFromCode(code) {
  if (code === 61) return "rain";
  if (code === 71) return "snow";
  return "sun";
}
function celsiusToFahrenheit(value) { return 32 + value * 1.8; }""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/WeatherCardWarningsHarness.qml", directory / "shell.qml"
    )


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    try:
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            cwd=ROOT,
            env=effects.isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        assert settings.read_bytes() == original, "real settings changed"
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, f"WeatherCard runtime failed: {result.returncode}"
    assert "WEATHER_CARD_BEHAVIOR_PASS" in output
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-weather-card-warnings-"
    ) as temporary:
        directory = Path(temporary)
        if args.mode == "lint":
            run_lint(directory)
        else:
            run_behavior(directory)


if __name__ == "__main__":
    main()
