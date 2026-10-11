#!/usr/bin/env python3
"""Bounded SettingsPanel lint and offscreen production panel/settings lifecycle.

Production SmartPanel, Settings, SettingsData and panel widgets remain real.
Tab bodies and desktop services are inert fixtures; no physical input coverage.
"""

import argparse
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
PANEL = Path("Modules/Panels/Settings/SettingsPanel.qml")
REAL_SETTINGS = Path("/home/osso/.config/noctalia/settings.json")
TABS = (
    "General",
    "Launcher",
    "Bar",
    "Audio",
    "Battery",
    "Display",
    "Osd",
    "Network",
    "Location",
    "Wallpaper",
    "ScreenRecorder",
    "About",
    "Hooks",
    "Dock",
    "Notifications",
    "ControlCenter",
    "UserInterface",
    "LockScreen",
    "SessionMenu",
    "SystemMonitor",
)


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lint(directory):
    load_helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / PANEL),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint.log").write_text(output)
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("SETTINGS_PANEL_WARNINGS", len(warnings))
    assert not warnings, warnings
    assert result.returncode == 0, result.returncode


def write_tab(path, name):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import QtQuick\nimport qs.Commons\nRectangle {\n"
        f'  objectName: "fixture-{name}"\n'
        "  implicitHeight: 1800\n"
        "  implicitWidth: 300\n"
        "  Text { text: Settings.data.ui.fontDefault }\n"
        "}\n"
    )


def stage_runtime(directory):
    geometry = load_helper("setup-layout-geometry")
    geometry.prepare_sources(directory)
    # Restore actual settings lifecycle rather than the geometry alias fixture.
    shutil.rmtree(directory / "Modules/OSD")
    load_helper("settings-singleton-warnings").stage_runtime(directory)
    target = directory / PANEL
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / PANEL, target)
    for name in TABS:
        write_tab(target.parent / f"Tabs/{name}Tab.qml", name)
    write_tab(target.parent / "Tabs/ColorScheme/ColorSchemeTab.qml", "ColorScheme")
    geometry.write_singleton(
        directory,
        "Services/System/ProgramCheckerService.qml",
        "property int checks: 0\nfunction checkAllPrograms() { checks++; }",
    )
    geometry.write_singleton(
        directory,
        "Services/UI/PanelService.qml",
        "property int opens: 0\nproperty int closes: 0\n"
        "function registerPanel(key, panel) {}\n"
        "function unregisterPanel(key, panel) {}\n"
        "function willOpenPanel(panel) { opens++; }\n"
        "function closedPanel(panel) { closes++; }",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/SettingsPanelWarningsHarness.qml", directory / "shell.qml"
    )


def isolated_environment(directory):
    environment = load_helper("settings-singleton-warnings").isolated_environment(
        directory, "panel"
    )
    runtime = directory / "r"
    runtime.mkdir(mode=0o700)
    environment["XDG_RUNTIME_DIR"] = str(runtime)
    environment["DBUS_SESSION_BUS_ADDRESS"] = (
        "unix:path=/nonexistent/noctalia-panel-session"
    )
    environment["DBUS_SYSTEM_BUS_ADDRESS"] = (
        "unix:path=/nonexistent/noctalia-panel-system"
    )
    return environment


def seed_settings(path):
    settings = json.loads(
        (ROOT / "Tests/fixtures/settings-types-default.json").read_text()
    )
    settings["ui"]["fontDefault"] = "Panel Fixture Sans"
    settings["ui"]["settingsPanelAttachToBar"] = False
    settings["ui"]["panelsAttachedToBar"] = False
    settings["general"]["animationDisabled"] = False
    settings["general"]["animationSpeed"] = 10
    settings["bar"]["widgets"] = {
        "left": [{"id": "Clock"}],
        "center": [],
        "right": [{"id": "ControlCenter"}],
    }
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return settings


def run_behavior(directory):
    original = REAL_SETTINGS.read_bytes()
    backup_directory = Path(tempfile.mkdtemp(prefix="noctalia-settings-panel-backup-"))
    backup_directory.chmod(0o700)
    backup = backup_directory / "settings.json"
    with backup.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(original)
    digest = hashlib.sha256(original).hexdigest()

    def check_safety():
        assert backup.stat().st_mode & 0o777 == 0o600, "Backup permissions changed"
        assert backup.read_bytes() == original, "Backup bytes changed"
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest, (
            "Backup hash mismatch"
        )
        assert REAL_SETTINGS.read_bytes() == original, "Real settings changed"

    check_safety()
    print("SETTINGS_PANEL_BACKUP", backup, digest)
    stage_runtime(directory)
    environment = isolated_environment(directory)
    settings_file = Path(environment["NOCTALIA_SETTINGS_FILE"])
    expected = seed_settings(settings_file)
    try:
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        (directory / "runtime.log").write_text(output)
        print(output, end="")
        assert result.returncode == 0 and "SETTINGS_PANEL_BEHAVIOR_PASS" in output, (
            output
        )
        assert not re.search(
            r"\b(?:WARN|ERROR|FATAL)\b|ReferenceError|TypeError|Binding loop", output
        ), output
        expected["ui"]["fontDefault"] = "Panel Dirty Sans"
        assert json.loads(settings_file.read_bytes()) == expected, (
            "Persistence changed unrelated settings"
        )
    finally:
        check_safety()
        print("SETTINGS_PANEL_REAL_SHA_UNCHANGED", digest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    (run_lint if args.mode == "lint" else run_behavior)(args.artifacts)


if __name__ == "__main__":
    main()
