#!/usr/bin/env python3
"""Bounded MainScreen lint and isolated offscreen UI/layout/routing proof.

Production MainScreen bindings, loaders and shortcuts run with synthetic screen,
PanelWindow and Region transport. No compositor delivery or real-screen proof.
Installed Quickshell metadata remains unchanged for production source lint.
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
TARGET = Path("Modules/MainScreen/MainScreen.qml")


def isolation_helper():
    spec = importlib.util.spec_from_file_location(
        "main_screen_isolation", ROOT / "Tests/grid-list-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def helper():
    spec = importlib.util.spec_from_file_location(
        "main_screen_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper().stage_modules(directory)
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
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("MAIN_SCREEN_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory, mutation):
    write = helper().write_singleton
    target = directory / TARGET
    target.parent.mkdir(parents=True)
    source = (ROOT / TARGET).read_text()
    # Replace attached layer-shell transport only; all binding expressions stay real.
    for name, kind in (
        ("layer", "int"),
        ("namespace", "string"),
        ("exclusionMode", "int"),
        ("keyboardFocus", "int"),
    ):
        source = source.replace(
            f"WlrLayershell.{name}:", f"property {kind} fixture{name.capitalize()}:"
        )
    if mutation == "geometry":
        source = source.replace(
            "readonly property real attachmentOverlap: 1",
            "readonly property real attachmentOverlap: 0",
        )
    elif mutation == "routing":
        source = source.replace("screen: root.screen", "screen: null")
    elif mutation == "selection":
        source = source.replace(
            "readonly property ShellScreen selectedScreen: root.screen",
            "property ShellScreen selectedScreen: root.screen",
        ).replace(
            "Component.onCompleted: {",
            "Component.onCompleted: {\n    selectedScreen = root.screen;",
            1,
        )
    target.write_text(source)
    backgrounds = target.parent / "Backgrounds"
    backgrounds.mkdir()
    shutil.copyfile(
        ROOT / "Modules/MainScreen/Backgrounds/BackgroundRegion.qml",
        backgrounds / "BackgroundRegion.qml",
    )
    (backgrounds / "AllBackgrounds.qml").write_text(
        "import QtQuick\nItem { property var bar; property var windowRoot }\n"
    )
    (target.parent / "ScreenCorners.qml").write_text("import QtQuick\nItem {}\n")
    for module in ("Modules/Bar", "Modules/Bar/Extras", "Services/Compositor"):
        path = directory / module
        path.mkdir(parents=True, exist_ok=True)
        (path / "Fixture.qml").write_text("import QtQuick\nQtObject {}\n")
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["general"]["dimmerOpacity"] = 0.6
    write(
        directory / "Commons", "Settings", "property var data: " + json.dumps(defaults)
    )
    write(
        directory / "Commons",
        "NColor",
        'property color transparent: "transparent"\nproperty color mShadow: "#000000"',
    )
    write(
        directory / "Commons",
        "Style",
        "property int animationNormal: 0\nproperty int animationFaster: 0\nproperty int barHeight: 32\nproperty int marginXL: 16",
    )
    write(
        directory / "Commons",
        "Logger",
        "property var entries: []\nfunction d(...args) { entries.push(args); }",
    )
    write(directory / "Services/UI", "BarService", "property bool isVisible: false")
    write(
        directory / "Services/UI",
        "PanelService",
        """property var loaders: ({})
property var openedPanel: null
property int removed: 0
function registerPanelLoader(key, loader) {
  if (loaders[key]) throw new Error("duplicate loader " + key);
  loaders[key] = loader;
}
function unregisterPanelLoader(key, loader) {
  if (loaders[key] !== loader) throw new Error("wrong loader " + key);
  delete loaders[key];
  removed++;
}
function open(key) {
  const loader = loaders[key];
  loader.active = true;
  if (!loader.item) throw new Error("panel load failed " + key);
  openedPanel = loader.item;
  openedPanel.isClosing = false;
}
function finishClose() { openedPanel = null; }""",
    )
    panel_source = """import QtQuick
import Quickshell
import qs.Services.UI
import qs.Modules.MainScreen.Backgrounds
Item {
  property ShellScreen screen
  property bool exclusiveKeyboard: false
  property bool isClosing: false
  property BackgroundRegion panelRegion: BackgroundRegion { width: 200; height: 100 }
  function close() { isClosing = true; }
}
"""
    panels = {
        "Audio": "AudioPanel",
        "Battery": "BatteryPanel",
        "Bluetooth": "BluetoothPanel",
        "Brightness": "BrightnessPanel",
        "Changelog": "ChangelogPanel",
        "Clock": "ClockPanel",
        "ControlCenter": "ControlCenterPanel",
        "Launcher": "Launcher",
        "NotificationHistory": "NotificationHistoryPanel",
        "SessionMenu": "SessionMenu",
        "Settings": "SettingsPanel",
        "SetupWizard": "SetupWizard",
        "Process": "ProcessPanel",
        "Tray": "TrayDrawerPanel",
        "Wallpaper": "WallpaperPanel",
        "WiFi": "WiFiPanel",
        "VPN": "VPNPanel",
    }
    for module, name in panels.items():
        path = directory / "Modules/Panels" / module
        path.mkdir(parents=True)
        navigation = "\nproperty int selectedIndex: 2\n"
        if name in ("Launcher", "SessionMenu", "SettingsPanel"):
            navigation += "function onBackTabPressed() { selectedIndex--; }\n"
        if name == "Launcher":
            navigation += "function onCtrlNPressed() { selectedIndex++; }\n"
            navigation += "function onCtrlPPressed() { selectedIndex--; }\n"
        (path / f"{name}.qml").write_text(
            panel_source.rsplit("}", 1)[0] + navigation + "}\n"
        )
    stage_transport(directory)
    modules = {}
    for path in directory.rglob("*.qml"):
        if path.parts[-1] == "tst_main_screen.qml":
            continue
        relative = path.relative_to(directory)
        singleton = path.read_text().startswith("pragma Singleton")
        prefix = "singleton " if singleton else ""
        modules.setdefault(relative.parent, []).append(
            f"{prefix}{path.stem} 1.0 {path.name}\n"
        )
    for relative, declarations in modules.items():
        name = ".".join(("qs", *relative.parts))
        (directory / relative / "qmldir").write_text(
            f"module {name}\n" + "".join(declarations)
        )
    shutil.copyfile(
        ROOT / "Tests/Qml/MainScreenWarningsHarness.qml",
        directory.parent / "tst_main_screen.qml",
    )


def stage_transport(directory):
    core = directory.parent / "Quickshell"
    core.mkdir()
    sources = {
        "ShellScreen": """import QtQuick
QtObject {
  property string name
  property int width
  property int height
  property int x
  property int y
}
""",
        "WindowAnchors": """import QtQuick
QtObject {
  property bool top
  property bool bottom
  property bool left
  property bool right
}
""",
        "PanelWindow": """import QtQuick
import Quickshell
QtObject {
  id: window
  default property alias data: content.data
  property ShellScreen screen
  property bool visible: false
  property color color
  property Region mask
  property WindowAnchors anchors: WindowAnchors {}
  readonly property real width: screen ? screen.width : 0
  readonly property real height: screen ? screen.height : 0
  property Item contentItem: Item {
    id: content
    width: window.width
    height: window.height
  }
}
""",
        "Region": """import QtQuick
QtObject {
  default property list<QtObject> children
  property list<QtObject> regions
  property real x
  property real y
  property real width
  property real height
  property int intersection
}
""",
        "Intersection": "import QtQuick\nQtObject { enum Mode { Xor, Subtract } }\n",
    }
    for name, source in sources.items():
        (core / f"{name}.qml").write_text(source)
    (core / "qmldir").write_text(
        "module Quickshell\n" + "".join(f"{name} 1.0 {name}.qml\n" for name in sources)
    )
    wayland = core / "Wayland"
    wayland.mkdir()
    sources = {
        "WlrLayer": "enum Layer { Top }",
        "ExclusionMode": "enum Mode { Ignore }",
        "WlrKeyboardFocus": "enum Focus { None, Exclusive, OnDemand }",
    }
    for name, body in sources.items():
        (wayland / f"{name}.qml").write_text(
            "import QtQuick\nQtObject { " + body + " }\n"
        )
    (wayland / "qmldir").write_text(
        "module Quickshell.Wayland\n"
        + "".join(f"{name} 1.0 {name}.qml\n" for name in sources)
    )


def lint_harness(directory, environment, inject_warning=False):
    modules = directory / "qs"
    modules.mkdir()
    stage_runtime(modules, "none")
    harness = directory / "tst_main_screen.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                'name: "MainScreenWarnings"',
                'name: "MainScreenWarnings"\n  property int injectedDiagnostic: missingFixtureValue',
                1,
            )
        )
    code, output = isolation_helper().run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            str(directory),
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            "0",
            "--json",
            "-",
            str(harness),
        ],
        "main-screen-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("MAIN_SCREEN_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert code != 0, "injected warning accepted"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        environment = isolation_helper().isolated_environment(staged)
        code = lint_harness(staged, environment, injected)
        assert (code != 0) if injected else (code == 0), code
    print("MAIN_SCREEN_HARNESS_WARNING_REJECTED")


def runtime(directory, mutation="none"):
    environment = isolation_helper().isolated_environment(directory)
    environment.update(
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/main-screen-test",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/main-screen-test",
    )
    settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
    settings.parent.mkdir(mode=0o700, parents=True)
    original = (ROOT / "Assets/settings-default.json").read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        path.touch(mode=0o600)
        path.write_bytes(original)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    modules = directory / "qs"
    modules.mkdir()
    stage_runtime(modules, mutation)
    try:
        code, output = isolation_helper().run_audited(
            directory,
            environment,
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_main_screen.qml"),
                "-import",
                str(directory),
            ],
            "main-screen-runtime",
        )
        assert code == 0, code
        assert "MAIN_SCREEN_RUNTIME_PASS" in output, output
        assert not re.search(
            r"QWARN| WARN | ERROR | FATAL |ReferenceError|TypeError|Binding loop",
            output,
        ), output
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"
        print("MAIN_SCREEN_FIXTURE_SETTINGS_SHA", digest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "runtime", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument(
        "--mutation",
        choices=("none", "geometry", "routing", "selection"),
        default="none",
    )
    args = parser.parse_args()
    if args.mode != "runtime" and args.mutation != "none":
        parser.error("mutations apply only to staged runtime fixtures")
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-main-screen-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation = isolation_helper()
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode == "lint":
            lint(directory)
        elif args.mode == "lint-harness":
            raise SystemExit(
                lint_harness(
                    directory,
                    isolation.isolated_environment(directory),
                    args.inject_warning,
                )
            )
        elif args.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        else:
            runtime(directory, args.mutation)
