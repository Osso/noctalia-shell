#!/usr/bin/env python3
"""Bounded production shortcut/clock proof; synthetic services, no desktop/config.

Clock header/month and shortcut widget loader remain production QML. Only service,
clock drawing and action-widget boundaries are fixtures. Config audit denies host
reads in staging; allowlist bwrap mounts and strace prove runtime denial too.
"""

import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("Modules/Cards/ShortcutsCard.qml"),
    Path("Modules/Panels/Clock/ClockPanel.qml"),
)


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory, shadow, mutation):
    helper("calendar-month-card-warnings.test.py").stage_runtime(directory)
    writer = helper("about-tab-warnings.test.py")
    write, singleton = writer.write_module, writer.singleton
    commons = directory / "qs/Commons"
    style = commons / "Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {",
            """QtObject {
property real uiScaleRatio: 1
property real marginL: 12
property real marginXL: 16
property real radiusL: 10
property real fontSizeXXXL: 24
property real fontSizeXL: 16
property real fontSizeXS: 9""",
            1,
        )
    )
    colors = commons / "NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "QtObject {", 'QtObject {\nproperty color mOnPrimary: "#ffffff"', 1
        )
    )
    write(
        directory,
        "qs.Commons",
        {
            **{p.stem: p.read_text() for p in commons.glob("*.qml")},
            "Settings": singleton("""property var data: ({
controlCenter: {shortcuts: {left: [{id: 'Action', caption: 'Left'}], right: [{id: 'Action', caption: 'Right'}]}},
calendar: {cards: []},
location: {weatherEnabled: false, analogClockInCalendar: false, firstDayOfWeek: 1,
showWeekNumberInCalendar: true, showCalendarEvents: false, use12hourFormat: false},
ui: {fontFixed: 'monospace'}
})"""),
            "Logger": singleton("function w(...args) { console.warn(...args); }"),
            "I18n": singleton(
                'property var locale: Qt.locale("en_US")\nfunction tr(key) { return key; }'
            ),
        },
    )
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Quickshell": singleton(
                "property var launches: []\nfunction execDetached(args) { launches = launches.concat([args]); }"
            ),
        },
    )
    write(directory, "Quickshell.Wayland", {"Inert": "import QtQuick\nQtObject {}"})
    service = directory / "qs/Services/Location/CalendarService.qml"
    service.write_text(
        service.read_text().replace(
            "QtObject {",
            """QtObject {
property int pollingRefs: 0
function beginPolling() { pollingRefs++; }
function endPolling() { pollingRefs--; }""",
            1,
        )
    )
    location = directory / "qs/Services/Location"
    write(
        directory,
        "qs.Services.Location",
        {
            "CalendarService": service.read_text(),
            "LocationService": singleton("property var data: ({weather: null})"),
        },
    )
    ui = directory / "qs/Services/UI"
    write(
        directory,
        "qs.Services.UI",
        {
            **{p.stem: p.read_text() for p in ui.glob("*.qml")},
            "ControlCenterWidgetRegistry": singleton("""property var widgets: ({})
function getWidget(id) { return widgets[id] || null; }
function hasWidget(id) { return id in widgets; }"""),
        },
    )
    widgets = directory / "qs/Widgets"
    write(
        directory,
        "qs.Widgets",
        {
            **{p.stem: p.read_text() for p in widgets.glob("*.qml")},
            "NClock": """import QtQuick
Text {
property string clockStyle
property color progressColor
property date now
text: Qt.formatDateTime(now, 'HH:mm')
}""",
        },
    )
    write(
        directory,
        "qs.Modules.Panels.ControlCenter",
        {
            "ControlCenterPanel": """import QtQuick
import Quickshell
Item { property ShellScreen screen; property int shortcutsHeight: 52 }""",
            "ControlCenterWidgetLoader": (
                ROOT / "Modules/Panels/ControlCenter/ControlCenterWidgetLoader.qml"
            ).read_text(),
        },
    )
    shortcuts = (ROOT / TARGETS[0]).read_text()
    if mutation:
        shortcuts = shortcuts.replace("pragma ComponentBehavior: Bound\n", "")
    if shadow:
        shortcuts = shortcuts.replace(
            "required property var modelData",
            "required property var modelData\nproperty var shortcuts: null",
        )
    write(
        directory,
        "qs.Modules.Cards",
        {
            "ShortcutsCard": shortcuts,
            "CalendarHeaderCard": (
                ROOT / "Modules/Cards/CalendarHeaderCard.qml"
            ).read_text(),
            "CalendarMonthCard": (
                ROOT / "Modules/Cards/CalendarMonthCard.qml"
            ).read_text(),
            "TimerCard": "import QtQuick\nItem { implicitHeight: 80 }",
            "WeatherCard": "import QtQuick\nItem { property int forecastDays; property bool showLocation; implicitHeight: 90 }",
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
property Component panelContent
property real preferredWidth
property alias contentItem: loader.item
signal opened()
signal closed()
Loader { id: loader; anchors.fill: parent; sourceComponent: parent.panelContent }
}""",
        },
    )
    source = (ROOT / TARGETS[1]).read_text()
    if mutation:
        source = source.replace("pragma ComponentBehavior: Bound\n", "")
    if shadow:
        # Probe Qt's actual nested component lookup: delegate properties collide
        # with the panel's IDs. Bound must retain the lexical card components.
        source = source.replace(
            "required property var modelData",
            """required property var modelData
property Component calendarHeaderCard: null
property Component calendarMonthCard: null
property Component timerCard: null
property Component weatherCard: null""",
        )
    write(directory, "qs.Modules.Panels.Clock", {"ClockPanel": source})
    (directory / "tst_shortcuts_clock.qml").write_text(
        (ROOT / "Tests/Qml/ShortcutsClockWarningsHarness.qml").read_text()
    )
    (directory / "probe.py").write_text("""import os
for path in ('/home/osso/.config/noctalia/settings.json', '/home/osso/.config/noctalia'):
    try: fd = os.open(path, os.O_RDONLY)
    except OSError as error: print('CONFIG_DENIED', path, error.errno)
    else:
        os.close(fd)
        raise AssertionError(path)
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--expect-warnings", nargs=2, type=int, default=(1, 0))
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--mutation", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-shortcuts-clock-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = helper("wallpaper-tab-warnings.test.py")
        isolation.install_audit(directory)
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            helper("media-mini-warnings.test.py").stage_modules(directory)
            for target, expected in zip(TARGETS, args.expect_warnings):
                result = subprocess.run(
                    isolation.sandbox_command(
                        directory,
                        [
                            "/usr/lib/qt6/bin/qmllint",
                            "-I",
                            temporary,
                            str(directory / "qs" / target),
                        ],
                    ),
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                output = result.stdout + result.stderr
                print(output, end="")
                warnings = [
                    line for line in output.splitlines() if line.startswith("Warning:")
                ]
                print(target.name, "WARNINGS", len(warnings))
                assert result.returncode == 0 and len(warnings) == expected, output
            return
        stage_runtime(directory, args.shadow, args.mutation)
        trace_path = directory / "access.trace"
        command = isolation.sandbox_command(
            directory,
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_shortcuts_clock.qml"),
                "-import",
                temporary,
            ],
        )
        probe = subprocess.run(
            isolation.sandbox_command(
                directory, ["/usr/bin/python3", str(directory / "probe.py")]
            ),
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(probe.stdout + probe.stderr, end="")
        assert probe.returncode == 0 and probe.stdout.count("CONFIG_DENIED") == 2
        result = subprocess.run(
            [
                "strace",
                "-f",
                "-qq",
                "-s",
                "512",
                "-e",
                "trace=%file,%network",
                "-o",
                str(trace_path),
                *command,
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        trace = trace_path.read_text()
        assert not re.search(r'openat\(.*"/home/osso/.*= [0-9]+', trace), (
            "host home opened"
        )
        assert not re.search(r"connect\(.*sa_family=AF_INET6?[,}]", trace), (
            "network attempted"
        )
        print("CONFIG_RUNTIME_AUDIT_PASS: host home absent, no network connection")
        assert result.returncode == 0 and "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output


if __name__ == "__main__":
    main()
