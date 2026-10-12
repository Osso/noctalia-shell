#!/usr/bin/env python3
"""Bounded AudioPanel lint and offscreen behavior; no host audio or settings writes."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = Path("Modules/Panels/Audio/AudioPanel.qml")


def card_fixture():
    spec = importlib.util.spec_from_file_location(
        "audio_card_fixture", ROOT / "Tests/audio-card-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lint(directory):
    card_fixture().fixture_helper().stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / PANEL),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("AUDIO_PANEL_WARNINGS", len(warnings))
    assert not warnings, warnings
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    fixture = card_fixture()
    fixture.stage_runtime(directory)
    (directory / "tst_audio_card.qml").unlink()
    fixture.write_module(
        directory,
        "qs.Modules.Panels.Audio",
        {
            "AudioPanel": (ROOT / PANEL).read_text(),
        },
    )
    # Only the desktop host is replaced: real panel content runs inside a Loader.
    fixture.write_module(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property bool isPanelOpen: true
  function close() { isPanelOpen = false; }
  Loader { anchors.fill: parent; active: parent.isPanelOpen; sourceComponent: parent.panelContent }
}
""",
        },
    )
    widgets = directory / "qs/Widgets"
    for name in ("NValueSlider", "NRadioButton", "NScrollView"):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
        with (widgets / "qmldir").open("a") as declarations:
            declarations.write(f"{name} 1.0 {name}.qml\n")
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "\n}",
            """
readonly property real marginL: 12
readonly property real marginS: 4
readonly property real fontSizeS: 10
readonly property real fontSizeXXL: 20
readonly property real fontWeightBold: 700
readonly property real borderM: 1
}
""",
        )
    )
    commons = directory / "qs/Commons"
    (commons / "I18n.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject { function tr(key) { return key; } }"
    )
    with (commons / "qmldir").open("a") as declarations:
        declarations.write("singleton I18n 1.0 I18n.qml\n")
    harness = directory / "tst_audio_panel.qml"
    shutil.copyfile(ROOT / "Tests/Qml/AudioPanelRegressionHarness.qml", harness)
    return harness


def main():
    card_fixture().run_main(
        stage_runtime, run_lint, "AUDIO_PANEL", 7, Path(__file__).absolute()
    )


if __name__ == "__main__":
    main()
