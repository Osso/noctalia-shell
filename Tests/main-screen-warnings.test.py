#!/usr/bin/env python3
"""Bounded MainScreen lint and nonvisible production PanelWindow lifecycle.

Panels/background rendering and services are inert fixtures. MainScreen, Loaders,
window color, Region geometry and layer-shell properties remain unchanged. The
mask assertions cover empty input-region construction, not compositor delivery.
Private headless Cage never connects to the active display; animations are disabled.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/MainScreen/MainScreen.qml")


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
    # Installed screen metadata (5) and optional SmartPanel key handlers (6).
    assert counts == {"missing-property": 11}, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    write = helper().write_singleton
    target = directory / TARGET
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / TARGET, target)
    backgrounds = target.parent / "Backgrounds"
    backgrounds.mkdir()
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
    write(directory / "Commons", "Logger", "function d(...args) {}")
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
Item {
  property ShellScreen screen
  property bool exclusiveKeyboard: false
  property bool isClosing: false
  property Item panelRegion: Item { width: 200; height: 100 }
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
        (path / f"{name}.qml").write_text(panel_source)
    shutil.copyfile(
        ROOT / "Tests/Qml/MainScreenWarningsHarness.qml", directory / "shell.qml"
    )


def stop_process_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    stage_runtime(directory)
    environment = helper().isolate_environment(directory)
    environment.update(
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        QT_QPA_PLATFORM="wayland",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/main-screen-test",
    )
    process = subprocess.Popen(
        ["cage", "--", "quickshell", "--no-color", "-p", str(directory / "shell.qml")],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            stop_process_group(process)
            stdout, stderr = process.communicate(timeout=3)
            print(stdout + stderr, end="")
            raise
        output = stdout + stderr
        print(output, end="")
        assert process.returncode == 0, process.returncode
        assert "MAIN_SCREEN_RUNTIME_PASS" in output, output
        assert not re.search(
            r" WARN | ERROR | FATAL |ReferenceError|TypeError|Binding loop",
            output,
        ), output
    finally:
        stop_process_group(process)
        assert settings.read_bytes() == original, "real settings changed"
        print("MAIN_SCREEN_SETTINGS_SHA", digest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-main-screen-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
