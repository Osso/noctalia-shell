#!/usr/bin/env python3
"""Bounded AudioCard lint and actual-QML behavior with isolated fake PipeWire."""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CARD = Path("Modules/Cards/AudioCard.qml")


def fixture_helper():
    spec = importlib.util.spec_from_file_location(
        "media_fixture", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolation_helper():
    spec = importlib.util.spec_from_file_location(
        "audio_isolation", ROOT / "Tests/audio-notification-settings-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ISOLATION = isolation_helper()


def write_module(directory, uri, files):
    target = directory.joinpath(*uri.split("."))
    target.mkdir(parents=True, exist_ok=True)
    declarations = [f"module {uri}\n"]
    for name, source in files.items():
        (target / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml\n")
    (target / "qmldir").write_text("".join(declarations))


def run_lint(directory):
    fixture_helper().stage_modules(directory)
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
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "block-scope-var"
        for line in warnings
    )
    print("AUDIO_CARD_LINT_COUNTS", dict(counts))
    assert not warnings, f"AudioCard warnings remain: {dict(counts)}"
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    write_module(
        directory, "qs.Modules.Cards", {"AudioCard": (ROOT / CARD).read_text()}
    )
    write_module(
        directory,
        "qs.Services.Media",
        {
            "AudioService": (ROOT / "Services/Media/AudioService.qml").read_text(),
        },
    )
    write_module(
        directory,
        "qs.Widgets",
        {
            name: (ROOT / f"Widgets/{name}.qml").read_text()
            for name in ("NBox", "NSlider", "NIconButton", "NText", "NIcon")
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    style = {
        "uiScaleRatio": 1,
        "marginM": 8,
        "marginXS": 3,
        "marginXXS": 2,
        "radiusM": 8,
        "radiusL": 12,
        "borderS": 1,
        "borderL": 2,
        "baseWidgetSize": 32,
        "sliderWidth": 160,
        "animationFast": 0,
        "animationNormal": 0,
        "fontSizeXS": 9,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontWeightMedium": 500,
        "opacityFull": 1,
        "opacityMedium": 0.5,
    }
    colors = {
        "mSurfaceVariant": "#202020",
        "mSurface": "#303030",
        "mOutline": "#808080",
        "mPrimary": "#abcdef",
        "mError": "#ff0000",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#dddddd",
        "mHover": "#404040",
        "mOnHover": "#ffffff",
        "transparent": "transparent",
    }
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": "pragma Singleton\nimport QtQuick\nQtObject { property var data: "
            + json.dumps(defaults)
            + " }",
            "Style": "pragma Singleton\nimport QtQuick\nQtObject {\n"
            + "\n".join(
                f"readonly property real {key}: {value}" for key, value in style.items()
            )
            + "\n}",
            "NColor": "pragma Singleton\nimport QtQuick\nQtObject {\n"
            + "\n".join(
                f"readonly property color {key}: {json.dumps(value)}"
                for key, value in colors.items()
            )
            + "\n}",
            "Icons": "pragma Singleton\nimport QtQuick\nQtObject {\n"
            'readonly property string defaultIcon: "volume-high"\n'
            'readonly property string fontFamily: "sans-serif"\n'
            'function get(name) { return "*"; }\n}',
            "Logger": "pragma Singleton\nimport QtQuick\nQtObject {\n"
            "function w(...args) { console.warn(...args); }\n"
            "function callStack() { console.trace(); }\n}",
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": "pragma Singleton\nimport QtQuick\nQtObject {\n"
            "function show(...args) {}\nfunction hide() {}\n}",
        },
    )
    write_module(directory, "Quickshell", {"Singleton": "import QtQuick\nItem {}"})
    write_module(
        directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"}
    )
    write_module(
        directory,
        "Quickshell.Services.Pipewire",
        {
            "PwNodeAudio": "import QtQuick\nQtObject {\n"
            "property real volume: 0.4\nproperty bool muted: false\n}",
            "PwNode": "import QtQuick\nQtObject {\n"
            'property int nodeId: 1\nreadonly property int id: nodeId\nproperty string description: "Device"\n'
            "property bool ready: true\nproperty bool isSink: true\n"
            'property bool isStream: false\nproperty string type: ""\n'
            "property PwNodeAudio audio: PwNodeAudio {}\n}",
            "PwObjectTracker": "import QtQuick\nQtObject { property var objects: [] }",
            "Pipewire": "pragma Singleton\nimport QtQuick\nQtObject {\n"
            "property bool ready: true\nproperty var nodes: ({values: []})\n"
            "property PwNode preferredDefaultAudioSink: null\n"
            "property PwNode preferredDefaultAudioSource: null\n"
            "readonly property PwNode defaultAudioSink: preferredDefaultAudioSink\n"
            "readonly property PwNode defaultAudioSource: preferredDefaultAudioSource\n}",
        },
    )
    harness = directory / "tst_audio_card.qml"
    shutil.copyfile(ROOT / "Tests/Qml/AudioCardHarness.qml", harness)
    return harness


def lint_harness(directory, stage, label, inject_warning=False):
    harness = stage(directory)
    if inject_warning:
        source = harness.read_text()
        marker = "id: scene"
        assert source.count(marker) == 1, "harness scene must be unique"
        harness.write_text(
            source.replace(
                marker,
                marker + "\n  property int injectedWarning: scene.missingLintProbe",
                1,
            )
        )
    code, output = ISOLATION.run_child(
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
        directory,
        ISOLATION.isolated_environment(directory),
    )
    diagnostics = [
        warning
        for result in json.loads(output)["files"]
        for warning in result["warnings"]
    ]
    warnings = sum(warning["type"] == "warning" for warning in diagnostics)
    print(label, "HARNESS_WARNINGS", warnings, "EXIT", code, flush=True)
    if inject_warning:
        assert any(
            "missingLintProbe" in warning["message"] for warning in diagnostics
        ), output
        assert warnings > 0 and code != 0, "semantic warning accepted"
    else:
        assert not diagnostics, output
        assert code == 0, code
    return code


def run_behavior(directory, stage, passed):
    harness = stage(directory)
    code, output = ISOLATION.run_child(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ],
        directory,
        ISOLATION.isolated_environment(directory),
    )
    assert code == 0 and f"{passed} passed, 0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def run_main(stage, lint, label, passed, runner):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    sys.addaudithook(ISOLATION.audit)
    with (
        patch("os.stat", ISOLATION.guard_metadata(os.stat)),
        patch("os.lstat", ISOLATION.guard_metadata(os.lstat)),
        patch("os.readlink", ISOLATION.guard_metadata(os.readlink)),
    ):
        ISOLATION.prove_denial()
        if args.sandbox:
            directory = args.sandbox
            mounts = Path("/proc/self/mountinfo").read_text()
            for path in ("/home", "/syncthing", "/run"):
                assert any(
                    line.split()[4] == path and " - tmpfs " in line
                    for line in mounts.splitlines()
                ), path
            if args.mode == "lint":
                lint(directory)
            elif args.mode == "behavior":
                run_behavior(directory, stage, passed)
            elif args.mode == "lint-harness":
                raise SystemExit(
                    lint_harness(directory, stage, label, args.inject_warning)
                )
            else:
                for name, injected in (("clean", False), ("injected", True)):
                    staged = directory / name
                    staged.mkdir(mode=0o700)
                    lint_harness(staged, stage, label, injected)
                print(label, "HARNESS_WARNING_REJECTED", flush=True)
            return
        with tempfile.TemporaryDirectory(
            prefix="noctalia-" + label.lower() + "-"
        ) as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
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
                temporary,
                temporary,
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                temporary,
                "--",
                "/usr/bin/python3",
                str(runner),
                args.mode,
                "--sandbox",
                temporary,
            ]
            if args.inject_warning:
                command.append("--inject-warning")
            code, _ = ISOLATION.run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


def main():
    run_main(stage_runtime, run_lint, "AUDIO_CARD", 8, Path(__file__).absolute())


if __name__ == "__main__":
    main()
