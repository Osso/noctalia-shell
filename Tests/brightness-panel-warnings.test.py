#!/usr/bin/env python3
"""BrightnessPanel-only lint and offscreen actual-slider proof; inert providers.

Production panel, NValueSlider, NSlider and NScrollView run unchanged. Monitor,
brightness, panel host and leaf presentation widgets are fixtures. No hardware,
real settings persistence, visible surface or whole-shell acceptance is tested.
"""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Brightness/BrightnessPanel.qml")


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
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint.log").write_text(output)
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("BRIGHTNESS_PANEL_WARNINGS", len(warnings))
    assert not warnings, warnings
    assert result.returncode == 0, result.returncode


def stage_behavior(directory):
    helpers = helper("about-tab-warnings.test.py")
    write, singleton = helpers.write_module, helpers.singleton
    write(
        directory,
        "qs.Modules.Panels.Brightness",
        {"BrightnessPanel": (ROOT / TARGET).read_text()},
    )
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": """import QtQuick
QtObject {
  property string name
  property string model
  property int width
  property int height
}""",
            "Quickshell": singleton("property var screens: []"),
        },
    )
    # The original panel imports Io but never uses it; keep an inert module for RED.
    write(directory, "Quickshell.Io", {"Inert": "import QtQuick\nQtObject {}"})
    style = dict(
        uiScaleRatio=1,
        marginS=4,
        marginM=8,
        marginL=12,
        radiusM=8,
        radiusL=12,
        baseWidgetSize=32,
        fontSizeM=12,
        fontSizeL=14,
        fontSizeXL=18,
        fontSizeXXL=20,
        fontWeightBold=700,
        sliderWidth=240,
        borderS=1,
        borderL=2,
        animationFast=0,
    )
    colors = dict(
        mPrimary="#abcdef",
        mSurface="#202020",
        mOnSurface="#ffffff",
        mOutline="#808080",
        mHover="#404040",
        transparent="transparent",
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
                'readonly property var data: ({ui: {fontFixed: "monospace"}})'
            ),
            "I18n": singleton(
                "function tr(key, values) { return values ? JSON.stringify(values) : key; }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": singleton(
                'function getDisplayScale(name) { return name === "eDP-1" ? 1.5 : 1; }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton("function show() {}\nfunction hide() {}"),
        },
    )
    monitor = """QtObject {
  property real brightness: INITIAL
  property bool brightnessControlAvailable: AVAILABLE
  property var writes: []
  function setBrightness(value) { writes = writes.concat([value]); brightness = value; }
}"""
    provider = "\n".join(
        f"property QtObject {name}: "
        + monitor.replace("INITIAL", str(value)).replace("AVAILABLE", available)
        for name, value, available in (
            ("internalMonitor", 0.25, "true"),
            ("externalMonitor", 0.6, "false"),
            ("replacementMonitor", 0.4, "true"),
        )
    )
    provider += """
readonly property bool enableDdcSupport: false
function getMonitorForScreen(screen) {
  if (!screen) return null;
  if (screen.name === "eDP-1") return internalMonitor;
  if (screen.name === "DP-1") return externalMonitor;
  if (screen.name === "fake-replacement") return replacementMonitor;
  return null;
}
"""
    write(directory, "qs.Services.Hardware", {"BrightnessService": singleton(provider)})
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  id: host
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property int closeCount: 0
  property alias contentItem: loader.item
  function close() { host.closeCount++; }
  Loader { id: loader; anchors.fill: parent; sourceComponent: host.panelContent }
}""",
        },
    )
    widgets = {
        name: (ROOT / f"Widgets/{name}.qml").read_text()
        for name in ("NValueSlider", "NSlider", "NScrollView")
    }
    widgets.update(
        {
            "NBox": "import QtQuick\nRectangle {}",
            "NText": "import QtQuick\nText { property real pointSize; property string family; font.pointSize: pointSize; font.family: family }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize; implicitWidth: 24; implicitHeight: 24 }",
            "NLabel": "import QtQuick\nItem { property string label; property color labelColor; property string description; implicitHeight: 30 }",
            "NIconButton": "import QtQuick\nItem { property string icon; property string tooltipText; property real baseSize; implicitWidth: baseSize; implicitHeight: baseSize; signal clicked() }",
        }
    )
    write(directory, "qs.Widgets", widgets)
    (directory / "tst_brightness.qml").write_text(
        (ROOT / "Tests/Qml/BrightnessPanelWarningsHarness.qml").read_text()
    )


def isolated_environment(directory):
    excluded = {
        "HOME",
        "DISPLAY",
        "DBUS_SESSION_BUS_ADDRESS",
        "DBUS_SYSTEM_BUS_ADDRESS",
        "NIRI_SOCKET",
        "HYPRLAND_INSTANCE_SIGNATURE",
        "SWAYSOCK",
    }
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in excluded
        and not k.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
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
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent-brightness-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent-brightness-system",
    )
    return environment


def behavior(directory):
    stage_behavior(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_brightness.qml"),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=isolated_environment(directory),
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def runtime_identity():
    processes = subprocess.run(
        ["pgrep", "-af", "^quickshell"], capture_output=True, text=True, timeout=10
    )
    assert processes.returncode == 0, processes.stderr
    registry = subprocess.run(
        ["quickshell", "list", "--all"], capture_output=True, text=True, timeout=10
    )
    assert registry.returncode == 0, registry.stderr
    # Elapsed uptime changes; PID, instance, launch time, config and display must not.
    stable = re.sub(r" \(running for [^\n]*\)", "", registry.stdout)
    return processes.stdout, stable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = args.artifacts / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert backup.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    identity = runtime_identity()
    (args.artifacts / "canonical-runtime.txt").write_text("\n".join(identity))
    try:
        {"lint": lint, "behavior": behavior}[args.mode](args.artifacts)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"
        assert runtime_identity() == identity, "canonical process/registry changed"
        print("CANONICAL_RUNTIME_UNCHANGED")
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
