#!/usr/bin/env python3
"""ProcessPanel-only lint and actual offscreen panel with recorded IO boundaries."""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Process/ProcessPanel.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_proof(directory, mode):
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
            str(directory / "tst_process.qml"),
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
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        print("PROCESS_PANEL_WARNINGS", len(warnings))
        assert not warnings, warnings
    else:
        assert "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output
    assert result.returncode == 0, result.returncode


def stage_behavior(directory):
    fixture = helper("about-tab-warnings.test.py")
    write, singleton = fixture.write_module, fixture.singleton
    write(
        directory,
        "qs.Modules.Panels.Process",
        {"ProcessPanel": (ROOT / TARGET).read_text()},
    )
    write(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton("""
property var requests: []
function execDetached(argv) {
  if (argv[0] !== "wl-copy") throw new Error("Forbidden launch: " + argv);
  requests = requests.concat([argv]);
}
""")
        },
    )
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
  property bool isPanelOpen: false
  property int closeCount: 0
  property alias contentItem: loader.item
  signal opened()
  signal closed()
  function open() { host.isPanelOpen = true; host.opened(); }
  function close() { host.closeCount++; host.isPanelOpen = false; host.closed(); }
  Loader { id: loader; anchors.fill: parent; active: host.isPanelOpen; sourceComponent: host.panelContent }
}
"""
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NBox": "import QtQuick\nRectangle {}",
            "NText": (ROOT / "Widgets/NText.qml").read_text(),
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize }",
            "NIconButton": """import QtQuick
Item {
  property string icon
  property string tooltipText
  property real baseSize
  implicitWidth: baseSize
  implicitHeight: baseSize
  signal clicked()
}
""",
        },
    )
    style = dict(
        uiScaleRatio=1,
        marginXXS=2,
        marginXS=4,
        marginS=6,
        marginM=8,
        marginL=12,
        radiusXS=2,
        radiusS=4,
        fontSizeXS=9,
        fontSizeS=10,
        fontSizeM=12,
        fontSizeL=14,
        fontSizeXXL=20,
        fontWeightMedium=500,
        fontWeightBold=700,
        baseWidgetSize=32,
        animationFaster=0,
    )
    colors = dict(
        mPrimary="#3355aa",
        mSecondary="#557733",
        mTertiary="#ffbb00",
        mError="#cc2233",
        mOnSurface="#ffffff",
        mOnSurfaceVariant="#aaaaaa",
        mSurfaceVariant="#141414",
    )
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "\n".join(f"readonly property real {k}: {v}" for k, v in style.items())
            ),
            "NColor": singleton(
                "\n".join(
                    f'readonly property color {k}: "{v}"' for k, v in colors.items()
                )
            ),
            "Settings": singleton(
                'readonly property var data: ({ui: {fontDefault: "Sans Serif", fontFixed: "monospace", fontDefaultScale: 1, fontFixedScale: 1}})'
            ),
            "I18n": singleton("function tr(key, values) { return key; }"),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "SystemStatService": singleton("""
property real cpuUsage: 42.5
property real memGb: 3.5
property var polling: []
function beginPolling(metric) { polling = polling.concat(["begin:" + metric]); }
function endPolling(metric) { polling = polling.concat(["end:" + metric]); }
"""),
            "ProcessService": singleton("""
property var source: []
property var processes: []
property int processCount: source.length
property string sortBy: "cpu"
property bool sortDescending: true
property string filter: ""
property int refCount: 0
property var requests: []
function publish() {
  const matching = source.filter(row => row.command.includes(filter));
  matching.sort((a, b) => {
    const key = sortBy === "memory" ? "memoryKB" : sortBy;
    const order = key === "name" ? a.displayName.localeCompare(b.displayName) : a[key] - b[key];
    return sortDescending ? -order : order;
  });
  processes = matching;
}
function setSortBy(key) { sortBy = key; publish(); }
function toggleSortDirection() { sortDescending = !sortDescending; publish(); }
function setFilter(value) { filter = value; publish(); }
function addRef() { refCount++; }
function removeRef() { refCount--; }
function killProcess(pid) { requests = requests.concat([{action: "kill", pid: pid}]); }
function forceKillProcess(pid) { requests = requests.concat([{action: "force-kill", pid: pid}]); }
function getProcessIcon(command) { return command.includes("firefox") ? "web" : "process"; }
function formatCpu(value) { return value.toFixed(1) + "%"; }
function formatMemory(value) { return (value / 1024).toFixed(1) + " MB"; }
"""),
        },
    )
    (directory / "tst_process.qml").write_text(
        (ROOT / "Tests/Qml/ProcessPanelWarningsHarness.qml").read_text()
    )


def canonical_instances():
    result = subprocess.run(
        ["quickshell", "list", "--all"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return tuple(
        line.strip()
        for line in result.stdout.splitlines()
        if re.match(
            r"\s*(Instance |Process ID:|Shell ID:|Config path:|Display connection:)",
            line,
        )
    )


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
    instances = canonical_instances()
    try:
        run_proof(args.artifacts, args.mode)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"
        assert canonical_instances() == instances, "shell process/registry changed"
        print("SETTINGS_SHA_UNCHANGED", digest)
        print("CANONICAL_REGISTRY_UNCHANGED", instances)


if __name__ == "__main__":
    main()
