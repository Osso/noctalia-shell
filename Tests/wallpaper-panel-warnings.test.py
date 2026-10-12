#!/usr/bin/env python3
"""One-file lint and isolated offscreen production wallpaper panel behavior.

Only desktop, styled-control, settings and wallpaper-service boundaries are fake.
Production filtering, grids, delegates, keyboard/tap handlers and options run in Qt.
"""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Wallpaper/WallpaperPanel.qml")


def write_module(directory, uri, sources):
    module = directory.joinpath(*uri.split("."))
    module.mkdir(parents=True, exist_ok=True)
    declarations = ["module " + uri]
    for name, source in sources.items():
        (module / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml")
    (module / "qmldir").write_text("\n".join(declarations) + "\n")


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def lint(directory):
    spec = importlib.util.spec_from_file_location(
        "media_lint_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    staging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(staging)
    staging.stage_modules(directory)
    result = subprocess.run(
        sandbox_command(
            directory,
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / TARGET),
            ],
        ),
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = re.findall(r"^Warning:.*$", output, re.M)
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("WALLPAPER_PANEL_LINT_COUNTS", dict(counts))
    blocks = re.split(r"(?=Warning:)", output)[1:]
    actionable = [
        block
        for block in blocks
        if "[unqualified]" in block and "ComponentBehavior: Bound" not in block
    ]
    assert not actionable, "Known-owner accesses remain:\n" + "".join(actionable)
    assert not counts, dict(counts)
    assert result.returncode == 0
    print("WALLPAPER_PANEL_LINT_PASS (zero warnings)")


def stage_runtime(directory):
    files = directory / "absent-wallpapers"
    assert not files.exists()
    write_module(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name; property int width: 1920 }",
            "Quickshell": """pragma Singleton
import QtQuick
QtObject {
  property list<ShellScreen> screens: [ShellScreen { name: "DP-1" }, ShellScreen { name: "HDMI-A-1"; width: 2560 }]
}""",
        },
    )
    wallpaper = dict(
        panelPosition="follow_bar",
        useWallhaven=False,
        setWallpaperOnAllMonitors=False,
        enableMultiMonitorDirectories=False,
        hideWallpaperFilenames=False,
        wallhavenQuery="forest",
        wallhavenResolutionWidth="1920",
        wallhavenResolutionHeight="1080",
        wallhavenResolutionMode="atleast",
        wallhavenCategories="111",
        wallhavenPurity="100",
        wallhavenSorting="relevance",
        wallhavenOrder="desc",
    )
    properties = []
    for name, value in wallpaper.items():
        kind = "bool" if isinstance(value, bool) else "var"
        properties.append(f"property {kind} {name}: {json.dumps(value)}")
    source = (ROOT / TARGET).read_text()
    style = set(re.findall(r"Style\.(\w+)", source))
    colors = set(re.findall(r"NColor\.(\w+)", source))
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                'property string cacheDirImagesWallpapers: ""\nproperty QtObject data: QtObject { property var bar: ({position: "top"}); property QtObject wallpaper: QtObject {\n'
                + "\n".join(properties)
                + "\n} }"
            ),
            "Style": singleton(
                "\n".join(
                    f"property real {name}: {0 if name.startswith('animation') else 1 if name == 'uiScaleRatio' else 12}"
                    for name in sorted(style)
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "{"transparent" if name == "transparent" else "#808080"}"'
                    for name in sorted(colors)
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Logger": singleton("function d(...args) {}"),
        },
    )
    write_module(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
import Quickshell
Item {
  property ShellScreen screen
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property real preferredWidthRatio
  property real preferredHeightRatio
  property bool panelAnchorHorizontalCenter
  property bool panelAnchorVerticalCenter
  property bool panelAnchorLeft
  property bool panelAnchorRight
  property bool panelAnchorBottom
  property bool panelAnchorTop
  property bool contentActive: true
  property int closeCount: 0
  signal opened
  signal closed
  function close() { closeCount++; closed(); }
  Loader { anchors.fill: parent; active: parent.contentActive; sourceComponent: parent.panelContent }
}""",
        },
    )
    write_module(
        directory,
        "qs.Modules.Panels.Settings",
        {
            "SettingsPanel": "import QtQuick\nItem { enum Tab { Wallpaper } }",
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "WallpaperService": singleton(
                """property bool scanning: false
property var changes: []
property string files: "@FILES@"
property var lists: ({"DP-1": [files + "/forest.png", files + "/desert.png"], "HDMI-A-1": [files + "/ocean.png"]})
property var selected: ({"DP-1": files + "/forest.png", "HDMI-A-1": files + "/ocean.png"})
signal wallpaperChanged(string screenName, string path)
signal wallpaperDirectoryChanged(string screenName, string directory)
signal wallpaperListChanged(string screenName, int count)
function getWallpapersList(name) { return lists[name] || []; }
function getWallpaper(name) { return selected[name] || ""; }
function changeWallpaper(path, name) {
  changes = changes.concat([{path: path, screen: name === undefined ? "ALL" : name}]);
  if (name !== undefined) { selected[name] = path; wallpaperChanged(name, path); }
}
function refreshWallpapersList() { wallpaperListChanged("DP-1", lists["DP-1"].length); }
""".replace("@FILES@", str(files))
            ),
            "WallhavenService": singleton("""property var searches: []
property var downloads: []
property bool fetching: false
property bool initialSearchScheduled: false
property string categories
property string purity
property string sorting
property string order
property string minResolution
property string resolutions
property int currentPage: 1
property int lastPage: 3
signal searchCompleted(var results, var meta)
signal searchFailed(string error)
function search(query, page) { searches = searches.concat([{query: query, page: page}]); initialSearchScheduled = false; }
function getThumbnailUrl(wallpaper, size) { return ""; }
function downloadWallpaper(wallpaper, callback) { downloads = downloads.concat([wallpaper.id]); callback(true, wallpaper.local); }
function previousPage() { currentPage--; }
function nextPage() { currentPage++; }
"""),
            "PanelService": singleton(
                """property var routes: []
property QtObject settingsPanel: QtObject {
  property int requestedTab: -1
  property int opens: 0
  function open() { opens++; }
}
function getPanel(name, screen) {
  routes = routes.concat([{name: name, screen: screen.name}]);
  return settingsPanel;
}"""
            ),
        },
    )
    write_module(
        directory,
        "qs.Widgets",
        {
            "NText": "import QtQuick\nText { property real pointSize: 12; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize; text: icon }",
            "NIconButton": "import QtQuick\nItem { property string icon; property string tooltipText; property real baseSize; signal clicked; implicitWidth: 32; implicitHeight: 32 }",
            "NTextInput": "import QtQuick.Controls\nTextField { property alias inputItem: input; id: input }",
            "NComboBox": "import QtQuick\nItem { property var model; property string currentKey; signal selected(string key); implicitWidth: 100; implicitHeight: 30 }",
            "NToggle": "import QtQuick\nItem { property string label; property string description; property bool checked; signal toggled(bool checked); implicitHeight: 30 }",
            "NTabBar": "import QtQuick\nRow { property int currentIndex }",
            "NDivider": "import QtQuick\nItem { implicitHeight: 1 }",
            "NBusyIndicator": "import QtQuick\nItem { property real size; property color color }",
            "NImageCached": "import QtQuick\nItem { property string imagePath; property string cacheFolder }",
            "NTabButton": "import QtQuick\nItem { property string text; property int tabIndex; property bool checked; implicitWidth: 100; implicitHeight: 30; signal clicked; onClicked: parent.currentIndex = tabIndex }",
        },
    )
    write_module(directory, "qs.Modules.Panels.Wallpaper", {"WallpaperPanel": source})
    module = directory / "qs/Modules/Panels/Wallpaper"
    (module / "WallhavenSettingsPopup.qml").write_text(
        "import QtQuick\nItem { property var screen; function showAt(anchor) {} }"
    )
    helpers = directory / "qs/Helpers"
    helpers.mkdir()
    shutil.copyfile(ROOT / "Helpers/FuzzySort.js", helpers / "FuzzySort.js")
    (directory / "tst_wallpaper.qml").write_text(
        (ROOT / "Tests/Qml/WallpaperPanelWarningsHarness.qml").read_text()
    )


def runtime(directory, mutation=False):
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
    settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
    settings.parent.mkdir(mode=0o700, parents=True)
    original = b'{"fixture": "wallpaper-panel-only"}\n'
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        path.touch(mode=0o600)
        path.write_bytes(original)
        assert path.read_bytes() == original, "fixture bytes differ"
        assert path.stat().st_mode & 0o777 == 0o600, "fixture mode differs"
    try:
        stage_runtime(directory)
        if mutation:
            source = directory / "qs" / TARGET
            source.write_text(
                source.read_text().replace(
                    "panelScreen: root.screen", "panelScreen: Quickshell.screens[0]"
                )
            )
        result = subprocess.run(
            sandbox_command(
                directory,
                [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    str(directory / "tst_wallpaper.qml"),
                    "-import",
                    str(directory),
                ],
            ),
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"Offscreen panel exit {result.returncode}"
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
        assert not (directory / "absent-wallpapers").exists()
        print("WALLPAPER_PANEL_RUNTIME_PASS")
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"
        assert settings.stat().st_mode & 0o777 == 0o600, "fixture settings mode changed"
        assert backup.stat().st_mode & 0o777 == 0o600, "fixture backup mode changed"


def isolation_helper():
    spec = importlib.util.spec_from_file_location(
        "wallpaper_tab_isolation", ROOT / "Tests/wallpaper-tab-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sandbox_command(directory, argv):
    return isolation_helper().sandbox_command(directory, argv)


def isolation(directory):
    result = subprocess.run(
        sandbox_command(
            directory,
            [
                "/usr/bin/python3",
                "-c",
                "import pathlib, socket\n"
                "for p in ('/home/osso/.config', '/syncthing', '/run/user'):\n"
                " assert not pathlib.Path(p).exists(), p\n"
                " print('MASK_ABSENT', p)\n"
                "s = socket.socket(); s.settimeout(1)\n"
                "try: s.connect(('1.1.1.1', 443))\n"
                "except OSError: print('NETWORK_DENIED')\n"
                "else: raise AssertionError('network accessible')\n"
                "finally: s.close()\n",
            ],
        ),
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=15,
    )
    print(result.stdout + result.stderr, end="")
    assert result.returncode == 0
    assert "NETWORK_DENIED" in result.stdout
    print("WALLPAPER_PANEL_ISOLATION_PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("lint", "runtime", "isolation"), required=True
    )
    parser.add_argument("--mutation", action="store_true")
    args = parser.parse_args()
    if args.mutation and args.mode != "runtime":
        parser.error("--mutation requires --mode runtime")
    with tempfile.TemporaryDirectory(prefix="noctalia-wallpaper-panel-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation_helper().install_audit(directory)
        if args.mode == "runtime":
            runtime(directory, args.mutation)
        else:
            {"lint": lint, "isolation": isolation}[args.mode](directory)
