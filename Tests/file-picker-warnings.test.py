#!/usr/bin/env python3
"""Targeted lint and offscreen production picker; no desktop/settings bootstrap.

Only surrounding styled controls and Quickshell environment access are fixtures.
The Popup, FolderListModel, filtering, delegates and event handlers are production.
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

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "Widgets/NFilePicker.qml"


def write_module(directory, module, sources):
    path = directory / module.replace(".", "/")
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for name, source in sources.items():
        (path / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml\n")
    (path / "qmldir").write_text(f"module {module}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def lint(directory):
    # Reuse staging only: lint exactly one production file, never the full tree.
    spec = importlib.util.spec_from_file_location(
        "media_lint_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    staging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(staging)
    staging.stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs/Widgets/NFilePicker.qml"),
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
    print("FILE_PICKER_LINT_COUNTS", dict(counts))
    blocks = re.split(r"(?=Warning:)", output)[1:]
    actionable = [
        block
        for block in blocks
        if "[unqualified]" in block and "ComponentBehavior: Bound" not in block
    ]
    assert not actionable, "Known-owner unqualified accesses remain:\n" + "".join(
        actionable
    )
    assert counts.keys() <= {"unqualified", "missing-property", "incompatible-type"}
    assert result.returncode in (0, 255)
    print("FILE_PICKER_LINT_PASS (unbound outer IDs retained)")


def runtime(directory):
    files = directory / "files"
    files.mkdir()
    (files / "child").mkdir()
    (files / "alpha.txt").write_text("alpha")
    (files / "beta.log").write_text("beta")
    (files / ".hidden.txt").write_text("hidden")
    write_module(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton(
                f"function env(key) {{ return {json.dumps(str(files))}; }}"
            )
        },
    )
    write_module(
        directory, "Quickshell.Io", {"IoFixture": "import QtQuick\nQtObject {}"}
    )
    style_names = set(re.findall(r"Style\.(\w+)", TARGET.read_text()))
    colors = set(re.findall(r"NColor\.(\w+)", TARGET.read_text()))
    write_module(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "\n".join(
                    f"property real {name}: {0 if name.startswith('animation') else 12}"
                    for name in sorted(style_names)
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "{"transparent" if name == "transparent" else "#808080"}"'
                    for name in sorted(colors)
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
        },
    )
    write_module(
        directory,
        "qs.Widgets",
        {
            "NFilePicker": TARGET.read_text(),
            "NText": "import QtQuick\nText { property real pointSize; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize; text: icon }",
            "NButton": "import QtQuick\nRectangle { property string text; property string icon; property bool outlined; signal clicked; implicitWidth: 160; implicitHeight: 32; MouseArea { anchors.fill: parent; onClicked: parent.clicked() } }",
            "NIconButton": "import QtQuick\nRectangle { property string icon; property string tooltipText; property real baseSize; property string text: icon; signal clicked; implicitWidth: 32; implicitHeight: 32; MouseArea { anchors.fill: parent; onClicked: parent.clicked() } }",
            "NTextInput": "import QtQuick.Controls\nTextField { property string inputIconName }",
            "NDivider": "import QtQuick\nRectangle { implicitHeight: 1 }",
            "NListView": "import QtQuick\nListView {}",
        },
    )
    helpers = directory / "qs/Helpers"
    helpers.mkdir()
    shutil.copyfile(ROOT / "Helpers/FuzzySort.js", helpers / "FuzzySort.js")
    source = (ROOT / "Tests/Qml/FilePickerWarningsHarness.qml").read_text()
    (directory / "tst_picker.qml").write_text(source.replace("@FILES@", str(files)))
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "WAYLAND_DISPLAY",
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "QML_IMPORT_PATH",
            "QML2_IMPORT_PATH",
        }
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_picker.qml"),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
    )
    print(result.stdout + result.stderr, end="")
    assert result.returncode == 0, "Offscreen production picker failed"
    print("FILE_PICKER_RUNTIME_PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("lint", "runtime"), required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-picker-") as temporary:
        {"lint": lint, "runtime": runtime}[args.mode](Path(temporary))
