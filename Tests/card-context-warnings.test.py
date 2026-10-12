#!/usr/bin/env python3
"""Bounded card dependencies: actual ShellScreens, private Quickshell, no desktop IO."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("Modules/Cards/ProfileCard.qml"),
    Path("Modules/Cards/ShortcutsCard.qml"),
    Path("Modules/Panels/ControlCenter/ControlCenterPanel.qml"),
)


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory, shadow):
    helper("wallpaper-tab-warnings.test.py").stage_runtime(directory)
    writer = helper("about-tab-warnings.test.py")
    write, singleton = writer.write_module, writer.singleton
    # Use installed Quickshell, including its real ShellScreen and uptime Process.
    for module in directory.glob("Quickshell*"):
        for path in sorted(
            module.rglob("*"), key=lambda path: len(path.parts), reverse=True
        ):
            if path.is_dir():
                path.rmdir()
            else:
                path.unlink()
        module.rmdir()
    write(
        directory,
        "qs.Modules.Cards",
        {
            "ProfileCard": (ROOT / TARGETS[0]).read_text(),
            "ShortcutsCard": (ROOT / TARGETS[1]).read_text(),
            "AudioCard": "import QtQuick\nItem {}",
            "WeatherCard": "import QtQuick\nItem {}",
            "MediaCard": "import QtQuick\nItem {}",
        },
    )
    write(
        directory,
        "qs.Modules.Panels.ControlCenter",
        {
            "ControlCenterPanel": (ROOT / TARGETS[2]).read_text(),
            "ControlCenterWidgetLoader": (
                ROOT / "Modules/Panels/ControlCenter/ControlCenterWidgetLoader.qml"
            ).read_text(),
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
import Quickshell
Item {
  id: host
  property ShellScreen screen
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool panelAnchorHorizontalCenter: false
  property bool panelAnchorVerticalCenter: false
  property bool panelAnchorTop: false
  property bool panelAnchorBottom: false
  property bool panelAnchorLeft: false
  property bool panelAnchorRight: false
  property bool isPanelOpen: false
  signal opened()
  signal closed()
  function open() { host.isPanelOpen = true; host.opened(); }
  function close() { host.isPanelOpen = false; host.closed(); }
  Loader { anchors.fill: parent; sourceComponent: host.panelContent }
}"""
        },
    )
    commons = directory / "qs/Commons"
    settings = commons / "Settings.qml"
    settings.write_text(
        singleton("""property var data: ({
  general: {avatarImage: ""},
  controlCenter: {position: "center", cards: [
    {id: "profile-card", enabled: true}, {id: "shortcuts-card", enabled: true}
  ], shortcuts: {left: [{id: "Action", caption: "Left"}], right: [{id: "Action", caption: "Right"}]}},
  bar: {monitors: []}, location: {weatherEnabled: false},
  ui: {fontDefault: "Sans Serif", fontFixed: "monospace", fontDefaultScale: 1, fontFixedScale: 1}
})
function preprocessPath(path) { return path; }""")
    )
    widgets = directory / "qs/Widgets"
    write(
        directory,
        "qs.Widgets",
        {
            **{p.stem: p.read_text() for p in widgets.glob("*.qml")},
            "NImageRounded": (ROOT / "Widgets/NImageRounded.qml").read_text(),
        },
    )
    write(
        directory,
        "qs.Modules.Panels.Settings",
        {
            "SettingsPanel": "import QtQuick\nQtObject { enum Tab { General, Display } }",
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "HostService": singleton('property string displayName: "Fixture User"'),
        },
    )
    write(
        directory,
        "qs.Services.Media",
        {
            "MediaService": singleton("property bool autoSwitchingPaused: false"),
        },
    )
    write(
        directory,
        "qs.Services.Networking",
        {
            "VPNService": singleton(
                "function beginPolling() {}\nfunction endPolling() {}"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "ControlCenterWidgetRegistry": singleton("""property var widgets: ({})
function getWidget(id) { return widgets[id] || null; }
function hasWidget(id) { return id in widgets; }"""),
            "TooltipService": singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
            "PanelService": singleton("""property var events: []
property var actionEvents: []
property var panel: ({requestedTab: -1, open: function() {}, close: function() {}})
function getPanel(name, screen) {
  events = events.concat([{name: name, screen: screen}]);
  return panel;
}"""),
        },
    )
    if shadow:
        button = widgets / "NIconButton.qml"
        source = button.read_text()
        assert source.count("id: root") == 1
        button.write_text(
            source.replace(
                "id: root",
                "id: root\n  property ShellScreen screen: Quickshell.screens[1]",
            )
        )
    (directory / "qs/shell.qml").write_text(
        (ROOT / "Tests/Qml/CardContextWarningsHarness.qml").read_text()
    )


def run_child(directory, environment, argv):
    sandbox = helper("wallpaper-tab-warnings.test.py").sandbox_command
    trace = directory / "access.trace"
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
            str(trace),
            *sandbox(directory, argv),
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="", flush=True)
    accesses = trace.read_text()
    assert not re.search(r'openat\(.*"/(?:home|syncthing)/.*= [0-9]+', accesses), (
        "host file opened"
    )
    assert not re.search(r"connect\(.*sa_family=AF_INET6?[,}]", accesses), (
        "network attempted"
    )
    print("CARD_CONFIG_RUNTIME_AUDIT_PASS")
    return result.returncode, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("baseline", "lint", "lint-harness", "runtime"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--direct-only", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-card-context-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = helper("wallpaper-tab-warnings.test.py")
        isolation.install_audit(directory)
        environment = isolation.isolated_environment(directory)
        if args.mode in ("baseline", "lint"):
            helper("media-mini-warnings.test.py").stage_modules(directory)
            for target, expected in zip(
                TARGETS, (4, 1, 1) if args.mode == "baseline" else (0, 0, 0)
            ):
                argv = [
                    "/usr/lib/qt6/bin/qmllint",
                    "-I",
                    temporary,
                    "-I",
                    "/usr/lib/qt6/qml",
                    "--json",
                    "-",
                ]
                if args.mode == "lint":
                    argv += ["--max-warnings", "0", "--unqualified", "error"]
                code, output = run_child(
                    directory, environment, [*argv, str(directory / "qs" / target)]
                )
                diagnostics = json.loads(output)
                warnings = [
                    warning
                    for entry in diagnostics["files"]
                    for warning in entry["warnings"]
                    if warning["type"] in ("warning", "critical")
                ]
                print(target.name, "WARNINGS", len(warnings), "EXIT", code)
                assert code == 0 and len(warnings) == expected, output
                if args.mode == "baseline" and target == TARGETS[2]:
                    assert [warning["id"] for warning in warnings] == [
                        "block-scope-var-declaration"
                    ], output
            return
        stage_runtime(directory, args.shadow)
        if args.direct_only:
            harness = directory / "qs/shell.qml"
            harness.write_text(
                harness.read_text().replace(
                    "property bool directOnly: false", "property bool directOnly: true"
                )
            )
        if args.mode == "lint-harness":
            harness = directory / "qs/shell.qml"
            if args.inject_warning:
                source = harness.read_text()
                assert source.count("id: scene") == 1
                harness.write_text(
                    source.replace(
                        "id: scene",
                        "id: scene\n    property int injectedWarning: scene.missingLintProbe",
                    )
                )
            code, output = run_child(
                directory,
                environment,
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "--bare",
                    "-I",
                    temporary,
                    "-I",
                    "/usr/lib/qt6/qml",
                    "--max-warnings",
                    "0",
                    "--json",
                    "-",
                    str(harness),
                ],
            )
            diagnostics = json.loads(output)
            warnings = [
                warning
                for entry in diagnostics["files"]
                for warning in entry["warnings"]
                if warning["type"] != "info"
            ]
            print("CARD_HARNESS_WARNINGS", len(warnings), "EXIT", code)
            assert code == 0 and not warnings, output
            return
        screens = directory / "screens.json"
        screens.write_text(
            json.dumps(
                {
                    "screens": [
                        {
                            "name": "first",
                            "x": 0,
                            "y": 0,
                            "width": 800,
                            "height": 600,
                            "dpi": 96,
                            "dpr": 1,
                        },
                        {
                            "name": "second",
                            "x": 800,
                            "y": 0,
                            "width": 800,
                            "height": 600,
                            "dpi": 96,
                            "dpr": 1,
                        },
                    ]
                }
            )
        )
        environment["QT_QPA_PLATFORM"] = "offscreen:configfile=" + str(screens)
        environment["QT_QPA_OFFSCREEN_NO_GLX"] = "1"
        code, output = run_child(
            directory,
            environment,
            [
                "/usr/bin/quickshell",
                "--no-color",
                "-p",
                str(directory / "qs"),
            ],
        )
        assert code == 0 and "CARD_CONTEXT_PASS:" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:|WARN|ERROR|CARD_CONTEXT_FAIL",
            output,
        ), output


if __name__ == "__main__":
    main()
