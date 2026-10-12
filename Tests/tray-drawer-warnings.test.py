#!/usr/bin/env python3
"""Targeted production tray drawer lint and isolated offscreen Loader regression.

Desktop panel, popup and notifier boundaries are fixtures; drawer bindings,
Repeater delegates, icon sources and mouse handlers are unmodified production.
Pin/unpin is exercised through settings changes, not a live tray menu/service.
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Tray/TrayDrawerPanel.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load_helper("tray_runtime_helpers", "workspace-runtime.test.py")
isolation = load_helper("drawer_isolation", "grid-list-warnings.test.py")


def lint(directory):
    load_helper("tray_lint_staging", "media-mini-warnings.test.py").stage_modules(
        directory
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = re.findall(r"^Warning:.*$", output, re.MULTILINE)
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("TRAY_DRAWER_LINT_COUNTS", dict(counts))
    # Bound removes both creation-site captures. Loader.item stays dynamic;
    # the two UntypedObjectModel.values metadata warnings remain honest.
    blocks = re.split(r"(?=Warning:)", output)[1:]
    captures = [block for block in blocks if "[unqualified]" in block]
    assert not captures, "Owner captures remain:\n" + "".join(captures)
    assert counts.get("missing-property") == 2, dict(counts)
    assert set(counts) == {"missing-property"}, dict(counts)
    metadata = [block for block in blocks if "[missing-property]" in block]
    assert (
        sum(
            'Member "values" not found on type "UntypedObjectModel"' in block
            for block in metadata
        )
        == 2
    )
    assert result.returncode in (0, 255), result.returncode
    print("TRAY_DRAWER_LINT_PASS")


def stage_runtime(directory, shadow=False):
    write = helpers.write_module
    singleton = helpers.singleton
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Quickshell": singleton('property string shellDir: ""'),
        },
    )
    write(
        directory,
        "Quickshell.Services.SystemTray",
        {
            "SystemTray": singleton(
                "property alias items: model\n"
                "property QtObject model: QtObject { id: model; property var values: [] }"
            ),
        },
    )
    write(
        directory,
        "Quickshell.Widgets",
        {
            "IconImage": """import QtQuick
Item {
  property string source
  property bool asynchronous
  property alias backer: image
  Image { id: image }
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("""property var data: ({bar: {position: "top", widgets: {left: [], right: []}}, colorSchemes: {darkMode: true}})
signal settingsSaved
"""),
            "Style": singleton(
                "property real capsuleHeight: 40; property real marginM: 8; property real marginS: 4"
            ),
            "NColor": singleton(
                'property color mOnSurface: "white"; property color mSurfaceVariant: "gray"'
            ),
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "PopupMenuWindow": """import QtQuick
import qs.Modules.Bar.Extras
Item {
  visible: false
  readonly property alias trayMenuLoader: menuLoader
  property int opens: 0
  property int closes: 0
  function open() { opens++; visible = true; }
  function close() { closes++; visible = false; }
  Loader { id: menuLoader; sourceComponent: TrayMenu {} }
}""",
            "SmartPanel": """import QtQuick
import Quickshell
Item {
  property ShellScreen screen
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool exclusiveKeyboard
  property bool isClosing: false
  property int closeCount: 0
  property alias contentItem: contentLoader.item
  function close() { closeCount++; visible = false; }
  Loader { id: contentLoader; anchors.fill: parent; sourceComponent: parent.panelContent }
}""",
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("""property QtObject popup
property QtObject openedPanel
signal popupMenuWindowRegistered(var registeredScreen)
function getPopupMenuWindow(screen) { return popup; }
"""),
            "TooltipService": singleton("""property string text: ""
property Item anchor
function hideImmediately() { text = ""; }
function hide() { text = ""; }
function show(item, title, direction) { anchor = item; text = title; }
"""),
            "BarService": singleton(
                'function getTooltipDirection() { return "bottom"; }'
            ),
        },
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "TrayMenu": """import QtQuick
Item {
  width: 120
  property var trayItem
  property string widgetSection
  property int widgetIndex
  property Item anchor
  property real menuX
  property real menuY
  function showAt(item, x, y) { anchor = item; menuX = x; menuY = y; }
}"""
        },
    )
    write(directory, "qs.Widgets", {"NText": "import QtQuick\nText {}"})
    write(
        directory,
        "qs.Modules.Panels.Tray",
        {"TrayDrawerPanel": (ROOT / TARGET).read_text()},
    )
    if shadow:
        panel = directory / "qs/Modules/MainScreen/SmartPanel.qml"
        panel.write_text(
            panel.read_text().replace(
                "id: contentLoader;",
                "id: contentLoader; property QtObject root: QtObject {};",
            )
        )
        drawer = directory / "qs" / TARGET
        drawer.write_text(
            drawer.read_text().replace(
                "id: repeater\n",
                "id: repeater\n          property QtObject content: QtObject {}\n",
            )
        )
    (directory / "tst_tray_drawer.qml").write_text(
        (ROOT / "Tests/Qml/TrayDrawerWarningsHarness.qml").read_text()
    )


def lint_harness(directory, inject_warning=False):
    stage_runtime(directory)
    harness = directory / "tst_tray_drawer.qml"
    if inject_warning:
        source = harness.read_text()
        marker = "id: scene"
        assert source.count(marker) == 1, "injection owner must be unique"
        harness.write_text(
            source.replace(
                marker,
                marker + "\n  property int injectedWarning: scene.missingLintProbe",
                1,
            )
        )
    code, output = isolation.run_audited(
        directory,
        isolation.isolated_environment(directory),
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
        "drawer-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("TRAY_DRAWER_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected semantic warning not diagnosed"
        assert "missingLintProbe" in output, "injected diagnostic not visible"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        case = directory / name
        case.mkdir(mode=0o700)
        code = lint_harness(case, injected)
        if injected:
            assert code != 0, "genuine harness warning accepted"
        else:
            assert code == 0, "clean harness lint failed"
    print("TRAY_DRAWER_HARNESS_WARNING_REJECTED")


def reload_regression(directory):
    load_helper("drawer_native", "tray-drawer-resolution.test.py").runtime(directory)


def runtime(directory, shadow=False):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key
        not in {
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "HOME",
            "NIRI_SOCKET",
            "HYPRLAND_INSTANCE_SIGNATURE",
            "SWAYSOCK",
        }
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    settings = Path(environment["HOME"]) / ".config/noctalia/fixture.json"
    settings.parent.mkdir(mode=0o700, parents=True)
    original = (ROOT / "Assets/settings-default.json").read_bytes()
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        path.touch(mode=0o600)
        path.write_bytes(original)
        assert path.read_bytes() == original, "fixture bytes differ"
        assert path.stat().st_mode & 0o777 == 0o600, "fixture mode differs"
    try:
        stage_runtime(directory, shadow)
        code, output = isolation.run_audited(
            directory,
            environment,
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_tray_drawer.qml"),
                "-import",
                str(directory),
            ],
            "drawer-runtime",
        )
        assert code == 0, f"Offscreen drawer exit {code}"
        assert "8 passed, 0 failed" in output
        assert not re.search(r"QWARN|QFATAL|ReferenceError|TypeError", output), output
        print("TRAY_DRAWER_RUNTIME_PASS")
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"
        assert settings.stat().st_mode & 0o777 == 0o600, "fixture settings mode changed"
        assert backup.stat().st_mode & 0o777 == 0o600, "fixture backup mode changed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mode", choices=("lint", "runtime"))
    mode.add_argument(
        "command",
        choices=("lint-harness", "lint-harness-regression", "reload-regression"),
        nargs="?",
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--shadow", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.command != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-tray-drawer-") as temporary:
        directory = Path(temporary)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.command == "lint-harness":
            raise SystemExit(lint_harness(directory, args.inject_warning))
        if args.command == "lint-harness-regression":
            lint_harness_regression(directory)
        elif args.command == "reload-regression":
            reload_regression(directory)
        else:
            if args.mode == "runtime":
                runtime(directory, args.shadow)
            else:
                lint(directory)
