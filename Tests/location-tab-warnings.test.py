#!/usr/bin/env python3
"""Bounded LocationTab diagnostics and offscreen UI with synthetic settings only."""

import argparse
import importlib.util
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/LocationTab.qml")


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_behavior(directory):
    helper = load_helper("about-tab-warnings.test.py")
    # Only its staging function is used; its real-settings main is never executed.
    helper.stage_behavior(directory)
    (directory / "tst_about.qml").unlink()
    controls = (
        "NHeader",
        "NText",
        "NIcon",
        "NIconButton",
        "NLabel",
        "NTextInput",
        "NDivider",
        "NToggle",
        "NComboBox",
        "NListView",
        "NReorderCheckboxes",
    )
    helper.write_module(
        directory,
        "qs.Widgets",
        {name: (ROOT / f"Widgets/{name}.qml").read_text() for name in controls},
    )
    helper.write_module(
        directory, "qs.Tabs", {"LocationTab": (ROOT / TARGET).read_text()}
    )
    helper.write_module(
        directory,
        "qs.Services.Location",
        {
            "LocationService": helper.singleton("""
      property bool coordinatesReady: false
      property string stableName: 'Fixture City'
      property string displayCoordinates: '12,34'
      property int resets: 0
      function resetWeather() { resets++; }
    """)
        },
    )
    commons = directory / "qs/Commons"
    (commons / "Settings.qml").write_text(
        helper.singleton("""
      property string defaultLocation: 'Fixture Default'
      property QtObject data: QtObject {
        property QtObject ui: QtObject {
          property string fontDefault: 'Sans Serif'
          property string fontFixed: 'monospace'
        }
        property QtObject location: QtObject {
          property string name: 'Fixture City'
          property bool weatherEnabled: true
          property bool useFahrenheit: false
          property bool weatherShowEffects: true
          property bool use12hourFormat: false
          property bool showWeekNumberInCalendar: false
          property int firstDayOfWeek: -1
          property bool showCalendarEvents: true
          property bool analogClockInCalendar: false
        }
        property QtObject calendar: QtObject { property var cards: [] }
      }
    """)
    )
    (commons / "I18n.qml").write_text(
        helper.singleton("""
      property var locale: Qt.locale('en_US')
      function tr(key, values) { return key; }
    """)
    )
    style = commons / "Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {",
            """QtObject {
      property real fontWeightRegular: 400
      property real radiusXS: 2
      property real radiusL: 12
      property real animationNormal: 0
    """,
            1,
        )
    )
    colors = commons / "NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "QtObject {",
            "QtObject {\nproperty color mSurface: '#202020'\nproperty color mError: '#ff0000'",
            1,
        )
    )
    (directory / "tst_location.qml").write_text(
        (ROOT / "Tests/Qml/LocationTabWarningsHarness.qml").read_text()
    )


def isolated_environment(directory):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for name in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/location-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/location-system",
    )
    return environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-location-tab-") as temporary:
        directory = Path(temporary)
        environment = isolated_environment(directory)
        if args.mode == "lint":
            load_helper("media-mini-warnings.test.py").stage_modules(directory)
            argv = [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / TARGET),
            ]
        else:
            stage_behavior(directory)
            argv = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_location.qml"),
                "-import",
                str(directory),
            ]
        result = subprocess.run(
            argv, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if args.mode == "lint":
            warnings = [
                line for line in output.splitlines() if line.startswith("Warning:")
            ]
            print("LOCATION_TAB_WARNING_COUNT", len(warnings))
            assert not warnings, "LocationTab warnings remain"
        else:
            assert "0 failed" in output, "Missing QtTest completion"
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
                output,
            ), output
        assert result.returncode == 0, result.returncode


if __name__ == "__main__":
    main()
