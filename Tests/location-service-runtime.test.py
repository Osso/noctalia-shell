#!/usr/bin/env python3
"""Unchanged production location singleton, real FileView/XHR, fixture transport only."""

import argparse
from collections import Counter
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
  component FixtureLocation: QtObject {
    property bool weatherEnabled: Quickshell.env('LOCATION_SCENARIO') === 'missing'
    property string name: 'Fixture City'
  }
  component FixtureColorSchemes: QtObject { property string schedulingMode: 'off' }
  component FixtureSettingsData: QtObject {
    property FixtureLocation location: FixtureLocation {}
    property FixtureColorSchemes colorSchemes: FixtureColorSchemes {}
  }
  property FixtureSettingsData data: FixtureSettingsData {}""",
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
    (directory / "qmldir").write_text("module qs\n")
    (commons / "qmldir").write_text(
        "module qs.Commons\n"
        + "".join(
            f"singleton {name} 1.0 {name}.qml\n"
            for name in ("Settings", "Time", "Logger")
        )
    )
    (location / "qmldir").write_text(
        "module qs.Services.Location\nsingleton LocationService 1.0 LocationService.qml\n"
    )
    (directory.parent / "qs").symlink_to(directory, target_is_directory=True)


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
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
    )
    return env


def run_isolated(directory, arguments, scenario):
    return subprocess.run(
        [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/",
            "/",
            "--tmpfs",
            "/home",
            "--tmpfs",
            "/syncthing",
            "--tmpfs",
            "/run",
            "--bind",
            str(directory),
            str(directory),
            "--chdir",
            str(directory),
            *arguments,
        ],
        env=environment(directory, scenario),
        capture_output=True,
        text=True,
        timeout=30,
    )


def lint_harness(directory, max_warnings, inject_warning):
    harness = directory / "shell/shell.qml"
    if inject_warning:
        source = harness.read_text()
        anchor = "id: root\n"
        assert source.count(anchor) == 1, (
            "warning injection anchor missing or ambiguous"
        )
        harness.write_text(
            source.replace(
                anchor,
                anchor + "  property int injectedWarning: missingFixtureOwner.value\n",
                1,
            )
        )
    result = run_isolated(
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
        SCENARIOS[0],
    )
    print(result.stdout, end="")
    print(result.stderr, end="")
    report = json.loads(result.stdout)
    counts = Counter(
        warning["id"]
        for entry in report["files"]
        for warning in entry["warnings"]
        if warning["type"] == "warning"
    )
    print("LOCATION_HARNESS_LINT_COUNTS", dict(counts), "exit", result.returncode)
    if counts or any(not entry["success"] for entry in report["files"]):
        return result.returncode or 1
    return result.returncode


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
    result = run_isolated(
        directory,
        [
            "quickshell",
            "--no-color",
            "-p",
            str(directory / "shell/shell.qml"),
        ],
        scenario,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", nargs="?", default="runtime", choices=("runtime", "lint-harness")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-location-runtime-") as temporary:
        directory = Path(temporary)
        env = environment(directory, SCENARIOS[0])
        settings = Path(env["HOME"]) / ".config/noctalia/settings.json"
        settings.parent.mkdir(mode=0o700, parents=True)
        original = (ROOT / "Assets/settings-default.json").read_bytes()
        settings.touch(mode=0o600)
        settings.write_bytes(original)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert backup.read_bytes() == original, "fixture backup bytes differ"
        build_transport(directory)
        shell = directory / "shell"
        shell.mkdir()
        stage_service(shell)
        try:
            if args.mode == "lint-harness":
                raise SystemExit(
                    lint_harness(directory, args.max_warnings, args.inject_warning)
                )
            for scenario in SCENARIOS:
                run_scenario(directory, scenario)
            print(f"LOCATION_RUNTIME_COUNTS {len(SCENARIOS)} passed, 0 failed")
        finally:
            assert settings.read_bytes() == original, "fixture settings changed"
            assert backup.read_bytes() == original, "fixture backup changed"


if __name__ == "__main__":
    main()
