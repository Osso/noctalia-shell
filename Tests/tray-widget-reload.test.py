#!/usr/bin/env python3
"""Private actual-Tray/TrayMenu cold start, source reload and failed-reload recovery.

Real Quickshell resolver and PopupWindow; synthetic services, inert controls and
an invisible popup owner. No canonical process, settings or desktop access.
"""

import importlib.util
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).absolute().parents[1]


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


widget_tests = helper("tray-widget-warnings.test.py")
isolation = widget_tests.isolation
lifecycle = helper("shell-root-warnings.test.py")


PROBE = """import QtQuick
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets
import qs.Modules.Bar.Extras
import qs.Services.UI
ShellRoot {
  Item {
    id: scene
    visible: false
    property int passes: 0
    Item {
      id: popup
      visible: false
      property alias trayMenuLoader: menuLoader
      function close() { popup.visible = false; }
      function open() { popup.visible = true; }
      Loader { id: menuLoader; sourceComponent: TrayMenu {} }
    }
    Tray { id: first; widgetId: "Tray"; section: "left"; sectionWidgetIndex: 0 }
    Tray { id: second; widgetId: "Tray"; section: "left"; sectionWidgetIndex: 0 }
    QtObject {
      id: notifier
      property string name: "Private notifier"
      property string icon: ""
    }
    QtObject {
      id: drawer
      property string widgetSection
      property int widgetIndex
      property int toggles: 0
      function toggle(item) { drawer.toggles++; }
    }
    Component.onCompleted: {
      Settings.data = {bar: {position: "top", density: false, widgets: {left: [{id: "Tray", drawerEnabled: false, colorizeIcons: false}]}}, colorSchemes: {darkMode: true}};
      PanelService.popup = popup;
      PanelService.drawer = drawer;
      SystemTray.items.values = [notifier];
      first._performFilteredItemsUpdate();
      second._performFilteredItemsUpdate();
    }
    Timer {
      interval: 150
      running: true
      repeat: true
      function check(condition, message) {
        if (!condition) throw new Error("TRAY_RELOAD_ASSERT: " + message);
      }
      onTriggered: {
        check(menuLoader.item !== null, "real menu loaded");
        first.onLoaded();
        second.onLoaded();
        check(menuLoader.item.screen === null, "screen handoff");
        check(first.filteredItems.length === 1 && second.filteredItems.length === 1, "two owner models");
        popup.open();
        first.toggleDrawer(first);
        check(!popup.visible && drawer.toggles === 1, "first owner closes popup and routes drawer");
        menuLoader.active = false;
        first.onLoaded();
        second.onLoaded();
        check(menuLoader.item === null, "menu teardown");
        menuLoader.active = true;
        check(menuLoader.item !== null, "menu recreation");
        second.onLoaded();
        check(menuLoader.item.screen === null, "recreated screen handoff");
        PanelService.popup = null;
        first.onLoaded();
        check(first.trayMenu === null && second.trayMenu === null, "owner unregister");
        PanelService.popup = popup;
        PanelService.popupMenuWindowRegistered(null);
        popup.open();
        second.toggleDrawer(second);
        check(!popup.visible && drawer.toggles === 2, "second owner after re-registration");
        running = false;
        console.log("TRAY_PRIVATE_READY");
      }
    }
  }
  Connections {
    target: Quickshell
    function onReloadCompleted() { Quickshell.inhibitReloadPopup(); }
  }
}
""".replace(
    "import qs.Commons", "import Quickshell.Services.SystemTray\nimport qs.Commons", 1
)


def stage(directory):
    widget_tests.stage_runtime(directory, shadow=True)
    # Installed Quickshell URIs outrank local stubs; isolate the notifier import.
    shutil.rmtree(directory / "Quickshell")
    widget_tests.helpers.write_module(
        directory,
        "qs.TestTray",
        {
            "SystemTray": widget_tests.helpers.singleton(
                "property QtObject items: QtObject { property var values: [] }"
            ),
            "SystemTrayItem": "import QtQuick\nimport Quickshell\nQtObject { property QsMenuHandle menu; property string tooltipTitle; property string name; property string id }",
        },
    )
    # Production TrayMenu + inert leaf controls. Never invent production metadata.
    menu_fixtures = directory / "menu-fixtures"
    menu_fixtures.mkdir()
    helper("tray-menu-warnings.test.py").stage_runtime(menu_fixtures, None)
    shutil.copytree(
        menu_fixtures / "qs/Widgets", directory / "qs/Widgets", dirs_exist_ok=True
    )
    for name in ("Style", "NColor"):
        target = directory / f"qs/Commons/{name}.qml"
        source = target.read_text()
        fixture = (menu_fixtures / f"qs/Commons/{name}.qml").read_text()
        existing = set(re.findall(r"property \w+ (\w+)", source))
        additions = [
            line
            for line in fixture.splitlines()
            if (match := re.match(r"property \w+ (\w+)", line))
            and match[1] not in existing
        ]
        target.write_text(
            source.rsplit("}", 1)[0] + "\n" + "\n".join(additions) + "\n}\n"
        )
    menu = directory / "qs/Modules/Bar/Extras/TrayMenu.qml"
    menu.write_text((ROOT / "Modules/Bar/Extras/TrayMenu.qml").read_text())
    for target in (directory / "qs" / widget_tests.TARGET, menu):
        target.write_text(
            target.read_text().replace(
                "import Quickshell.Services.SystemTray", "import qs.TestTray"
            )
        )
    shutil.rmtree(menu_fixtures)
    for path in (directory / "qs").iterdir():
        shutil.move(str(path), directory / path.name)
    (directory / "qs").rmdir()
    for declaration in directory.rglob("qmldir"):
        if "Quickshell" not in declaration.parts:
            declaration.unlink()
    (directory / "shell.qml").write_text(
        PROBE.replace("import Quickshell.Services.SystemTray", "import qs.TestTray")
    )
    return directory / widget_tests.TARGET


def wait_for(process, selector, output, marker, allow_error=False):
    start = len(output)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        for key, _ in selector.select(0.1):
            chunk = os.read(key.fileobj.fileno(), 65536).decode()
            output.append(chunk)
            print(chunk, end="", flush=True)
            current = "".join(output[start:])
            if not allow_error:
                assert not re.search(
                    r" WARN | ERROR | FATAL |ReferenceError|TypeError|Binding loop|TRAY_RELOAD_ASSERT|SHADOW_",
                    current,
                ), current
            if marker in current:
                if allow_error:
                    while selector.select(0.3):
                        tail = os.read(process.stdout.fileno(), 65536).decode()
                        output.append(tail)
                        print(tail, end="", flush=True)
                    current = "".join(output[start:])
                return current
        assert process.poll() is None, "".join(output)
    raise AssertionError("private reload timed out:\n" + "".join(output))


def runtime(directory):
    source = stage(directory)
    original = source.read_text()
    environment = isolation.isolated_environment(directory)
    environment["QS_NO_RELOAD_POPUP"] = "1"
    trace = directory / "reload.trace"
    output = []
    with (
        subprocess.Popen(
            [
                "strace",
                "-f",
                "-qq",
                "-e",
                "trace=%file",
                "-o",
                str(trace),
                *lifecycle.sandbox(
                    directory, ["quickshell", "--no-color", "-p", str(directory)]
                ),
            ],
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
            wait_for(process, selector, output, "TRAY_PRIVATE_READY")
            print("TRAY_PRIVATE_COLD_START_PASS")
            source.write_text(original + "\n// private reload\n")
            wait_for(process, selector, output, "TRAY_PRIVATE_READY")
            print("TRAY_PRIVATE_SOURCE_RELOAD_PASS")
            source.write_text(original + "\nINVALID PRIVATE RELOAD\n")
            rejected = wait_for(
                process,
                selector,
                output,
                "Failed to load configuration",
                allow_error=True,
            )
            assert "Tray.qml" in rejected, rejected
            source.write_text(original + "\n// private recovery\n")
            wait_for(process, selector, output, "TRAY_PRIVATE_READY")
            print("TRAY_PRIVATE_RECOVERY_PASS")
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                tail, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                tail, _ = process.communicate(timeout=5)
            print(tail.decode(), end="")
    assert process.poll() is not None
    assert "settings.json" not in trace.read_text(), "child attempted settings access"
    print("TRAY_PRIVATE_EXITED_ZERO_SETTINGS_ATTEMPTS")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="noctalia-tray-reload-") as temporary:
        directory = Path(temporary)
        isolation.install_settings_guard(directory)
        runtime(directory)
