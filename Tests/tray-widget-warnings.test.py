#!/usr/bin/env python3
"""Production Tray + installed IconImage, offscreen with inert desktop boundaries."""

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
TARGET = Path("Modules/Bar/Widgets/Tray.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load_helper("tray_widget_helpers", "workspace-runtime.test.py")


def lint(directory):
    load_helper("tray_widget_lint", "media-mini-warnings.test.py").stage_modules(
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
    print("TRAY_WIDGET_LINT_COUNTS", dict(counts))
    blocks = re.split(r"(?=Warning:)", output)[1:]
    actionable = [block for block in blocks if "[unqualified]" in block]
    assert not actionable, "Known-owner accesses remain:\n" + "".join(actionable)
    assert set(counts) <= {"unqualified", "missing-property", "incompatible-type"}, (
        dict(counts)
    )
    # Explicit delegate inputs expose QObject popup/Loader.item metadata gaps.
    # Repeater.itemAdded exposes QQuickItem, not the delegate's binding method.
    # Runtime fixtures exercise those boundaries; no casts mask metadata gaps.
    assert counts.get("missing-property") == 19, dict(counts)
    assert counts.get("incompatible-type") == 1, dict(counts)
    assert result.returncode in (0, 255), result.returncode
    print("TRAY_WIDGET_LINT_PASS")


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
            "IconImage": Path(
                "/usr/lib/qt6/qml/Quickshell/Widgets/IconImage.qml"
            ).read_text(),
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                'property var data: ({bar: {position: "top", density: false, widgets: {left: []}}, colorSchemes: {darkMode: true}})\nsignal settingsSaved'
            ),
            "Style": singleton(
                'property real capsuleHeight: 40; property real barHeight: 40; property real marginM: 8; property real marginXS: 3; property real radiusM: 8; property color capsuleColor: "black"'
            ),
            "NColor": singleton(
                'property color transparent: "transparent"; property color mOnSurface: "white"; property color mOnPrimary: "white"; property color mSurfaceVariant: "gray"'
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Logger": singleton(
                "function d(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("""property QtObject popup
property QtObject openedPanel
property QtObject drawer
signal popupMenuWindowRegistered(var registeredScreen)
function getPopupMenuWindow(screen) { return popup; }
function getPanel(name, screen) { return drawer; }
"""),
            "TooltipService": singleton("""property string text: ""
property Item anchor
function hideImmediately() { text = ""; }
function hide() { text = ""; }
function show(item, title, direction) { anchor = item; text = title; }
"""),
            "BarService": singleton(
                'function getTooltipDirection() { return "bottom"; }\nfunction getPillDirection(item) { return false; }'
            ),
        },
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "BarWidgetRegistry": singleton(
                "property var widgetMetadata: ({Tray: {blacklist: [], pinned: [], drawerEnabled: true}})"
            ),
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NIconButton": """import QtQuick
Item {
  property string tooltipText
  property string tooltipDirection
  property bool density
  property real baseSize
  property bool applyUiScale
  property color colorBg
  property color colorFg
  property color colorBorder
  property color colorBorderHover
  property string icon
  signal clicked
  signal rightClicked
}"""
        },
    )
    write(directory, "qs.Modules.Bar.Widgets", {"Tray": (ROOT / TARGET).read_text()})
    (directory / "tst_tray_widget.qml").write_text(
        (ROOT / "Tests/Qml/TrayWidgetWarningsHarness.qml").read_text()
    )
    # Local SVG reaches real Image.Ready without icon themes/providers or DBus.
    (directory / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>'
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
                str(directory / "tst_tray_widget.qml"),
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
        assert result.returncode == 0, f"Offscreen Tray exit {result.returncode}"
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
        print("TRAY_WIDGET_RUNTIME_PASS")
    finally:
        assert (settings.read_bytes() if settings.exists() else None) == original, (
            "real settings changed"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("lint", "runtime"), required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-tray-widget-") as temporary:
        {"lint": lint, "runtime": runtime}[args.mode](Path(temporary))
