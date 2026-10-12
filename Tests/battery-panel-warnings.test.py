#!/usr/bin/env python3
"""BatteryPanel-only lint and offscreen presentation/selection regression.

UPower and desktop/service boundaries are inert fixtures, never production types
for lint. Positive changeRate magnitudes exercise both states; no watts row exists.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Battery/BatteryPanel.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_behavior(directory):
    fixture = helper("process-panel-warnings.test.py")
    fixture.stage_behavior(directory)
    write = helper("battery-widget-warnings.test.py").write_module
    singleton = helper("battery-widget-warnings.test.py").singleton
    write(
        directory,
        "qs.Modules.Panels.Battery",
        {
            "BatteryPanel": (ROOT / TARGET).read_text(),
        },
    )
    write(directory, "Quickshell", {"Singleton": "import QtQuick\nQtObject {}"})
    write(directory, "Quickshell.Io", {"Fixture": "import QtQuick\nQtObject {}"})
    write(directory, "qs.Services.UI", {"Fixture": "import QtQuick\nQtObject {}"})
    # A Loader supplies a real context; collisions must not redirect panel bindings.
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
  property bool isPanelOpen: true
  property int closeCount: 0
  property alias contentItem: loader.item
  function close() { host.closeCount++; host.isPanelOpen = false; }
  Loader {
    id: loader
    anchors.fill: parent
    active: host.isPanelOpen
    sourceComponent: host.panelContent
    property string iconName: "loader-shadow"
    property string timeText: "loader-shadow"
    property int percent: 3
    property bool isReady: false
    property bool healthAvailable: false
    property int healthPercent: 3
  }
}
"""
        },
    )
    write(
        directory,
        "Quickshell.Services.UPower",
        {
            "UPowerDevice": """import QtQuick
QtObject {
  property string nativePath: "BAT0"
  property int type: UPowerDeviceType.Battery
  property bool ready: true
  property bool isPresent: true
  property bool isLaptopBattery: true
  property string model: "Internal battery"
  property real percentage: 0.65
  property int state: UPowerDeviceState.Discharging
  property int timeToEmpty: 7200
  property int timeToFull: 3600
  property real changeRate: 12.5
  property bool healthSupported: true
  property real healthPercentage: 85
}
""",
            "UPowerDeviceType": singleton("enum Type { Battery, LinePower, Mouse }"),
            "UPowerDeviceState": singleton(
                "enum State { Discharging, Charging, FullyCharged }"
            ),
            "UPower": singleton("""property UPowerDevice displayDevice: UPowerDevice {}
component DeviceList: QtObject { property var values: [] }
property DeviceList devices: DeviceList {}
"""),
        },
    )
    write(
        directory,
        "qs.Services.Hardware",
        {
            "BatteryService": (
                ROOT / "Services/Hardware/BatteryService.qml"
            ).read_text(),
        },
    )
    write(
        directory,
        "qs.Services.Networking",
        {
            "BluetoothService": singleton(
                "component DeviceList: QtObject { property var values: [] }\n"
                "property DeviceList devices: DeviceList {}"
            ),
        },
    )
    commons = directory / "qs/Commons"
    settings = commons / "Settings.qml"
    settings.write_text(
        settings.read_text().replace(
            "readonly property var data:", "property var data:"
        )
    )
    with (commons / "Style.qml").open("r+") as stream:
        source = stream.read().replace("\n}", "\nproperty real radiusL: 12\n}")
        stream.seek(0)
        stream.write(source)
        stream.truncate()
    (commons / "I18n.qml").write_text(
        singleton(
            "function tr(key, values) { return key + (values ? ':' + JSON.stringify(values) : ''); }"
        )
    )
    (commons / "Time.qml").write_text(
        singleton(
            "function formatVagueHumanReadableDuration(seconds) { return seconds + ' seconds'; }"
        )
    )
    with (commons / "qmldir").open("a") as stream:
        stream.write("singleton Time 1.0 Time.qml\n")
    (directory / "tst_process.qml").unlink()
    (directory / "tst_battery_panel.qml").write_text(
        (ROOT / "Tests/Qml/BatteryPanelWarningsHarness.qml").read_text()
    )


def lint_harness(directory):
    stage_behavior(directory)
    return check_harness(directory, directory / "tst_battery_panel.qml")


def lint_harness_regression(directory):
    clean = directory / "clean"
    clean.mkdir()
    assert lint_harness(clean) == 0, "clean harness lint failed"
    injected = directory / "injected"
    injected.mkdir()
    stage_behavior(injected)
    harness = injected / "tst_battery_panel.qml"
    source = harness.read_text()
    marker = "id: suite"
    assert source.count(marker) == 1, "injection owner must be unique"
    harness.write_text(
        source.replace(
            marker,
            marker + "\n  property int injectedWarning: suite.missingLintProbe",
            1,
        )
    )
    assert check_harness(injected, harness) != 0, "genuine warning was accepted"
    print("BATTERY_PANEL_HARNESS_WARNING_REJECTED")


def run_proof(directory, mode):
    if mode == "lint-harness":
        assert lint_harness(directory) == 0, "harness lint failed"
        return
    if mode == "lint-harness-regression":
        lint_harness_regression(directory)
        return
    if mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
        environment = None
    else:
        stage_behavior(directory)
        command = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_battery_panel.qml"),
            "-import",
            str(directory),
        ]
        environment = helper(
            "wifi-networks-list-warnings.test.py"
        ).isolated_environment(directory)
    result = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60
    )
    output = result.stdout + result.stderr
    (directory / f"{mode}.log").write_text(output)
    print(output, end="")
    if mode == "lint":
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "var-hoisting"
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print("BATTERY_PANEL_LINT_COUNTS", dict(counts), "EXIT", result.returncode)
        assert not counts, dict(counts)
    else:
        assert "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
            output,
        ), output
    assert result.returncode == 0, result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
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
        run_proof(args.artifacts, args.mode)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest, "Backup changed"
        print("Real settings/backup unchanged; bounded offscreen runner exited.")


if __name__ == "__main__":
    main()
