#!/usr/bin/env python3
"""Targeted Battery lint and isolated production widget/pill regression."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Widgets/Battery.qml")
SETTINGS = Path("/home/osso/.config/noctalia/settings.json")


def load_staging():
    spec = importlib.util.spec_from_file_location(
        "media_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_staging().stage_modules(directory)
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
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "block-var"
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("BATTERY_WIDGET_LINT_COUNTS", dict(counts))
    assert not counts, f"Battery warnings remain: {dict(counts)}"
    assert result.returncode == 0, result.returncode


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def write_module(directory, uri, sources):
    path = directory.joinpath(*uri.split("."))
    path.mkdir(parents=True, exist_ok=True)
    declarations = ["module " + uri]
    for name, source in sources.items():
        (path / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml")
    (path / "qmldir").write_text("\n".join(declarations) + "\n")


def stage_widget(directory):
    write_module(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Singleton": "import QtQuick\nQtObject {}",
        },
    )
    write_module(directory, "Quickshell.Io", {"Fixture": "import QtQuick\nQtObject {}"})
    write_module(
        directory,
        "Quickshell.Services.UPower",
        {
            "UPowerDevice": """import QtQuick
QtObject {
  property string nativePath: "BAT0"
  property int type: UPowerDeviceType.Battery
  property bool ready: true
  property bool isPresent: true
  property real percentage: 0.65
  property int state: UPowerDeviceState.Discharging
  property int timeToEmpty: 7200
  property int timeToFull: 0
  property real changeRate: 12.5
  property real healthPercentage: 85
}""",
            "UPowerDeviceType": singleton("enum Type { Battery, LinePower, Mouse }"),
            "UPowerDeviceState": singleton(
                "enum State { Discharging, Charging, FullyCharged }"
            ),
            "UPower": singleton("""property UPowerDevice displayDevice: UPowerDevice {}
property UPowerDevice peripheral: UPowerDevice { nativePath: "bluetooth/aa:bb:cc:dd:ee:ff"; type: UPowerDeviceType.Mouse }
property var devices: ({values: [displayDevice, peripheral]})"""),
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["bar"].update(position="top", density="comfortable")
    defaults["bar"]["widgets"]["left"] = [
        {"id": "Battery", "displayMode": "alwaysShow", "warningThreshold": 20}
    ]
    defaults["ui"].update(fontDefault="Sans Serif", fontFixed="monospace")
    style = dict(
        uiScaleRatio=1,
        marginM=8,
        marginS=4,
        marginXS=3,
        marginXXS=2,
        radiusM=8,
        radiusL=12,
        borderS=1,
        capsuleHeight=32,
        animationNormal=0,
        animationFast=0,
        fontSizeS=10,
        fontSizeM=12,
        fontWeightMedium=500,
        fontWeightBold=700,
        opacityFull=1,
        opacityNone=0,
        pillDelay=10,
        tooltipDelay=10,
        tooltipDelayLong=10,
    )
    colors = dict(
        mSurface="#202020",
        mOnSurface="#ffffff",
        mOnSurfaceVariant="#dddddd",
        mPrimary="#3355aa",
        mOnPrimary="#ffffff",
        mError="#cc2233",
        mOnError="#ffff00",
        mOutline="#808080",
        mHover="#404040",
        mOnHover="#ffffff",
        transparent="transparent",
    )
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(
                    f"property real {key}: {value}" for key, value in style.items()
                )
                + '\nproperty color capsuleColor: "#202020"'
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {key}: "{value}"' for key, value in colors.items()
                )
            ),
            "I18n": singleton(
                "function tr(key, params) { return key + (params ? ':' + JSON.stringify(params) : ''); }"
            ),
            "Time": singleton(
                "function formatVagueHumanReadableDuration(seconds) { return seconds + ' seconds'; }"
            ),
            "Icons": singleton(
                "property string defaultIcon: 'battery'\nproperty string fontFamily: 'Sans Serif'\nfunction get(icon) { return icon; }"
            ),
            "Logger": singleton(
                "function w(...args) { console.warn(...args); }\nfunction callStack() { console.trace(); }"
            ),
        },
    )
    write_module(
        directory,
        "qs.Modules.Bar.Extras",
        {
            **{
                name: (ROOT / f"Modules/Bar/Extras/{name}.qml").read_text()
                for name in ("BarPill", "BarPillHorizontal", "BarPillVertical")
            },
            "BarWidgetRegistry": singleton(
                'property var widgetMetadata: ({Battery: {displayMode: "alwaysShow", warningThreshold: 20}})'
            ),
        },
    )
    write_module(
        directory,
        "qs.Widgets",
        {
            **{
                name: (ROOT / f"Widgets/{name}.qml").read_text()
                for name in ("NText", "NIcon")
            },
            # Popup windows are a desktop boundary; never construct a surface here.
            "NPopupContextMenu": "import QtQuick\nItem { property var model; signal triggered(string action) }",
        },
    )
    write_module(
        directory,
        "qs.Services.Hardware",
        {
            "BatteryService": (
                ROOT / "Services/Hardware/BatteryService.qml"
            ).read_text(),
        },
    )
    write_module(
        directory,
        "qs.Services.Networking",
        {
            "BluetoothService": singleton("""property QtObject headphones: QtObject {
property string address: "AA:BB:CC:DD:EE:FF"
property bool batteryAvailable: true
property real battery: 0.43
property bool connected: true
}
property var devices: ({values: [headphones]})"""),
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "ToastService": singleton(
                "property var warnings: []\nfunction showWarning(title, message) { warnings = warnings.concat([{title: title, message: message}]); }"
            ),
            "PanelService": singleton(
                "function getPopupMenuWindow(screen) { return null; }\nfunction getPanel(...args) { return null; }"
            ),
            "BarService": singleton(
                "function getPillDirection(widget) { return false; }\nfunction getTooltipDirection() { return 'bottom'; }\nfunction openWidgetSettings(...args) {}"
            ),
            "TooltipService": singleton(
                "function show(...args) {}\nfunction hide() {}\nfunction updateText(text) {}"
            ),
        },
    )
    write_module(
        directory, "qs.BatteryWidget", {"Battery": (ROOT / TARGET).read_text()}
    )
    (directory / "tst_battery.qml").write_text(
        (ROOT / "Tests/Qml/BatteryWidgetWarningsHarness.qml").read_text()
    )


def lint_harness(directory):
    stage_widget(directory)
    return check_harness(directory, directory / "tst_battery.qml")


def behavior(directory):
    stage_widget(directory)
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for name in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/battery-widget-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/battery-widget-system",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_battery.qml"),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, "Production Battery widget failed"
    assert not re.search(r"\b(?:QWARN|WARN|ERROR|FATAL)\b", output), output
    assert "BATTERY_WIDGET_BEHAVIOR_PASS" in output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-battery-widget-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        original = SETTINGS.read_bytes()
        backup = directory / "settings-backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        digest = hashlib.sha256(original).hexdigest()
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
        try:
            (lint if args.mode == "lint" else behavior)(directory)
        finally:
            assert hashlib.sha256(SETTINGS.read_bytes()).hexdigest() == digest, (
                "Real settings changed"
            )
            print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
