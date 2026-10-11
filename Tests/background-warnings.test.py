#!/usr/bin/env python3
"""Bounded lint and offscreen Background helpers/transition context.

Runtime retains production Loaders, shader Components, images and callbacks.
Only layer-shell screen/namespace declarations are removed; PanelWindow becomes
an invisible Qt Window with fixture anchors. No shader pixels/output routing,
wallpaper performance, real services or real settings persistence are tested.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Background/Background.qml")


def load_helpers(filename):
    spec = importlib.util.spec_from_file_location(
        "background_staging", ROOT / "Tests" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    load_helpers("media-mini-warnings.test.py").stage_modules(directory)
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
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1] if "[" in line else "block-var"
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("BACKGROUND_LINT_COUNTS", dict(counts))
    assert not counts, f"Background warnings remain: {dict(counts)}"
    assert result.returncode == 0, result.returncode
    print("BACKGROUND_LINT_PASS")


def stage_runtime(directory):
    helpers = load_helpers("wallpaper-panel-warnings.test.py")
    write_module, singleton = helpers.write_module, helpers.singleton
    write_module(
        directory,
        "Quickshell",
        {
            "ShellScreen": 'import QtQuick\nQtObject { property string name: "fixture"; property int width: 640; property int height: 360 }',
            "Quickshell": singleton(
                'property list<ShellScreen> screens: [ShellScreen {}]\nproperty string shellDir: "'
                + str(directory)
                + '"'
            ),
            "Variants": """import QtQuick
Item {
  property alias model: repeater.model
  property alias delegate: repeater.delegate
  property alias fixtureRepeater: repeater
  Repeater { id: repeater }
}""",
            "PanelWindow": """import QtQuick
Window {
  visible: false
  width: 640; height: 360
  property FixtureAnchors anchors: FixtureAnchors {}
}""",
            "FixtureAnchors": """import QtQuick
QtObject { property bool top; property bool bottom; property bool left; property bool right }""",
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())[
        "wallpaper"
    ]
    defaults.update(
        enabled=True,
        transitionType="none",
        transitionDuration=250,
        fillColor="#336699",
    )
    properties = "\n".join(
        f"property var {key}: {json.dumps(value)}" for key, value in defaults.items()
    )
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                "property QtObject data: QtObject { property QtObject wallpaper: QtObject {\n"
                + properties
                + "\n} }"
            ),
            "NColor": singleton('property color transparent: "transparent"'),
            "Logger": singleton(
                "function d(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
        },
    )
    write_module(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": singleton(
                "property real scale: 1\nsignal displayScalesChanged()\nfunction getDisplayScale(name) { return scale; }"
            ),
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "WallpaperService": singleton("""property bool isInitialized: true
property string initialPath: ""
property var allTransitions: ["fade", "wipe", "disc", "stripes"]
signal wallpaperChanged(string screenName, string path)
function getWallpaper(name) { return initialPath; }
function getFillModeUniform() { return 0; }"""),
        },
    )
    source = (ROOT / TARGET).read_text().replace("import Quickshell.Wayland\n", "")
    source = re.sub(
        r"^\s*(?:screen: [^\n]+|WlrLayershell\.[^\n]+)\n", "\n", source, flags=re.M
    )
    write_module(directory, "qs.Modules.Background", {"Background": source})
    shutil.copytree(ROOT / "Shaders/qsb", directory / "Shaders/qsb")
    # Synthetic images only; no real wallpaper or visible surface.
    (directory / "red.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="1280" height="720" fill="#ff0000"/></svg>'
    )
    (directory / "blue.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="1280" height="720" fill="#0000ff"/></svg>'
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/BackgroundWarningsHarness.qml",
        directory / "tst_background.qml",
    )


def runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    stage_runtime(directory)
    environment = load_helpers("media-mini-warnings.test.py").isolate_environment(
        directory
    )
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_background.qml"),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, result.returncode
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
        print("BACKGROUND_RUNTIME_PASS")
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        print("BACKGROUND_SETTINGS_SHA", digest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-background-warnings-"
    ) as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
