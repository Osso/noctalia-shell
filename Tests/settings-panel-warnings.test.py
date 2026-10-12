#!/usr/bin/env python3
"""Bounded SettingsPanel lint and offscreen production panel/settings lifecycle.

Production SmartPanel, Settings, SettingsData and panel widgets remain real.
Tab bodies and desktop services are inert fixtures; no physical input coverage.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
PANEL = Path("Modules/Panels/Settings/SettingsPanel.qml")
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
    home_config = Path(environment["HOME"]) / ".config"
    home_config.mkdir(mode=0o700)
    for config in (home_config, Path(environment["XDG_CONFIG_HOME"])):
        config.chmod(0)
        try:
            (config / "noctalia/settings.json").read_bytes()
        except PermissionError:
            print("SETTINGS_PANEL_SYNTHETIC_CONFIG_DENIED", config)
        else:
            raise AssertionError("Synthetic config was accessible")
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
    harness = stage_harness(directory)
    environment = isolated_environment(directory)
    settings_file = Path(environment["NOCTALIA_SETTINGS_FILE"])
    expected = seed_settings(settings_file)
    result = subprocess.run(
        ["quickshell", "--no-color", "-p", str(harness)],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "SETTINGS_PANEL_BEHAVIOR_PASS" in output, output
    assert not re.search(
        r"\b(?:WARN|ERROR|FATAL)\b|ReferenceError|TypeError|Binding loop", output
    ), output
    expected["ui"]["fontDefault"] = "Panel Dirty Sans"
    assert json.loads(settings_file.read_bytes()) == expected, (
        "Persistence changed unrelated settings"
    )


def stage_harness(directory):
    sources = directory / "qs"
    sources.mkdir()
    stage_runtime(sources)
    modules = {}
    for qml in sorted(sources.rglob("*.qml")):
        parent = qml.relative_to(sources).parent
        for ancestor in (parent, *parent.parents):
            modules.setdefault(ancestor, [])
        singleton = re.search(r"^\s*pragma\s+Singleton\b", qml.read_text(), re.M)
        prefix = "singleton " if singleton else ""
        modules[parent].append(f"{prefix}{qml.stem} 1.0 {qml.name}\n")
    for parent, declarations in modules.items():
        module = ".".join(("qs", *parent.parts))
        (sources / parent / "qmldir").write_text(
            f"module {module}\n" + "".join(declarations)
        )
    return sources / "shell.qml"


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
    print("SETTINGS_PANEL_HARNESS_WARNINGS", warnings, "EXIT", result.returncode)
    passed = (
        result.returncode == 0
        and warnings == 0
        and all(item["success"] for item in diagnostics["files"])
    )
    return 0 if passed else result.returncode or 1


def lint_harness(directory):
    return check_harness(directory, stage_harness(directory))


def lint_harness_regression(directory):
    clean = directory / "clean"
    clean.mkdir()
    assert lint_harness(clean) == 0, "Clean harness rejected"
    injected = directory / "injected"
    injected.mkdir()
    harness = stage_harness(injected)
    source = harness.read_text()
    marker = "id: harness"
    assert source.count(marker) == 1, "Injection owner must be unique"
    harness.write_text(
        source.replace(
            marker,
            marker + "\n  property int injectedWarning: harness.missingLintProbe",
            1,
        )
    )
    assert check_harness(injected, harness) != 0, "Injected warning accepted"
    assert "missingLintProbe" in (injected / "lint-harness.log").read_text()
    print("SETTINGS_PANEL_HARNESS_WARNING_REJECTED")


def deny_host_path(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    name = os.path.abspath(os.fsdecode(path))
    if (
        name == "/home"
        or name.startswith("/home/")
        or (name.startswith("/syncthing/") and not name.startswith(str(ROOT) + "/"))
    ):
        raise PermissionError(f"Host config access denied: {name}")


def audit(event, arguments):
    if event in ("open", "os.listdir", "os.scandir"):
        deny_host_path(arguments[0])


def guard_metadata(function):
    def guarded(path, *arguments, **keywords):
        deny_host_path(path)
        return function(path, *arguments, **keywords)

    return guarded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--sandbox", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.addaudithook(audit)
    with (
        patch("os.stat", guard_metadata(os.stat)),
        patch("os.lstat", guard_metadata(os.lstat)),
        patch("os.readlink", guard_metadata(os.readlink)),
    ):
        if not args.sandbox:
            args.artifacts = args.artifacts.absolute()
            args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
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
                str(args.artifacts),
                str(args.artifacts),
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                str(args.artifacts),
                "--",
                "/usr/bin/python3",
                str(Path(__file__).absolute()),
                args.mode,
                "--artifacts",
                str(args.artifacts),
                "--max-warnings",
                "0",
                "--sandbox",
            ]
            result = subprocess.run(
                command,
                env={
                    "PATH": "/usr/bin",
                    "LANG": "C.UTF-8",
                    "HOME": str(args.artifacts),
                },
                timeout=90,
            )
            raise SystemExit(result.returncode)
        if args.mode == "lint-harness":
            assert lint_harness(args.artifacts) == 0, "Harness lint failed"
        elif args.mode == "lint-harness-regression":
            lint_harness_regression(args.artifacts)
        else:
            (run_lint if args.mode == "lint" else run_behavior)(args.artifacts)


if __name__ == "__main__":
    main()
