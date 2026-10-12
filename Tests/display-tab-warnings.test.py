#!/usr/bin/env python3
"""Focused DisplayTab lint and offscreen UI proof with inert monitor boundaries."""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import struct
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/DisplayTab.qml")


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_behavior(directory):
    helper = load_helper("about-tab-warnings.test.py")
    helper.stage_behavior(directory)
    (directory / "tst_about.qml").unlink()
    write = helper.write_module
    singleton = helper.singleton
    controls = (
        "NHeader",
        "NText",
        "NIcon",
        "NLabel",
        "NValueSlider",
        "NSlider",
        "NDivider",
        "NSpinBox",
        "NToggle",
        "NComboBox",
        "NListView",
    )
    write(
        directory,
        "qs.Widgets",
        {name: (ROOT / f"Widgets/{name}.qml").read_text() for name in controls},
    )
    write(
        directory,
        "qs.Modules.Panels.Settings.Tabs",
        {"DisplayTab": (ROOT / TARGET).read_text()},
    )
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": """import QtQuick
QtObject {
  property string name
  property string model
  property int width
  property int height
}""",
            "Quickshell": singleton("""
  property ShellScreen laptop: ShellScreen { name: 'eDP-1'; model: 'Laptop'; width: 1920; height: 1080 }
  property ShellScreen external: ShellScreen { name: 'DP-1'; model: 'External'; width: 2560; height: 1440 }
  property ShellScreen unavailable: ShellScreen { name: 'HDMI-1'; model: 'ReadOnly'; width: 1280; height: 720 }
  property ShellScreen missing: ShellScreen { name: 'DP-2'; model: 'NoBrightness'; width: 800; height: 600 }
  property var screens: [laptop, external, unavailable, missing]
"""),
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "StdioCollector": "import QtQuick\nQtObject {}",
            "Process": """import QtQuick
QtObject {
  property var command
  property bool running: false
  property StdioCollector stdout
  property StdioCollector stderr
  signal exited(int exitCode)
}""",
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": singleton("""
  function getDisplayScale(name) { return name === 'DP-1' ? 1.5 : 1; }
"""),
        },
    )
    write(
        directory,
        "qs.Services.Hardware",
        {
            "BrightnessService": singleton("""
  component Monitor: QtObject {
    property real brightness: 0.4
    property bool brightnessControlAvailable: true
    property string method: 'internal'
    property var writes: []
    function setBrightness(value) {
      if (!brightnessControlAvailable) throw new Error('Unavailable brightness write');
      brightness = value;
      writes = writes.concat([value]);
    }
  }
  property Monitor laptop: Monitor {}
  property Monitor external: Monitor { brightness: 0.7; method: 'ddcutil' }
  property Monitor unavailable: Monitor { brightness: 0.6; brightnessControlAvailable: false; method: 'ddcutil' }
  function getMonitorForScreen(screen) {
    if (screen.name === 'eDP-1') return laptop;
    if (screen.name === 'DP-1') return external;
    if (screen.name === 'HDMI-1') return unavailable;
    return null;
  }
"""),
        },
    )
    write(
        directory,
        "qs.Services.Location",
        {
            "LocationService": singleton("property string stableName: 'FixtureCity'"),
            "NightLightService": singleton(
                "property int applies: 0\nfunction apply() { applies++; }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
            "ToastService": singleton("""
  property var notices: []
  property var warnings: []
  function showNotice(title, body, icon) { notices = notices.concat([body]); }
  function showWarning(title, body) { warnings = warnings.concat([body]); }
"""),
        },
    )
    commons = directory / "qs/Commons"
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    bodies = []
    for section in ("ui", "brightness", "nightLight"):
        fields = []
        for key, value in defaults[section].items():
            if section == "ui" and key in ("fontDefault", "fontFixed"):
                value = "Sans Serif"
            kind = (
                "bool"
                if isinstance(value, bool)
                else "real"
                if isinstance(value, (int, float))
                else "var"
            )
            fields.append(f"property {kind} {key}: {json.dumps(value)}")
        bodies.append(
            f"property QtObject {section}: QtObject {{\n" + "\n".join(fields) + "\n}"
        )
    (commons / "Settings.qml").write_text(
        singleton("property QtObject data: QtObject {\n" + "\n".join(bodies) + "\n}")
    )
    # Preserve production monitor-description interpolation, using deterministic locale text.
    (commons / "I18n.qml").write_text(
        singleton("""
  function tr(key, values) {
    if (key === 'system.monitor-description')
      return values.model + ':' + values.width + 'x' + values.height + '@' + values.scale;
    return key;
  }
""")
    )
    with (commons / "Style.qml").open("r+") as stream:
        text = stream.read().replace(
            "QtObject {",
            "QtObject {\nproperty real sliderWidth: 200\nproperty real fontSizeXXL: 20\nproperty real borderL: 2",
            1,
        )
        stream.seek(0)
        stream.write(text)
        stream.truncate()
    colors = commons / "NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "QtObject {", "QtObject {\nproperty color mSurface: '#202020'", 1
        )
    )
    (directory / "tst_display.qml").write_text(
        (ROOT / "Tests/Qml/DisplayTabWarningsHarness.qml").read_text()
    )


isolation = load_helper("grouped-osd-settings-warnings.test.py")


def isolated_environment(directory):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for name in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_CONFIG_DIRS",
        "XDG_DATA_DIRS",
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/display-tab-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/display-tab-system",
    )
    return environment


def execute(mode, directory, environment, inject_warning=False):
    if mode == "lint":
        staging = load_helper("media-mini-warnings.test.py")
        staging.stage_modules(directory)
        argv = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
    else:
        stage_behavior(directory)
        harness = directory / "tst_display.qml"
        if mode == "lint-harness":
            if inject_warning:
                source = harness.read_text()
                marker = "  id: testCase"
                assert source.count(marker) == 1
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
                str(directory),
                "-I",
                "/usr/lib/qt6/qml",
                "--max-warnings",
                "0",
                "--json",
                "-",
                str(harness),
            ]
        else:
            argv = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(harness),
                "-import",
                str(directory),
            ]
    result = subprocess.run(
        argv, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60
    )
    output = result.stdout + result.stderr
    (directory / f"{mode}.log").write_text(output)
    print(output, end="")
    if mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        print("DISPLAY_TAB_WARNING_COUNT", len(warnings))
        assert not warnings, "DisplayTab warnings remain"
    elif mode == "lint-harness":
        reports = json.loads(output)["files"]
        assert len(reports) == 1 and reports[0]["filename"] == str(harness), reports
        warnings = [warning for report in reports for warning in report["warnings"]]
        print("DISPLAY_HARNESS_LINT_WARNINGS", len(warnings), "EXIT", result.returncode)
        if inject_warning:
            assert any("missingLintProbe" in warning["message"] for warning in warnings)
            assert result.returncode != 0, "Injected semantic warning accepted"
            raise SystemExit(result.returncode)
        assert not warnings and reports[0]["success"], reports
    else:
        assert "8 passed, 0 failed" in output, "Missing QtTest completion"
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|qt\.qml\.|Warning:",
            output,
        ), output
        for scale in ("1", "1.5"):
            image = (directory / f"display-scale-{scale}.png").read_bytes()
            assert image[:8] == b"\x89PNG\r\n\x1a\n"
            width, height = struct.unpack(">II", image[16:24])
            assert width == 900 and height > 500, (width, height)
            print("DISPLAY_RENDER_PNG", scale, width, height, len(image))
    assert result.returncode == 0, result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--sandbox", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    sys.addaudithook(isolation.audit)
    with (
        patch("os.stat", isolation.guard_metadata(os.stat)),
        patch("os.lstat", isolation.guard_metadata(os.lstat)),
        patch("os.readlink", isolation.guard_metadata(os.readlink)),
    ):
        isolation.prove_denial()
        directory = args.artifacts.absolute()
        if args.sandbox:
            mounts = Path("/proc/self/mountinfo").read_text().splitlines()
            for path in ("/home", "/syncthing", "/run"):
                assert any(
                    line.split()[4] == path and " - tmpfs " in line for line in mounts
                ), path
            execute(
                args.mode,
                directory,
                isolated_environment(directory),
                args.inject_warning,
            )
            return
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        directory.chmod(0o700)
        command = [
            "bwrap",
            "--die-with-parent",
            "--unshare-all",
            "--new-session",
            "--ro-bind",
            "/",
            "/",
            "--perms",
            "000",
            "--tmpfs",
            "/home",
            "--tmpfs",
            "/syncthing",
            "--ro-bind",
            str(ROOT),
            str(ROOT),
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/run",
            "--bind",
            str(directory),
            str(directory),
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--chdir",
            str(directory),
            "--",
            "/usr/bin/python3",
            str(Path(__file__).absolute()),
            args.mode,
            "--artifacts",
            str(directory),
            "--sandbox",
        ]
        if args.inject_warning:
            command.append("--inject-warning")
        code, _ = isolation.run_child(
            command,
            directory,
            {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": str(directory)},
        )
        raise SystemExit(code)


if __name__ == "__main__":
    main()
