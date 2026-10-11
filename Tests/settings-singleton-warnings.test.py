#!/usr/bin/env python3
"""Bounded lint and real Settings singleton lifecycle; no desktop or user writes."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Commons/Settings.qml")
REAL = Path("/home/osso/.config/noctalia/settings.json")
BACKUP = Path("/tmp/noctalia-settings-before-color-defaults-20261011T170411798433.json")
HASH = "bc53e7cae6f456d443ba79ccee688802f18fb38abd6cbfc695ae331885b841e4"


def check_safety(original):
    assert BACKUP.stat().st_mode & 0o777 == 0o600, "Backup permissions changed"
    assert hashlib.sha256(BACKUP.read_bytes()).hexdigest() == HASH, "Backup changed"
    assert REAL.read_bytes() == original, "Real settings changed"


def helpers():
    spec = importlib.util.spec_from_file_location(
        "settings_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helpers().stage_modules(directory)
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
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("SETTINGS_LINT_COUNTS", dict(counts))
    # QQmlApplication.font metadata and the unbound cross-component saveTimer ID
    # remain outside this singleton/owner qualification slice.
    assert counts == {"missing-property": 1, "unqualified": 1}, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    for relative in (
        TARGET,
        Path("Commons/SettingsData.qml"),
        Path("Helpers/SettingsDefaults.js"),
        Path("Helpers/QtObj2JS.js"),
        Path("Commons/Migrations/MigrationRegistry.qml"),
        Path("Commons/Migrations/Migration26.qml"),
    ):
        destination = directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    fixture = helpers()
    fixture.write_singleton(
        directory / "Commons",
        "Logger",
        "function d(...args) { console.log(...args); }\n"
        "function i(...args) { console.log(...args); }\n"
        "function w(...args) { console.log(...args); }\n"
        "function e(...args) { console.log(...args); }",
    )
    names = [
        "CustomButton",
        "Clock",
        "SystemMonitor",
        "ActiveWindow",
        "MediaMini",
        "Workspace",
        "ScreenRecorder",
        "Tray",
        "NotificationHistory",
        "Battery",
        "Volume",
        "Brightness",
        "ControlCenter",
    ]
    fixture.write_singleton(
        directory / "Services/UI",
        "BarWidgetRegistry",
        "property var widgets: " + json.dumps(dict.fromkeys(names, True)) + "\n"
        "property var widgetMetadata: "
        + json.dumps({name: {"id": name, "allowUserSettings": False} for name in names})
        + "\nfunction hasWidget(name) { return widgets[name] === true; }",
    )
    (directory / "Modules/OSD").mkdir(parents=True)
    (directory / "Modules/OSD/OSD.qml").write_text(
        "import QtQuick\nQtObject { enum Type { Volume, InputVolume, Brightness, LockKey } }\n"
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/SettingsSingletonHarness.qml", directory / "shell.qml"
    )


def isolated_environment(directory, mode):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for variable in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_CONFIG_DIRS",
        "XDG_DATA_DIRS",
    ):
        path = directory / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    config = directory / "config"
    cache = directory / "cache"
    config.mkdir(mode=0o700)
    cache.mkdir(mode=0o700)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        NOCTALIA_CONFIG_DIR=str(config) + "/",
        NOCTALIA_CACHE_DIR=str(cache) + "/",
        NOCTALIA_SETTINGS_FILE=str(config / "settings.json"),
        SETTINGS_SINGLETON_MODE=mode,
        SETTINGS_SINGLETON_REPAIR_MARKER=str(config / "repair-marker"),
    )
    assert (
        not {"DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"}
        & environment.keys()
    )
    return environment


def run_case(directory, mode, original):
    check_safety(original)
    stage_runtime(directory)
    environment = isolated_environment(directory, mode)
    settings = Path(environment["NOCTALIA_SETTINGS_FILE"])
    snapshot = directory / "cache/settings-bootstrap.json"
    marker = Path(environment["SETTINGS_SINGLETON_REPAIR_MARKER"])
    marker.write_bytes(b"waiting")
    value = json.loads(
        (ROOT / "Tests/fixtures/settings-types-default.json").read_bytes()
    )
    value["ui"]["fontDefault"] = "Fixture Sans"
    value["bar"]["widgets"] = {
        "left": [{"id": "Clock"}],
        "center": [],
        "right": [{"id": "ControlCenter"}],
    }
    raw = (json.dumps(value, indent=3) + "\n").encode()
    if mode == "valid":
        settings.write_bytes(raw)
    elif mode == "malformed":
        settings.write_bytes(b'{"ui": broken}\n')
    transcript = []
    process = subprocess.Popen(
        ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
        cwd=directory,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            for key, _ in selector.select(timeout=0.1):
                line = key.fileobj.readline()
                if not line:
                    continue
                transcript.append(line)
                print(line, end="")
                if "SETTINGS_AWAIT_EXTERNAL" in line:
                    assert snapshot.read_bytes() == raw, (
                        "Validated snapshot changed bytes"
                    )
                    saved = json.loads(settings.read_bytes())
                    assert saved["ui"]["fontDefault"] == "Saved Sans"
                    assert saved["audio"]["volumeStep"] == 7
                    expected = json.loads(raw)
                    expected["ui"]["fontDefault"] = "Saved Sans"
                    expected["audio"]["volumeStep"] = 7
                    assert saved == expected, "Save changed unrelated schema/state"
                    saved["ui"]["fontDefault"] = "External Sans"
                    settings.write_text(json.dumps(saved))
                elif "SETTINGS_AWAIT_MALFORMED" in line:
                    settings.write_bytes(b'{"ui": broken}\n')
                elif "SETTINGS_AWAIT_REPAIR" in line:
                    assert settings.read_bytes() == b'{"ui": broken}\n', (
                        "Invalid bytes overwritten"
                    )
                    value["ui"]["fontDefault"] = "Repaired Sans"
                    repaired = (json.dumps(value) + "\n").encode()
                    settings.write_bytes(repaired)
                    marker.write_bytes(b"repaired")
                elif "SETTINGS_SINGLETON_PASS" in line:
                    remaining, _ = process.communicate(timeout=3)
                    transcript.append(remaining)
                    output = "".join(transcript)
                    assert process.returncode == 0, output
                    assert not re.search(
                        r"TypeError|ReferenceError| WARN | ERROR ", output
                    ), output
                    if mode == "malformed":
                        assert settings.read_bytes() == b'{"ui": broken}\n'
                        assert not snapshot.exists()
                    elif mode == "valid":
                        assert snapshot.read_bytes() == repaired
                        assert settings.read_bytes() == repaired, (
                            "Retry rewrote validated bytes"
                        )
                    else:
                        initial = re.search(r"SETTINGS_INITIAL (\{.*\})", output)
                        assert initial, output
                        actual = json.loads(settings.read_bytes())
                        expected = json.loads(
                            (
                                ROOT / "Tests/fixtures/settings-types-default.json"
                            ).read_bytes()
                        )
                        expected["general"]["avatarImage"] = (
                            environment["HOME"] + "/.face"
                        )
                        expected["screenRecorder"]["directory"] = (
                            environment["HOME"] + "/Videos"
                        )
                        expected["wallpaper"]["directory"] = (
                            environment["HOME"] + "/Pictures/Wallpapers"
                        )
                        expected["ui"]["fontDefault"] = json.loads(initial[1])["ui"][
                            "fontDefault"
                        ]
                        expected["ui"]["fontFixed"] = "monospace"
                        assert actual == expected, (
                            "First-run defaults changed schema/state"
                        )
                        assert json.loads(snapshot.read_bytes()) == expected
                    print("SETTINGS_CASE_PASS", mode)
                    return
            if process.poll() is not None:
                break
        raise AssertionError("Harness did not finish: " + "".join(transcript))
    finally:
        selector.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        process.stdout.close()
        check_safety(original)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    mode = parser.parse_args().mode
    original = REAL.read_bytes()
    check_safety(original)
    if mode == "lint":
        with tempfile.TemporaryDirectory(prefix="noctalia-settings-lint-") as temporary:
            lint(Path(temporary))
    else:
        for case in ("valid", "malformed", "defaults"):
            with tempfile.TemporaryDirectory(
                prefix="noctalia-settings-singleton-"
            ) as temporary:
                run_case(Path(temporary), case, original)
    check_safety(original)


if __name__ == "__main__":
    main()
