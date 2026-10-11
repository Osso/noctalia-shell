#!/usr/bin/env python3
"""Bounded actual WiFiPanel proof with inert networking and offscreen hosting."""

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/WiFi/WiFiPanel.qml")


def list_fixture():
    spec = importlib.util.spec_from_file_location(
        "wifi_list_fixture", ROOT / "Tests/wifi-networks-list-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    list_fixture().load_staging().stage_modules(directory)
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
    print("WIFI_PANEL_WARNINGS", len(warnings))
    assert not warnings and result.returncode == 0, warnings


def stage_panel(directory):
    fixture = list_fixture()
    fixture.stage_list(directory)
    shutil.copyfile(ROOT / TARGET, directory / TARGET)
    host = directory / "Modules/MainScreen"
    host.mkdir(parents=True)
    (host / "SmartPanel.qml").write_text("""import QtQuick
Item {
  id: host
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool isPanelOpen: false
  signal opened()
  signal closed()
  function open() { host.isPanelOpen = true; host.opened(); }
  function close() { host.isPanelOpen = false; host.closed(); }
  Loader { anchors.fill: parent; active: host.isPanelOpen; sourceComponent: host.panelContent }
}
""")
    fixture.singleton(
        directory / "Commons",
        "Settings",
        """property QtObject network: QtObject { property bool wifiEnabled: true }
readonly property var data: ({network: network, ui: {fontDefault: "Sans Serif", fontFixed: "monospace", fontDefaultScale: 1, fontFixedScale: 1}})""",
    )
    fixture.singleton(
        directory / "Services/Networking",
        "NetworkService",
        """property var networks: ({})
property bool scanning: false
property string lastError: ""
property string connectingTo: ""
property string disconnectingFrom: ""
property string forgettingNetwork: ""
property bool connecting: false
property int polling: 0
property var requests: []
function record(action, ssid, password) { requests = requests.concat([{action: action, ssid: ssid || "", password: password || ""}]); }
function beginActivePolling() { polling++; }
function endActivePolling() { polling--; }
function setWifiEnabled(enabled) { Settings.data.network.wifiEnabled = enabled; record(enabled ? "enable" : "disable"); }
function scan() { record("scan"); }
function isSecured(security) { return security === "WPA2"; }
function signalIcon(signal, connected) { return connected ? "wifi" : "wifi-low"; }
function connect(ssid, password) { record("connect", ssid, password); }
function disconnect(ssid) { record("disconnect", ssid); }
function forget(ssid) { record("forget", ssid); }
""",
    )
    network = directory / "Services/Networking/NetworkService.qml"
    network.write_text(
        network.read_text().replace(
            "import QtQuick", "import QtQuick\nimport qs.Commons"
        )
    )
    style = directory / "Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "\n}",
            "\nreadonly property real fontWeightSemiBold: 600\nreadonly property real borderM: 1\n}",
        )
    )
    for name in ("NToggle", "NLabel", "NScrollView"):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", directory / f"Widgets/{name}.qml")
    shutil.copyfile(
        ROOT / "Tests/Qml/WiFiPanelWarningsHarness.qml", directory / "tst_wifi.qml"
    )


def behavior(directory):
    stage_panel(directory)
    result = subprocess.run(
        ["quickshell", "--no-color", "-p", str(directory / "tst_wifi.qml")],
        cwd=ROOT,
        env=list_fixture().isolated_environment(directory),
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "WIFI_PANEL_BEHAVIOR_PASS" in output, output
    assert not re.search(
        r"\b(?:WARN|ERROR|FATAL)\b|ReferenceError|TypeError|Binding loop", output
    ), output


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
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    try:
        (lint if args.mode == "lint" else behavior)(args.artifacts)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
