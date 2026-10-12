#!/usr/bin/env python3
"""Targeted production tray drawer lint and isolated offscreen Loader regression.

Desktop panel, popup and notifier boundaries are fixtures; drawer bindings,
Repeater delegates, icon sources and mouse handlers are unmodified production.
Pin/unpin is exercised through settings changes, not a live tray menu/service.
"""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

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
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = re.findall(r"^Warning:.*$", output, re.M)
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("TRAY_DRAWER_LINT_COUNTS", dict(counts))
    # Keep only two explicit creation-site owner captures (without Bound),
    # UntypedObjectModel.values metadata, and Loader.item's QObject type gap.
    blocks = re.split(r"(?=Warning:)", output)[1:]
    captures = [block for block in blocks if "[unqualified]" in block]
    assert len(captures) == 2, "Unexpected owner captures:\n" + "".join(captures)
    assert all("ComponentBehavior: Bound" in block for block in captures)
    assert counts.get("missing-property") == 2, dict(counts)
    assert counts.get("incompatible-type") == 1, dict(counts)
    assert set(counts) == {"unqualified", "missing-property", "incompatible-type"}, (
        dict(counts)
    )
    metadata = [block for block in blocks if "[missing-property]" in block]
    assert (
        sum(
            'Member "values" not found on type "UntypedObjectModel"' in block
            for block in metadata
        )
        == 2
    )
    incompatible = [block for block in blocks if "[incompatible-type]" in block]
    assert "Cannot assign binding of type QObject to TrayMenu" in incompatible[0]
    assert result.returncode in (0, 255), result.returncode
    print("TRAY_DRAWER_LINT_PASS")


def stage_runtime(directory):
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
    # Copy only source inputs needed by the existing private resolver regression.
    sources = (
        TARGET,
        Path("Tests/tray-drawer-resolution.test.py"),
        Path("Tests/tray-widget-resolution.test.py"),
        Path("Tests/tray-drawer-warnings.test.py"),
        Path("Tests/workspace-runtime.test.py"),
        Path("Tests/grid-list-warnings.test.py"),
        Path("Tests/Qml/TrayDrawerWarningsHarness.qml"),
    )
    private_repo = directory / "source"
    for relative in sources:
        destination = private_repo / relative
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination.write_bytes((ROOT / relative).read_bytes())
    script = """import importlib.util
from pathlib import Path
root = Path('source')
spec = importlib.util.spec_from_file_location('drawer_resolution', root / 'Tests/tray-drawer-resolution.test.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
wait_message = module.resolver.wait_message

def wait_loaded(process, selector, output, marker, allow_failure=False):
    initial = not output
    wait_message(process, selector, output, marker, allow_failure)
    if initial and 'Configuration Loaded' not in ''.join(output):
        wait_message(process, selector, output, 'Configuration Loaded')

# Loader.onLoaded precedes engine startup completion and watcher installation.
module.resolver.wait_message = wait_loaded
for index, mode in enumerate(('cold-start', 'reload', 'reload-after-failure')):
    case = Path(str(index)).absolute()
    case.mkdir(mode=0o700)
    module.resolution(case, mode)
"""
    code, output = isolation.run_audited(
        directory,
        isolation.isolated_environment(directory),
        ["/usr/bin/python3", "-c", script],
        "drawer-private-reload",
    )
    assert code == 0, f"private reload regression exit {code}"
    assert output.count("DRAWER_RESOLUTION_PASS") == 3, output
    print("TRAY_DRAWER_PRIVATE_RELOAD_PASS: 3 cases; private children terminated")


def runtime(directory):
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
        stage_runtime(directory)
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
        assert "7 passed, 0 failed" in output
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
            {"lint": lint, "runtime": runtime}[args.mode](directory)
