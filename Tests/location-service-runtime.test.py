#!/usr/bin/env python3
"""Unchanged production location singleton, real FileView/XHR, fixture transport only."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    "cached",
    "reuse",
    "geocode",
    "missing",
    "geo-http-error",
    "geo-unresolved-error",
    "geo-parse-error",
    "weather-http-error",
    "weather-parse-error",
)


def command(arguments, **options):
    result = subprocess.run(
        arguments, cwd=ROOT, capture_output=True, text=True, timeout=30, **options
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


def write_singleton(directory, name, body):
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nimport Quickshell\nQtObject {\n"
        + body
        + "\n}\n"
    )


def build_transport(directory):
    plugin = directory / "LocationNetwork"
    plugin.mkdir()
    shutil.copyfile(
        ROOT / "Tests/Fixtures/LocationNetworkPlugin.cpp",
        plugin / "LocationNetworkPlugin.cpp",
    )
    include_flags = shlex.split(
        command(["pkg-config", "--cflags", "Qt6Qml", "Qt6Network"])
    )
    command(
        [
            "/usr/lib/qt6/moc",
            *include_flags,
            str(plugin / "LocationNetworkPlugin.cpp"),
            "-o",
            str(plugin / "LocationNetworkPlugin.moc"),
        ]
    )
    flags = shlex.split(
        command(["pkg-config", "--cflags", "--libs", "Qt6Qml", "Qt6Network"])
    )
    command(
        [
            "g++",
            "-std=c++17",
            "-shared",
            "-fPIC",
            "-Wall",
            "-Wextra",
            str(plugin / "LocationNetworkPlugin.cpp"),
            "-o",
            str(plugin / "liblocationnetwork.so"),
            *flags,
        ]
    )
    (plugin / "qmldir").write_text("module LocationNetwork\nplugin locationnetwork\n")


def stage_service(directory):
    commons = directory / "Commons"
    location = directory / "Services/Location"
    commons.mkdir()
    location.mkdir(parents=True)
    shutil.copyfile(
        ROOT / "Services/Location/LocationService.qml", location / "LocationService.qml"
    )
    write_singleton(
        commons,
        "Settings",
        """  property string cacheDir: Qt.resolvedUrl('../cache/').toString().replace('file://', '')
  property QtObject data: QtObject {
    property QtObject location: QtObject {
      property bool weatherEnabled: Quickshell.env('LOCATION_SCENARIO') === 'missing'
      property string name: 'Fixture City'
    }
    property QtObject colorSchemes: QtObject { property string schedulingMode: 'off' }
  }""",
    )
    write_singleton(commons, "Time", "  property int timestamp: 1000")
    write_singleton(
        commons,
        "Logger",
        """  property var errors: []
  function d() {}
  function i() {}
  function w() {}
  function e(module, message) { errors.push(message); }""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/LocationServiceHarness.qml", directory / "shell.qml"
    )


def environment(directory, scenario):
    env = {
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
        path.mkdir(mode=0o700, exist_ok=True)
        env[variable] = str(path)
    # The native module lives outside the QML config root: Quickshell intercepts
    # files under that root with its virtual qs URL scheme.
    env.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QML_IMPORT_PATH=str(directory),
        LOCATION_FIXTURES=str(directory),
        LOCATION_SCENARIO=scenario,
        NOCTALIA_WEATHER_FILE=str(directory / "location.json"),
    )
    return env


def run_scenario(directory, scenario):
    weather = {"latitude": 32, "longitude": -96, "current_weather": {"temperature": 21}}
    cache = {
        "latitude": "",
        "longitude": "",
        "name": "",
        "weatherLastFetch": 0,
        "weather": None,
    }
    if scenario in ("cached", "reuse"):
        cache.update(
            latitude="32",
            longitude="-96",
            name="Fixture City",
            weatherLastFetch=1000 if scenario == "cached" else 1,
            weather=weather if scenario == "cached" else None,
        )
    location_file = directory / "location.json"
    if scenario == "missing":
        location_file.unlink(missing_ok=True)
    else:
        location_file.write_text(json.dumps(cache))
    geo = {
        "status": 200,
        "body": json.dumps(
            {"lat": 32, "lng": -96, "name": "Fixture City", "country": "ZZ"}
        ),
    }
    forecast = {"status": 200, "body": json.dumps(weather)}
    if scenario == "geo-http-error":
        geo["status"] = 503
    if scenario == "geo-unresolved-error":
        geo["body"] = "{}"
    if scenario == "geo-parse-error":
        geo["body"] = "not JSON"
    if scenario == "weather-http-error":
        forecast["status"] = 503
    if scenario == "weather-parse-error":
        forecast["body"] = "not JSON"
    for name, response in (("geocode", geo), ("weather", forecast)):
        (directory / f"{name}.json").write_text(json.dumps(response))
    requests = directory / "requests.txt"
    requests.unlink(missing_ok=True)
    output = command(
        [
            "bwrap",
            "--unshare-net",
            "--die-with-parent",
            "--ro-bind",
            "/",
            "/",
            "--bind",
            str(directory),
            str(directory),
            "quickshell",
            "--no-color",
            "-p",
            str(directory / "shell/shell.qml"),
        ],
        env=environment(directory, scenario),
    )
    print(output, end="")
    assert f"LOCATION_PASS {scenario}" in output, output
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )
    urls = requests.read_text().splitlines() if requests.exists() else []
    expected_count = (
        0
        if scenario == "cached"
        else 1
        if scenario == "reuse" or scenario.startswith("geo-")
        else 2
    )
    assert len(urls) == expected_count, urls
    saved = json.loads((directory / "location.json").read_text())
    if not scenario.endswith("error"):
        assert saved["latitude"] == "32" and saved["longitude"] == "-96", saved
        assert saved["weatherLastFetch"] == 1000 and saved["weather"] == weather, saved
    if scenario not in ("cached", "reuse"):
        assert (
            urls[0]
            == "https://assets.noctalia.dev/geocode.php?city=Fixture%20City&language=en&format=json"
        ), urls
    if scenario in ("reuse", "geocode", "missing") or scenario.startswith("weather-"):
        assert urls[-1].startswith(
            "https://api.open-meteo.com/v1/forecast?latitude=32&longitude=-96&"
        ), urls


def main():
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    with tempfile.TemporaryDirectory(prefix="noctalia-location-runtime-") as temporary:
        directory = Path(temporary)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert (
            hashlib.sha256(backup.read_bytes()).digest()
            == hashlib.sha256(original).digest()
        )
        build_transport(directory)
        shell = directory / "shell"
        shell.mkdir()
        stage_service(shell)
        try:
            for scenario in SCENARIOS:
                run_scenario(directory, scenario)
        finally:
            assert settings.read_bytes() == original, "real settings changed"


if __name__ == "__main__":
    main()
