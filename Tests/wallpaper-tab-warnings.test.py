#!/usr/bin/env python3
"""WallpaperTab-only lint and private offscreen UI; no host settings or images."""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/WallpaperTab.qml")
PARENT = Path("Modules/Panels/Settings/SettingsPanel.qml")


def install_audit(directory):
    def audit(event, args):
        if event in ("socket.connect", "socket.getaddrinfo"):
            raise PermissionError("network denied")
        if event not in ("open", "os.listdir", "os.scandir"):
            return
        if not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.path.abspath(os.fsdecode(args[0])))
        if path.is_relative_to(directory):
            return
        if path.is_relative_to(ROOT):
            if path.suffix in (".qml", ".js", ".py", ".pyc"):
                return
            raise PermissionError(f"non-code repository resource denied: {path}")
        if path.is_relative_to("/home") or path.is_relative_to("/syncthing"):
            raise PermissionError(f"host resource denied: {path}")

    sys.addaudithook(audit)
    for path in (
        "/home/osso/.config/noctalia/settings.json",
        "/syncthing/Sync/wallpaper-probe.jpg",
    ):
        try:
            open(path, "rb")
        except PermissionError:
            print("AUDIT_ACCESS_DENIED", path)
        else:
            raise AssertionError(f"audit allowed {path}")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory, owner_shadow=False):
    writer = helper("about-tab-warnings.test.py")
    write = writer.write_module
    singleton = writer.singleton
    controls = (
        "NHeader",
        "NText",
        "NIcon",
        "NIconButton",
        "NLabel",
        "NTextInput",
        "NTextInputButton",
        "NDivider",
        "NToggle",
        "NComboBox",
        "NBox",
        "NColorPicker",
        "NValueSlider",
        "NSlider",
        "NListView",
        "NScrollView",
    )
    write(
        directory,
        "qs.Widgets",
        {
            **{name: (ROOT / f"Widgets/{name}.qml").read_text() for name in controls},
            # Unopened color dialog is outside this tab's routing coverage.
            "NColorPickerDialog": """import QtQuick.Controls
Popup {
  property color selectedColor
  signal colorSelected(color color)
}""",
            # Filesystem picker boundary: records selection/open, never enumerates files.
            "NFilePicker": """import QtQuick
Item {
  property string selectionMode
  property string title
  property string initialPath
  property int opens: 0
  signal accepted(var paths)
  function open() { opens++; }
}""",
        },
    )
    if owner_shadow:
        button = directory / "qs/Widgets/NIconButton.qml"
        button.write_text(
            button.read_text().replace(
                "id: root",
                "id: root\n  property ShellScreen screen: Quickshell.screens[1]",
            )
        )
    stage_parent(directory, write, singleton)
    write(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton(
                'property var screens: []\nfunction env(name) { return "/private-fixture"; }'
            ),
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
        },
    )
    write(directory, "Quickshell.Io", {"Fixture": "import QtQuick\nQtObject {}"})
    write(directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"})
    settings = {
        "ui": {
            "fontDefault": "Sans Serif",
            "fontFixed": "monospace",
            "fontDefaultScale": 1,
            "fontFixedScale": 1,
            "settingsPanelAttachToBar": False,
        },
        "bar": {"position": "top", "floating": False},
        "wallpaper": {
            "enabled": True,
            "overviewEnabled": False,
            "directory": "/private-fixture/main",
            "recursiveSearch": False,
            "enableMultiMonitorDirectories": True,
            "hideWallpaperFilenames": False,
            "panelPosition": "follow_bar",
            "fillMode": "crop",
            "fillColor": "#112233",
            "transitionType": "fade",
            "transitionDuration": 1000,
            "transitionEdgeSmoothness": 0.5,
            "randomEnabled": True,
            "randomIntervalSec": 300,
        },
    }
    style = {
        "uiScaleRatio": 1,
        "marginXXS": 2,
        "marginXS": 4,
        "marginS": 6,
        "marginM": 9,
        "marginL": 13,
        "radiusXS": 2,
        "radiusS": 4,
        "radiusM": 8,
        "radiusL": 12,
        "borderS": 1,
        "borderM": 2,
        "borderL": 3,
        "baseWidgetSize": 32,
        "sliderWidth": 200,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXL": 16,
        "fontSizeXXL": 18,
        "marginXL": 18,
        "fontWeightRegular": 400,
        "fontWeightMedium": 500,
        "fontWeightSemiBold": 600,
        "fontWeightBold": 700,
        "animationFast": 0,
        "animationNormal": 0,
        "opacityFull": 1,
        "opacityMedium": 0.6,
    }
    colors = {
        "mPrimary": "#3355aa",
        "mSecondary": "#557733",
        "mOnPrimary": "#ffffff",
        "mSurface": "#202020",
        "mSurfaceVariant": "#141414",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#aaaaaa",
        "mOutline": "#808080",
        "mHover": "#404040",
        "mOnHover": "#ffffff",
        "mError": "#ff0000",
        "black": "#000000",
        "transparent": "transparent",
    }
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(settings)),
            "Style": singleton(
                "\n".join(
                    f"property real {key}: {value}" for key, value in style.items()
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {key}: "{value}"' for key, value in colors.items()
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Time": singleton(
                'function formatVagueHumanReadableDuration(seconds) { return seconds + " seconds"; }'
            ),
            "Icons": singleton(
                'property string defaultIcon: "disc"\nproperty string fontFamily: "Sans Serif"\nfunction get(name) { return "*"; }'
            ),
            "Logger": singleton(
                "function w(...args) { console.warn(...args); }\nfunction callStack() { console.trace(); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {"CompositorService": singleton("property bool isNiri: true")},
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
            "PanelService": singleton("""property var panels: []
property var requests: []
function getPanel(name, screen) {
  requests = requests.concat([{name: name, screen: screen}]);
  return panels.find(panel => panel.screen === screen) || null;
}"""),
            "WallpaperService": singleton("""property int restarts: 0
property var directories: ({fixture: '/private-fixture/monitor'})
property var fillModeModel: [{key: 'crop', name: 'Crop'}, {key: 'fit', name: 'Fit'}]
property var transitionsModel: [{key: 'fade', name: 'Fade'}, {key: 'none', name: 'None'}]
function restartRandomWallpaperTimer() { restarts++; }
function getMonitorDirectory(name) { return directories[name] || ''; }
function setMonitorDirectory(name, path) { directories = Object.assign({}, directories, {[name]: path}); }"""),
        },
    )
    (directory / "tst_wallpaper_tab.qml").write_text(
        (ROOT / "Tests/Qml/WallpaperTabWarningsHarness.qml").read_text()
    )


def stage_parent(directory, write, singleton):
    # Retain the real SettingsPanel Component -> Repeater -> Flickable -> Loader path.
    # Only unrelated tab bodies and the desktop-surface boundary are inert.
    tabs = helper("settings-panel-warnings.test.py").TABS
    write(
        directory,
        "qs.Modules.Panels.Settings.Tabs",
        {
            **{name + "Tab": "import QtQuick\nItem {}" for name in tabs},
            "WallpaperTab": (ROOT / TARGET).read_text(),
        },
    )
    write(
        directory,
        "qs.Modules.Panels.Settings.Tabs.ColorScheme",
        {"ColorSchemeTab": "import QtQuick\nItem {}"},
    )
    write(
        directory,
        "qs.Modules.Panels.Settings",
        {"SettingsPanel": (ROOT / PARENT).read_text()},
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
import Quickshell
Item {
  id: panel
  property ShellScreen screen
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool forceAttachToBar
  property bool panelAnchorHorizontalCenter
  property bool panelAnchorVerticalCenter
  property bool panelAnchorTop
  property bool panelAnchorBottom
  property bool panelAnchorLeft
  property bool panelAnchorRight
  property bool isPanelOpen: false
  signal opened()
  function setPosition() {}
  function close() { isPanelOpen = false; }
  Loader { anchors.fill: parent; sourceComponent: panel.panelContent }
}"""
        },
    )
    write(
        directory,
        "qs.Services.System",
        {"ProgramCheckerService": singleton("function checkAllPrograms() {}")},
    )


def mutate_routing(directory, mutation):
    if mutation == "owner":
        path = directory / "qs" / TARGET
        original = 'getPanel("wallpaperPanel", root.screen)'
        replacement = 'getPanel("wallpaperPanel", screen)'
    else:
        path = directory / "qs" / PARENT
        original = "screen: root.screen"
        replacement = (
            ""
            if mutation == "caller"
            else "Component.onCompleted: screen = root.screen"
        )
    source = path.read_text()
    assert source.count(original) == 1, "routing mutation site missing or ambiguous"
    path.write_text(source.replace(original, replacement))


def isolated_environment(directory):
    environment = {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for name in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    # Neither config location is readable, even inside this private mount.
    private_config = Path(environment["HOME"]) / ".config"
    private_config.mkdir(mode=0o700)
    for config in (private_config, Path(environment["XDG_CONFIG_HOME"])):
        config.chmod(0)
        try:
            (config / "noctalia/settings.json").read_bytes()
        except PermissionError:
            print("PRIVATE_CONFIG_DENIED", config)
        else:
            raise AssertionError("private config readable")
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/system",
    )
    return environment


def sandbox_command(directory, argv):
    # Allowlist mounts: neither repository, real home, wallpaper trees nor /run survive.
    return [
        "bwrap",
        "--die-with-parent",
        "--unshare-all",
        "--new-session",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--ro-bind",
        "/etc/fonts",
        "/etc/fonts",
        "--ro-bind",
        "/etc/ld.so.cache",
        "/etc/ld.so.cache",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(directory),
        str(directory),
        "--chdir",
        str(directory),
        "--",
        *argv,
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "lint-harness", "runtime", "isolation")
    )
    parser.add_argument("--mutation", action="store_true")
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--owner-shadow", action="store_true")
    parser.add_argument("--routing-mutation", choices=("owner", "caller", "snapshot"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-wallpaper-tab-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        install_audit(directory)
        environment = isolated_environment(directory)
        if args.mode == "lint":
            helper("media-mini-warnings.test.py").stage_modules(directory)
            argv = [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                temporary,
                str(directory / "qs" / TARGET),
                str(directory / "qs" / PARENT),
            ]
        elif args.mode == "lint-harness":
            stage_runtime(directory, owner_shadow=args.owner_shadow)
            harness = directory / "tst_wallpaper_tab.qml"
            if args.inject_warning:
                harness.write_text(
                    harness.read_text().replace(
                        'name: "WallpaperTabWarnings"',
                        'name: "WallpaperTabWarnings"\n  property int injectedWarning: missingFixtureValue',
                    )
                )
            argv = [
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
            ]
        elif args.mode == "runtime":
            stage_runtime(directory, owner_shadow=args.owner_shadow)
            if args.mutation:
                staged = directory / "qs" / TARGET
                staged.write_text(
                    staged.read_text().replace(
                        "onToggled: checked => Settings.data.wallpaper.enabled = checked",
                        "onToggled: checked => Settings.data.wallpaper.enabled = !checked",
                    )
                )
            if args.routing_mutation:
                mutate_routing(directory, args.routing_mutation)
            argv = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_wallpaper_tab.qml"),
                "-import",
                temporary,
            ]
        else:
            argv = [
                "/usr/bin/python3",
                "-c",
                """import pathlib, socket
for path in ('/home/osso/.config/noctalia/settings.json', '/syncthing', '/run/user'):
    assert not pathlib.Path(path).exists(), path
    print('SANDBOX_PATH_ABSENT', path)
s = socket.socket()
s.settimeout(1)
try:
    s.connect(('1.1.1.1', 443))
except OSError as error:
    print('SANDBOX_NETWORK_DENIED', error)
else:
    raise AssertionError('network accessible')
finally:
    s.close()
""",
            ]
        result = subprocess.run(
            sandbox_command(directory, argv),
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if args.mode == "lint":
            warnings = [
                line for line in output.splitlines() if line.startswith("Warning:")
            ]
            counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
            print("WALLPAPER_TAB_LINT_COUNTS", dict(counts), "TOTAL", len(warnings))
            assert not warnings, dict(counts)
        elif args.mode == "lint-harness":
            diagnostics = json.loads(result.stdout)
            warnings = [
                warning
                for diagnostic in diagnostics["files"]
                for warning in diagnostic["warnings"]
                if warning["type"] == "warning"
            ]
            print("WALLPAPER_TAB_HARNESS_LINT_COUNTS", {"total": len(warnings)})
            assert not warnings, "WallpaperTab harness warnings remain"
        elif args.mode == "runtime":
            assert "0 failed" in output, "Missing successful QtTest completion"
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
                output,
            ), output
        assert result.returncode == 0, result.returncode


if __name__ == "__main__":
    main()
