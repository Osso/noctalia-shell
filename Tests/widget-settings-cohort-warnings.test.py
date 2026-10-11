#!/usr/bin/env python3
"""Five production widget editors/dialog, isolated offscreen controls and lint.

Fixture settings/services; no real persistence, desktop, or live hardware proof.
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
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("LockKeys", "ControlCenter", "SystemMonitor", "MediaMini", "Workspace")
EDITOR_DIR = Path("Modules/Panels/Settings/Bar/WidgetSettings")
FIXTURES = {
    "LockKeys": {
        "showCapsLock": True,
        "showNumLock": True,
        "showScrollLock": True,
        "capsLockIcon": "letter-c",
        "numLockIcon": "letter-n",
        "scrollLockIcon": "letter-s",
    },
    "ControlCenter": {
        "icon": "settings",
        "useDistroLogo": True,
        "customIconPath": "",
        "enableColorization": False,
        "colorizeSystemIcon": "none",
    },
    "SystemMonitor": {
        "usePrimaryColor": True,
        "showCpuUsage": True,
        "showCpuTemp": True,
        "showMemoryUsage": True,
        "showMemoryAsPercent": True,
        "showNetworkStats": True,
        "showDiskUsage": True,
        "diskPath": "/",
        "showFanSpeed": True,
    },
    "MediaMini": {
        "hideWhenIdle": False,
        "showAlbumArt": True,
        "showArtistFirst": True,
        "showVisualizer": True,
        "visualizerType": "linear",
        "scrollingMode": "always",
        "maxWidth": 240,
        "useFixedWidth": True,
        "showProgressRing": True,
    },
    "Workspace": {
        "labelMode": "name",
        "hideUnoccupied": True,
        "followFocusedScreen": True,
        "characterCount": 3,
    },
}


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(
        "cohort_helper", ROOT / "Tests" / filename
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def lint(directory):
    load_helper("media-mini-warnings.test.py").stage_modules(directory)
    failures = []
    for name in NAMES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / EDITOR_DIR / f"{name}Settings.qml"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / f"{name}.lint.log").write_text(output)
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
            for line in warnings
        )
        print(name, "LINT_COUNTS", dict(counts), "EXIT", result.returncode)
        if warnings or result.returncode:
            failures.append(name)
    assert not failures, f"Editor warnings remain: {failures}; see per-editor lint logs"


def stage_runtime(directory):
    helper = load_helper("clock-settings-warnings.test.py")
    helper.stage_runtime(directory)
    helper.write_module(
        directory,
        "qs.Modules.Panels.Settings.Bar.WidgetSettings",
        {
            f"{name}Settings": (ROOT / EDITOR_DIR / f"{name}Settings.qml").read_text()
            for name in NAMES
        },
    )
    helper.write_module(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": helper.singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
            "BarWidgetRegistry": helper.singleton(
                "property var widgetSettingsMap: "
                + json.dumps(
                    {name: f"WidgetSettings/{name}Settings.qml" for name in NAMES}
                )
                + "\nproperty var widgetMetadata: "
                + json.dumps(FIXTURES)
            ),
        },
    )
    helper.write_module(
        directory,
        "qs.Services.System",
        {
            "SystemStatService": helper.singleton(
                'property var diskPercents: ({"/": 12, "/data": 34})'
            ),
        },
    )
    helper.write_module(
        directory,
        "qs.Services.Hardware",
        {
            "FanService": helper.singleton("property bool available: true"),
        },
    )
    helper.write_module(
        directory,
        "Quickshell",
        {
            "Quickshell": helper.singleton(
                "function env(key) { return key === 'HOME' ? "
                + json.dumps(str(directory / "home"))
                + " : ''; }"
            ),
        },
    )
    helper.write_module(
        directory, "Quickshell.Io", {"Fixture": "import QtQuick\nQtObject {}"}
    )
    helper.write_module(
        directory,
        "qs.Commons",
        {
            path.stem: path.read_text()
            for path in (directory / "qs/Commons").glob("*.qml")
            if path.stem != "Icons"
        }
        | {
            "Icons": helper.singleton(
                'property string fontFamily: "DejaVu Sans"\nproperty var icons: ({})\nfunction get(key) { return ""; }'
            )
        },
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/WidgetSettingsCohortHarness.qml", directory / "tst_cohort.qml"
    )
    (directory / "tst_clock.qml").unlink()


def behavior(directory):
    stage_runtime(directory)
    helper = load_helper("datetime-tokens-layout-runtime.test.py")
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_cohort.qml"),
            "-import",
            str(directory),
        ],
        cwd=directory,
        env=helper.isolate_environment(directory),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "18 passed, 0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
        output,
    ), output
    print("WIDGET_SETTINGS_COHORT_BEHAVIOR_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(original)
    digest = hashlib.sha256(original).digest()
    assert backup.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(backup.read_bytes()).digest() == digest
    try:
        (lint if args.mode == "lint" else behavior)(args.artifacts)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest, "Backup changed"
    print("Real settings and backup unchanged; bounded child exited.")


if __name__ == "__main__":
    main()
