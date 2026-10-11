#!/usr/bin/env python3
"""Production setup child geometry/content; isolated offscreen, never desktop/config IO."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "Tests/fixtures/setup-layout-geometry.json"
SETTINGS = Path("/home/osso/.config/noctalia/settings.json")
SETTINGS_ALIAS = """pragma Singleton
import QtQuick
QtObject {
  readonly property alias data: adapter
  property SettingsData adapter: SettingsData { id: adapter }
  readonly property string defaultWallpapersDirectory: ""
  readonly property string configDir: ""
  readonly property string cacheDir: ""
  readonly property bool isLoaded: true
  signal settingsSaved()
  property int saveRequests: 0
  function saveImmediate() { saveRequests++; }
}
"""
STUBS = {
    "Commons/Logger.qml": """function i(...args) {}
function d(...args) {}
property var warnings: []
function w(...args) { warnings.push(args.join(" ")); }
function e(...args) { console.error(...args); }
function callStack() { console.trace(); }""",
    "Services/Power/PowerProfileService.qml": "readonly property bool noctaliaPerformanceMode: false",
    "Services/System/ProgramCheckerService.qml": "readonly property bool matugenAvailable: true",
    "Services/Theming/AppThemeService.qml": "function generate() { throw new Error('Unexpected theme generation'); }",
    "Services/Theming/ColorSchemeService.qml": """readonly property var schemes: SCHEMES
function applyScheme(name) { throw new Error('Unexpected scheme application'); }""",
    "Services/UI/PanelService.qml": """function registerPanel(key, panel) {}
function unregisterPanel(key, panel) {}""",
    "Services/UI/BarService.qml": "readonly property var barWidgets: ({})",
    "Services/UI/ToastService.qml": "function showNotice(...args) { throw new Error('Unexpected toast'); }",
    "Services/UI/TooltipService.qml": """function show(...args) { throw new Error('Unexpected tooltip'); }
function hide() {}""",
    "Services/UI/WallpaperService.qml": """readonly property var wallpapers: []
signal wallpaperChanged()
signal wallpaperDirectoryChanged()
signal wallpaperListChanged()
property int refreshRequests: 0
property string appliedWallpaper: ""
function refreshWallpapersList() { refreshRequests++; }
function changeWallpaper(path, screen) { appliedWallpaper = path; }
function getWallpapersList(screen) { return []; }""",
    "Services/Compositor/CompositorService.qml": "function getDisplayScale(name) { return 1; }",
}
PALETTE = {
    "mPrimary": "#c7a1d8",
    "mOnPrimary": "#1a151f",
    "mSecondary": "#a984c4",
    "mTertiary": "#e0b7c9",
    "mError": "#e9899d",
    "mSurface": "#1a151f",
    "mSurfaceVariant": "#302835",
    "mOnSurface": "#f3edf7",
    "mOnSurfaceVariant": "#d1c7d6",
    "mOutline": "#807080",
    "mHover": "#403040",
    "mOnHover": "#f3edf7",
    "transparent": "transparent",
}


def write_singleton(root, relative, body):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n")


def prepare_sources(root):
    # Production components/widgets/layouts; only external service boundaries are inert.
    for relative in (
        "Commons",
        "Helpers",
        "Widgets",
        "Modules/Panels/SetupWizard",
        "Assets",
    ):
        shutil.copytree(ROOT / relative, root / relative)
    panel = root / "Modules/MainScreen/SmartPanel.qml"
    panel.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "Modules/MainScreen/SmartPanel.qml", panel)
    for relative, body in STUBS.items():
        if "SCHEMES" in body:
            schemes = []
            for name in ("Rose Pine", "Nord", "Catppuccin"):
                path = root / (name + ".json")
                path.write_text(json.dumps({"dark": PALETTE, "light": PALETTE}))
                schemes.append(str(path))
            body = body.replace("SCHEMES", json.dumps(schemes))
        write_singleton(root, relative, body)
    write_singleton(
        root,
        "Commons/NColor.qml",
        "\n".join(
            f'readonly property color {key}: "{value}"'
            for key, value in PALETTE.items()
        ),
    )
    (root / "Commons/Settings.qml").write_text(SETTINGS_ALIAS)
    osd = root / "Modules/OSD/OSD.qml"
    osd.parent.mkdir(parents=True)
    osd.write_text(
        "import QtQuick\nQtObject { enum Type { Volume, InputVolume, Brightness, LockKey } }\n"
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/SetupLayoutGeometryHarness.qml", root / "shell.qml"
    )


def isolated_environment(root):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for variable in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_CONFIG_DIRS",
        "XDG_DATA_DIRS",
    ):
        path = root / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/noctalia-geometry-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/noctalia-geometry-system",
    )
    return environment


def capture_geometry(directory, transitions=False):
    with tempfile.TemporaryDirectory(prefix="noctalia-setup-offscreen-") as temporary:
        root = Path(temporary)
        prepare_sources(root)
        environment = isolated_environment(root)
        environment["NOCTALIA_TEST_TRANSITIONS"] = "1" if transitions else "0"
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(root / "shell.qml")],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / "runtime.log").write_text(output)
        if result.returncode or re.search(r"\b(?:WARN|ERROR|FATAL)\b", output):
            raise AssertionError(
                f"Offscreen component load/runtime failed ({result.returncode}); see {directory / 'runtime.log'}"
            )
        match = re.search(r"SETUP_GEOMETRY (\[.*\])", output)
        if not match:
            raise AssertionError(
                f"Missing geometry result; see {directory / 'runtime.log'}"
            )
        snapshots = json.loads(match[1])
        (directory / "geometry.json").write_text(json.dumps(snapshots, indent=2) + "\n")
        return snapshots


def flatten(tree):
    yield tree
    for child in tree["children"]:
        yield from flatten(child)


def assert_content(snapshots):
    assert len(snapshots) == 20, f"Expected 20 cases, got {len(snapshots)}"
    expected_content = {
        "appearance": "Appearance",
        "customize": "Customize",
        "dock": "Dock",
        "wizard": "Welcome to Noctalia! ✨",
    }
    for snapshot in snapshots:
        scenario = snapshot["scenario"]
        nodes = list(flatten(snapshot["tree"]))
        texts = [node.get("text", "") for node in nodes]
        label = expected_content[scenario["component"]]
        assert any(label in text for text in texts), (scenario, label, texts)
        assert snapshot["tree"]["width"] == scenario["width"], scenario
        assert all(node["width"] >= 0 and node["height"] >= 0 for node in nodes), (
            scenario
        )


def assert_geometry(actual, expected, path="cases"):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        for key in expected:
            assert_geometry(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for index, value in enumerate(expected):
            assert_geometry(actual[index], value, f"{path}[{index}]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert abs(actual - expected) < 0.001, f"{path}: {actual} != {expected}"
    else:
        assert actual == expected, f"{path}: {actual!r} != {expected!r}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--capture-only",
        action="store_true",
        help="Capture pre-change geometry; do not update tracked expectations",
    )
    parser.add_argument("--wizard-transitions", action="store_true")
    parser.add_argument(
        "--expected",
        type=Path,
        help="Compare transition geometry with pre-change capture",
    )
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True, mode=0o700)
    before = SETTINGS.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(before)
    assert (
        hashlib.sha256(backup.read_bytes()).digest() == hashlib.sha256(before).digest()
    )
    try:
        snapshots = capture_geometry(args.artifacts, args.wizard_transitions)
        if args.wizard_transitions:
            assert len(snapshots) == 52, (
                f"Expected 52 transition cases, got {len(snapshots)}"
            )
            for snapshot in snapshots:
                assert snapshot["step"] in range(5)
                assert snapshot["tree"]["width"] == snapshot["scenario"]["width"]
                nodes = list(flatten(snapshot["tree"]))
                assert all(node["width"] >= 0 and node["height"] >= 0 for node in nodes)
            if args.expected:
                assert_geometry(snapshots, json.loads(args.expected.read_text()))
            print(
                "PASS wizard: 52 offscreen transition snapshots; value handoff/back/next/finish/skip/cancel"
            )
            return
        assert_content(snapshots)
        if not args.capture_only:
            assert_geometry(snapshots, json.loads(GOLDEN.read_text()))
            print(
                "PASS setup geometry: 20 offscreen cases, actual child geometry/content"
            )
    finally:
        assert SETTINGS.read_bytes() == before, (
            "Real settings changed during isolated test"
        )


if __name__ == "__main__":
    main()
