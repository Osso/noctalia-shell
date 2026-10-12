#!/usr/bin/env python3
"""ProcessPanel-only lint and actual offscreen panel with recorded IO boundaries."""

import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Process/ProcessPanel.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_proof(directory, mode, environment):
    if mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
    else:
        stage_behavior(directory)
        command = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_process.qml"),
            "-import",
            str(directory),
        ]
    code, output = helper("grid-list-warnings.test.py").run_audited(
        directory, environment, command, f"process-panel-{mode}"
    )
    (directory / f"{mode}.log").write_text(output)
    if mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        print("PROCESS_PANEL_WARNINGS", len(warnings))
        assert not warnings, warnings
    else:
        assert "6 passed, 0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
    assert code == 0, code


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


def lint_harness(directory, environment, inject_warning):
    stage_behavior(directory)
    harness = directory / "tst_process.qml"
    if inject_warning:
        source = harness.read_text()
        marker = "id: testCase"
        assert source.count(marker) == 1, "injection owner must be unique"
        harness.write_text(
            source.replace(
                marker,
                marker
                + "\n    property int injectedWarning: testCase.missingLintProbe",
                1,
            )
        )
    code, output = helper("grid-list-warnings.test.py").run_audited(
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
            str(harness),
        ],
        "process-harness-lint",
    )
    (directory / "lint-harness.json").write_text(output)
    diagnostics = json.loads(output)
    warnings = sum(
        diagnostic["type"] == "warning"
        for entry in diagnostics["files"]
        for diagnostic in entry["warnings"]
    )
    print("PROCESS_PANEL_HARNESS_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0 and code != 0, "injected warning was accepted"
        assert any(
            diagnostic["id"] == "missing-property"
            and "missingLintProbe" in diagnostic["message"]
            for entry in diagnostics["files"]
            for diagnostic in entry["warnings"]
        ), "injected semantic diagnostic missing"
    else:
        assert warnings == 0 and code == 0, "strict harness lint failed"
    return code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    isolation = helper("grid-list-warnings.test.py")
    isolation.install_settings_guard(args.artifacts)
    environment = isolation.isolated_environment(args.artifacts)
    if args.mode == "lint-harness":
        raise SystemExit(lint_harness(args.artifacts, environment, args.inject_warning))
    run_proof(args.artifacts, args.mode, environment)


if __name__ == "__main__":
    main()
