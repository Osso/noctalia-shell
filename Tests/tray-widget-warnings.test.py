#!/usr/bin/env python3
"""Production Tray + installed IconImage, offscreen with inert desktop boundaries."""

import argparse
from collections import Counter
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Widgets/Tray.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load_helper("tray_widget_helpers", "workspace-runtime.test.py")
isolation = load_helper("tray_widget_isolation", "grid-list-warnings.test.py")


def lint(directory):
    load_helper("tray_widget_lint", "media-mini-warnings.test.py").stage_modules(
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
    print("TRAY_WIDGET_LINT_COUNTS", dict(counts))
    blocks = re.split(r"(?=Warning:)", output)[1:]
    actionable = [block for block in blocks if "[unqualified]" in block]
    assert not actionable, "Known-owner accesses remain:\n" + "".join(actionable)
    assert set(counts) <= {"unqualified", "missing-property", "incompatible-type"}, (
        dict(counts)
    )
    # Actual production metadata, not fixture metadata, must expose the menu.
    menu_warnings = [block for block in blocks if "QQuickLoader::item" in block]
    assert not menu_warnings, "Loaded menu remains untyped:\n" + "".join(menu_warnings)
    # Popup QObject, Repeater QQuickItem and external model metadata stay visible.
    assert counts.get("missing-property") == 12, dict(counts)
    assert counts.get("incompatible-type") == 1, dict(counts)
    assert result.returncode in (0, 255), result.returncode
    print("TRAY_WIDGET_LINT_PASS")


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
                "component TrayItems: QtObject { property var values: [] }\n"
                "property TrayItems items: TrayItems {}"
            ),
        },
    )
    write(
        directory,
        "Quickshell.Widgets",
        {
            "IconImage": Path(
                "/usr/lib/qt6/qml/Quickshell/Widgets/IconImage.qml"
            ).read_text(),
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                'property var data: ({bar: {position: "top", density: false, widgets: {left: []}}, colorSchemes: {darkMode: true}})\nsignal settingsSaved'
            ),
            "Style": singleton(
                'property real capsuleHeight: 40; property real barHeight: 40; property real marginM: 8; property real marginXS: 3; property real radiusM: 8; property color capsuleColor: "black"'
            ),
            "NColor": singleton(
                'property color transparent: "transparent"; property color mOnSurface: "white"; property color mOnPrimary: "white"; property color mSurfaceVariant: "gray"'
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Logger": singleton(
                "function d(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("""property QtObject popup
property QtObject openedPanel
property QtObject drawer
signal popupMenuWindowRegistered(var registeredScreen)
function getPopupMenuWindow(screen) { return popup; }
function getPanel(name, screen) { return drawer; }
"""),
            "TooltipService": singleton("""property string text: ""
property Item anchor
function hideImmediately() { text = ""; }
function hide() { text = ""; }
function show(item, title, direction) { anchor = item; text = title; }
"""),
            "BarService": singleton(
                'function getTooltipDirection() { return "bottom"; }\nfunction getPillDirection(item) { return false; }'
            ),
        },
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "BarWidgetRegistry": singleton(
                "property var widgetMetadata: ({Tray: {blacklist: [], pinned: [], drawerEnabled: true}})"
            ),
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NIconButton": """import QtQuick
Item {
  property string tooltipText
  property string tooltipDirection
  property bool density
  property real baseSize
  property bool applyUiScale
  property color colorBg
  property color colorFg
  property color colorBorder
  property color colorBorderHover
  property string icon
  signal clicked
  signal rightClicked
}"""
        },
    )
    source = (ROOT / TARGET).read_text()
    if shadow:
        source = source.replace(
            "        MouseArea {",
            """        MouseArea {
          property QtObject popupMenuWindow: QtObject {
            function close() { throw new Error("SHADOW_POPUP"); }
          }
          property Loader trayMenu: Loader {}
          property QtObject loadedTrayMenu: QtObject {}
          property QtObject screen: QtObject {}
""",
        )
    write(directory, "qs.Modules.Bar.Widgets", {"Tray": source})
    harness = (ROOT / "Tests/Qml/TrayWidgetWarningsHarness.qml").read_text()
    # Give the inert transport the same nominal module type as the real menu.
    menu_start = harness.index("  component TrayMenu: Item {")
    menu_end = harness.index("\n\n  Item {", menu_start)
    menu = harness[menu_start:menu_end].replace("  component TrayMenu:", "", 1)
    menu_module = directory / "qs/Modules/Bar/Extras"
    (menu_module / "TrayMenu.qml").write_text(
        "import QtQuick\nimport Quickshell\n" + menu
    )
    with (menu_module / "qmldir").open("a") as declarations:
        declarations.write("TrayMenu 1.0 TrayMenu.qml\n")
    harness = harness[:menu_start] + harness[menu_end:]
    harness = harness.replace(
        "import qs.Modules.Bar.Widgets",
        "import qs.Modules.Bar.Extras\nimport qs.Modules.Bar.Widgets",
    )
    (directory / "tst_tray_widget.qml").write_text(harness)
    # Local SVG reaches real Image.Ready without icon themes/providers or DBus.
    (directory / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>'
    )


def lint_harness(directory):
    stage_runtime(directory)
    return check_harness(directory, directory / "tst_tray_widget.qml")


def lint_harness_regression(directory):
    clean = directory / "clean"
    clean.mkdir()
    assert lint_harness(clean) == 0, "clean harness lint failed"
    injected = directory / "injected"
    injected.mkdir()
    stage_runtime(injected)
    harness = injected / "tst_tray_widget.qml"
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
    assert check_harness(injected, harness) != 0, "genuine warning was accepted"
    print("TRAY_WIDGET_HARNESS_WARNING_REJECTED")


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
                str(directory / "tst_tray_widget.qml"),
                "-import",
                str(directory),
            ],
            "tray-widget-shadow" if shadow else "tray-widget-runtime",
        )
        assert code == 0, f"Offscreen Tray exit {code}"
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
        print("TRAY_WIDGET_RUNTIME_PASS")
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
        "command", choices=("lint-harness", "lint-harness-regression"), nargs="?"
    )
    parser.add_argument("--shadow", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-tray-widget-") as temporary:
        directory = Path(temporary)
        isolation.install_settings_guard(directory)
        if args.command == "lint-harness":
            raise SystemExit(lint_harness(directory))
        if args.command == "lint-harness-regression":
            lint_harness_regression(directory)
        else:
            if args.mode == "runtime":
                runtime(directory, args.shadow)
            else:
                lint(directory)
