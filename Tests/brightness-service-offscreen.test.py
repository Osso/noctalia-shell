#!/usr/bin/env python3
"""Brightness-only lint and offscreen lifecycle proof with audited inert I/O.

No real settings, screens, processes or FileViews enter the runtime fixture.
DDC stays disabled, including for a fake screen with a matching DDC record.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/Hardware/BrightnessService.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory, expected):
    helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--max-warnings",
            "0",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint.log").write_text(output)
    print(output, end="")
    warnings = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("BRIGHTNESS_LINT", dict(warnings), "exit", result.returncode)
    assert warnings == (Counter(unqualified=expected) if expected else Counter()), (
        warnings
    )
    assert result.returncode == (255 if expected else 0), result.returncode


def stage_runtime(directory, mutation):
    workspace = helper("workspace-runtime")
    write = workspace.write_module
    singleton = workspace.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem { property string reloadableId }",
            "ShellScreen": "import QtQuick\nQtObject { property string name; property string model }",
            "Quickshell": singleton("""property var screens: []
property var commands: []
function execDetached(argv) { commands = commands.concat([argv]); }"""),
            "Variants": """import QtQuick
import QtQml.Models
Item {
  id: variants
  property alias model: objects.model
  default property alias delegate: objects.delegate
  property var instances: []
  Instantiator {
    id: objects
    onObjectAdded: function(index, object) {
      let values = variants.instances.slice();
      values.splice(index, 0, object);
      variants.instances = values;
    }
    onObjectRemoved: function(index, object) {
      variants.instances = variants.instances.filter(value => value !== object);
    }
  }
}""",
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton("property var processes: []"),
            "Process": """import QtQuick
Item {
  id: process
  property bool running: false
  property var command: []
  property QtObject stdout
  property QtObject stderr
  signal exited(int exitCode)
  Component.onCompleted: FixtureIo.processes = FixtureIo.processes.concat([process])
}""",
            "StdioCollector": 'import QtQuick\nQtObject { property string text: ""; signal streamFinished() }',
            "FileView": "import QtQuick\nQtObject { property string path; property bool watchChanges; signal fileChanged() }",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("""component BrightnessSettings: QtObject {
  readonly property bool enableDdcSupport: false
  property int brightnessStep: 10
  property bool enforceMinimum: true
}
component FixtureSettings: QtObject {
  property BrightnessSettings brightness: BrightnessSettings {}
}
property FixtureSettings data: FixtureSettings {}"""),
            "Logger": singleton("""property var warnings: []
function i(...args) {}
function d(...args) {}
function w(...args) { warnings = warnings.concat([args.join(" ")]); }"""),
        },
    )
    source = (ROOT / TARGET).read_text()
    if mutation == "monitor-signal":
        source, count = re.subn(
            r"(?:root|BrightnessService)\.monitorBrightnessChanged\(monitor, monitor.brightness\);",
            "",
            source,
        )
        assert count == 1
    elif mutation == "apple-callback":
        source, count = re.subn(
            r"(?:root|BrightnessService)\.appleDisplayPresent = text.trim\(\).length > 0",
            "{}",
            source,
        )
        assert count == 1
    write(directory, "qs.Services.Hardware", {"BrightnessService": source})
    helpers = directory / "qs/Helpers"
    helpers.mkdir(parents=True)
    shutil.copyfile(
        ROOT / "Helpers/BrightnessParsing.js", helpers / "BrightnessParsing.js"
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/BrightnessServiceOffscreenHarness.qml",
        directory / "tst_brightness.qml",
    )
    (directory / "fonts.conf").write_text(
        "<fontconfig><dir>/usr/share/fonts</dir><cachedir>/tmp/fonts</cachedir></fontconfig>"
    )


def run_audited(directory, command):
    environment = {
        "PATH": "/usr/bin",
        "HOME": "/home/fixture",
        "XDG_CONFIG_HOME": "/home/fixture/config",
        "XDG_CACHE_HOME": "/tmp/cache",
        "XDG_RUNTIME_DIR": "/tmp/runtime",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "FONTCONFIG_FILE": "/fixture/fonts.conf",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent",
    }
    result = subprocess.run(
        [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/home",
            "--dir",
            "/home/fixture",
            "--dir",
            "/tmp/runtime",
            "--chmod",
            "0700",
            "/tmp/runtime",
            "--ro-bind",
            str(directory),
            "/fixture",
            "--bind",
            str(directory / "audit"),
            "/audit",
            "--chdir",
            "/fixture",
            "/usr/bin/strace",
            "-f",
            "-e",
            "trace=%file",
            "-o",
            "/audit/files.log",
            *command,
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    (directory / "runtime.log").write_text(result.stdout + result.stderr)
    audit = (directory / "audit/files.log").read_text()
    # Count attempted accesses too, not just successful opens. /home, /sys,
    # D-Bus and the real config are absent from the namespace in addition.
    forbidden = re.findall(
        r'"[^"\n]*(?:/home/osso|/sys/class/backlight|/dev/i2c|noctalia/settings)[^"\n]*"',
        audit,
    )
    assert not forbidden, forbidden
    executables = re.findall(r'execve\("([^"]+)"', audit)
    assert executables == [command[0]], executables
    print("AUDIT: zero real-config/hardware attempts; exec", executables)
    return result


def runtime(directory, mutation):
    stage_runtime(directory, mutation)
    (directory / "audit").mkdir(mode=0o700)
    result = run_audited(
        directory,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            "/fixture/tst_brightness.qml",
            "-import",
            "/fixture",
        ],
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output
    if mutation:
        expected_test = {
            "monitor-signal": "test_monitor_brightness_signals_before_recorded_commands",
            "apple-callback": "test_apple_collector_updates_singleton_and_matching_monitor",
        }[mutation]
        failures = re.findall(r"FAIL!\s+:.*::(test_\w+)\(\)", output)
        assert result.returncode != 0 and failures == [expected_test], (
            result.returncode,
            output,
        )
    else:
        assert result.returncode == 0 and "0 failed" in output, (
            result.returncode,
            output,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--expected", type=int, default=0)
    parser.add_argument("--mutation", choices=("monitor-signal", "apple-callback"))
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700)
    if args.mode == "lint":
        assert args.mutation is None
        lint(args.artifacts, args.expected)
    else:
        runtime(args.artifacts, args.mutation)


if __name__ == "__main__":
    main()
