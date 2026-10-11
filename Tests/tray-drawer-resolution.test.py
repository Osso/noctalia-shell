#!/usr/bin/env python3
"""Production drawer cold-start and failed-reload recovery, private/no surfaces."""

import hashlib
import importlib.util
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Tray/TrayDrawerPanel.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolver = load_helper("tray_resolution", "tray-widget-resolution.test.py")
fixtures = load_helper("drawer_fixtures", "tray-drawer-warnings.test.py")


def stage(directory):
    fixtures.stage_runtime(directory)
    (directory / "tst_tray_drawer.qml").unlink()
    for source in (directory / "qs").iterdir():
        shutil.move(source, directory / source.name)
    shutil.rmtree(directory / "qs")
    shutil.rmtree(directory / "Quickshell")
    for declaration in directory.rglob("qmldir"):
        declaration.unlink()
    (directory / "Services/UI/DrawerRegistry.qml").write_text("""pragma Singleton
import QtQuick
import Quickshell
import qs.Modules.Panels.Tray
Singleton {
  property Component drawerComponent: Component { TrayDrawerPanel {} }
}
""")
    (directory / "shell.qml").write_text("""import QtQuick
import Quickshell
import Quickshell.Io
import qs.Services.UI
ShellRoot {
  IpcHandler {
    target: "drawer-test"
    function reload(): void { Quickshell.reload(false); }
  }
  Loader {
    sourceComponent: DrawerRegistry.drawerComponent
    onLoaded: {
      if (!item.contentItem) throw new Error("Drawer content missing");
      console.log("DRAWER_RESOLUTION_READY");
    }
  }
}
""")


def reload_private(process, environment):
    result = subprocess.run(
        [
            "quickshell",
            "ipc",
            "--pid",
            str(process.pid),
            "call",
            "drawer-test",
            "reload",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def resolution(directory, mode):
    stage(directory)
    source = directory / TARGET
    production = source.read_bytes()
    baseline = "import QtQuick\nItem { property Item contentItem: Item {} }\n"
    if mode != "cold-start":
        source.write_text(baseline)
    environment = resolver.private_environment(directory)
    # No desktop bus or host backend access, including the real SystemTray.
    environment.update(
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
    )
    output = []
    with (
        subprocess.Popen(
            ["quickshell", "--no-color", "-p", str(directory)],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ) as process,
        selectors.DefaultSelector() as selector,
    ):
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            resolver.wait_message(process, selector, output, "DRAWER_RESOLUTION_READY")
            if mode == "reload-after-failure":
                source.write_text("""import QtQuick
Item {
  property Item contentItem: Item {}
  component DrawerDelegate: Item {}
  DrawerDelegate {}
}
""")
                resolver.wait_message(
                    process, selector, output, "DrawerDelegate is not a type", True
                )
            if mode != "cold-start":
                source.write_bytes(production)
                if mode == "reload-after-failure":
                    reload_private(process, environment)
                resolver.wait_message(
                    process, selector, output, "DRAWER_RESOLUTION_READY"
                )
        finally:
            process.terminate()
            try:
                tail, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                tail, _ = process.communicate(timeout=5)
            print(tail.decode(), end="")
    print("DRAWER_RESOLUTION_PASS", mode)


def main():
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    with tempfile.TemporaryDirectory(prefix="noctalia-drawer-resolution-") as temporary:
        directory = Path(temporary)
        if original is not None:
            backup = directory / "settings.backup.json"
            backup.touch(mode=0o600)
            backup.write_bytes(original)
            assert (
                hashlib.sha256(backup.read_bytes()).digest()
                == hashlib.sha256(original).digest()
            )
        try:
            for index, mode in enumerate(
                ("cold-start", "reload", "reload-after-failure")
            ):
                case = directory / str(index)
                case.mkdir(mode=0o700)
                resolution(case, mode)
        finally:
            assert (settings.read_bytes() if settings.exists() else None) == original


if __name__ == "__main__":
    main()
