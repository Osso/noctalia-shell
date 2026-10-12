#!/usr/bin/env python3
"""Bounded DockMenu proof: private offscreen fixtures, audited empty-home sandbox."""

import argparse
import importlib.util
import json
import os
import re
import sys
import shutil
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/Dock/DockMenu.qml")


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load("dock_isolation", "grid-list-warnings.test.py")
fixtures = load("dock_fixtures", "workspace-runtime.test.py")


def run_audited(directory, environment, command, label):
    code, output = isolation.run_audited(directory, environment, command, label)
    trace = (directory / f"{label}.trace").read_text()
    executables = re.findall(r'execve\("([^"]+)"', trace)
    assert executables, "execution audit missing"
    allowed = {"/usr/bin/bwrap", command[0]}
    assert set(executables) <= allowed, executables
    print("APP_LAUNCH_AUDIT: only sandbox and requested Qt tool executed")
    return code, output


def stage_runtime(directory, mutation):
    write = fixtures.write_module
    singleton = fixtures.singleton
    write(
        directory,
        "Quickshell",
        {
            "PopupAnchor": "import QtQuick\nQtObject { property Item item; property rect rect }",
            "PopupWindow": "import QtQuick\nimport Quickshell\nItem { property color color; property PopupAnchor anchor: PopupAnchor {}; width: implicitWidth; height: implicitHeight }",
            "DesktopAction": "import QtQuick\nQtObject { property string name; property int executions: 0; function execute() { executions++; } }",
            "DesktopEntry": "import QtQuick\nimport Quickshell\nQtObject { property string id; property list<DesktopAction> actions }",
            "DesktopEntries": singleton(
                "property var entry: null\nfunction heuristicLookup(id) { return entry; }\nfunction byId(id) { return entry; }"
            ),
        },
    )
    write(
        directory,
        "Quickshell.Wayland",
        {
            "Toplevel": "import QtQuick\nQtObject { property string appId; property int activations: 0; property int closes: 0; function activate() { activations++; } function close() { closes++; } }",
            "ToplevelManager": singleton("property var toplevels: ({values: []})"),
        },
    )
    write(
        directory,
        "Quickshell.Widgets",
        {"FixtureMarker": "import QtQuick\nQtObject {}"},
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: ({dock: {pinnedApps: []}})"),
            "I18n": singleton("function tr(key) { return key; }"),
            "Style": singleton(
                "\n".join(
                    f"property real {name}: {value}"
                    for name, value in {
                        "marginS": 4,
                        "marginM": 8,
                        "fontSizeS": 10,
                        "fontSizeL": 14,
                        "radiusS": 4,
                        "radiusXS": 2,
                        "borderS": 1,
                    }.items()
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "{value}"'
                    for name, value in {
                        "transparent": "transparent",
                        "mSurfaceVariant": "#222222",
                        "mOutline": "gray",
                        "mHover": "#444444",
                        "mOnHover": "white",
                        "mOnSurfaceVariant": "gray",
                    }.items()
                )
            ),
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NText": "import QtQuick\nText { property real pointSize: 10; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize }",
        },
    )
    source = (ROOT / TARGET).read_text()
    mutations = {
        "hover": (
            "root.hoveredItem = root.getHoveredItem(mouse.y);",
            "root.hoveredItem = -1;",
        ),
        "selection": (
            "return itemIndex >= 0 && itemIndex < root.items.length ? itemIndex : -1;",
            "return -1;",
        ),
        "action": ("action.execute();", "/* negative control: omit action */"),
        "close": ("root.requestClose();", "/* negative control: omit close request */"),
    }
    if mutation:
        old, new = mutations[mutation]
        assert old in source, mutation
        source = source.replace(old, new)
    write(directory, "qs.Modules.Dock", {"DockMenu": source})
    shutil.copyfile(
        ROOT / "Tests/Qml/DockMenuWarningsHarness.qml", directory / "tst_dock_menu.qml"
    )


def runtime(directory, environment, mutation):
    stage_runtime(directory, mutation)
    code, output = run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_dock_menu.qml"),
            "-import",
            str(directory),
        ],
        "dock-menu-runtime",
    )
    assert code == 0, f"runtime exit {code}"
    assert "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def lint_harness(directory, environment, inject_warning=False):
    stage_runtime(directory, None)
    harness = directory / "tst_dock_menu.qml"
    if inject_warning:
        source = harness.read_text()
        harness.write_text(
            source.replace(
                "id: tests",
                "id: tests\n    property int injectedWarning: tests.missingLintProbe",
                1,
            )
        )
    code, output = run_audited(
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
        "dock-menu-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("DOCK_MENU_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        code = lint_harness(staged, isolation.isolated_environment(staged), injected)
        if injected:
            assert code != 0, "genuine harness warning accepted"
        else:
            assert code == 0, "clean harness lint failed"
    print("DOCK_MENU_HARNESS_WARNING_REJECTED")


def deny_parent_access(event, args):
    if event in ("open", "os.listdir", "os.scandir") and args:
        path = args[0]
        if isinstance(path, (str, bytes, os.PathLike)):
            requested = Path(os.path.abspath(os.fsdecode(path)))
            protected = Path("/home/osso/.config")
            if requested == protected or protected in requested.parents:
                raise PermissionError(f"REAL_CONFIG_AUDIT_DENIED: {requested}")
    if event in ("socket.connect", "socket.bind", "socket.getaddrinfo"):
        raise PermissionError("PARENT_NETWORK_AUDIT_DENIED")


def prove_parent_guard():
    for event, args in (
        ("open", ("/home/osso/.config/noctalia/settings.json", "r", 0)),
        ("socket.connect", (None, ("127.0.0.1", 9))),
    ):
        try:
            sys.audit(event, *args)
        except PermissionError as error:
            print(error)
        else:
            raise AssertionError(f"parent guard failed: {event}")


def prove_child_guard(directory, environment):
    code, output = run_audited(
        directory,
        environment,
        [
            "/usr/bin/python3",
            "-c",
            "import errno, pathlib, socket; "
            "assert not pathlib.Path('/home/osso/.config').exists(); "
            "connection = socket.socket(); connection.settimeout(1); "
            "assert connection.connect_ex(('192.0.2.1', 9)) == errno.ENETUNREACH; "
            "connection.close(); print('CHILD_CONFIG_NETWORK_DENIED')",
        ],
        "dock-menu-guard",
    )
    assert code == 0, output
    assert "CHILD_CONFIG_NETWORK_DENIED" in output, output


def lint(directory, environment):
    load("dock_lint", "media-mini-warnings.test.py").stage_modules(directory)
    code, output = run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        "dock-menu-lint",
    )
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("DOCK_MENU_LINT_COUNTS", dict(counts), "EXIT", code)
    return counts, code


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "lint",
            "baseline",
            "runtime",
            "guard",
            "lint-harness",
            "lint-harness-regression",
        ),
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--mutation", choices=("hover", "selection", "action", "close"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-dock-menu-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        sys.addaudithook(deny_parent_access)
        prove_parent_guard()
        environment = isolation.isolated_environment(directory)
        if args.mode in ("lint", "baseline"):
            counts, code = lint(directory, environment)
            if args.mode == "lint":
                assert not counts, dict(counts)
                assert code == 0, code
        elif args.mode == "runtime":
            runtime(directory, environment, args.mutation)
        elif args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory, environment))
        elif args.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        elif args.mode == "guard":
            prove_child_guard(directory, environment)
