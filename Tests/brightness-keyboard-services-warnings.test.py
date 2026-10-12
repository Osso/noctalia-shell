#!/usr/bin/env python3
"""Bounded real-service lint and signal/order tests behind inert I/O boundaries."""

import argparse
from collections import Counter
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("Services/Hardware/BrightnessService.qml"),
    Path("Services/Keyboard/KeyboardLayoutService.qml"),
)


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory, expected):
    helper("media-mini-warnings").stage_modules(directory)
    counts = []
    for target in TARGETS:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / (target.stem + ".lint.log")).write_text(output)
        print(output, end="")
        warnings = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print(target, dict(warnings))
        assert result.returncode == 0, result.returncode
        assert set(warnings) <= {"unqualified"}, warnings
        counts.append(warnings["unqualified"])
    assert counts == expected, (counts, expected)


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
            "Settings": singleton("""property QtObject data: QtObject {
  property QtObject brightness: QtObject {
    property bool enableDdcSupport: false
    property int brightnessStep: 10
    property bool enforceMinimum: true
  }
  property QtObject notifications: QtObject {
    property bool enableKeyboardLayoutToast: true
  }
}"""),
            "Logger": singleton(
                "function i(...args) {}\nfunction d(...args) {}\nfunction w(...args) {}"
            ),
            "I18n": singleton(
                'function tr(key, values) { return values ? key + ":" + values.layout : key; }'
            ),
        },
    )
    write(
        directory, "qs.Services.Compositor", {"Unused": "import QtQuick\nQtObject {}"}
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "ToastService": singleton("""property var notices: []
function showNotice(message, body, icon, duration) {
  notices = notices.concat([{message: message, duration: duration}]);
}"""),
        },
    )
    for target in TARGETS:
        source = (ROOT / target).read_text()
        if mutation == "ddc-signal" and target == TARGETS[0]:
            source, count = re.subn(
                r"(?m)^\s*(?:root\.)?requestDdcDetection\(\);(?=\n      } else)",
                "",
                source,
            )
            assert count == 1
        if mutation == "keyboard-timer" and target == TARGETS[1]:
            source, count = re.subn(
                r"(?m)^\s*(?:root\.)?isInitialized = true;", "", source
            )
            assert count == 1
        write(directory, "qs." + ".".join(target.parent.parts), {target.stem: source})
    helpers = directory / "qs/Helpers"
    helpers.mkdir(parents=True)
    shutil.copyfile(
        ROOT / "Helpers/BrightnessParsing.js", helpers / "BrightnessParsing.js"
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/BrightnessKeyboardServicesHarness.qml",
        directory / "tst_services.qml",
    )
    (directory / "fonts.conf").write_text(
        "<fontconfig><dir>/usr/share/fonts</dir><cachedir>/tmp/fonts</cachedir></fontconfig>"
    )


def runtime(directory, mutation):
    stage_runtime(directory, mutation)
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
            "--chdir",
            "/fixture",
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            "/fixture/tst_services.qml",
            "-import",
            "/fixture",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    if mutation:
        assert result.returncode != 0 and "FAIL!" in output, (result.returncode, output)
        expected_test = (
            "test_ddc_enable_exit_then_stop_order"
            if mutation == "ddc-signal"
            else "test_keyboard_initialization_then_toast_order"
        )
        assert re.search(r"FAIL!\s+:.*::" + expected_test + r"\(\)", output), output
    else:
        assert result.returncode == 0 and "0 failed" in output, result.returncode
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--expected", type=int, nargs=2, default=[5, 0])
    parser.add_argument("--mutation", choices=("ddc-signal", "keyboard-timer"))
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700)
    if args.mode == "lint":
        assert args.mutation is None
        lint(args.artifacts, args.expected)
    elif args.mode == "lint-harness":
        assert args.mutation is None
        stage_runtime(args.artifacts, None)
        raise SystemExit(
            check_harness(args.artifacts, args.artifacts / "tst_services.qml")
        )
    else:
        runtime(args.artifacts, args.mutation)


if __name__ == "__main__":
    main()
