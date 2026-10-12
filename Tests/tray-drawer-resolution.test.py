#!/usr/bin/env python3
"""Private Winit/layer-shell drawer cold start, reload and failed-load recovery.

Production drawer + PopupMenuWindow; synthetic tray, SmartPanel and menu content.
QtTest injects pointer events into native Qt windows, not the compositor seat.
"""

import argparse
import importlib.util
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/Panels/Tray/TrayDrawerPanel.qml")


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixtures = load_helper("drawer_fixtures", "tray-drawer-warnings.test.py")
display = load_helper("drawer_display", "popup-private-display.py")

PROBE = """import QtQuick
import QtTest
import QtQuick.Window
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.TestTray
import qs.Modules.MainScreen
import qs.Modules.Panels.Tray
import qs.Services.UI
ShellRoot {
  Connections {
    target: Quickshell
    function onReloadCompleted() { Quickshell.inhibitReloadPopup(); }
  }
  PopupMenuWindow { id: popup; screen: Quickshell.screens[0] }
  PanelWindow {
    id: surface
    screen: Quickshell.screens[0]
    anchors.top: true
    anchors.left: true
    implicitWidth: 600
    implicitHeight: 300
    visible: true
    WlrLayershell.layer: WlrLayer.Bottom
    WlrLayershell.namespace: "private-drawer-test"
    TrayDrawerPanel {
      id: first
      screen: surface.screen
      widgetSection: "left"
      widgetIndex: 0
      width: preferredWidth
      height: preferredHeight
    }
    TrayDrawerPanel {
      id: second
      x: 300
      screen: surface.screen
      widgetSection: "right"
      widgetIndex: 0
      width: preferredWidth
      height: preferredHeight
    }
    QtObject {
      id: alpha
      property string name: "Alpha"
      property string icon: ""
      property bool onlyMenu: false
      property bool hasMenu: true
      property QtObject menu: QtObject {}
      property int activations: 0
      property int secondaryActivations: 0
      property int up: 0
      property int down: 0
      function activate() { activations++; }
      function secondaryActivate() { secondaryActivations++; }
      function scrollUp() { up++; }
      function scrollDown() { down++; }
    }
    QtObject {
      id: beta
      property string name: "Beta"
      property string icon: ""
      property bool onlyMenu: false
      property bool hasMenu: true
      property QtObject menu: QtObject {}
      property int activations: 0
      property int secondaryActivations: 0
      property int up: 0
      property int down: 0
      function activate() { activations++; }
      function secondaryActivate() { secondaryActivations++; }
      function scrollUp() { up++; }
      function scrollDown() { down++; }
    }
    TestEvent { id: input }
    TestResult { id: rendering }
    function click(owner, button) {
      const mouse = area(owner, 0);
      check(input.mouseClick(mouse, mouse.width / 2, mouse.height / 2, button, Qt.NoModifier, -1), "native click dispatched");
    }
    function check(condition, message) {
      if (!condition) throw new Error("DRAWER_NATIVE_ASSERT: " + message);
    }
    function find(parent, member) {
      if (parent[member] !== undefined) return parent;
      for (const child of parent.children) {
        const found = find(child, member);
        if (found) return found;
      }
      return null;
    }
    function delegates(owner) { return find(owner.contentItem, "itemAt"); }
    function area(owner, index) { return find(delegates(owner).itemAt(index), "clicked"); }
    Component.onCompleted: {
      Settings.data = {bar: {position: "top", widgets: {
        left: [{id: "Tray", pinned: ["Beta"], colorizeIcons: false}],
        right: [{id: "Tray", pinned: ["Alpha"], colorizeIcons: false}]
      }}, colorSchemes: {darkMode: true}};
      SystemTray.items.values = [alpha, beta];
    }
    Timer {
      interval: 250
      running: true
      onTriggered: {
        surface.check(popup.trayMenuLoader.item !== null, "native popup menu loaded");
        surface.check(first.popupMenuWindow === popup && second.popupMenuWindow === popup, "popup registry identity");
        surface.check(first.contentItem.drawer === first && second.contentItem.drawer === second, "independent content owners");
        surface.check(surface.delegates(first).itemAt(0).drawer === first, "first delegate owner");
        surface.check(surface.delegates(second).itemAt(0).drawer === second, "second delegate owner");
        surface.check(surface.delegates(first).itemAt(0).modelData === alpha, "first pinned model");
        surface.check(surface.delegates(second).itemAt(0).modelData === beta, "second pinned model");
        surface.check(surface.contentItem.Window.window !== null && surface.contentItem.Window.window.visible, "native drawer window visible");
        // Startup starts empty; the production drawer closes before fixture items arrive.
        first.visible = true;
        second.visible = true;
        surface.check(surface.area(first, 0).visible && surface.area(second, 0).visible, "both drawer input targets visible");
        const firstCloses = first.closeCount;
        const secondCloses = second.closeCount;
        PanelService.openedPanel = first;
        surface.click(first, Qt.LeftButton);
        surface.check(alpha.activations === 1 && beta.activations === 0 && first.closeCount === firstCloses + 1, "left activation routes first owner");
        PanelService.openedPanel = second;
        surface.click(second, Qt.MiddleButton);
        surface.check(beta.secondaryActivations === 1 && second.closeCount === secondCloses + 1, "middle activation routes second owner");
        SystemTray.items.values = [];
        surface.check(surface.delegates(first).count === 0 && surface.delegates(second).count === 0, "both models cleared");
        SystemTray.items.values = [beta, alpha];
        surface.check(surface.delegates(first).itemAt(0).modelData === alpha && surface.delegates(second).itemAt(0).modelData === beta, "models recreated");
        first.visible = true;
        second.visible = true;
        surface.check(rendering.waitForPolish(surface.delegates(second).parent, 1000), "recreated grid polished");
        surface.check(input.mouseWheel(surface.area(second, 0), 10, 10, Qt.NoButton, Qt.NoModifier, 0, 120, -1), "native wheel dispatched");
        surface.check(beta.up === 1 && alpha.up === 0, "wheel routes recreated model");
        surface.click(second, Qt.RightButton);
        surface.check(popup.visible && second.trayMenuItem.trayItem === beta, "native popup opened for second model");
        surface.check(second.trayMenuItem.widgetSection === "right" && second.trayMenuItem.widgetIndex === 0, "second owner menu context");
        surface.check(second.trayMenuItem.anchor === surface.find(surface.delegates(second).itemAt(0), "backer"), "menu anchor identity");
        surface.click(second, Qt.RightButton);
        surface.check(!popup.visible, "second right click closes native popup");
        popup.trayMenuLoader.active = false;
        surface.check(first.trayMenuItem === null && second.trayMenuItem === null, "menu teardown reaches both owners");
        popup.trayMenuLoader.active = true;
        Qt.callLater(() => {
          surface.check(first.trayMenuItem !== null && first.trayMenuItem === second.trayMenuItem, "menu recreated for both owners");
          surface.click(first, Qt.RightButton);
          surface.check(popup.visible && first.trayMenuItem.trayItem === alpha && first.trayMenuItem.widgetSection === "left", "first menu after recreation");
          surface.area(first, 0).entered();
          surface.check(!popup.visible && TooltipService.text === "Alpha", "hover closes native popup and routes tooltip");
          console.log("DRAWER_NATIVE_READY");
        });
      }
    }
  }
}
"""


def stage(directory, shadow):
    fixtures.stage_runtime(directory, shadow)
    (directory / "tst_tray_drawer.qml").unlink()
    shutil.rmtree(directory / "Quickshell")
    fixtures.helpers.write_module(
        directory,
        "qs.TestTray",
        {
            "SystemTray": fixtures.helpers.singleton(
                "property QtObject items: QtObject { property var values: [] }"
            ),
        },
    )
    drawer = directory / "qs" / TARGET
    drawer.write_text(
        drawer.read_text().replace(
            "import Quickshell.Services.SystemTray", "import qs.TestTray"
        )
    )
    popup = directory / "qs/Modules/MainScreen/PopupMenuWindow.qml"
    popup.write_bytes((ROOT / "Modules/MainScreen/PopupMenuWindow.qml").read_bytes())
    registry = directory / "qs/Services/UI/PanelService.qml"
    registry.write_text(
        registry.read_text().rsplit("}", 1)[0]
        + """
function registerPopupMenuWindow(screen, window) {
  popup = window;
  popupMenuWindowRegistered(screen);
}
function unregisterPopupMenuWindow(key, window) { if (popup === window) popup = null; }
}
"""
    )
    colors = directory / "qs/Commons/NColor.qml"
    colors.write_text(
        colors.read_text().rsplit("}", 1)[0]
        + '\nproperty color transparent: "transparent"\n}\n'
    )
    menu = directory / "qs/Modules/Bar/Extras/TrayMenu.qml"
    menu.write_text(
        menu.read_text().rsplit("}", 1)[0]
        + """
property var screen
function hideMenu() {}
}
"""
    )
    for source in (directory / "qs").iterdir():
        shutil.move(source, directory / source.name)
    (directory / "qs").rmdir()
    for declaration in directory.rglob("qmldir"):
        declaration.unlink()
    (directory / "shell.qml").write_text(PROBE)
    return directory / TARGET


def wait_for(process, log, errors, marker, start, allow_failure=False):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        output = (log.read_text() + errors.read_text())[start:]
        assert process.poll() is None, output
        if not allow_failure:
            assert not re.search(
                r" WARN | ERROR | FATAL |ReferenceError|TypeError|Binding loop|DRAWER_NATIVE_ASSERT",
                output,
            ), output
        if marker in output:
            return
        time.sleep(0.05)
    raise AssertionError("native drawer timed out:\n" + output)


def runtime(directory, shadow=False):
    source = stage(directory, shadow)
    original = source.read_bytes()
    log = directory / "runtime.log"
    errors = directory / "client.stderr"
    trace = directory / "client.trace"
    with (
        display.PopupPrivateDisplay(directory / "display") as environment,
        log.open("w") as stream,
        errors.open("w") as stderr,
    ):
        process = subprocess.Popen(
            display.sandbox(
                directory,
                [
                    "strace",
                    "-f",
                    "-qq",
                    "-e",
                    "trace=%file",
                    "-o",
                    str(trace),
                    "quickshell",
                    "--no-color",
                    "-p",
                    str(directory / "shell.qml"),
                ],
            ),
            cwd=directory,
            env=environment,
            stdout=stream,
            stderr=stderr,
            start_new_session=True,
        )
        try:
            wait_for(process, log, errors, "DRAWER_NATIVE_READY", 0)
            print("DRAWER_NATIVE_COLD_PASS")
            # Watchers attach after Configuration Loaded; the probe is delayed.
            start = len(log.read_text()) + len(errors.read_text())
            source.write_bytes(original + b"\n// private source reload\n")
            wait_for(process, log, errors, "DRAWER_NATIVE_READY", start)
            print("DRAWER_NATIVE_RELOAD_PASS")
            start = len(log.read_text()) + len(errors.read_text())
            source.write_bytes(original + b"\nINVALID PRIVATE DRAWER\n")
            wait_for(process, log, errors, "Failed to load configuration", start, True)
            rejected = (log.read_text() + errors.read_text())[start:]
            assert "TrayDrawerPanel.qml" in rejected, rejected
            start = len(log.read_text()) + len(errors.read_text())
            source.write_bytes(original + b"\n// private recovery\n")
            wait_for(process, log, errors, "DRAWER_NATIVE_READY", start)
            print("DRAWER_NATIVE_RECOVERY_PASS")
        finally:
            display.stop_owned(process)
            print(log.read_text() + errors.read_text(), end="")
            assert process.poll() is not None
    assert "settings.json" not in trace.read_text(), "client attempted settings access"
    assert log.read_text().count("DRAWER_NATIVE_READY") == 3
    print(
        "DRAWER_NATIVE_CLEANUP_PASS zero settings attempts; private client/display groups terminated"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.out:
        directory = args.out.absolute()
        directory.mkdir(mode=0o700)
        fixtures.isolation.install_settings_guard(directory)
        runtime(directory, args.shadow)
    else:
        with tempfile.TemporaryDirectory(prefix="ncd-") as temporary:
            directory = Path(temporary)
            fixtures.isolation.install_settings_guard(directory)
            runtime(directory, args.shadow)
