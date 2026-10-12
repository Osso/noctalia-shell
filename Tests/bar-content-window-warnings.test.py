#!/usr/bin/env python3
"""Standalone BarContentWindow proof; no host settings or desktop access.

Runtime uses synthetic PanelWindow transport and Bar content, preserving the
production bindings. Installed Quickshell metadata remains real for source lint.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/MainScreen/BarContentWindow.qml")
EXCLUSIONS = (
    Path("Modules/MainScreen/BarExclusionZone.qml"),
    Path("Modules/Bar/Extras/BarExclusionZone.qml"),
)


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load_helper("bar_content_isolation", "grid-list-warnings.test.py")
fixtures = load_helper("bar_content_fixtures", "about-tab-warnings.test.py")


def stage_runtime(directory, mutation):
    write, singleton = fixtures.write_module, fixtures.singleton
    write(
        directory,
        "FixtureTransport",
        {
            "Region": "import QtQuick\nQtObject {}",
            "WindowAnchors": "import QtQuick\nQtObject { property bool top; property bool bottom; property bool left; property bool right }",
            "WindowMargins": "import QtQuick\nQtObject { property real top; property real bottom; property real left; property real right }",
            "PanelWindow": """import QtQuick
import FixtureTransport
QtObject {
  id: window
  default property alias children: content.data
  property QtObject screen
  property color color
  property QtObject mask
  property real width: implicitWidth
  property real height: implicitHeight
  property real implicitWidth
  property real implicitHeight
  property WindowAnchors anchors: WindowAnchors {}
  property WindowMargins margins: WindowMargins {}
  property Item contentItem: Item {
    id: content
    width: window.implicitWidth
    height: window.implicitHeight
  }
}
""",
        },
    )
    write(
        directory,
        "FixtureWayland",
        {
            "WlrLayershell": singleton(
                "property string namespace\nproperty int layer\nproperty int exclusionMode"
            ),
            "WlrLayer": "import QtQuick\nQtObject { enum Layer { Top } }",
            "ExclusionMode": "import QtQuick\nQtObject { enum Mode { Ignore, Auto } }",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                """component BarSettings: QtObject {
  property string position: "top"
  property bool exclusive: true
  property bool floating: false
  property real marginHorizontal: 1.5
  property real marginVertical: 0.75
}
component SettingsData: QtObject {
  property BarSettings bar: BarSettings {}
}
property SettingsData data: SettingsData {}"""
            ),
            "Style": singleton(
                "property real marginXL: 12\nproperty real barHeight: 40"
            ),
            "NColor": singleton('property color transparent: "transparent"'),
            "Logger": singleton(
                "property var events: []\nfunction d(...args) { events = events.concat([args]); }"
            ),
        },
    )
    write(
        directory,
        "qs.Modules.Bar",
        {
            "Bar": 'import QtQuick\nItem { objectName: "fixtureBar"; property QtObject screen }'
        },
    )
    write(directory, "qs.Services.UI", {"Fixture": "import QtQuick\nQtObject {}"})
    source = stage_transport((ROOT / TARGET).read_text())
    # Only layer-shell transport is replaced; namespace expression stays real.
    source = source.replace(
        "WlrLayershell.namespace:", "property string fixtureNamespace:"
    )
    source = source.replace("WlrLayershell.layer:", "property int fixtureLayer:")
    source = source.replace(
        "WlrLayershell.exclusionMode:", "property int fixtureExclusionMode:"
    )
    if mutation == "routing":
        source = source.replace("screen: barWindow.selectedScreen", "screen: null")
    elif mutation == "owner-snapshot":
        source = source.replace(
            "readonly property ShellScreen selectedScreen: barWindow.screen",
            "property ShellScreen selectedScreen",
        ).replace(
            "Component.onCompleted: {",
            "Component.onCompleted: {\n    selectedScreen = barWindow.screen;",
            1,
        )
    elif mutation == "rotation":
        source = source.replace(
            'barPosition === "left" || barPosition === "right"', "false"
        )
    elif mutation == "margins":
        source = source.replace(
            "Settings.data.bar.marginHorizontal * Style.marginXL", "0"
        )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "BarContentWindow": source,
            "BarExclusionZone": stage_transport((ROOT / EXCLUSIONS[0]).read_text()),
        },
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "BarExclusionZone": stage_transport((ROOT / EXCLUSIONS[1]).read_text()),
        },
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/BarContentWindowWarningsHarness.qml",
        directory / "tst_bar_content.qml",
    )


def stage_transport(source):
    source = source.replace("import Quickshell.Wayland", "import FixtureWayland")
    source = source.replace(
        "import Quickshell\n",
        "import Quickshell\nimport FixtureTransport as Transport\n",
    )
    source = source.replace("PanelWindow {", "Transport.PanelWindow {")
    source = source.replace("mask: Region {}", "mask: Transport.Region {}")
    for field, kind in (
        ("namespace", "string"),
        ("layer", "int"),
        ("exclusionMode", "int"),
    ):
        source = source.replace(
            f"WlrLayershell.{field}:",
            f"property {kind} fixture{field[0].upper() + field[1:]}:",
        )
    return source


def screen_environment(directory, environment):
    config = directory / "screens.json"
    config.write_text(
        json.dumps(
            {
                "screens": [
                    {"name": "wide", "width": 1920, "height": 1080},
                    {"name": "portrait", "width": 900, "height": 1600},
                ]
            }
        )
    )
    environment["QT_QPA_PLATFORM"] = "offscreen:configfile=" + str(config)
    return environment


def lint_harness(directory, environment, inject_warning=False):
    stage_runtime(directory, None)
    harness = directory / "tst_bar_content.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: testCase",
                "id: testCase\n  property int injectedWarning: testCase.missingLintProbe",
                1,
            )
        )
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
            str(harness),
        ],
        "bar-content-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("BAR_CONTENT_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert code != 0, "injected warning accepted"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        code = lint_harness(staged, isolation.isolated_environment(staged), injected)
        assert (code != 0) if injected else (code == 0), code
    print("BAR_CONTENT_HARNESS_WARNING_REJECTED")


def execute(args, directory, environment):
    if args.mode == "lint":
        load_helper("bar_content_lint", "media-mini-warnings.test.py").stage_modules(
            directory
        )
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
    else:
        stage_runtime(directory, args.mutation)
        shutil.copyfile(directory / "tst_bar_content.qml", directory / "shell.qml")
        for path in (directory / "qs").iterdir():
            shutil.move(str(path), directory / path.name)
        environment["QML_IMPORT_PATH"] = str(directory)
        screen_environment(directory, environment)
        command = [
            "quickshell",
            "--no-color",
            "-p",
            str(directory / "shell.qml"),
        ]
    code, output = isolation.run_audited(
        directory, environment, command, "bar-content-" + args.mode
    )
    if args.mode == "lint":
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print("BAR_CONTENT_LINT_COUNTS", dict(counts), "EXIT", code)
        assert counts == {"uncreatable-type": 1, "missing-property": 4}, counts
        missing_margins = re.findall(r'Could not find property "([^"]+)"', output)
        missing_screen = re.findall(
            r'Member "([^"]+)" not found on type "QuickshellScreenInfo"', output
        )
        assert sorted(missing_margins) == ["bottom", "left", "right", "top"], (
            missing_margins
        )
        assert missing_screen == [], missing_screen
        for index, target in enumerate(EXCLUSIONS):
            exit_code, diagnostics = isolation.run_audited(
                directory,
                environment,
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "-I",
                    str(directory),
                    str(directory / "qs" / target),
                ],
                f"exclusion-{index}-lint",
            )
            warnings = [
                line for line in diagnostics.splitlines() if line.startswith("Warning:")
            ]
            print("SCREEN_OWNER_LINT", str(target), len(warnings), "EXIT", exit_code)
            assert len(warnings) == 1 and "[uncreatable-type]" in warnings[0], warnings
            assert exit_code == 0, exit_code
        assert code == 0, code
    else:
        assert code == 0, f"runtime exit {code}"
        assert "BAR_SCREEN_OWNER_PASS" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL| WARN[: ]| ERROR[: ]|ReferenceError|TypeError|Binding loop",
            output,
        ), output


NATIVE_HARNESS = """import QtQuick
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Modules.Bar.Extras as Extras
ShellRoot {
  id: probe
  property string generation: "INITIAL"
  property int step: 0
  property var windows: []
  property ShellScreen originalScreen: Quickshell.screens[0]
  Component { id: content; BarContentWindow { visible: false } }
  Component { id: mainZone; BarExclusionZone { visible: false } }
  Component { id: extraZone; Extras.BarExclusionZone { visible: false } }

  function check(value, message) {
    if (!value) throw new Error(message);
  }

  function recreate() {
    for (const window of windows) window.destroy();
    windows = [];
    for (const component of [content, mainZone, extraZone]) {
      const window = component.createObject(probe, {screen: originalScreen});
      check(window !== null, "native creation");
      windows.push(window);
    }
  }

  function assertScreen() {
    for (const window of windows) {
      check(window.selectedScreen === window.screen, "owner identity");
      check(window.screen === originalScreen, "actual ShellScreen identity");
      check(window.screenName === originalScreen.name, "screen name");
    }
    const bar = windows[0];
    const vertical = bar.barIsVertical;
    check(bar.implicitWidth === (vertical ? 40 : originalScreen.width), "reactive width");
    check(bar.implicitHeight === (vertical ? originalScreen.height : 40), "reactive height");
  }

  Timer {
    interval: 50
    running: true
    repeat: true
    onTriggered: {
      try {
        if (probe.step === 0) {
          probe.recreate();
          probe.assertScreen();
          console.log("BAR_NATIVE_READY", probe.generation, probe.originalScreen.width, probe.originalScreen.height);
          probe.step++;
        } else if (probe.step === 1 && probe.originalScreen.width === 640) {
          for (const position of ["top", "right", "bottom", "left"]) {
            Settings.data.bar.position = position;
            probe.assertScreen();
          }
          probe.recreate();
          probe.step++;
        } else if (probe.step === 2) {
          probe.assertScreen();
          console.log("BAR_NATIVE_PASS", probe.generation);
          probe.step++;
          if (probe.generation === "RELOADED") Qt.quit();
        }
      } catch (error) {
        console.error(error);
        Qt.exit(1);
      }
    }
  }
}
"""


def await_marker(process, log, marker, count=1):
    deadline = time.monotonic() + 15
    while log.read_text().count(marker) < count:
        output = log.read_text()
        assert process.poll() is None, output
        assert not re.search(
            r" WARN[: ]| ERROR[: ]|TypeError|ReferenceError|Binding loop", output
        ), output
        assert time.monotonic() < deadline, output
        time.sleep(0.05)


def native(directory):
    stage_runtime(directory, None)
    for path in (directory / "qs").iterdir():
        shutil.move(str(path), directory / path.name)
    for target in (TARGET, *EXCLUSIONS):
        (directory / target).write_text((ROOT / target).read_text())
    shell = directory / "shell.qml"
    shell.write_text(NATIVE_HARNESS)
    display = load_helper("bar_private_display", "popup-private-display.py")
    log = directory / "native.log"
    with (
        display.PopupPrivateDisplay(directory / "display") as environment,
        log.open("w") as stream,
    ):
        environment["QML_IMPORT_PATH"] = str(directory)
        process = subprocess.Popen(
            display.sandbox(directory, ["quickshell", "--no-color", "-p", str(shell)]),
            env=environment,
            stdout=stream,
            stderr=stream,
            start_new_session=True,
        )
        try:
            await_marker(process, log, "BAR_NATIVE_READY INITIAL 1280 720")
            result = subprocess.run(
                display.sandbox(
                    directory / "display",
                    ["niri", "msg", "output", "winit", "scale", "2"],
                ),
                env=environment,
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            await_marker(process, log, "BAR_NATIVE_PASS INITIAL")
            # Reload a production owner file, not just the harness.
            owner = directory / TARGET
            owner.write_text(owner.read_text() + "\n// Private owner reload probe.\n")
            await_marker(process, log, "BAR_NATIVE_READY INITIAL 640 360")
            await_marker(process, log, "BAR_NATIVE_PASS INITIAL", count=2)
            shell.write_text(
                NATIVE_HARNESS.replace(
                    'generation: "INITIAL"', 'generation: "RELOADED"'
                )
            )
            process.wait(timeout=15)
            output = log.read_text()
            print(output, end="")
            assert process.returncode == 0, output
            assert "BAR_NATIVE_PASS RELOADED" in output, output
            assert output.count("BAR_NATIVE_PASS INITIAL") == 2, output
            assert not re.search(
                r" WARN[: ]| ERROR[: ]|TypeError|ReferenceError|Binding loop", output
            ), output
            print("BAR_NATIVE_COLD_GEOMETRY_RECREATION_OWNER_RELOAD_PASS")
        finally:
            display.stop_owned(process)
            assert process.poll() is not None, "private bar client survived"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "lint",
            "runtime",
            "lint-harness",
            "lint-harness-regression",
            "native",
        ),
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument(
        "--mutation", choices=("routing", "rotation", "margins", "owner-snapshot")
    )
    args = parser.parse_args()
    if args.mutation and args.mode != "runtime":
        parser.error("--mutation requires runtime")
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-content-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        else:
            environment = isolation.isolated_environment(directory)
            if args.mode == "native":
                native(directory)
                return
            if args.mode == "lint-harness":
                raise SystemExit(
                    lint_harness(directory, environment, args.inject_warning)
                )
            execute(args, directory, environment)


if __name__ == "__main__":
    main()
