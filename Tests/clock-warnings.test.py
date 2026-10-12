#!/usr/bin/env python3
"""Targeted Clock lint and actual offscreen widget with fixed Time/UI services.

Reuse weather's isolated paths and basic production text/icon fixtures; no live
clock scheduling, settings bootstrap, panels, desktop input, or persistence.
"""

import argparse
from collections import Counter
import json
import sys
import importlib.util
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Widgets/Clock.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


effects = load_helper("clock_fixtures", "weather-card-effects.test.py")
lint_fixture = load_helper("clock_lint", "media-mini-warnings.test.py")
isolation = load_helper("clock_isolation", "grid-list-warnings.test.py")
config_guard = load_helper("clock_config_guard", "simple-widgets-warnings.test.py")


def run_lint(directory, environment):
    lint_fixture.stage_modules(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "clock-lint",
    )
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
        for line in warnings
    )
    print("CLOCK_LINT_COUNTS", dict(counts))
    assert not warnings, f"Clock warnings remain: {dict(counts)}"
    assert code == 0, f"qmllint failed: {code}"
    print("CLOCK_LINT_PASS")


def stage_runtime(directory):
    effects.stage_card(directory)
    for path in (TARGET, Path("Widgets/NPopupContextMenu.qml")):
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    commons = directory / "Commons"
    with (commons / "Style.qml").open("r+") as source:
        style = source.read()
        source.seek(0)
        source.write(
            style.rsplit("}", 1)[0]
            + """
property real capsuleHeight: 32
property color capsuleColor: "#202020"
property real radiusS: 4
property real fontSizeS: 10
property real animationNormal: 0
}\n"""
        )
        source.truncate()
    with (commons / "NColor.qml").open("r+") as source:
        colors = source.read()
        source.seek(0)
        source.write(
            colors.rsplit("}", 1)[0]
            + """
property color mSurface: "#202020"
property color mHover: "#404040"
property color mOnHover: "#ffffff"
}\n"""
        )
        source.truncate()
    effects.write_singleton(
        commons,
        "I18n",
        'property var locale: Qt.locale("en_US")\nfunction tr(key) { return key; }',
    )
    effects.write_singleton(
        commons,
        "Time",
        """property date now: new Date(2026, 9, 11, 14, 30, 45)
property int secondUpdateRefs: 0
function beginSecondUpdates() { secondUpdateRefs++; }
function endSecondUpdates() { secondUpdateRefs--; }
function formatRequiresSeconds(format) { return /(^|[^A-Za-z])s{1,2}([^A-Za-z]|$)/.test(format); }""",
    )
    extras = directory / "Modules/Bar/Extras"
    extras.mkdir(parents=True)
    effects.write_singleton(
        extras,
        "BarWidgetRegistry",
        """property var widgetMetadata: ({Clock: {
usePrimaryColor: false, useCustomFont: false, customFont: "",
formatHorizontal: "HH:mm", formatVertical: "HH mm"
}})""",
    )
    ui = directory / "Services/UI"
    ui.mkdir(parents=True)
    effects.write_singleton(
        ui,
        "PanelService",
        """function getPopupMenuWindow(screen) { return null; }
function getPanel(name, screen) { return null; }""",
    )
    effects.write_singleton(
        ui,
        "BarService",
        """function getTooltipDirection() { return "bottom"; }
function openWidgetSettings(...args) {}
function getContextMenuPosition(...args) { return {x: 0, y: 0}; }""",
    )
    effects.write_singleton(
        ui,
        "TooltipService",
        """function show(...args) {}
function hide() {}""",
    )
    # Quickshell's qs imports map to the shell directory. Expose that same tree
    # to qmllint, with explicit singleton metadata shared by both commands.
    (directory / "qs").symlink_to(".", target_is_directory=True)
    for module in (
        commons,
        directory / "Widgets",
        directory / "Modules/Bar/Widgets",
        extras,
        ui,
    ):
        uri = "qs." + ".".join(module.relative_to(directory).parts)
        entries = []
        for source in sorted(module.glob("*.qml")):
            singleton = "singleton " if "pragma Singleton" in source.read_text() else ""
            entries.append(f"{singleton}{source.stem} 1.0 {source.name}\n")
        (module / "qmldir").write_text(f"module {uri}\n" + "".join(entries))
    shutil.copyfile(
        ROOT / "Tests/Qml/ClockWarningsHarness.qml", directory / "shell.qml"
    )


def run_harness_lint(directory, environment, inject_warning=False):
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
    code, output = isolation.run_audited(
        directory,
        environment,
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
        "clock-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for file in diagnostics["files"]
        for warning in file["warnings"]
    )
    print("CLOCK_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert code != 0, "injected warning accepted"
    assert not warnings or code != 0, "qmllint accepted harness warnings"
    return code


def run_behavior(directory, environment):
    stage_runtime(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
        "clock-runtime",
    )
    assert code == 0, f"Clock runtime failed: {code}"
    assert "CLOCK_BEHAVIOR_PASS" in output
    assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
        output
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-clock-warnings-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        sys.addaudithook(config_guard.deny_real_config)
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint-harness":
            raise SystemExit(
                run_harness_lint(directory, environment, args.inject_warning)
            )
        (run_lint if args.mode == "lint" else run_behavior)(directory, environment)


if __name__ == "__main__":
    main()
