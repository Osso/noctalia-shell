#!/usr/bin/env python3
"""Bounded TrayMenu lint and offscreen production delegate/lifecycle proof.

Popup transport and notifier handles are synthetic; production menu layout,
Repeater, entry handlers and reopen lifecycle remain unchanged. Host settings
are never read, resolved, hashed or backed up; sandbox and audits deny access.
"""

import argparse
import importlib.util
import json
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/Bar/Extras/TrayMenu.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load_helper("tray_menu_isolation", "grid-list-warnings.test.py")
fixtures = load_helper("tray_menu_fixtures", "workspace-runtime.test.py")


def stage_runtime(directory, mutation):
    write = fixtures.write_module
    singleton = fixtures.singleton
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property real height: 480 }",
            "QsMenuHandle": "import QtQuick\nQtObject { property var entries: [] }",
            "QsMenuOpener": """import QtQuick
import Quickshell
QtObject {
  property QsMenuHandle menu
  property QtObject children: QtObject { property var values: parentOpener.menu ? parentOpener.menu.entries : [] }
  id: parentOpener
}""",
            "PopupAnchor": """import QtQuick
QtObject {
  property Item item
  property rect rect: Qt.rect(0, 0, 0, 0)
  property int updates: 0
  function updateAnchor() { updates++; }
}""",
            "PopupWindow": """import QtQuick
import Quickshell
Item {
  visible: false
  width: implicitWidth
  height: implicitHeight
  property color color
  property PopupAnchor anchor: PopupAnchor {}
}""",
        },
    )
    write(
        directory,
        "Quickshell.Services.SystemTray",
        {
            "SystemTrayItem": """import QtQuick
import Quickshell
QtObject {
  property QsMenuHandle menu
  property string tooltipTitle
  property string name
  property string id
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                'property var data: ({bar: {position: "top", widgets: {left: [], right: []}}})\nfunction saveImmediate() { throw new Error("unexpected persistence"); }'
            ),
            "Style": singleton(
                "\n".join(
                    f"property real {name}: {value}"
                    for name, value in {
                        "marginS": 4,
                        "marginM": 8,
                        "marginL": 12,
                        "barHeight": 40,
                        "borderS": 1,
                        "radiusM": 8,
                        "radiusS": 4,
                        "animationNormal": 0,
                        "fontSizeS": 10,
                    }.items()
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "{value}"'
                    for name, value in {
                        "transparent": "transparent",
                        "mSurface": "#222222",
                        "mOutline": "gray",
                        "mHover": "#444444",
                        "mOnHover": "white",
                        "mOnSurface": "white",
                        "mOnSurfaceVariant": "gray",
                        "mOnTertiary": "white",
                        "mPrimary": "cyan",
                    }.items()
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Logger": singleton(
                'function w(scope, message) { throw new Error(scope + ": " + message); }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("""property var panels: []
function getPanel(name, screen) {
  for (const panel of panels) if (panel.screen === screen) return panel;
  throw new Error("unknown owner screen");
}"""),
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NText": "import QtQuick\nText { property real pointSize: 10; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize; property bool applyUiScale }",
            "NDivider": 'import QtQuick\nRectangle { height: 1; color: "gray" }',
        },
    )
    source = (ROOT / TARGET).read_text()
    if mutation == "activation":
        source = source.replace(
            "entry.menuItem.triggered();", "/* negative control: omit activation */"
        )
    elif mutation == "owner":
        source = source.replace("root.hideMenu();", "root.visible = true;")
    write(directory, "qs.Modules.Bar.Extras", {"TrayMenu": source})
    shutil.copyfile(
        ROOT / "Tests/Qml/TrayMenuWarningsHarness.qml", directory / "tst_tray_menu.qml"
    )


def lint(directory, environment):
    load_helper("tray_menu_lint", "media-mini-warnings.test.py").stage_modules(
        directory
    )
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "tray-menu-lint",
    )
    blocks = re.split(r"(?=Warning:)", output)[1:]
    counts = Counter(re.findall(r"\[([^]]+)\]", block)[0] for block in blocks)
    print("TRAY_MENU_LINT_COUNTS", dict(counts), "EXIT", code)
    assert counts == {"missing-property": 1}, dict(counts)
    assert 'Member "updateAnchor" not found on type "PopupAnchor"' in blocks[0], blocks[
        0
    ]
    assert code in (0, 255), code
    print("TRAY_MENU_LINT_PASS: installed PopupAnchor metadata residual preserved")


def lint_harness(directory, environment):
    stage_runtime(directory, None)
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
            str(directory / "tst_tray_menu.qml"),
        ],
        "tray-menu-harness-lint",
    )
    report = json.loads(output)
    assert len(report["files"]) == 1, report
    print("TRAY_MENU_HARNESS_LINT_FILE_COUNT", len(report["files"]), "EXIT", code)
    return code


def runtime(directory, environment, mutation):
    stage_runtime(directory, mutation)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_tray_menu.qml"),
            "-import",
            str(directory),
        ],
        "tray-menu-runtime",
    )
    assert code == 0, f"runtime exit {code}"
    assert "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime", "guard"))
    parser.add_argument(
        "--max-warnings",
        type=int,
        choices=(0,),
        default=0,
        help="fixture harness lint is always strict (zero warnings)",
    )
    parser.add_argument("--mutation", choices=("activation", "owner"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-tray-menu-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode != "guard":
            environment = isolation.isolated_environment(directory)
            if args.mode == "lint-harness":
                raise SystemExit(lint_harness(directory, environment))
            if args.mode == "lint":
                lint(directory, environment)
            else:
                runtime(directory, environment, args.mutation)
