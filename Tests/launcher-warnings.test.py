#!/usr/bin/env python3
"""Exact Launcher lint and private offscreen model/delegate behavior.

External plugins, image decode, panel surface and leaf controls are inert.
Launcher source, Qt model/delegate lifetime, bindings and keyboard routing are real.
No real settings are read, backed up, or written; host paths are not mounted.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/Panels/Launcher/Launcher.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_module(directory, name, sources):
    path = directory.joinpath(*name.split("."))
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for name, source in sources.items():
        (path / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml\n")
    (path / "qmldir").write_text(
        "module "
        + ".".join(path.relative_to(directory).parts)
        + "\n"
        + "".join(declarations)
    )


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def stage_runtime(directory, owner_shadow, mutation):
    source = (ROOT / TARGET).read_text()
    if mutation == "revision":
        source = re.sub(
            r"readonly property int _rev: ClipboardService.revision",
            "readonly property int _rev: 0",
            source,
        )
    if mutation == "selection":
        source = source.replace(
            "selectedIndex = 0;\n  }\n\n  onSearchTextChanged",
            "selectedIndex = 1;\n  }\n\n  onSearchTextChanged",
        )
    write_module(
        directory,
        "qs.Modules.Panels.Launcher",
        {
            "Launcher": source,
            "ClipboardPreview": "import QtQuick\nItem { property var currentItem }",
        },
    )
    fuzzysort = directory / "qs/Helpers/FuzzySort.js"
    fuzzysort.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "Helpers/FuzzySort.js", fuzzysort)
    write_module(directory, "Quickshell", {"Unused": "import QtQuick\nItem {}"})
    write_module(
        directory, "Quickshell.Widgets", {"IconImage": "import QtQuick\nImage {}"}
    )
    shadow = (
        "property int currentIndex: 97; property int nextIndex: 98; property var availableCategories: ['wrong']; property string prefix: 'wrong'"
        if owner_shadow
        else ""
    )
    write_module(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  property real preferredWidth; property real preferredHeight
  property real preferredWidthRatio; property real preferredHeightRatio
  property bool panelAnchorHorizontalCenter; property bool panelAnchorVerticalCenter
  property bool panelAnchorLeft; property bool panelAnchorRight
  property bool panelAnchorBottom; property bool panelAnchorTop
  property Item panelContent
  signal opened(); signal closed()
  width: 526; height: 600
  onPanelContentChanged: { panelContent.parent = this; panelContent.anchors.fill = this; }
  function close() {}
"""
            + shadow
            + "\n}"
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["appLauncher"].update(
        viewMode="list", enableClipboardHistory=True, enableClipPreview=False
    )
    # Generate only literal style/color constants referenced by this target.
    styles = set(re.findall(r"Style\.([A-Za-z0-9_]+)", source))
    colors = set(re.findall(r"NColor\.([A-Za-z0-9_]+)", source))
    style_values = {"uiScaleRatio": 1, "baseWidgetSize": 32, "animationFast": 0}
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(
                    f"property real {name}: {style_values.get(name, 8)}"
                    for name in sorted(styles)
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "{"transparent" if name == "transparent" else "#404040"}"'
                    for name in sorted(colors)
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Logger": singleton("function d(...args) {}"),
            "ThemeIcons": singleton(
                'function iconFromName(name, alternate) { return ""; }'
            ),
        },
    )
    write_module(
        directory,
        "qs.Services.Keyboard",
        {
            "ClipboardService": singleton("""
property int revision: 0
property var items: []
property var cache: ({})
function getImageData(id) { return cache[id]; }
function decodeToDataUrl(id, mime, callback) {}
function publish(id, value) { cache[id] = value; revision++; }
""")
        },
    )
    plugin = """import QtQuick
Item {
  property var launcher
  property string name: "Applications"
  property bool handleSearch: false
  property bool isBrowsingMode: true
  property var categories: ["recent", "faces", "nature"]
  property var availableCategories: ["all", "tools", "games"]
  property string selectedCategory: "all"
  property var categoryIcons: ({})
  function selectCategory(category) { selectedCategory = category; }
  function getCategoryName(category) { return category; }
  function getResults(text) { return []; }
}
"""
    write_module(
        directory,
        "qs.Modules.Panels.Launcher.Plugins",
        {
            name: plugin.replace("Item {", f'Item {{ objectName: "{name}";', 1)
            for name in (
                "ApplicationsPlugin",
                "CalculatorPlugin",
                "ClipboardPlugin",
                "EmojiPlugin",
            )
        },
    )
    widgets = {
        "NBox": "import QtQuick\nRectangle {}",
        "NText": "import QtQuick\nText { property alias pointSize: self.font.pointSize; id: self }",
        "NDivider": "import QtQuick\nItem { implicitHeight: 1 }",
        "NTabBar": "import QtQuick\nItem { property int currentIndex }",
        "NIconTabButton": "import QtQuick\nItem { property string icon; property int tabIndex; property string tooltipText; property bool checked; signal clicked() }",
        "NIconButton": "import QtQuick\nItem { property string icon; property string tooltipText; signal clicked() }",
        "NTextInput": """import QtQuick
import QtQuick.Controls
TextField {
  id: input
  property alias fontSize: input.font.pointSize
  property alias fontWeight: input.font.weight
  readonly property Item inputItem: input
  objectName: "searchInput"
}""",
        "NImageRounded": """import QtQuick
Item {
  property string imagePath
  property real radius
  property int status: Image.Ready
  objectName: "imagePreview"
}""",
        "NListView": "import QtQuick\nListView { property int horizontalPolicy; property int verticalPolicy; objectName: 'resultsList' }",
        "NGridView": "import QtQuick\nGridView { property int horizontalPolicy; property int verticalPolicy; objectName: 'resultsGrid' }",
    }
    write_module(directory, "qs.Widgets", widgets)
    shutil.copyfile(
        ROOT / "Tests/Qml/LauncherWarningsHarness.qml", directory / "tst_launcher.qml"
    )


def run_isolated(directory, command, label):
    environment = {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "QML_DISABLE_DISK_CACHE": "1",
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700, exist_ok=True)
        environment[key] = str(path)
    sandbox = [
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
        *command,
    ]
    trace = directory / f"{label}.trace"
    result = subprocess.run(
        [
            "strace",
            "-f",
            "-qq",
            "-e",
            "trace=%file,%network",
            "-o",
            str(trace),
            *sandbox,
        ],
        cwd=directory,
        env=environment,
        timeout=60,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    accesses = trace.read_text()
    assert "settings.json" not in accesses, "settings access attempted"
    assert not re.search(r"connect\(.*sa_family=AF_INET6?[,}]", accesses), (
        "network connection attempted"
    )
    print(
        "ISOLATION: zero settings/network attempts; host home, config and desktop not mounted"
    )
    return result.returncode, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--owner-shadow", action="store_true")
    parser.add_argument("--mutation", choices=("revision", "selection"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-launcher-proof-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if args.mode == "lint":
            helper("media-mini-warnings.test.py").stage_modules(directory)
            code, output = run_isolated(
                directory,
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "-I",
                    str(directory),
                    "--max-warnings",
                    "0",
                    str(directory / "qs" / TARGET),
                ],
                "lint",
            )
            warnings = re.findall(r"^Warning:.*$", output, re.M)
            print("LAUNCHER_WARNINGS", len(warnings), "EXIT", code)
            assert not warnings and code == 0, "strict Launcher diagnostics failed"
        else:
            stage_runtime(directory, args.owner_shadow, args.mutation)
            code, output = run_isolated(
                directory,
                [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    str(directory / "tst_launcher.qml"),
                    "-import",
                    str(directory),
                ],
                "runtime",
            )
            assert code == 0 and "0 failed" in output, "launcher runtime failed"
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
                output,
            ), "runtime diagnostics"


if __name__ == "__main__":
    main()
