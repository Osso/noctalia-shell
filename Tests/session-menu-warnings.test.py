#!/usr/bin/env python3
"""Bounded production SessionMenu lint and offscreen behavior with inert backends.

Real menu, Repeater, PowerButton and Qt layouts/timer; panel shell and leaf
widgets are fixtures. No desktop surface, authorization, or backend-action proof.
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
TARGET = Path("Modules/Panels/SessionMenu/SessionMenu.qml")


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
    print("SESSION_MENU_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    helpers = helper("about-tab-warnings.test.py")
    write, singleton = helpers.write_module, helpers.singleton
    for uri in ("Quickshell.Wayland", "Quickshell.Widgets"):
        write(directory, uri, {"Inert": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton(
                'function execDetached(argv) { throw new Error("Forbidden process launch: " + argv); }'
            )
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "Process": """import QtQuick
QtObject {
  property var command: []
  property bool running: false
  onRunningChanged: if (running) throw new Error("Forbidden process launch: " + command)
}"""
        },
    )
    style = dict(
        uiScaleRatio=1,
        marginS=4,
        marginM=8,
        marginL=12,
        radiusS=4,
        radiusL=12,
        borderM=2,
        baseWidgetSize=32,
        fontSizeS=11,
        fontSizeM=12,
        fontSizeL=14,
        fontSizeXXL=20,
        fontWeightBold=700,
        fontWeightMedium=500,
        animationFast=0,
    )
    colors = dict(
        transparent="transparent",
        mPrimary="#00ff00",
        mOnPrimary="#000000",
        mHover="#404040",
        mOnHover="#ffffff",
        mOnSurface="#ffffff",
        mOutline="#808080",
        mError="#ff0000",
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
            "I18n": singleton(
                'function tr(key, values) { return values ? key + ":" + values.action + ":" + values.seconds : key; }'
            ),
            "Settings": """pragma Singleton
import QtQuick
QtObject {
  property QtObject data: QtObject {
    property QtObject general: QtObject { property bool lockOnSuspend: false }
    property QtObject sessionMenu: QtObject {
      property bool showHeader: true
      property string position: "center"
      property int countdownDuration: 60000
      property bool enableCountdown: true
      property var powerOptions: []
    }
  }
}""",
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": singleton("""
property var events: []
function suspend() { events = events.concat(["suspend"]); }
function lockAndSuspend() { events = events.concat(["lockAndSuspend"]); }
function hibernate() { events = events.concat(["hibernate"]); }
function reboot() { events = events.concat(["reboot"]); }
function logout() { events = events.concat(["logout"]); }
function shutdown() { events = events.concat(["shutdown"]); }
""")
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton(
                "property QtObject lockScreen: QtObject { property bool active: false }"
            )
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  id: panel
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool panelAnchorHorizontalCenter
  property bool panelAnchorVerticalCenter
  property bool panelAnchorLeft
  property bool panelAnchorRight
  property bool panelAnchorBottom
  property bool panelAnchorTop
  property int closeCount: 0
  property alias contentItem: loader.item
  signal opened()
  signal closed()
  function close() { closeCount++; closed(); }
  Loader { id: loader; anchors.fill: parent; sourceComponent: panel.panelContent }
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
            "NDivider": "import QtQuick\nRectangle { implicitHeight: 1 }",
            "NIconButton": """import QtQuick
Item {
  property string icon
  property string tooltipText
  property real baseSize
  property color colorBg
  property color colorFg
  implicitWidth: baseSize
  implicitHeight: baseSize
  signal clicked()
}""",
        },
    )
    write(
        directory,
        "qs.Modules.Panels.SessionMenu",
        {"SessionMenu": (ROOT / TARGET).read_text()},
    )
    (directory / "tst_session_menu.qml").write_text(
        (ROOT / "Tests/Qml/SessionMenuWarningsHarness.qml").read_text()
    )


def runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    sha = hashlib.sha256(original).hexdigest()
    assert backup.stat().st_mode & 0o777 == 0o600
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
                str(directory / "tst_session_menu.qml"),
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
        print("SESSION_MENU_SETTINGS_SHA", sha)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-session-menu-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
