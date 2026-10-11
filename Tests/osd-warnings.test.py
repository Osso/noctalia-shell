#!/usr/bin/env python3
"""Bounded OSD lint and production-component behavior on private headless Cage.

Cage has no layer-shell integration. Platform warnings remain visible; assertions
cover component state/content/timers, not rendered pixels or output-layer placement.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/OSD/OSD.qml")


def staging_helpers():
    spec = importlib.util.spec_from_file_location(
        "osd_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    staging_helpers().stage_modules(directory)
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
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("OSD_LINT_COUNTS", dict(counts))
    # Existing unbound nested-component context and screen metadata gaps remain.
    assert counts == {"unqualified": 37, "missing-property": 5}, dict(counts)
    assert result.returncode == 0, result.returncode
    print("OSD_LINT_SLICE_PASS (remaining diagnostics above)")


def stage_osd(directory):
    helpers = staging_helpers()
    for relative in [TARGET, Path("Helpers/BrightnessParsing.js")] + [
        Path(f"Widgets/{name}.qml") for name in ("NIcon", "NText", "NDropShadow")
    ]:
        destination = directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["osd"].update(
        enabled=True, monitors=[], enabledTypes=[], autoHideMs=240, location="top_right"
    )
    defaults["general"]["enableShadows"] = False
    helpers.write_singleton(
        directory / "Commons", "Settings", "property var data: " + json.dumps(defaults)
    )
    style = {
        "uiScaleRatio": 1,
        "marginM": 8,
        "marginS": 4,
        "marginL": 12,
        "marginXL": 16,
        "radiusL": 12,
        "borderM": 2,
        "barHeight": 32,
        "animationNormal": 0,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXL": 18,
        "fontWeightMedium": 500,
        "fontWeightRegular": 400,
        "shadowOpacity": 0,
        "shadowBlur": 0,
        "shadowBlurMax": 0,
    }
    helpers.write_singleton(
        directory / "Commons",
        "Style",
        "\n".join(
            f"readonly property real {key}: {value}" for key, value in style.items()
        ),
    )
    colors = {
        "mSurface": "#202020",
        "mSurfaceVariant": "#303030",
        "mOutline": "#808080",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#cccccc",
        "mPrimary": "#abcdef",
        "mError": "#ff0000",
        "transparent": "transparent",
        "black": "#000000",
    }
    helpers.write_singleton(
        directory / "Commons",
        "NColor",
        "\n".join(
            f'readonly property color {key}: "{value}"' for key, value in colors.items()
        ),
    )
    helpers.write_singleton(
        directory / "Commons",
        "Icons",
        """readonly property string defaultIcon: "volume-high"
readonly property string fontFamily: "sans-serif"
function get(name) { return name; }""",
    )
    helpers.write_singleton(
        directory / "Commons",
        "Logger",
        """function w(...args) { console.warn(...args); }
function callStack() { throw new Error("Unexpected icon"); }""",
    )
    helpers.write_singleton(
        directory / "Services/Media",
        "AudioService",
        """property real volume: 0.25
property bool muted: false
property real inputVolume: 0.4
property bool inputMuted: false
property bool hasInput: true
signal sinkChanged()
signal sourceChanged()
function consumeOutputOSDSuppression() { return false; }
function consumeInputOSDSuppression() { return false; }""",
    )
    helpers.write_singleton(
        directory / "Services/Hardware",
        "BrightnessService",
        """property var monitors: [monitor]
property QtObject monitor: QtObject { signal brightnessUpdated(real value) }""",
    )
    helpers.write_singleton(
        directory / "Services/Keyboard",
        "LockKeysService",
        """property bool capsLockOn: false
property bool numLockOn: false
property bool scrollLockOn: false
signal capsLockChanged(bool active)
signal numLockChanged(bool active)
signal scrollLockChanged(bool active)""",
    )
    helpers.write_singleton(
        directory / "Services/Power",
        "PowerProfileService",
        "property bool noctaliaPerformanceMode: false",
    )
    shutil.copyfile(ROOT / "Tests/Qml/OSDWarningsHarness.qml", directory / "shell.qml")


def stop_process_group(process):
    # Cage, Quickshell and possible Xwayland descendants share this private group.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    original_sha = hashlib.sha256(original).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == original_sha
    stage_osd(directory)
    environment = staging_helpers().isolate_environment(directory)
    environment.update(
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        QT_QPA_PLATFORM="wayland",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/osd-test-system",
    )
    process = subprocess.Popen(
        ["cage", "--", "quickshell", "--no-color", "-p", str(directory / "shell.qml")],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=18)
        except subprocess.TimeoutExpired:
            stop_process_group(process)
            stdout, stderr = process.communicate(timeout=3)
            print(stdout + stderr, end="")
            raise
    finally:
        stop_process_group(process)
        assert hashlib.sha256(settings.read_bytes()).hexdigest() == original_sha, (
            "real settings changed"
        )
        print("OSD_SETTINGS_SHA", original_sha)
    output = stdout + stderr
    print(output, end="")
    assert process.returncode == 0, process.returncode
    assert "OSD_BEHAVIOR_PASS" in output, "assertions did not finish"
    assert not re.search(
        r"(?: ERROR | FATAL | WARN scene:|ReferenceError|TypeError|Binding loop)",
        output,
    ), output
    print(
        "OSD_PLATFORM_LIMIT: Cage lacks layer-shell; warnings retained, no pixel/output-layer proof"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-osd-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        (lint if args.mode == "lint" else behavior)(directory)


if __name__ == "__main__":
    main()
