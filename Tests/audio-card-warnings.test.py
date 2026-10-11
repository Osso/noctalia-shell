#!/usr/bin/env python3
"""Bounded AudioCard lint and actual-QML behavior with isolated fake PipeWire."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CARD = Path("Modules/Cards/AudioCard.qml")


def fixture_helper():
    spec = importlib.util.spec_from_file_location(
        "media_fixture", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    shutil.copyfile(
        ROOT / "Tests/Qml/AudioCardHarness.qml", directory / "tst_audio_card.qml"
    )


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=fixture_helper().isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0 and "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-audio-card-") as temporary:
        directory = Path(temporary)
        (run_lint if args.mode == "lint" else run_behavior)(directory)


if __name__ == "__main__":
    main()
