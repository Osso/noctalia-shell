#!/usr/bin/env python3
"""Bounded BluetoothPanel lint and sandboxed offscreen owner/routing proof.

Production panel only; Bluetooth, widgets and SmartPanel hosting are inert
fixtures. Source lint uses unchanged installed metadata, not fixture types.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/Panels/Bluetooth/BluetoothPanel.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = helper("grid-list-warnings")


def lint(directory, environment):
    helper("media-mini-warnings").stage_modules(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "bluetooth-panel-lint",
    )
    blocks = re.split(r"(?=Warning:)", output)[1:]
    counts = Counter(re.findall(r"\[([^]]+)\]", block)[0] for block in blocks)
    print("BLUETOOTH_PANEL_LINT_COUNTS", dict(counts), "EXIT", code)
    assert counts == {"missing-property": 4}, dict(counts)
    assert all(
        'Member "values" not found on type "UntypedObjectModel"' in block
        for block in blocks
    )
    assert code in (0, 255), code


def stage_runtime(directory):
    workspace = helper("workspace-runtime")
    write = workspace.write_module
    singleton = workspace.singleton
    write(directory, "Quickshell", {"Fixture": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "Quickshell.Bluetooth",
        {
            "Bluetooth": singleton(
                "component DeviceList: QtObject { property var values: [] }\n"
                "property DeviceList devices: DeviceList {}"
            ),
            "BluetoothAdapter": "import QtQuick\nQtObject { property bool enabled: false; property bool discovering: false }",
            "BluetoothDevice": """import QtQuick
QtObject {
  property string name
  property bool blocked: false
  property bool connected: false
  property bool paired: false
  property bool trusted: false
  property bool pairing: false
  property int signalStrength: 80
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "I18n": singleton("function tr(key) { return key; }"),
            "NColor": singleton('''property color transparent: "transparent"
property color mPrimary: "green"
property color mOnSurface: "white"
property color mOnSurfaceVariant: "gray"'''),
            "Style": singleton(
                "\n".join(
                    f"property real {name}: {value}"
                    for name, value in {
                        "uiScaleRatio": 1,
                        "marginM": 8,
                        "marginL": 12,
                        "marginXS": 2,
                        "fontSizeXXL": 20,
                        "fontSizeL": 16,
                        "fontSizeM": 12,
                        "fontSizeS": 10,
                        "fontWeightBold": 700,
                        "baseWidgetSize": 40,
                        "animationSlow": 100,
                    }.items()
                )
            ),
        },
    )
    write(directory, "qs.Services.UI", {"Fixture": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Services.Networking",
        {
            "BluetoothService": """pragma Singleton
import QtQuick
import Quickshell.Bluetooth
QtObject {
  id: service
  property BluetoothAdapter adapter: null
  readonly property bool enabled: adapter ? adapter.enabled : false
  property var requests: []
  function setBluetoothEnabled(value) { requests = requests.concat([value]); }
  function sortDevices(devices) { return devices.slice().sort((a, b) => a.name.localeCompare(b.name)); }
}""",
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
  property int closes: 0
  readonly property var content: contentLoader.item
  function open() { host.isPanelOpen = true; }
  function close() { host.closes++; host.isPanelOpen = false; }
  Loader {
    id: contentLoader
    anchors.fill: parent
    active: host.isPanelOpen
    sourceComponent: host.panelContent
  }
}""",
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NBox": "import QtQuick\nRectangle {}",
            "NText": "import QtQuick\nText { property real pointSize: 12; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize: 12 }",
            "NToggle": "import QtQuick\nItem { property bool checked; property real baseSize; signal toggled(bool checked) }",
            "NIconButton": "import QtQuick\nItem { property string icon; property string tooltipText; property real baseSize; signal clicked() }",
            "NScrollView": "import QtQuick.Controls\nScrollView { property int horizontalPolicy; property int verticalPolicy }",
        },
    )
    write(
        directory,
        "qs.Modules.Panels.Bluetooth",
        {
            "BluetoothPanel": (ROOT / TARGET).read_text(),
            "BluetoothDevicesList": "import QtQuick\nItem { property string label; property string tooltipText; property var model; implicitHeight: model.length * 30 }",
        },
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/BluetoothPanelWarningsHarness.qml",
        directory / "tst_bluetooth_panel.qml",
    )


def check_harness(directory, environment, label):
    code, output = isolation.run_audited(
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
            str(directory / "tst_bluetooth_panel.qml"),
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
    print("BLUETOOTH_PANEL_HARNESS_LINT_COUNTS", dict(counts), "EXIT", code)
    return code, diagnostics


def lint_harness(directory, environment):
    stage_runtime(directory)
    code, diagnostics = check_harness(directory, environment, "harness-lint")
    assert code == 0 and not diagnostics, (code, diagnostics)


def lint_harness_regression(directory, environment):
    lint_harness(directory, environment)
    harness = directory / "tst_bluetooth_panel.qml"
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
    code, diagnostics = check_harness(directory, environment, "harness-injected")
    assert code != 0, "injected diagnostic was accepted"
    assert any(
        diagnostic["id"] == "missing-property"
        and "missingLintProbe" in diagnostic["message"]
        for diagnostic in diagnostics
    ), diagnostics
    print("BLUETOOTH_PANEL_HARNESS_WARNING_REJECTED")


def runtime(directory, environment):
    stage_runtime(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_bluetooth_panel.qml"),
            "-import",
            str(directory),
        ],
        "bluetooth-panel-runtime",
    )
    assert code == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("lint", "lint-harness", "lint-harness-regression", "runtime", "guard"),
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-bluetooth-panel-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        environment = isolation.isolated_environment(directory)
        if args.mode == "guard":
            try:
                isolation.run_audited(
                    directory,
                    environment,
                    [
                        "/usr/bin/python3",
                        "-c",
                        "open('/home/osso/.config/noctalia/settings.json')",
                    ],
                    "guard-probe",
                )
            except AssertionError as error:
                assert "SETTINGS_AUDIT_DENIED" in str(error)
                print(
                    "CHILD_SETTINGS_AUDIT_GUARD: forbidden attempt detected; host home unmounted"
                )
            else:
                raise AssertionError("child settings guard failed")
        else:
            globals()[args.mode.replace("-", "_")](directory, environment)


if __name__ == "__main__":
    main()
