#!/usr/bin/env python3
"""Bounded VPN production rows/list/panel proof; no backend or desktop access."""

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    Path(f"Modules/Panels/VPN/{name}.qml")
    for name in ("VPNConnectionItem", "VPNConnectionsList", "VPNPanel")
]


def fixture():
    spec = importlib.util.spec_from_file_location(
        "wifi_fixture", ROOT / "Tests/wifi-networks-list-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    fixture().load_staging().stage_modules(directory)
    residuals = {}
    exit_codes = {}
    for target in TARGETS:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / f"{target.stem}.lint.log").write_text(output)
        print(output, end="")
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        residuals[target.name] = len(warnings)
        exit_codes[target.name] = result.returncode
    print("VPN_RESIDUALS", residuals)
    assert not any(residuals.values()), residuals
    assert not any(exit_codes.values()), exit_codes


def stage_panel(directory):
    helpers = fixture()
    helpers.stage_list(directory)
    for target in TARGETS:
        destination = directory / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / target, destination)
    shutil.copyfile(
        ROOT / "Widgets/NScrollView.qml", directory / "Widgets/NScrollView.qml"
    )
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
    helpers.singleton(
        directory / "Services/Networking",
        "VPNService",
        """
property var connections: ({})
property bool refreshing: false
property string connectingUuid: ""
property string disconnectingUuid: ""
property string lastError: ""
property int pollingRefs: 0
property var requests: []
readonly property var activeConnections: Object.values(connections).filter(connection => connection.active)
readonly property var inactiveConnections: Object.values(connections).filter(connection => !connection.active)
function beginPolling() { pollingRefs++; }
function endPolling() { pollingRefs--; }
function refresh() { requests = requests.concat([{action: "refresh", uuid: ""}]); }
function connect(uuid) { connectingUuid = uuid; requests = requests.concat([{action: "connect", uuid: uuid}]); }
function disconnect(uuid) { disconnectingUuid = uuid; requests = requests.concat([{action: "disconnect", uuid: uuid}]); }
""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/VPNPanelWarningsHarness.qml", directory / "tst_vpn.qml"
    )


def behavior(directory):
    stage_panel(directory)
    result = subprocess.run(
        ["quickshell", "--no-color", "-p", str(directory / "tst_vpn.qml")],
        cwd=ROOT,
        env=fixture().isolated_environment(directory),
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "VPN_PANEL_BEHAVIOR_PASS" in output, output
    assert not re.search(
        r"\b(?:WARN|ERROR|FATAL)\b|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = Path("/home/osso/.config/noctalia/settings.json")
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
