#!/usr/bin/env python3
"""Setup wallpaper-only lint and sandboxed UI, never host config or images."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/SetupWizard/SetupWallpaperStep.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory):
    writer = helper("wallpaper-panel-warnings.test.py")
    write = writer.write_module
    singleton = writer.singleton
    source = (ROOT / TARGET).read_text()
    wizard = (ROOT / "Modules/Panels/SetupWizard/SetupWizard.qml").read_text()
    style = set(re.findall(r"Style\.(\w+)", source + wizard))
    colors = set(re.findall(r"NColor\.(\w+)", source + wizard))
    write(
        directory,
        "qs.Commons",
        {
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
            "I18n": singleton("function tr(key, values) { return key; }"),
            "Logger": singleton(
                "function i(...args) {}\nfunction w(...args) { console.warn(...args); }\nfunction e(...args) { console.error(...args); }"
            ),
            "Settings": singleton("""property var data: ({wallpaper: {directory: '/fixture/gallery'}, general: {scaleRatio: 1}, bar: {position: 'top'}})
property string defaultWallpapersDirectory: '/fixture/gallery'
signal settingsSaved()
property int saves: 0
function saveImmediate() { saves++; }"""),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "WallpaperService": singleton("""property var files: ['/fixture/forest.png', '/fixture/desert.jpg', '/fixture/ocean.webp']
property string currentWallpaper: ''
property string appliedWallpaper: ''
property int refreshes: 0
signal wallpaperListChanged(string screenName, int count)
function getWallpapersList(screenName) { return files; }
function refreshWallpapersList() { refreshes++; }
function changeWallpaper(path, screenName) { appliedWallpaper = path; }""")
        },
    )
    write(directory, "qs.Services.System", {"Fixture": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
property Component panelContent
property real preferredWidth
property real preferredHeight
property real preferredWidthRatio
property real preferredHeightRatio
property bool panelAnchorHorizontalCenter
property bool panelAnchorVerticalCenter
property bool closeWithEscape
signal opened()
function close() {}
}"""
        },
    )
    # No Image, filesystem picker or Process executes at the external boundaries.
    write(
        directory,
        "qs.Widgets",
        {
            "NText": "import QtQuick\nText { property alias pointSize: text.font.pointSize; id: text }",
            "NIcon": "import QtQuick\nText { property string icon; property alias pointSize: text.font.pointSize; id: text }",
            "NButton": "import QtQuick.Controls\nButton { property bool outlined }",
            "NBusyIndicator": "import QtQuick\nItem { property bool running; property real size }",
            "NImageRounded": """import QtQuick
Item { property string imagePath; property real radius; property color borderColor; property real borderWidth }""",
            "NImageCached": "import QtQuick\nItem { property url source; property int status: Image.Ready }",
            "NTextInputButton": """import QtQuick
Item {
property string label
property string description
property string text
property string buttonIcon
property string buttonTooltip
signal inputEditingFinished()
signal buttonClicked()
}""",
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
    write(
        directory,
        "qs.Modules.Panels.SetupWizard",
        {
            "SetupWallpaperStep": source,
            "SetupWizard": wizard,
            "SetupAppearanceStep": "import QtQuick\nItem {}",
            "SetupCustomizeStep": """import QtQuick
Item {
property real selectedScaleRatio
property string selectedBarPosition
signal scaleRatioChanged(real ratio)
signal barPositionChanged(string position)
}""",
            "SetupDockStep": "import QtQuick\nItem {}",
        },
    )
    # Private synthetic logo only; wallpaper leaf fixtures never decode resources.
    assets = directory / "qs/Assets"
    assets.mkdir()
    (assets / "noctalia.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    )
    helpers = directory / "qs/Helpers"
    helpers.mkdir(parents=True)
    (helpers / "FuzzySort.js").write_text((ROOT / "Helpers/FuzzySort.js").read_text())
    (directory / "qs/shell.qml").write_text(
        (ROOT / "Tests/Qml/SetupWallpaperWarningsHarness.qml").read_text()
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("lint", "lint-harness", "runtime", "isolation")
    )
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="sw-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        boundary = helper("wallpaper-tab-warnings.test.py")
        boundary.install_audit(directory)
        environment = boundary.isolated_environment(directory)
        if args.mode == "lint":
            helper("media-mini-warnings.test.py").stage_modules(directory)
            argv = [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                temporary,
                str(directory / "qs" / TARGET),
            ]
        elif args.mode == "lint-harness":
            stage_runtime(directory)
            harness = directory / "qs/shell.qml"
            if args.inject_warning:
                source = harness.read_text()
                harness.write_text(
                    source.replace(
                        "id: test",
                        "id: test\n    property int injectedWarning: test.missingLintProbe",
                        1,
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
            stage_runtime(directory)
            argv = [
                "/usr/bin/quickshell",
                "--no-color",
                "-p",
                str(directory / "qs/shell.qml"),
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
except OSError:
    print('SANDBOX_NETWORK_DENIED')
else:
    raise AssertionError('network accessible')
finally:
    s.close()
""",
            ]
        result = subprocess.run(
            boundary.sandbox_command(directory, argv),
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if args.mode == "lint":
            warnings = re.findall(r"^Warning:.*$", output, re.M)
            print("SETUP_WALLPAPER_WARNINGS", len(warnings))
            assert not warnings, warnings
        elif args.mode == "lint-harness":
            diagnostics = json.loads(result.stdout)
            warnings = [
                warning
                for diagnostic in diagnostics["files"]
                for warning in diagnostic["warnings"]
                if warning["type"] == "warning"
            ]
            print(
                "SETUP_WALLPAPER_HARNESS_LINT_WARNINGS",
                len(warnings),
                "EXIT",
                result.returncode,
            )
            assert not warnings, "SetupWallpaper harness warnings remain"
        elif args.mode == "runtime":
            assert "PASS setup wallpaper: 7 cases" in output, output
            assert not re.search(
                r"\b(?:WARN|ERROR|FATAL)\b|ReferenceError|TypeError|Binding loop|Warning:",
                output,
            ), output
        assert result.returncode == 0, result.returncode


if __name__ == "__main__":
    main()
