#!/usr/bin/env python3
"""Run unchanged WeatherCard in Qt/Quickshell with no desktop or real config access.

Service fixtures avoid network/settings bootstrap; production widgets, Loader,
NumberAnimation, ShaderEffect and ShaderEffectSource remain real QML objects.
"""

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
    with tempfile.TemporaryDirectory(prefix="noctalia-weather-effects-") as temporary:
        directory = Path(temporary)
        environment = isolate_environment(directory)
        settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
        settings.parent.mkdir(mode=0o700, parents=True)
        original = (ROOT / "Assets/settings-default.json").read_bytes()
        settings.touch(mode=0o600)
        settings.write_bytes(original)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert backup.read_bytes() == original, "fixture backup bytes differ"
        stage_card(directory)
        try:
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
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
        assert "WEATHER_EFFECTS_PASS" in output, "WeatherCard assertions did not finish"
        assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
            output
        )


if __name__ == "__main__":
    main()
