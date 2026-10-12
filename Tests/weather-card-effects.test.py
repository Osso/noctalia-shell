#!/usr/bin/env python3
"""Run unchanged WeatherCard in Qt/Quickshell with no desktop or real config access.

Service fixtures avoid network/settings bootstrap; production widgets, Loader,
NumberAnimation, ShaderEffect and ShaderEffectSource remain real QML objects.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def write_singleton(directory, name, body):
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"
    )


def stage_card(directory):
    commons = directory / "Commons"
    widgets = directory / "Widgets"
    cards = directory / "Modules/Cards"
    location = directory / "Services/Location"
    for path in (commons, widgets, cards, location):
        path.mkdir(parents=True, mode=0o700)
    shutil.copyfile(ROOT / "Modules/Cards/WeatherCard.qml", cards / "WeatherCard.qml")
    for name in ("NBox", "NText", "NIcon", "NDivider", "NBusyIndicator"):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
    shutil.copytree(ROOT / "Shaders/qsb", directory / "Shaders/qsb")
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["location"]["weatherEnabled"] = True
    write_singleton(commons, "Settings", "  property var data: " + json.dumps(defaults))
    style = {
        "uiScaleRatio": 1,
        "marginXL": 16,
        "marginM": 8,
        "marginS": 4,
        "marginXXS": 2,
        "marginL": 12,
        "marginXS": 3,
        "radiusM": 12,
        "borderS": 1,
        "borderL": 3,
        "baseWidgetSize": 24,
        "animationSlow": 300,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXL": 18,
        "fontSizeXXL": 22,
        "fontSizeXXXL": 26,
        "fontSizeXS": 9,
        "fontWeightMedium": 500,
        "fontWeightBold": 700,
    }
    write_singleton(
        commons,
        "Style",
        "\n".join(
            f"  readonly property real {name}: {value}" for name, value in style.items()
        ),
    )
    colors = {
        "mSurfaceVariant": "#202020",
        "mOutline": "#808080",
        "mPrimary": "#abcdef",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#dddddd",
        "transparent": "transparent",
    }
    write_singleton(
        commons,
        "NColor",
        "\n".join(
            f"  readonly property color {name}: {json.dumps(value)}"
            for name, value in colors.items()
        ),
    )
    write_singleton(
        commons,
        "Icons",
        """  readonly property string defaultIcon: "sun"
  readonly property string fontFamily: "sans-serif"
  function get(name) { return "*"; }""",
    )
    write_singleton(
        commons, "I18n", '  readonly property var locale: Qt.locale("en_US")'
    )
    write_singleton(
        location,
        "LocationService",
        """  readonly property var data: ({weather: {
    current_weather: {weathercode: 0, temperature: 15},
    timezone_abbreviation: "UTC",
    daily: {time: [], weathercode: [], temperature_2m_max: [], temperature_2m_min: []}
  }})
  function weatherSymbolFromCode(code) { return "sun"; }
  function celsiusToFahrenheit(value) { return 32 + value * 1.8; }""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/WeatherCardEffectsHarness.qml", directory / "shell.qml"
    )
    (directory / "qmldir").write_text("module qs\n")
    for path in (commons, widgets, cards, location):
        module = "qs." + ".".join(path.relative_to(directory).parts)
        declarations = []
        for source in sorted(path.glob("*.qml")):
            singleton = (
                "singleton "
                if source.read_text().startswith("pragma Singleton")
                else ""
            )
            declarations.append(f"{singleton}{source.stem} 1.0 {source.name}\n")
        (path / "qmldir").write_text(f"module {module}\n" + "".join(declarations))
    (directory / "qs").symlink_to(".", target_is_directory=True)


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def lint_harness(directory, environment, max_warnings, inject_warning):
    # Reuse the exact fake weather service and harness staged for runtime.
    load_helper("weather-card-warnings.test.py").stage_runtime(directory)
    harness = directory / "shell.qml"
    if inject_warning:
        source = harness.read_text()
        anchor = "id: harness\n"
        assert source.count(anchor) == 1, "warning injection owner must be unique"
        harness.write_text(
            source.replace(
                anchor,
                anchor + "  property int injectedWarning: harness.missingLintProbe\n",
                1,
            )
        )
    isolation = load_helper("wallpaper-tab-warnings.test.py")
    result = subprocess.run(
        isolation.sandbox_command(
            directory,
            [
                "/usr/lib/qt6/bin/qmllint",
                "--bare",
                "-I",
                str(directory),
                "-I",
                "/usr/lib/qt6/qml",
                "--max-warnings",
                str(max_warnings),
                "--json",
                "-",
                str(harness),
            ],
        ),
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout, end="")
    print(result.stderr, end="")
    report = json.loads(result.stdout)
    counts = Counter(
        diagnostic["id"]
        for entry in report["files"]
        for diagnostic in entry["warnings"]
        if diagnostic["type"] == "warning"
    )
    print(
        "WEATHER_CARD_HARNESS_LINT_COUNTS",
        dict(counts),
        "WARNINGS",
        sum(counts.values()),
        "EXIT",
        result.returncode,
    )
    if inject_warning:
        assert counts["missing-property"] > 0 and result.returncode != 0, (
            "injected semantic warning was accepted"
        )
        return result.returncode
    if counts or any(not entry["success"] for entry in report["files"]):
        return result.returncode or 1
    return result.returncode


def isolate_environment(directory):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key not in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME")
    }
    for variable, name in {
        "HOME": "home",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "XDG_DATA_HOME": "data",
        "XDG_STATE_HOME": "state",
        "XDG_RUNTIME_DIR": "runtime",
        "NOCTALIA_CONFIG_DIR": "noctalia-config",
        "NOCTALIA_CACHE_DIR": "noctalia-cache",
    }.items():
        path = directory / name
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    # Software rendering tests effect lifecycle/uniforms, not GPU pixel output.
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    return environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        nargs="?",
        default="effects",
        choices=("effects", "behavior", "lint-harness"),
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-weather-effects-") as temporary:
        directory = Path(temporary)
        environment = isolate_environment(directory)
        if args.mode == "lint-harness":
            raise SystemExit(
                lint_harness(
                    directory, environment, args.max_warnings, args.inject_warning
                )
            )
        settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
        settings.parent.mkdir(mode=0o700, parents=True)
        original = (ROOT / "Assets/settings-default.json").read_bytes()
        settings.touch(mode=0o600)
        settings.write_bytes(original)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert (
            hashlib.sha256(backup.read_bytes()).digest()
            == hashlib.sha256(original).digest()
        ), "fixture backup bytes differ"
        if args.mode == "behavior":
            load_helper("weather-card-warnings.test.py").stage_runtime(directory)
        else:
            stage_card(directory)
        isolation = load_helper("wallpaper-tab-warnings.test.py")
        try:
            result = subprocess.run(
                isolation.sandbox_command(
                    directory,
                    ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                ),
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired as error:
            print((error.stdout or b"").decode(errors="replace"), end="")
            print((error.stderr or b"").decode(errors="replace"), end="")
            raise
        finally:
            assert settings.read_bytes() == original, "fixture settings changed"
            assert backup.read_bytes() == original, "fixture backup changed"
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, (
            f"WeatherCard runtime failed (exit {result.returncode})"
        )
        marker = (
            "WEATHER_CARD_BEHAVIOR_PASS"
            if args.mode == "behavior"
            else "WEATHER_EFFECTS_PASS"
        )
        assert marker in output, "WeatherCard assertions did not finish"
        assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
            output
        )


if __name__ == "__main__":
    main()
