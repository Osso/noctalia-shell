#!/usr/bin/env python3
"""Targeted notification lint and real component on private headless Cage.

Settings/service and widget boundaries are inert fixtures. Production notification
layout, actions, timers and Region objects remain real. Cage cannot prove desktop
layer-shell input delivery or cursor behavior.
"""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import sys

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Notification/Notification.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
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
    print("NOTIFICATION_LINT_COUNTS", dict(counts))
    # Repeater.itemAt() exposes QQuickItem, not the anonymous card's members.
    assert counts == {"missing-property": 3}, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    write = helper("media-mini-warnings").write_singleton
    target = directory / TARGET
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / TARGET, target)
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["general"]["animationDisabled"] = True
    defaults["notifications"].update(monitors=[], location="top_right")
    write(
        directory / "Commons", "Settings", "property var data: " + json.dumps(defaults)
    )
    style = dict(
        uiScaleRatio=1,
        marginM=8,
        marginS=4,
        marginL=12,
        marginXL=16,
        radiusL=12,
        radiusXS=2,
        borderS=1,
        barHeight=32,
        animationSlow=80,
        animationNormal=40,
        fontSizeXS=10,
        fontSizeXXS=8,
        fontSizeM=12,
        fontSizeS=10,
        fontWeightBold=700,
        fontWeightMedium=500,
        baseWidgetSize=32,
    )
    write(
        directory / "Commons",
        "Style",
        "\n".join(f"property real {key}: {value}" for key, value in style.items()),
    )
    colors = dict(
        mSurface="#202020",
        mOutline="#808080",
        mOnSurface="#ffffff",
        mPrimary="#00ff00",
        mError="#ff0000",
        mSecondary="#abcdef",
        mOnSurfaceVariant="#cccccc",
        mOnHover="#ffffff",
        mOnPrimary="#000000",
        mHover="#404040",
        transparent="transparent",
    )
    write(
        directory / "Commons",
        "NColor",
        "\n".join(f'property color {key}: "{value}"' for key, value in colors.items()),
    )
    write(directory / "Commons", "I18n", "function tr(key) { return key; }")
    write(
        directory / "Services/System",
        "Time",
        "function formatRelativeTime(timestamp) { return timestamp.toISOString(); }",
    )
    write(
        directory / "Services/System",
        "NotificationService",
        """
property ListModel activeList: ListModel {}
property var events: []
signal animateAndRemove(string notificationId)
function pauseTimeout(id) { events = events.concat(["pause:" + id]); }
function resumeTimeout(id) { events = events.concat(["resume:" + id]); }
function invokeAction(id, action) { events = events.concat(["action:" + id + ":" + action]); }
function removeFromHistory(id) { events = events.concat(["history:" + id]); }
function dismissActiveNotification(id) {
  events = events.concat(["dismiss:" + id]);
  for (let i = 0; i < activeList.count; i++) {
    if (activeList.get(i).id === id) { activeList.remove(i); break; }
  }
}""",
    )
    widgets = directory / "Widgets"
    widgets.mkdir()
    sources = {
        "NText": "Text { property real pointSize: 12; font.pointSize: pointSize }",
        "NDropShadow": "Item { property var source; property bool autoPaddingEnabled }",
        "NImageRounded": "Item { property real radius; property string imagePath; property color borderColor; property real borderWidth; property string fallbackIcon; property real fallbackIconSize }",
        "NButton": """Item { property string text; property real fontSize; property color backgroundColor
property color textColor; property color hoverColor; property bool outlined; property bool hovered: false
signal entered(); signal exited(); signal clicked(); implicitWidth: 80; implicitHeight: 24 }""",
        "NIconButton": """Item { property string icon; property string tooltipText; property real baseSize
signal clicked(); width: baseSize; height: baseSize }""",
    }
    for name, source in sources.items():
        (widgets / f"{name}.qml").write_text("import QtQuick\n" + source + "\n")
    shutil.copyfile(
        ROOT / "Tests/Qml/NotificationWarningsHarness.qml", directory / "shell.qml"
    )


def stage_harness_lint(directory):
    runtime = directory / "runtime"
    runtime.mkdir()
    stage_runtime(runtime)
    imports = directory / "imports"
    helper("media-mini-warnings").stage_modules(imports, source_root=runtime)
    return imports, imports / "qs/shell.qml"


def lint_harness(directory):
    imports, harness = stage_harness_lint(directory)
    return check_harness(imports, harness)


def lint_harness_regression(directory):
    clean = directory / "clean"
    clean.mkdir()
    assert lint_harness(clean) == 0, "clean harness lint failed"
    injected = directory / "injected"
    injected.mkdir()
    imports, harness = stage_harness_lint(injected)
    source = harness.read_text()
    marker = "id: harness"
    assert source.count(marker) == 1, "injection owner must be unique"
    harness.write_text(
        source.replace(
            marker,
            marker + "\n  property int injectedWarning: harness.missingLintProbe",
            1,
        )
    )
    assert check_harness(imports, harness) != 0, "genuine warning was accepted"
    print("NOTIFICATION_HARNESS_WARNING_REJECTED")


def behavior(directory):
    stage_runtime(directory)
    environment = helper("media-mini-warnings").isolate_environment(directory)
    environment.update(
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        QT_QPA_PLATFORM="wayland",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/notification-test",
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
        helper("osd-warnings").stop_process_group(process)
    output = stdout + stderr
    print(output, end="")
    assert process.returncode == 0, process.returncode
    assert "NOTIFICATION_BEHAVIOR_PASS" in output
    assert not re.search(
        r"(?: ERROR | FATAL | WARN scene:|ReferenceError|TypeError|Binding loop)",
        output,
    ), output
    print(
        "PLATFORM_LIMIT: no desktop input delivery/cursor proof; Cage lacks layer-shell"
    )


def deny_real_settings(event, args):
    if event == "open":
        path = args[0]
        if isinstance(path, (str, bytes, os.PathLike)):
            requested = Path(os.fsdecode(path)).absolute()
            protected = Path("/home/osso/.config/noctalia/settings.json")
            if requested == protected or requested.resolve() == protected.resolve():
                raise PermissionError(f"real settings access denied: {requested}")
    if event == "socket.connect":
        raise PermissionError("network access denied in notification fixture")


def main():
    sys.addaudithook(deny_real_settings)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "lint-harness", "lint-harness-regression", "behavior")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-notification-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        environment_directory = directory / "environment"
        environment_directory.mkdir(mode=0o700)
        environment = helper("media-mini-warnings").isolate_environment(
            environment_directory
        )
        os.environ.clear()
        os.environ.update(environment)
        try:
            sys.audit("open", "/home/osso/.config/noctalia/settings.json", "r", 0)
        except PermissionError:
            print("NOTIFICATION_REAL_SETTINGS_AUDIT_DENIED")
        else:
            raise AssertionError("real settings audit guard failed")
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        if args.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        else:
            (lint if args.mode == "lint" else behavior)(directory)


if __name__ == "__main__":
    main()
