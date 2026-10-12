#!/usr/bin/env python3
"""Bounded VPN production rows/list/panel proof; no backend or desktop access."""

import argparse
from collections import Counter
import json
import importlib.util
from pathlib import Path
import re
import shutil

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


def audited_fixture():
    spec = importlib.util.spec_from_file_location(
        "vpn_isolation", ROOT / "Tests/wifi-panel-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory, environment):
    fixture().load_staging().stage_modules(directory)
    residuals = {}
    exit_codes = {}
    for target in TARGETS:
        code, output = audited_fixture().run_audited(
            directory,
            environment,
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
            target.stem + "-lint",
        )
        (directory / f"{target.stem}.lint.log").write_text(output)
        print(output, end="")
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        residuals[target.name] = len(warnings)
        exit_codes[target.name] = code
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
    # Lint and runtime resolve the same fake services and production panel files.
    for relative in (
        "Commons",
        "Widgets",
        "Services/UI",
        "Services/Networking",
        "Modules/MainScreen",
        "Modules/Panels/WiFi",
        "Modules/Panels/VPN",
    ):
        module = directory / relative
        entries = ["module qs." + relative.replace("/", ".")]
        for source in sorted(module.glob("*.qml")):
            prefix = (
                "singleton "
                if source.read_text().startswith("pragma Singleton")
                else ""
            )
            entries.append(f"{prefix}{source.stem} 1.0 {source.name}")
        (module / "qmldir").write_text("\n".join(entries) + "\n")
    (directory / "qs").symlink_to(".", target_is_directory=True)
    shutil.copyfile(
        ROOT / "Tests/Qml/VPNPanelWarningsHarness.qml", directory / "tst_vpn.qml"
    )


def check_harness(directory, environment, label):
    code, output = audited_fixture().run_audited(
        directory,
        environment,
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
            str(directory / "tst_vpn.qml"),
        ],
        label,
    )
    diagnostics = [
        diagnostic
        for file in json.loads(output)["files"]
        for diagnostic in file["warnings"]
        if diagnostic["type"] in ("warning", "error")
    ]
    counts = Counter(diagnostic["id"] for diagnostic in diagnostics)
    print("VPN_PANEL_HARNESS_LINT_COUNTS", dict(counts), "EXIT", code)
    return code, diagnostics


def lint_harness(directory, environment):
    stage_panel(directory)
    code, diagnostics = check_harness(directory, environment, "harness-lint")
    assert code == 0 and not diagnostics, (code, diagnostics)


def lint_harness_regression(directory, environment):
    lint_harness(directory, environment)
    harness = directory / "tst_vpn.qml"
    source = harness.read_text()
    marker = "id: harness"
    assert source.count(marker) == 1, "injection owner must be unique"
    harness.write_text(
        source.replace(
            marker,
            marker + "\n  property int injectedWarning: harness.missingLintProbe",
            1,
        )
    )
    code, diagnostics = check_harness(directory, environment, "harness-injected")
    assert code != 0, "injected diagnostic was accepted"
    assert any(
        diagnostic["id"] == "missing-property"
        and "missingLintProbe" in diagnostic["message"]
        for diagnostic in diagnostics
    ), diagnostics
    print("VPN_PANEL_HARNESS_WARNING_REJECTED")


def behavior(directory, environment):
    stage_panel(directory)
    code, output = audited_fixture().run_audited(
        directory,
        environment,
        ["/usr/bin/quickshell", "--no-color", "-p", str(directory / "tst_vpn.qml")],
        "behavior",
    )
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert code == 0 and "VPN_PANEL_BEHAVIOR_PASS" in output, output
    assert not re.search(
        r"\b(?:WARN|ERROR|FATAL)\b|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    isolation = audited_fixture().isolation
    isolation.install_settings_guard(args.artifacts)
    isolation.prove_settings_guard()
    environment = isolation.isolated_environment(args.artifacts)
    globals()[args.mode.replace("-", "_")](args.artifacts, environment)


if __name__ == "__main__":
    main()
