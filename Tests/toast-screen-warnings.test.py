#!/usr/bin/env python3
"""Bounded ToastScreen lint and production lifecycle/Region offscreen proof.

Private headless Cage, no desktop connection, real notifications, or settings
bootstrap. Production ToastScreen/SimpleToast remain real; widgets and service
boundaries are inert. Cage lacks layer-shell: no mask, margin, input delivery,
layer placement, or cursor-flicker proof.
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
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Toast/ToastScreen.qml")


def helpers():
    spec = importlib.util.spec_from_file_location(
        "toast_staging", ROOT / "Tests/media-mini-warnings.test.py"
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
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("TOAST_SCREEN_LINT_COUNTS", dict(counts))
    assert counts == {"missing-property": 6, "unqualified": 2}, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    write = helpers().write_singleton
    for relative in (TARGET, Path("Modules/Toast/SimpleToast.qml")):
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["notifications"].update(location="top_right", overlayLayer=True)
    defaults["bar"].update(
        position="top", floating=True, marginVertical=2, marginHorizontal=3
    )
    write(
        directory / "Commons", "Settings", "property var data: " + json.dumps(defaults)
    )
    style = dict(
        uiScaleRatio=1,
        marginM=8,
        marginL=12,
        marginXL=16,
        marginXXS=2,
        radiusL=12,
        borderM=2,
        barHeight=32,
        animationNormal=0,
        animationFast=20,
        fontSizeXXL=20,
        fontSizeL=14,
        fontSizeM=12,
        fontWeightBold=700,
    )
    write(
        directory / "Commons",
        "Style",
        "\n".join(f"property real {key}: {value}" for key, value in style.items()),
    )
    colors = dict(
        mSurface="#202020",
        mPrimary="#00ff00",
        mError="#ff0000",
        mOutline="#808080",
        mOnSurface="#ffffff",
        transparent="transparent",
    )
    write(
        directory / "Commons",
        "NColor",
        "\n".join(f'property color {key}: "{value}"' for key, value in colors.items()),
    )
    write(directory / "Commons", "Logger", "function d(...args) {}")
    write(
        directory / "Services/UI",
        "ToastService",
        "signal notify(string message, string description, string icon, string type, int duration)",
    )
    widgets = directory / "Widgets"
    widgets.mkdir()
    for name, source in {
        "NText": "Text { property real pointSize: 12; font.pointSize: pointSize }",
        "NIcon": 'Text { property string icon; property real pointSize: 12; text: "*"; font.pointSize: pointSize }',
        "NDropShadow": "Item { property Item source; property bool autoPaddingEnabled }",
    }.items():
        (widgets / f"{name}.qml").write_text("import QtQuick\n" + source + "\n")
    shutil.copyfile(
        ROOT / "Tests/Qml/ToastScreenWarningsHarness.qml", directory / "shell.qml"
    )


def lint_harness(directory):
    runtime = directory / "runtime"
    runtime.mkdir()
    stage_runtime(runtime)
    imports = directory / "imports"
    helpers().stage_modules(imports, source_root=runtime)
    return check_harness(imports, imports / "qs/shell.qml")


def behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    stage_runtime(directory)
    environment = helpers().isolate_environment(directory)
    environment.update(
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/toast-test",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/toast-test",
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        QT_QPA_PLATFORM="wayland",
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
        stdout, stderr = process.communicate(timeout=15)
    finally:
        spec = importlib.util.spec_from_file_location(
            "toast_cleanup", ROOT / "Tests/osd-warnings.test.py"
        )
        cleanup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cleanup)
        cleanup.stop_process_group(process)
        assert settings.read_bytes() == original, "real settings changed"
        print("TOAST_SETTINGS_SHA", digest)
    output = stdout + stderr
    print(output, end="")
    assert process.returncode == 0, process.returncode
    assert "TOAST_SCREEN_BEHAVIOR_PASS" in output
    assert not re.search(
        r"(?: ERROR | FATAL | WARN scene:|ReferenceError|TypeError|Binding loop)",
        output,
    ), output
    print(
        "PLATFORM_LIMIT: Cage lacks layer-shell; no mask/margin/input delivery or cursor-flicker proof"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-toast-screen-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        (lint if args.mode == "lint" else behavior)(directory)


if __name__ == "__main__":
    main()
