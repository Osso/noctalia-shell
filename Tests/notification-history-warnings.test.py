#!/usr/bin/env python3
"""Production history panel on offscreen QtTest; inert panel/widgets/services.

Real Repeater, list layout, filtering and handlers; no shell, toast, persistence,
compositor, desktop input or full widget rendering proof.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/NotificationHistory/NotificationHistoryPanel.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
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
    print("HISTORY_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    helpers = helper("workspace-runtime.test.py")
    write, singleton = helpers.write_module, helpers.singleton
    for uri in (
        "Quickshell",
        "Quickshell.Services.Notifications",
        "Quickshell.Wayland",
    ):
        write(directory, uri, {"Inert": "import QtQuick\nQtObject {}"})
    style = dict(
        uiScaleRatio=1,
        marginXS=2,
        marginS=4,
        marginM=8,
        marginL=12,
        radiusM=8,
        radiusL=12,
        borderS=1,
        baseWidgetSize=32,
        fontSizeXXS=8,
        fontSizeXS=10,
        fontSizeS=11,
        fontSizeM=12,
        fontSizeL=14,
        fontSizeXXL=20,
        fontWeightBold=700,
        opacityMedium=0.5,
        animationFast=0,
    )
    colors = dict(
        transparent="transparent",
        mPrimary="#00ff00",
        mOnPrimary="#000000",
        mHover="#404040",
        mOnHover="#ffffff",
        mOnSurface="#ffffff",
        mSurfaceVariant="#202020",
        mOnSurfaceVariant="#cccccc",
        mOutline="#808080",
        mError="#ff0000",
        mSecondary="#abcdef",
    )
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "\n".join(f"property real {k}: {v}" for k, v in style.items())
            ),
            "NColor": singleton(
                "\n".join(f'property color {k}: "{v}"' for k, v in colors.items())
            ),
            "Settings": singleton(
                "property var data: ({general: {animationDisabled: true}})"
            ),
            "I18n": singleton("function tr(key) { return key; }"),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "Time": singleton(
                "function formatRelativeTime(ts) { return new Date(ts).toISOString(); }"
            ),
            "NotificationService": singleton("""
property ListModel historyList: ListModel {}
property bool doNotDisturb: false
property int seenCount: 0
property var removed: []
function updateLastSeenTs() { seenCount++; }
function removeFromHistory(id) {
  removed = removed.concat([id]);
  for (let i = 0; i < historyList.count; i++) {
    if (historyList.get(i).id === id) { historyList.remove(i); return; }
  }
  throw new Error("Unknown notification " + id);
}
function clearHistory() { historyList.clear(); }
"""),
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property int closeCount: 0
  property alias contentItem: loader.item
  signal opened()
  function close() { closeCount++; }
  Loader { id: loader; anchors.fill: parent; sourceComponent: parent.panelContent }
}"""
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NBox": "import QtQuick\nRectangle {}",
            "NText": "import QtQuick\nText { property real pointSize; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize }",
            "NImageRounded": """import QtQuick
Item { property real radius; property string imagePath; property color borderColor
property real borderWidth; property string fallbackIcon; property real fallbackIconSize }""",
            "NIconButton": """import QtQuick
Item { property string icon; property string tooltipText; property real baseSize
width: baseSize; height: baseSize; signal clicked() }""",
            "NButton": """import QtQuick
Item { property string text; property real fontSize; property bool outlined
property bool hovered: false; property color backgroundColor; property color textColor
property color hoverColor; signal clicked() }""",
            "NScrollView": "import QtQuick.Controls\nScrollView {}",
        },
    )
    write(
        directory,
        "qs.Modules.Panels.NotificationHistory",
        {
            "NotificationHistoryPanel": (ROOT / TARGET).read_text(),
        },
    )
    (directory / "tst_history.qml").write_text(
        (ROOT / "Tests/Qml/NotificationHistoryWarningsHarness.qml").read_text()
    )


def runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    sha = hashlib.sha256(original).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == sha
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and k
        not in {
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "HOME",
            "NIRI_SOCKET",
            "HYPRLAND_INSTANCE_SIGNATURE",
            "SWAYSOCK",
        }
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    stage_runtime(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_history.qml"),
                "-import",
                str(directory),
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, result.returncode
        assert "0 failed" in output
        assert not re.search(r"QWARN|QFATAL|ReferenceError|TypeError", output), output
    finally:
        assert hashlib.sha256(settings.read_bytes()).hexdigest() == sha
        print("HISTORY_SETTINGS_SHA", sha)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-history-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
