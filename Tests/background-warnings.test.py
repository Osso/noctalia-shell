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
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode
    print("BACKGROUND_LINT_PASS (zero warnings)")


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
    source = source.replace(
        "id: shaderLoader",
        """id: shaderLoader
        property var root: ({transitionProgress: -9, fillMode: -9})
        property var currentWallpaper: null
        property var nextWallpaper: null""",
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
    harness = (ROOT / "Tests/Qml/BackgroundWarningsHarness.qml").read_text()
    (directory / "tst_background.qml").write_text(
        harness.rstrip()[:-1] + SHADER_LIFECYCLE_TEST + "}\n"
    )


SHADER_LIFECYCLE_TEST = """
    function test_owner_shadow_reactivity_and_recreation_data() {
        return test_synthetic_transition_data();
    }

    function assert_shader_bindings(shader, type) {
        compare(shader.source1, currentImage);
        compare(shader.source2, nextImage);
        compare(shader.progress, window.transitionProgress);
        compare(shader.fillMode, window.fillMode);
        compare(shader.fillColor, window.fillColor);
        compare(shader.imageWidth1, currentImage.sourceSize.width);
        compare(shader.imageHeight1, currentImage.sourceSize.height);
        compare(shader.imageWidth2, nextImage.sourceSize.width);
        compare(shader.imageHeight2, nextImage.sourceSize.height);
        compare(shader.screenWidth, window.contentItem.width);
        compare(shader.screenHeight, window.contentItem.height);
        if (type !== "fade")
            compare(shader.smoothness, window.edgeSmoothness);

        if (type === "wipe")
            compare(shader.direction, window.wipeDirection);

        if (type === "disc" || type === "stripes")
            compare(shader.aspectRatio, window.width / window.height);

        if (type === "disc") {
            compare(shader.centerX, window.discCenterX);
            compare(shader.centerY, window.discCenterY);
        }
        if (type === "stripes") {
            compare(shader.stripeCount, window.stripesCount);
            compare(shader.angle, window.stripesAngle);
        }
    }

    function test_owner_shadow_reactivity_and_recreation(row) {
        window.setWallpaperImmediate(Qt.resolvedUrl("red.svg"));
        tryCompare(currentImage, "status", Image.Ready);
        nextImage.source = Qt.resolvedUrl("blue.svg");
        tryCompare(nextImage, "status", Image.Ready);
        window.transitionType = row.type;
        tryVerify(() => {
            return shaderLoader.item !== null;
        });
        assert_shader_bindings(shaderLoader.item, row.type);
        window.transitionProgress = 0.37;
        window.fillMode = 2;
        Settings.data.wallpaper.fillColor = "#993366";
        Settings.data.wallpaper.transitionEdgeSmoothness = 0.17;
        window.wipeDirection = 2;
        window.discCenterX = 0.23;
        window.discCenterY = 0.71;
        window.stripesCount = 11;
        window.stripesAngle = 0.4;
        window.width = 800;
        window.height = 500;
        currentImage.sourceSize = Qt.size(400, 200);
        nextImage.sourceSize = Qt.size(300, 100);
        assert_shader_bindings(shaderLoader.item, row.type);
        const oldShader = shaderLoader.item;
        shaderLoader.active = false;
        tryCompare(shaderLoader, "item", null);
        shaderLoader.active = true;
        tryVerify(() => {
            return shaderLoader.item !== null;
        });
        verify(shaderLoader.item !== oldShader);
        assert_shader_bindings(shaderLoader.item, row.type);
        window.transitionProgress = 0.64;
        assert_shader_bindings(shaderLoader.item, row.type);
        compare(window.monitorName, "fixture");
        const delegate = background.fixtureRepeater.itemAt(0);
        delegate.modelData.name = "changed-monitor";
        compare(window.monitorName, "changed-monitor");
        delegate.modelData.name = "fixture";
        Settings.data.wallpaper.fillColor = "#336699";
    }

"""


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
        command = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_background.qml"),
            "-import",
            str(directory),
        ]
        result = subprocess.run(
            load_helpers("wallpaper-panel-warnings.test.py").sandbox_command(
                directory, command
            ),
            cwd=directory,
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
