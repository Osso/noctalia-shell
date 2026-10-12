#!/usr/bin/env python3
"""Bounded actual WiFiPanel proof with inert networking and offscreen hosting."""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/Panels/WiFi/WiFiPanel.qml")


def list_fixture():
    spec = importlib.util.spec_from_file_location(
        "wifi_list_fixture", ROOT / "Tests/wifi-networks-list-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolation_fixture():
    spec = importlib.util.spec_from_file_location(
        "wifi_isolation", ROOT / "Tests/grid-list-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = isolation_fixture()


def run_audited(directory, environment, command, label):
    # A short, private mount keeps Quickshell IPC below Unix socket path limits.
    child_environment = dict(environment, XDG_RUNTIME_DIR="/run/wifi-fixture")
    trace = directory / f"{label}.trace"
    result = subprocess.run(
        [
            "/usr/bin/strace",
            "-f",
            "-qq",
            "-e",
            "trace=%file",
            "-o",
            str(trace),
            "/usr/bin/bwrap",
            "--die-with-parent",
            "--unshare-net",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--ro-bind",
            "/etc/fonts",
            "/etc/fonts",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--bind",
            str(directory),
            str(directory),
            "--bind",
            environment["XDG_RUNTIME_DIR"],
            "/run/wifi-fixture",
            "--chdir",
            str(directory),
            "--",
            *command,
        ],
        cwd=directory,
        env=child_environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    accesses = trace.read_text()
    assert "settings.json" not in accesses, (
        "SETTINGS_AUDIT_DENIED: child settings attempt"
    )
    output = result.stdout + result.stderr
    (directory / f"{label}.log").write_text(output)
    print(
        f"CHILD_SETTINGS_AUDIT: {label} zero settings attempts; host home/config not mounted"
    )
    print(output, end="")
    return result.returncode, output


def lint(directory, environment):
    list_fixture().load_staging().stage_modules(directory)
    code, output = run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "panel-lint",
    )
    (directory / "lint.log").write_text(output)
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("WIFI_PANEL_WARNINGS", len(warnings), "EXIT", code)
    assert not warnings and code == 0, (code, warnings)


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
    # Both Qt tools import these exact staged runtime files, never host qs metadata.
    for relative in (
        "Commons",
        "Widgets",
        "Services/UI",
        "Services/Networking",
        "Modules/MainScreen",
        "Modules/Panels/WiFi",
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
        ROOT / "Tests/Qml/WiFiPanelWarningsHarness.qml", directory / "tst_wifi.qml"
    )


def check_harness(directory, environment, label):
    code, output = run_audited(
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
            str(directory / "tst_wifi.qml"),
        ],
        label,
    )
    (directory / f"{label}.log").write_text(output)
    diagnostics = [
        diagnostic
        for file in json.loads(output)["files"]
        for diagnostic in file["warnings"]
        if diagnostic["type"] in ("warning", "error")
    ]
    counts = Counter(diagnostic["id"] for diagnostic in diagnostics)
    print("WIFI_PANEL_HARNESS_LINT_COUNTS", dict(counts), "EXIT", code)
    return code, diagnostics


def lint_harness(directory, environment):
    stage_panel(directory)
    code, diagnostics = check_harness(directory, environment, "harness-lint")
    assert code == 0 and not diagnostics, (code, diagnostics)


def lint_harness_regression(directory, environment):
    lint_harness(directory, environment)
    harness = directory / "tst_wifi.qml"
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
    print("WIFI_PANEL_HARNESS_WARNING_REJECTED")


def behavior(directory, environment):
    stage_panel(directory)
    code, output = run_audited(
        directory,
        environment,
        ["/usr/bin/quickshell", "--no-color", "-p", str(directory / "tst_wifi.qml")],
        "behavior",
    )
    (directory / "behavior.log").write_text(output)
    assert code == 0 and "WIFI_PANEL_BEHAVIOR_PASS" in output, output
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
    isolation.install_settings_guard(args.artifacts)
    isolation.prove_settings_guard()
    environment = isolation.isolated_environment(args.artifacts)
    globals()[args.mode.replace("-", "_")](args.artifacts, environment)


if __name__ == "__main__":
    main()
