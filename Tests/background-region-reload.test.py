#!/usr/bin/env python3
"""Real MainScreen/SmartPanel/background types: private cold-start and hot reload.

Leaf panel content, settings, logging and registry services are fixture boundaries.
No wallpaper component, real config, network or physical display is available.
"""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PANELS = (
    "audioPanel",
    "batteryPanel",
    "bluetoothPanel",
    "brightnessPanel",
    "clockPanel",
    "controlCenterPanel",
    "changelogPanel",
    "launcherPanel",
    "notificationHistoryPanel",
    "sessionMenuPanel",
    "settingsPanel",
    "setupWizardPanel",
    "trayDrawerPanel",
    "wallpaperPanel",
    "wifiPanel",
    "vpnPanel",
    "processPanel",
)


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage(directory):
    main = helper("main-screen-warnings.test.py")
    main.stage_runtime(directory / "qs", None)
    shutil.rmtree(directory / "Quickshell")
    for path in (directory / "qs").iterdir():
        shutil.move(str(path), directory / path.name)
    (directory / "qs").rmdir()
    module = directory / "Modules/MainScreen"
    for name in ("MainScreen", "SmartPanel"):
        shutil.copyfile(ROOT / f"Modules/MainScreen/{name}.qml", module / f"{name}.qml")
    for path in (ROOT / "Modules/MainScreen/Backgrounds").glob("*.qml"):
        shutil.copyfile(path, module / "Backgrounds" / path.name)
    for path in (directory / "Modules/Panels").rglob("*.qml"):
        path.write_text("""import QtQuick
import qs.Modules.MainScreen
SmartPanel {
  preferredWidth: 200
  preferredHeight: 100
  panelAnchorTop: true
  panelAnchorHorizontalCenter: true
  panelContent: Item {}
}
""")
    write = main.helper().write_singleton
    write(
        directory / "Commons",
        "Style",
        """property int animationNormal: 20
property int animationFaster: 10
property int animationFast: 20
property int barHeight: 32
property int marginXL: 16
property int marginL: 12
property int marginM: 8
property int radiusL: 12""",
    )
    write(
        directory / "Commons",
        "NColor",
        """property color transparent: "transparent"
property color mShadow: "#000000"
property color mSurface: "#204060"
property color mOutline: "#808080"
""",
    )
    write(
        directory / "Commons",
        "Logger",
        "function d(...args) {}\nfunction w(...args) { console.warn(...args); }",
    )
    write(directory / "Services/UI", "BarService", "property bool isVisible: true")
    write(
        directory / "Services/UI",
        "PanelService",
        """property var loaders: ({})
property var openedPanel: null
function registerPanelLoader(key, loader) { loaders[key] = loader; }
function unregisterPanelLoader(key, loader) { delete loaders[key]; }
function registerPanel(key, panel) {}
function unregisterPanel(key, panel) {}
function willOpenPanel(panel) { openedPanel = panel; }
function closedPanel(panel) { openedPanel = null; }""",
    )
    widgets = directory / "Widgets"
    widgets.mkdir()
    (widgets / "NDropShadow.qml").write_text(
        "import QtQuick\nItem { property Item source }\n"
    )
    for path in directory.rglob("qmldir"):
        path.unlink()
    shutil.copyfile(
        ROOT / "Tests/Qml/BackgroundRegionReloadHarness.qml", directory / "shell.qml"
    )
    return module / "Backgrounds/BackgroundRegion.qml"


def wait_ready(process, selector, output):
    start = len(output)
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        for key, _ in selector.select(0.1):
            chunk = os.read(key.fileobj.fileno(), 65536).decode()
            output.append(chunk)
            print(chunk, end="", flush=True)
            text = "".join(output[start:])
            assert not re.search(
                r" WARN | ERROR | FATAL |ReferenceError|TypeError|REGION_ASSERT", text
            ), text
            if "REGION_RESOLUTION_READY" in text:
                for name in PANELS:
                    assert "REGION_CALLER_PASS " + name in text, name
                assert "REGION_BAR_STATES_PASS" in text
                return
        assert process.poll() is None, "".join(output)
    raise AssertionError("Region readiness timed out:\n" + "".join(output[start:]))


def run_reload(directory):
    source = stage(directory)
    environment = helper("media-mini-warnings.test.py").isolate_environment(directory)
    environment.update(
        QT_QPA_PLATFORM="wayland",
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        QS_NO_RELOAD_POPUP="1",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/region-system",
    )
    sandbox = helper("wallpaper-panel-warnings.test.py").sandbox_command
    isolation = subprocess.run(
        sandbox(
            directory,
            [
                "/usr/bin/python3",
                "-c",
                "import pathlib,socket\nfor p in ('/home/osso/.config','/syncthing','/run/user'):\n assert not pathlib.Path(p).exists(),p\ns=socket.socket();s.settimeout(1)\ntry:s.connect(('1.1.1.1',443))\nexcept OSError:print('REGION_MASKS_NETWORK_PASS')\nelse:raise AssertionError('network accessible')\n",
            ],
        ),
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert isolation.returncode == 0, isolation.stdout + isolation.stderr
    print(isolation.stdout, end="")
    output = []
    with (
        subprocess.Popen(
            sandbox(
                directory,
                ["cage", "--", "quickshell", "--no-color", "-p", str(directory)],
            ),
            cwd=directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process,
        selectors.DefaultSelector() as selector,
    ):
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            wait_ready(process, selector, output)
            print("REGION_COLD_START_PASS")
            source.write_text(source.read_text() + "\n// private source reload probe\n")
            wait_ready(process, selector, output)
            print("REGION_SOURCE_RELOAD_PASS")
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                tail, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                tail, _ = process.communicate(timeout=5)
            output.append(tail.decode())
            (directory / "runtime.log").write_text("".join(output))
    assert process.poll() is not None
    print("REGION_PRIVATE_PROCESS_EXITED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    directory = parser.parse_args().artifacts.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(original)
    digest = hashlib.sha256(original).hexdigest()
    assert backup.read_bytes() == original
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    assert backup.stat().st_mode & 0o777 == 0o600
    print("SETTINGS_BACKUP_VERIFIED", backup, digest)
    try:
        run_reload(directory)
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
