#!/usr/bin/env python3
"""Targeted lint and offscreen production TimerCard/Time behavior regression."""

import argparse
from collections import Counter
import json
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CARD = Path("Modules/Cards/TimerCard.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_singleton(directory, name, body):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"
    )


def run_lint(directory):
    sources = subprocess.run(
        ["rg", "--files", "-g", "*.qml", "-g", "*.js", "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    modules = {}
    for name in sorted(sources.stdout.splitlines()):
        path = Path(name)
        target = directory / "qs" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
        if path.suffix != ".qml":
            continue
        for parent in (path.parent, *path.parent.parents):
            modules.setdefault(parent, [])
        singleton = (
            "singleton "
            if re.search(r"^\s*pragma\s+Singleton\b", target.read_text(), re.M)
            else ""
        )
        modules[path.parent].append(f"{singleton}{path.stem} 1.0 {path.name}\n")
    for path, declarations in modules.items():
        (directory / "qs" / path / "qmldir").write_text(
            f"module {'.'.join(('qs', *path.parts))}\n" + "".join(declarations)
        )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / CARD),
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
    print("TIMER_CARD_LINT_COUNTS", dict(counts))
    assert not warnings, f"TimerCard warnings remain: {dict(counts)}"
    assert result.returncode == 0, f"qmllint failed: {result.returncode}"
    print("TIMER_CARD_LINT_PASS")


def stage_runtime(directory):
    sources = [CARD, Path("Commons/Time.qml"), Path("Helpers/TimerDigits.js")]
    sources += [
        Path(f"Widgets/{name}.qml")
        for name in ("NBox", "NButton", "NText", "NIcon", "NTabBar", "NTabButton")
    ]
    for path in sources:
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    commons = directory / "Commons"
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    write_singleton(commons, "Settings", "property var data: " + json.dumps(defaults))
    style = {
        "uiScaleRatio": 1,
        "marginM": 8,
        "marginS": 4,
        "marginXS": 3,
        "marginL": 12,
        "radiusM": 12,
        "radiusS": 6,
        "radiusXS": 3,
        "borderS": 1,
        "baseWidgetSize": 32,
        "animationFast": 0,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXXL": 22,
        "fontSizeXXXL": 26,
        "fontWeightRegular": 400,
        "fontWeightMedium": 500,
        "fontWeightSemiBold": 600,
        "fontWeightBold": 700,
    }
    write_singleton(
        commons,
        "Style",
        "\n".join(
            f"readonly property real {key}: {value}" for key, value in style.items()
        ),
    )
    colors = {
        "mSurfaceVariant": "#202020",
        "mSurface": "#303030",
        "mOutline": "#808080",
        "mPrimary": "#abcdef",
        "mOnPrimary": "#000000",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#dddddd",
        "mHover": "#404040",
        "mOnHover": "#ffffff",
        "transparent": "transparent",
    }
    write_singleton(
        commons,
        "NColor",
        "\n".join(
            f"readonly property color {key}: {json.dumps(value)}"
            for key, value in colors.items()
        ),
    )
    write_singleton(
        commons,
        "Icons",
        """readonly property string defaultIcon: "clock"
readonly property string fontFamily: "sans-serif"
function get(name) { return "*"; }""",
    )
    write_singleton(commons, "I18n", "function tr(key) { return key; }")
    write_singleton(
        commons,
        "Logger",
        """function w(...args) { console.warn(...args); }
function callStack() { console.trace(); }""",
    )
    write_singleton(
        directory / "Services/System",
        "SoundService",
        """property int plays: 0
property int stops: 0
property string lastSound: ""
property var lastOptions
function playSound(name, options) { plays++; lastSound = name; lastOptions = options; }
function stopSound(name) { stops++; lastSound = name; }""",
    )
    write_singleton(
        directory / "Services/UI",
        "TooltipService",
        """function show(...args) {}
function hide() {}""",
    )
    # Expose the same staged runtime files to qmllint's URI resolver.
    (directory / "qs").symlink_to(".", target_is_directory=True)
    for path in (
        "Commons",
        "Services/System",
        "Services/UI",
        "Widgets",
        "Modules/Cards",
    ):
        module = directory / path
        declarations = []
        for source in sorted(module.glob("*.qml")):
            prefix = (
                "singleton "
                if source.read_text().startswith("pragma Singleton")
                else ""
            )
            declarations.append(f"{prefix}{source.stem} 1.0 {source.name}\n")
        (module / "qmldir").write_text(
            f"module qs.{path.replace('/', '.')}\n" + "".join(declarations)
        )
    shutil.copyfile(ROOT / "Tests/Qml/TimerCardHarness.qml", directory / "shell.qml")


def isolate_environment(directory):
    return helper("wallpaper-tab-warnings.test.py").isolated_environment(directory)


def run_behavior(directory):
    environment = isolate_environment(directory)
    # Parent-owned integrity fixtures are not the fake QML Settings singleton.
    # Keep them outside the child's intentionally inaccessible config directories.
    settings = directory / "settings.json"
    original = (ROOT / "Assets/settings-default.json").read_bytes()
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        path.touch(mode=0o600)
        path.write_bytes(original)
        assert path.read_bytes() == original, "fixture bytes differ"
        assert path.stat().st_mode & 0o777 == 0o600, "fixture mode differs"
    try:
        stage_runtime(directory)
        result = subprocess.run(
            helper("wallpaper-tab-warnings.test.py").sandbox_command(
                directory,
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            ),
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"
        assert settings.stat().st_mode & 0o777 == 0o600, "fixture settings mode changed"
        assert backup.stat().st_mode & 0o777 == 0o600, "fixture backup mode changed"
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, f"TimerCard runtime failed: {result.returncode}"
    assert "TIMER_CARD_BEHAVIOR_PASS" in output, "timer assertions did not finish"
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )


def lint_harness(directory, inject_warning):
    environment = isolate_environment(directory)
    stage_runtime(directory)
    harness = directory / "shell.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: harness",
                "id: harness\n  property int injectedWarning: harness.missingLintProbe",
                1,
            )
        )
    result = subprocess.run(
        helper("wallpaper-tab-warnings.test.py").sandbox_command(
            directory,
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
        ),
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout + result.stderr, flush=True)
    diagnostics = json.loads(result.stdout)
    warnings = sum(
        warning["type"] == "warning"
        for file in diagnostics["files"]
        for warning in file["warnings"]
    )
    print("TIMER_CARD_HARNESS_LINT_WARNINGS", warnings, "EXIT", result.returncode)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert result.returncode != 0, "injected warning accepted"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-timer-card-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if args.mode == "lint":
            run_lint(directory)
        elif args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory, args.inject_warning))
        else:
            run_behavior(directory)


if __name__ == "__main__":
    main()
