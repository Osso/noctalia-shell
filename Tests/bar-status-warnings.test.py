#!/usr/bin/env python3
"""Four production status widgets: per-file lint and isolated offscreen behavior.

Real buttons, pills, spectra, loaders and animations; inert services and popup
surface. Standalone test, no real radio, recorder, notification or settings IO.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("NotificationHistory", "ScreenRecorder", "WiFi", "AudioVisualizer")
EXPECTED = {
    "NotificationHistory": {"unqualified": 3, "block-scope-var-declaration": 4},
    "ScreenRecorder": {},
    "WiFi": {"block-scope-var-declaration": 1},
    "AudioVisualizer": {"unqualified": 6, "block-scope-var-declaration": 2},
}


def load_helper(name):
    sys.path.insert(0, str(ROOT / "Tests"))
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def stage_behavior(directory):
    controls = load_helper("bar-controls-warnings")
    controls.stage(directory)
    (directory / "tst_bar_controls.qml").unlink()
    helper = load_helper("workspace-runtime")
    singleton = helper.singleton

    def add(uri, sources):
        controls.add_module(helper, directory, uri, sources)

    add("Quickshell.Wayland", {"InertBoundary": "import QtQuick\nQtObject {}"})
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {",
            "QtObject {\nproperty real radiusXS: 2\nproperty real radiusS: 4\nproperty real marginS: 4\nproperty real animationSlow: 160",
        )
    )
    colors = directory / "qs/Commons/NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "QtObject {", 'QtObject {\nproperty color mOnPrimary: "white"'
        )
    )
    add(
        "qs.Services.System",
        {
            "NotificationService": singleton("""property bool doNotDisturb: false
property real lastSeenTs: 100
property ListModel historyList: ListModel {}
function clearHistory() { historyList.clear(); }""")
        },
    )
    add(
        "qs.Services.Media",
        {
            "ScreenRecorderService": singleton("""property bool isAvailable: true
property bool isRecording: false
property bool isPending: false
property int stopCount: 0
property int toggleCount: 0
property var captureSources: [{label: "Display", action: "screen"}, {label: "Window", action: "window"}]
function stopRecording() { stopCount++; isPending = false; isRecording = false; }
function toggleRecording() { toggleCount++; isPending = true; }"""),
            "MediaService": singleton("property bool isPlaying: true"),
            "CavaService": singleton("property var values: [0.2, 0.6, 0.9]"),
        },
    )
    add(
        "qs.Services.Networking",
        {
            "NetworkService": singleton("""property bool ethernetConnected: false
property bool internetConnectivity: true
property var networks: ({"FixtureNet": {connected: true, signal: 80}})
property var requests: []
function signalIcon(strength, connected) { return strength >= 60 ? "wifi" : "wifi-1"; }
function setWifiEnabled(value) { requests = requests.concat([value]); }""")
        },
    )
    add(
        "qs.Services.UI",
        {
            "ToastService": singleton("""property var errors: []
function showError(title, description) { errors = errors.concat([{title: title, description: description}]); }""")
        },
    )
    add(
        "qs.Widgets.AudioSpectrum",
        {
            name: (ROOT / f"Widgets/AudioSpectrum/{name}.qml").read_text()
            for name in ("NLinearSpectrum", "NMirroredSpectrum", "NWaveSpectrum")
        },
    )
    add(
        "qs.Modules.Bar.Widgets",
        {
            name: (ROOT / f"Modules/Bar/Widgets/{name}.qml").read_text()
            for name in NAMES
        },
    )
    (directory / "tst_bar_status.qml").write_text(
        (ROOT / "Tests/Qml/BarStatusHarness.qml").read_text()
    )


def behavior(directory):
    stage_behavior(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=load_helper("media-mini-warnings").isolate_environment(directory),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def lint(directory):
    load_helper("media-mini-warnings").stage_modules(directory)
    failures = []
    for name in NAMES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "--bare",
                "-I",
                str(directory),
                "-I",
                "/usr/lib/qt6/qml",
                "--json",
                "-",
                str(directory / f"qs/Modules/Bar/Widgets/{name}.qml"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / f"{name}.lint.log").write_text(output)
        warnings = [
            warning
            for warning in json.loads(result.stdout)["files"][0]["warnings"]
            if warning["type"] == "warning"
        ]
        counts = Counter(warning["id"] for warning in warnings)
        print(
            name,
            "LINT_COUNTS",
            dict(counts),
            "EXPECTED",
            EXPECTED[name],
            "EXIT",
            result.returncode,
        )
        if counts != EXPECTED[name] or result.returncode != 0:
            failures.append(name)
    assert not failures, failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    if args.artifacts:
        args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
        directory = args.artifacts
    else:
        temporary = tempfile.TemporaryDirectory(prefix="noctalia-bar-status-")
        directory = Path(temporary.name)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    try:
        (lint if args.mode == "lint" else behavior)(directory)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
