#!/usr/bin/env python3
"""Targeted production tray drawer lint and isolated offscreen Loader regression.

Desktop panel, popup and notifier boundaries are fixtures; drawer bindings,
Repeater delegates, icon sources and mouse handlers are unmodified production.
Pin/unpin is exercised through settings changes, not a live tray menu/service.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Tray/TrayDrawerPanel.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load_helper("tray_runtime_helpers", "workspace-runtime.test.py")


def lint(directory):
    load_helper("tray_lint_staging", "media-mini-warnings.test.py").stage_modules(
        directory
    )
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
    warnings = re.findall(r"^Warning:.*$", output, re.M)
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("TRAY_DRAWER_LINT_COUNTS", dict(counts))
    # Keep only two explicit creation-site owner captures (without Bound),
    # UntypedObjectModel.values metadata, and Loader.item's QObject type gap.
    blocks = re.split(r"(?=Warning:)", output)[1:]
    captures = [block for block in blocks if "[unqualified]" in block]
    assert len(captures) == 2, "Unexpected owner captures:\n" + "".join(captures)
    assert all("ComponentBehavior: Bound" in block for block in captures)
    assert counts.get("missing-property") == 2, dict(counts)
    assert counts.get("incompatible-type") == 1, dict(counts)
    assert set(counts) == {"unqualified", "missing-property", "incompatible-type"}, (
        dict(counts)
    )
    metadata = [block for block in blocks if "[missing-property]" in block]
    assert (
        sum(
            'Member "values" not found on type "UntypedObjectModel"' in block
            for block in metadata
        )
        == 2
    )
    incompatible = [block for block in blocks if "[incompatible-type]" in block]
    assert "Cannot assign binding of type QObject to TrayMenu" in incompatible[0]
    assert result.returncode in (0, 255), result.returncode
    print("TRAY_DRAWER_LINT_PASS")


def stage_runtime(directory):
    write = helpers.write_module
    singleton = helpers.singleton
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Quickshell": singleton('property string shellDir: ""'),
        },
    )
    write(
        directory,
        "Quickshell.Services.SystemTray",
        {
            "SystemTray": singleton(
                "property QtObject items: QtObject { property var values: [] }"
            ),
        },
    )
    write(
        directory,
        "Quickshell.Widgets",
        {
            "IconImage": """import QtQuick
Item {
  property string source
  property bool asynchronous
  property alias backer: image
  Image { id: image }
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("""property var data: ({bar: {position: "top", widgets: {left: [], right: []}}, colorSchemes: {darkMode: true}})
signal settingsSaved
"""),
            "Style": singleton(
                "property real capsuleHeight: 40; property real marginM: 8; property real marginS: 4"
            ),
            "NColor": singleton(
                'property color mOnSurface: "white"; property color mSurfaceVariant: "gray"'
            ),
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "PopupMenuWindow": """import QtQuick
import qs.Modules.Bar.Extras
Item {
  visible: false
  readonly property alias trayMenuLoader: menuLoader
  property int opens: 0
  property int closes: 0
  function open() { opens++; visible = true; }
  function close() { closes++; visible = false; }
  Loader { id: menuLoader; sourceComponent: TrayMenu {} }
}""",
            "SmartPanel": """import QtQuick
import Quickshell
Item {
  property ShellScreen screen
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool exclusiveKeyboard
  property bool isClosing: false
  property int closeCount: 0
  property alias contentItem: contentLoader.item
  function close() { closeCount++; visible = false; }
  Loader { id: contentLoader; anchors.fill: parent; sourceComponent: parent.panelContent }
}""",
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("""property QtObject popup
property QtObject openedPanel
signal popupMenuWindowRegistered(var registeredScreen)
function getPopupMenuWindow(screen) { return popup; }
"""),
            "TooltipService": singleton("""property string text: ""
property Item anchor
function hideImmediately() { text = ""; }
function hide() { text = ""; }
function show(item, title, direction) { anchor = item; text = title; }
"""),
            "BarService": singleton(
                'function getTooltipDirection() { return "bottom"; }'
            ),
        },
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "TrayMenu": """import QtQuick
Item {
  width: 120
  property var trayItem
  property string widgetSection
  property int widgetIndex
  property Item anchor
  property real menuX
  property real menuY
  function showAt(item, x, y) { anchor = item; menuX = x; menuY = y; }
}"""
        },
    )
    write(directory, "qs.Widgets", {"NText": "import QtQuick\nText {}"})
    write(
        directory,
        "qs.Modules.Panels.Tray",
        {"TrayDrawerPanel": (ROOT / TARGET).read_text()},
    )
    (directory / "tst_tray_drawer.qml").write_text(
        (ROOT / "Tests/Qml/TrayDrawerWarningsHarness.qml").read_text()
    )


def runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    if original is not None:
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert (
            hashlib.sha256(backup.read_bytes()).digest()
            == hashlib.sha256(original).digest()
        )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key
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
                str(directory / "tst_tray_drawer.qml"),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"Offscreen drawer exit {result.returncode}"
        assert "0 failed" in output
        assert not re.search(r"QWARN|QFATAL|ReferenceError|TypeError", output), output
        print("TRAY_DRAWER_RUNTIME_PASS")
    finally:
        assert (settings.read_bytes() if settings.exists() else None) == original, (
            "real settings changed"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("lint", "runtime"), required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-tray-drawer-") as temporary:
        {"lint": lint, "runtime": runtime}[args.mode](Path(temporary))
