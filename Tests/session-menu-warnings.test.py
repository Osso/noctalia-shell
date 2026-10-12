#!/usr/bin/env python3
"""Bounded production SessionMenu lint and offscreen behavior with inert backends.

Real menu, Repeater, PowerButton and Qt layouts/timer; panel shell and leaf
widgets are fixtures. No desktop surface, authorization, or backend-action proof.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
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
  component GeneralSettings: QtObject { property bool lockOnSuspend: false }
  component SessionMenuSettings: QtObject {
      property bool showHeader: true
      property string position: "center"
      property int countdownDuration: 60000
      property bool enableCountdown: true
      property var powerOptions: []
  }
  component SettingsData: QtObject {
    property GeneralSettings general: GeneralSettings {}
    property SessionMenuSettings sessionMenu: SessionMenuSettings {}
  }
  property SettingsData data: SettingsData {}
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
                "component LockScreen: QtObject { property bool active: false }\nproperty LockScreen lockScreen: LockScreen {}"
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


def runtime(directory, environment, isolation):
    settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
    settings.parent.mkdir(mode=0o700, parents=True)
    settings.touch(mode=0o600)
    settings.write_bytes(b'{"fixture": "session-menu"}\n')
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    sha = hashlib.sha256(original).hexdigest()
    assert backup.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == sha
    stage_runtime(directory)
    try:
        result = subprocess.run(
            isolation.sandbox_command(
                directory,
                [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    str(directory / "tst_session_menu.qml"),
                    "-import",
                    str(directory),
                ],
            ),
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


def lint_harness(directory, environment, isolation, inject_warning):
    stage_runtime(directory)
    harness = directory / "tst_session_menu.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: scene",
                "id: scene\n  property int injectedWarning: scene.missingLintProbe",
                1,
            )
        )
    result = subprocess.run(
        isolation.sandbox_command(
            directory,
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
        ),
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout + result.stderr, flush=True)
    diagnostics = json.loads(result.stdout)
    warnings = sum(
        warning["type"] == "warning"
        for file in diagnostics["files"]
        for warning in file["warnings"]
    )
    print("SESSION_MENU_HARNESS_LINT_WARNINGS", warnings, "EXIT", result.returncode)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert result.returncode != 0, "injected warning accepted"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime", "lint-harness"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-session-menu-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = helper("wallpaper-tab-warnings.test.py")
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            lint(directory)
        elif args.mode == "lint-harness":
            raise SystemExit(
                lint_harness(directory, environment, isolation, args.inject_warning)
            )
        else:
            runtime(directory, environment, isolation)
