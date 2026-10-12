#!/usr/bin/env python3
"""Four bar widgets: strict production lint and masked offscreen behavior.

Standalone scoped test; production pills/icons/layouts, inert command, power,
keyboard and panel boundaries. No host config, compositor or backend access.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("CustomButton", "KeepAwake", "KeyboardLayout", "Spacer")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = helper("grid-list-warnings")


def stage_runtime(directory, mutation=None):
    pill = helper("bar-pill-warnings")
    pill.stage_runtime(directory)
    (directory / "tst_bar_pill.qml").unlink()
    modules = helper("workspace-runtime")
    singleton = modules.singleton
    controls = helper("bar-controls-warnings")

    def add(uri, sources):
        controls.add_module(modules, directory, uri, sources)

    add(
        "Quickshell",
        {
            "Quickshell": singleton(
                "property var commands: []\nfunction execDetached(argv) { commands = commands.concat([argv]); }"
            )
        },
    )
    add("Quickshell.Wayland", {"InertBoundary": "import QtQuick\nQtObject {}"})
    add(
        "Quickshell.Io",
        {
            "Process": "import QtQuick\nQtObject { property var stdout; property var stderr; property var command: []; property bool running: false; signal exited(int exitCode, int exitStatus) }",
            "SplitParser": "import QtQuick\nQtObject { signal read(string line) }",
            "StdioCollector": 'import QtQuick\nQtObject { property string text: ""; signal streamFinished() }',
        },
    )
    add(
        "qs.Commons",
        {
            "I18n": singleton(
                'function tr(key, values) { return key + (values ? ":" + values.layout : ""); }'
            ),
            "Time": singleton(
                'function formatVagueHumanReadableDuration(value) { return value + "s"; }'
            ),
            "Logger": singleton(
                "function i(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
        },
    )
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {", "QtObject {\nproperty real barHeight: 40"
        )
    )
    registry = (ROOT / "Services/UI/BarWidgetRegistry.qml").read_text()
    metadata = re.search(r"property var widgetMetadata: (\(\{.*?\}\))", registry, re.S)
    assert metadata
    add(
        "qs.Services.UI",
        {
            "BarWidgetRegistry": singleton(
                "property var widgetMetadata: " + metadata[1]
            ),
            "BarService": singleton(
                'property var settingsArgs: []\nfunction getTooltipDirection() { return "bottom"; }\nfunction getPillDirection(item) { return false; }\nfunction getContextMenuPosition(item, width, height) { return {x: 7, y: 9}; }\nfunction openWidgetSettings(...args) { settingsArgs = args; }'
            ),
            "PanelService": singleton(
                'property var events: []\nproperty var lastMenu: null\nproperty var panel: ({requestedTab: -1, open: function() { PanelService.events = PanelService.events.concat(["open"]); }})\nproperty var popup: ({close: function() { PanelService.events = PanelService.events.concat(["close"]); }, showContextMenu: function(menu) { PanelService.lastMenu = menu; PanelService.events = PanelService.events.concat(["menu"]); }})\nfunction getPanel(name, screen) { events = events.concat([name]); return panel; }\nfunction getPopupMenuWindow(screen) { return popup; }'
            ),
        },
    )
    add(
        "qs.Services.Power",
        {
            "IdleInhibitorService": singleton(
                "property bool isInhibited: false\nproperty var timeout: null\nproperty var deltas: []\nfunction manualToggle() { isInhibited = !isInhibited; }\nfunction changeTimeout(delta) { deltas = deltas.concat([delta]); timeout = (timeout || 0) + delta; }"
            )
        },
    )
    add(
        "qs.Services.Keyboard",
        {"KeyboardLayoutService": singleton('property string currentLayout: "us"')},
    )
    add(
        "qs.Modules.Panels.Settings",
        {"SettingsPanel": "import QtQuick\nQtObject { enum Tab { Bar } }"},
    )
    add(
        "qs.Widgets",
        {
            "NPopupContextMenu": "import QtQuick\nItem { property var model: []; property var lastAnchor: null; property real lastX: 0; property real lastY: 0; signal triggered(string action); implicitWidth: 180; implicitHeight: 120; function openAtItem(item, x, y) { lastAnchor = item; lastX = x; lastY = y; } }"
        },
    )
    add(
        "qs.Modules.Bar.Widgets",
        {
            name: (ROOT / f"Modules/Bar/Widgets/{name}.qml").read_text()
            for name in NAMES
        },
    )
    content = directory / "qs/Helpers/CustomButtonContent.js"
    content.parent.mkdir(parents=True)
    content.write_text((ROOT / "Helpers/CustomButtonContent.js").read_text())
    if mutation:
        path = directory / "qs/Modules/Bar/Widgets/CustomButton.qml"
        source = path.read_text()
        if mutation == "tail":
            source = source.replace("Math.max(0, textEnd - currentMaxTextLength)", "0")
        else:
            source = source.replace("settingsPanel.open();", "return;")
        path.write_text(source)
    (directory / "tst_bar_multiline.qml").write_text(
        (ROOT / "Tests/Qml/BarMultilineVarHarness.qml").read_text()
    )


def lint(directory, environment):
    helper("media-mini-warnings").stage_modules(directory)
    failures = []
    for name in NAMES:
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
                str(directory / f"qs/Modules/Bar/Widgets/{name}.qml"),
            ],
            name + "-lint",
        )
        headers = [
            line
            for line in output.splitlines()
            if line.startswith(("Warning:", "Error:"))
        ]
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            if re.findall(r"\[([^]]+)\]", line)
            else "var-hoisting"
            for line in headers
        )
        print(
            name, "ALL_WARNING_HEADERS", headers, "RESIDUAL", dict(counts), "EXIT", code
        )
        if code or headers:
            failures.append(name)
    assert not failures, failures


def lint_harness(directory, environment, inject_warning):
    stage_runtime(directory)
    harness = directory / "tst_bar_multiline.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: scene",
                "id: scene\n    property int lintProbe: scene.missingLintProbe",
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
        "bar-multiline-harness-lint",
    )
    report = json.loads(output)
    headers = [warning for entry in report["files"] for warning in entry["warnings"]]
    print("BAR_MULTILINE_HARNESS_DIAGNOSTICS", len(headers), "EXIT", code)
    if inject_warning:
        assert code != 0 and "missingLintProbe" in output, output
    return code or bool(headers)


def runtime(directory, environment, mutation):
    stage_runtime(directory, mutation)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_bar_multiline.qml"),
            "-import",
            str(directory),
        ],
        "bar-multiline-runtime",
    )
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output
    if mutation:
        assert code != 0 and "FAIL!" in output, "behavior mutation escaped"
        print("NEGATIVE_CONTROL_REJECTED", mutation)
    else:
        assert code == 0 and "0 failed" in output, f"runtime exit {code}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--mutation", choices=("tail", "click"))
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    if args.mutation and args.mode != "runtime":
        parser.error("--mutation requires runtime")
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-multiline-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            lint(directory, environment)
        elif args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory, environment, args.inject_warning))
        else:
            runtime(directory, environment, args.mutation)


if __name__ == "__main__":
    main()
