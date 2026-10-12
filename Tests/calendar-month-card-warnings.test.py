#!/usr/bin/env python3
"""CalendarMonthCard-only lint and sandboxed synthetic calendar UI proof."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Cards/CalendarMonthCard.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory, mutation=False):
    writer = helper("clock-settings-warnings.test.py")
    write = writer.write_module
    singleton = writer.singleton
    source = (ROOT / TARGET).read_text()
    if mutation:
        source = source.replace(
            "return isToday ? NColor.mOnSecondary : NColor.mPrimary;",
            "return NColor.mTertiary;",
        )
    write(directory, "qs.Cards", {"CalendarMonthCard": source})
    write(
        directory,
        "qs.Widgets",
        {
            "NBox": (ROOT / "Widgets/NBox.qml").read_text(),
            "NText": "import QtQuick\nText { property real pointSize: 12; font.pointSize: pointSize }",
            "NDivider": "import QtQuick\nItem { implicitHeight: 1 }",
            "NIconButton": """import QtQuick
Rectangle {
  property string icon
  signal clicked
  implicitWidth: 32
  implicitHeight: 32
  MouseArea { anchors.fill: parent; onClicked: parent.clicked() }
}""",
        },
    )
    style = {
        "marginM": 8,
        "marginS": 4,
        "marginXXS": 2,
        "marginXS": 3,
        "baseWidgetSize": 32,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeXXS": 8,
        "radiusM": 6,
        "radiusXXS": 2,
        "borderS": 1,
        "fontWeightBold": 700,
        "fontWeightMedium": 500,
        "animationFast": 0,
        "tooltipDelay": 0,
    }
    colors = {
        "mSurfaceVariant": "#222222",
        "mOutline": "#444444",
        "mPrimary": "#ff0000",
        "mSecondary": "#00ff00",
        "mTertiary": "#0000ff",
        "mOnSecondary": "#ffffff",
        "mOnSurface": "#eeeeee",
        "mOnSurfaceVariant": "#999999",
        "transparent": "transparent",
    }
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "\n".join(f"property real {k}: {v}" for k, v in style.items())
            ),
            "NColor": singleton(
                "\n".join(f'property color {k}: "{v}"' for k, v in colors.items())
            ),
            "Time": singleton("property date now: new Date(2026, 0, 15, 12)"),
            "I18n": singleton('property var locale: Qt.locale("en_US")'),
            "Settings": singleton("""property var data: QtObject {
  property QtObject location: QtObject {
    property int firstDayOfWeek: 1
    property bool showWeekNumberInCalendar: true
    property bool showCalendarEvents: true
    property bool use12hourFormat: false
  }
  property QtObject ui: QtObject { property string fontFixed: "monospace" }
}"""),
        },
    )
    write(
        directory,
        "qs.Services.Location",
        {
            "CalendarService": singleton("""
property bool available: true
property var events: []
property var loads: []
function loadEvents(ahead, behind) { loads = loads.concat([{ahead: ahead, behind: behind}]); }
""")
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "ProgramCheckerService": singleton(
                "property bool gnomeCalendarAvailable: true"
            )
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton("""
property string message: ""
property var anchor: null
function show(item, text, position, delay, font) { anchor = item; message = text; }
function hide() { anchor = null; message = ""; }
""")
        },
    )
    write(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton("""
property var launches: []
function execDetached(args) { launches = launches.concat([args]); }
""")
        },
    )
    (directory / "tst_calendar.qml").write_text(
        (ROOT / "Tests/Qml/CalendarMonthCardWarningsHarness.qml").read_text()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "lint-harness", "runtime", "isolation")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--expect-warnings", type=int, default=0)
    parser.add_argument("--mutation", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-calendar-card-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = helper("wallpaper-tab-warnings.test.py")
        isolation.install_audit(directory)
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            helper("media-mini-warnings.test.py").stage_modules(directory)
            argv = [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                temporary,
                str(directory / "qs" / TARGET),
            ]
        elif args.mode == "lint-harness":
            stage_runtime(directory)
            harness = directory / "tst_calendar.qml"
            if args.inject_warning:
                source = harness.read_text()
                marker = "id: testCase"
                assert source.count(marker) == 1, "injection owner must be unique"
                harness.write_text(
                    source.replace(
                        marker,
                        marker
                        + "\n  property int injectedWarning: testCase.missingLintProbe",
                        1,
                    )
                )
            argv = [
                "/usr/lib/qt6/bin/qmllint",
                "--bare",
                "-I",
                temporary,
                "-I",
                "/usr/lib/qt6/qml",
                "--max-warnings",
                str(args.max_warnings),
                "--json",
                "-",
                str(harness),
            ]
        elif args.mode == "runtime":
            stage_runtime(directory, args.mutation)
            argv = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_calendar.qml"),
                "-import",
                temporary,
            ]
        else:
            argv = [
                "/usr/bin/python3",
                "-c",
                """import pathlib, socket
for path in ('/home/osso/.config', '/syncthing', '/run/user'):
    assert not pathlib.Path(path).exists(), path
    print('MASK_ABSENT', path)
s = socket.socket(); s.settimeout(1)
try: s.connect(('1.1.1.1', 443))
except OSError: print('NETWORK_DENIED')
else: raise AssertionError('network accessible')
finally: s.close()
""",
            ]
        result = subprocess.run(
            isolation.sandbox_command(directory, argv),
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if args.mode == "lint":
            warnings = [
                line for line in output.splitlines() if line.startswith("Warning:")
            ]
            print("CALENDAR_CARD_WARNINGS", len(warnings))
            assert len(warnings) == args.expect_warnings, output
            assert result.returncode == 0, result.returncode
        elif args.mode == "lint-harness":
            diagnostics = json.loads(result.stdout)
            warnings = sum(
                warning["type"] == "warning"
                for entry in diagnostics["files"]
                for warning in entry["warnings"]
            )
            print("CALENDAR_CARD_HARNESS_WARNINGS", warnings, "EXIT", result.returncode)
            if args.inject_warning:
                assert warnings > 0 and result.returncode != 0, (
                    "injected warning was accepted"
                )
                raise SystemExit(result.returncode)
            assert warnings == 0 and result.returncode == 0, (
                "strict harness lint failed"
            )
        else:
            assert result.returncode == 0, result.returncode
            if args.mode == "runtime":
                assert "7 passed, 0 failed" in output
                assert not re.search(
                    r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
                    output,
                ), output
            else:
                assert "NETWORK_DENIED" in output
        print("CALENDAR_CARD_" + args.mode.upper() + "_PASS")


if __name__ == "__main__":
    main()
