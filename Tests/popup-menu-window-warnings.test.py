#!/usr/bin/env python3
"""Bounded popup lint and native headless Cage→Niri layer-shell reload.

Real PanelWindow/Loader/attached bindings; inert registry, tray and menu content.
Consumer expressions and both taskbar opening bodies execute against the real
popup. No whole-widget/input acceptance or canonical settings/process access.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/MainScreen/PopupMenuWindow.qml")
CONSUMERS = (
    Path("Modules/Bar/Widgets/Taskbar.qml"),
    Path("Modules/Bar/Widgets/TaskbarGrouped.qml"),
)


def helper(runner="media-mini-warnings.test.py"):
    spec = importlib.util.spec_from_file_location(
        "popup_window_helpers", ROOT / "Tests" / runner
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper().stage_modules(directory)
    for target in (TARGET, *CONSUMERS):
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "--unqualified",
                "error",
                "-I",
                str(directory),
                str(directory / "qs" / target),
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
        print("POPUP_WINDOW_LINT_COUNTS", str(target), dict(counts))
        # Installed PanelWindow metadata is external; do not suppress or replace it.
        expected = {"uncreatable-type": 1} if target == TARGET else {}
        assert counts == expected, (str(target), dict(counts))
        assert result.returncode == 0, result.returncode
    print("POPUP_WINDOW_LINT_PASS")


def consumer_checks():
    """Execute current consumer member expressions, not source-shape assertions."""
    checks = []
    paths = sorted((ROOT / "Modules").rglob("*.qml")) + sorted(
        (ROOT / "Services").rglob("*.qml")
    )
    pattern = re.compile(
        r"\b(?:\w+\.)*popupMenuWindow\.(\w+)(?:\(([^()\n]*)\))?(?:\s*=\s*(contextMenu|true|false)\s*;)?"
    )
    expected = {
        "visible": "false",
        "trayMenuLoader": "window.trayMenuLoader.item !== null && window.trayMenuLoader.item.screen === window.screen",
        "dialogParent": "window.dialogParent.parent === window.contentItem && window.dialogParent.width === window.contentItem.width && window.dialogParent.height === window.contentItem.height",
        "hasDialog": "false",
    }
    for path in paths:
        source = path.read_text()
        if path.relative_to(ROOT) == TARGET:
            continue
        for match in pattern.finditer(source):
            member, arguments, assigned = match.groups()
            label = f"{path.relative_to(ROOT)}:{source.count(chr(10), 0, match.start()) + 1}"
            checks.extend(("window.close();", "window.hasDialog = false;"))
            if arguments is not None:
                arguments = arguments.replace("contextMenu", "hideMenuContent").replace(
                    "sourceMenu", "hideMenuContent"
                )
                if member == "close":
                    checks.append("window.open();")
                checks.append(f"window.{member}({arguments});")
                if member in ("open", "showContextMenu"):
                    checks.append(
                        f"check(window.visible, {json.dumps(label + ' opens')});"
                    )
                elif member == "close":
                    checks.append(
                        f"check(!window.visible, {json.dumps(label + ' closes')});"
                    )
                else:
                    raise AssertionError(f"unhandled consumer call {label}: {member}")
                if member == "showContextMenu":
                    checks.append(
                        f"check(window.activeMenu === hideMenuContent, {json.dumps(label + ' content')});"
                    )
            elif assigned:
                value = "hideMenuContent" if assigned == "contextMenu" else assigned
                checks.append(f"window.{member} = {value};")
                observed = "activeMenu" if assigned == "contextMenu" else member
                checks.append(
                    f"check(window.{observed} === {value}, {json.dumps(label + ' assignment')});"
                )
                if member == "hasDialog":
                    focus = "OnDemand" if assigned == "true" else "None"
                    checks.append(
                        f"check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.{focus}, {json.dumps(label + ' focus')});"
                    )
            else:
                assert member in expected, (label, member)
                condition = (
                    f"window.{member} === {expected[member]}"
                    if member in ("visible", "hasDialog")
                    else expected[member]
                )
                checks.append(f"check({condition}, {json.dumps(label + ' read')});")
            checks.append(f"console.log('POPUP_CONSUMER_PASS ' + {json.dumps(label)});")
    assert checks, "no production consumer operations found"
    return "\n".join(checks)


def taskbar_body(path):
    source = (ROOT / path).read_text()
    if path.name == "Taskbar.qml":
        match = re.search(
            r"    onTriggered: \{\n(.*?)\n    }\n  }\n}\s*$", source, re.S
        )
    else:
        match = re.search(
            r"  function openContextMenu\([^\n]*\) \{\n(.*?)\n  }\n}\s*$", source, re.S
        )
    assert match, f"cannot extract production opening body: {path}"
    return match[1]


HARNESS = """import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Services.UI
import qs.Modules.MainScreen

ShellRoot {
  id: harness
  property var window
  property string generation: "INITIAL"
  QtObject { id: screenDelegate; property ShellScreen modelData: Quickshell.screens[0] }
  Component {
    id: factory
    PopupMenuWindow { screen: screenDelegate.modelData }
  }
  QtObject {
    id: hideMenuContent
    property int hiddenCount: 0
    property int closedCount: 0
    function hideMenu() {
      harness.check(!harness.window.visible && harness.window.activeMenu === hideMenuContent, "hide ordering");
      hiddenCount++;
    }
    function close() { closedCount++; }
  }
  QtObject {
    id: closeContent
    property int closedCount: 0
    function close() {
      harness.check(!harness.window.visible && harness.window.activeMenu === closeContent, "close ordering");
      closedCount++;
    }
  }
  QtObject { id: inertContent }
  QtObject {
    id: consumerRoot
    property ShellScreen screen: screenDelegate.modelData
    property var selectedWindow: ({id: 23})
    property string selectedAppName: "Firefox"
    property string barPosition: "top"
  }
  Item {
    id: consumerMenu
    property var model: []
    property real itemHeight: 24
    property var lastAnchor: null
    property real lastX: 0
    property real lastY: 0
    property int hiddenCount: 0
    implicitWidth: 180
    implicitHeight: model.length * itemHeight
    function openAtItem(anchor, x, y) {
      harness.check(harness.window.visible, "production taskbar opens before menu anchoring");
      lastAnchor = anchor; lastX = x; lastY = y;
    }
    function hideMenu() { hiddenCount++; }
  }
  function check(condition, message) {
    if (!condition) {
      console.error(message);
      Qt.exit(1);
      throw new Error(message);
    }
  }
  function exerciseLifecycle() {
    const tray = window.trayMenuLoader.item;
    check(tray !== null && tray.screen === window.screen, "tray screen propagation");
    check(window.screen === screenDelegate.modelData, "AllScreens screen assignment");
    check(window.selectedScreen === window.screen, "typed screen binding preserves identity");
    check(window.contentItem === window.dialogParent.parent, "native contentItem is visual root");
    check(window.activeMenu === tray, "default tray content");
    window.initializeTrayMenu(null);
    check(window.activeMenu === tray, "null initialization unchanged");
    check(!window.visible && window.color.a === 0, "initially closed and transparent");
    check(window.anchors.top && window.anchors.bottom && window.anchors.left && window.anchors.right, "full-screen anchors");
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.None, "no dialog focus");
    window.hasDialog = true;
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.OnDemand, "dialog focus request");
    window.hasDialog = false;
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.None, "focus released");
    window.open();
    check(window.visible, "open");
    window.close();
    check(!window.visible && tray.hiddenCount === 1, "close tray");
    window.showContextMenu(hideMenuContent);
    window.showContextMenu(null);
    check(window.visible && window.activeMenu === hideMenuContent, "null context unchanged");
    window.close();
    check(hideMenuContent.hiddenCount === 1 && hideMenuContent.closedCount === 0, "hideMenu precedence");
    check(window.activeMenu === tray, "tray restored");
    window.showContextMenu(closeContent);
    window.close();
    check(closeContent.closedCount === 1 && window.activeMenu === tray, "close-only restoration");
    window.showContextMenu(inertContent);
    window.close();
    check(!window.visible && window.activeMenu === tray, "inert content restoration");
    window.activeMenu = null;
    window.close();
    check(window.activeMenu === tray, "null content restoration");
    window.open();
    check(window.visible, "reopen");
  }
  function exerciseConsumers() {
    @CONSUMERS@
    window.close();
  }
  function taskbar(globalX, globalY, itemWidth, itemHeight) {
    const root = consumerRoot;
    const screen = consumerRoot.screen;
    const contextMenu = consumerMenu;
    @TASKBAR@
  }
  function grouped(globalX, globalY, itemWidth, itemHeight) {
    const root = consumerRoot;
    const screen = consumerRoot.screen;
    const contextMenu = consumerMenu;
    @GROUPED@
  }
  function exerciseTaskbars() {
    for (const openMenu of [taskbar, grouped]) {
      for (const position of ["top", "bottom", "left", "right"]) {
        consumerRoot.barPosition = position;
        openMenu(100, 200, 40, 32);
        check(window.visible && window.activeMenu === consumerMenu, "taskbar owns active content");
        check(consumerMenu.lastAnchor === consumerRoot, "taskbar anchor");
        check(consumerMenu.model.length === 3 && consumerMenu.model[0].action === "activate" && consumerMenu.model[1].action === "close" && consumerMenu.model[2].action === "widget-settings", "window menu actions");
        const expectedX = {top: 30, bottom: 30, left: 36, right: -184};
        const expectedY = {top: 36, bottom: -88, left: 180, right: 180};
        check(consumerMenu.lastX === expectedX[position] && consumerMenu.lastY === expectedY[position], "taskbar position " + position);
        const hidden = consumerMenu.hiddenCount;
        window.close();
        check(consumerMenu.hiddenCount === hidden + 1 && window.activeMenu === window.trayMenuLoader.item, "taskbar closes selected content");
      }
      consumerRoot.selectedWindow = null;
      openMenu(100, 200, 40, 32);
      check(consumerMenu.model.length === 1 && consumerMenu.model[0].action === "widget-settings", "empty selection actions");
      window.close();
      consumerRoot.selectedWindow = ({id: 23});
    }
  }
  Timer {
    id: geometryReady
    interval: 150
    onTriggered: {
      window.contentItem.width = 640;
      window.contentItem.height = 480;
      Qt.callLater(() => {
        check(window.dialogParent.width === 640 && window.dialogParent.height === 480, "dialog anchored to native root");
        let catchers = 0;
        for (const child of window.contentItem.children) {
          if (child instanceof MouseArea) {
            catchers++;
            check(child.width === 640 && child.height === 480, "catcher full-screen geometry");
            check(child.acceptedButtons === (Qt.LeftButton | Qt.RightButton | Qt.MiddleButton), "catcher buttons");
            child.clicked(null);
          }
        }
        check(catchers === 1 && !window.visible, "outside signal closes");
        exerciseConsumers();
        exerciseTaskbars();
        const key = window.registrationKey;
        window.destroy();
        Qt.callLater(() => {
          check(PanelService.registeredWindow === null && PanelService.removals === 1 && PanelService.removedKey === key, "unregister on destruction");
          finish.start();
        });
      });
    }
  }
  Timer {
    id: finish
    interval: 150
    onTriggered: {
      console.log("POPUP_WINDOW_RUNTIME_PASS " + harness.generation);
      if (harness.generation === "RELOADED") Qt.quit();
    }
  }
  Component.onCompleted: {
    check(Quickshell.screens.length > 0, "private screen exists");
    window = factory.createObject(harness);
    check(window !== null, "production popup created");
    check(PanelService.registeredWindow === window && PanelService.registeredScreen === window.screen, "registered screen");
    check(window.registrationKey === window.screen.name, "registration key");
    check(window.objectName === "popupMenuWindow-" + window.screen.name, "object name");
    check(window.WlrLayershell.namespace === "noctalia-popupmenu-" + window.screen.name, "namespace");
    exerciseLifecycle();
    geometryReady.start();
  }
}
"""


def stage_runtime(directory):
    target = directory / TARGET
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / TARGET, target)
    write = helper().write_singleton
    write(directory / "Commons", "NColor", 'property color transparent: "transparent"')
    write(
        directory / "Commons",
        "Style",
        "property real barHeight: 32\nproperty real marginS: 4",
    )
    write(directory / "Commons", "I18n", "function tr(key, args) { return key; }")
    write(
        directory / "Services/UI",
        "PanelService",
        """property var registeredWindow: null
property var registeredScreen: null
property string removedKey: ""
property int removals: 0
function registerPopupMenuWindow(screen, window) {
  registeredScreen = screen;
  registeredWindow = window;
}
function getPopupMenuWindow(screen) {
  if (screen !== registeredScreen) throw new Error("wrong popup lookup screen");
  return registeredWindow;
}
function unregisterPopupMenuWindow(key, window) {
  if (registeredWindow !== window) throw new Error("wrong popup unregister");
  removedKey = key;
  registeredWindow = null;
  removals++;
}
""",
    )
    tray = directory / "Modules/Bar/Extras"
    tray.mkdir(parents=True)
    (tray / "TrayMenu.qml").write_text("""import QtQuick
import Quickshell
Item {
  property ShellScreen screen
  property int hiddenCount: 0
  function hideMenu() { hiddenCount++; }
}
""")
    harness = HARNESS.replace("@CONSUMERS@", consumer_checks())
    harness = harness.replace("@TASKBAR@", taskbar_body(CONSUMERS[0]))
    harness = harness.replace("@GROUPED@", taskbar_body(CONSUMERS[1]))
    (directory / "shell.qml").write_text(harness)


def assert_native_output(output):
    diagnostics = [
        line
        for line in output.splitlines()
        if re.search(
            r" WARN[: ]| ERROR[: ]| FATAL[: ]|ReferenceError|TypeError|Binding loop|^warning:|wl_callback|queue destroyed",
            line,
            re.I,
        )
    ]
    assert not diagnostics, diagnostics
    assert "POPUP_WINDOW_RUNTIME_PASS INITIAL" in output, output
    assert "POPUP_WINDOW_RUNTIME_PASS RELOADED" in output, output
    assert output.count("POPUP_WINDOW_RUNTIME_PASS") == 2, output
    expected_consumers = consumer_checks().count("POPUP_CONSUMER_PASS")
    assert output.count("POPUP_CONSUMER_PASS") == 2 * expected_consumers, output


def runtime(directory):
    stage_runtime(directory)
    display = helper("popup-private-display.py")
    log = directory / "runtime.log"
    errors = directory / "client.stderr.raw"
    with display.PopupPrivateDisplay(directory / "display") as environment:
        with log.open("w") as stream, errors.open("w") as stderr:
            process = subprocess.Popen(
                display.sandbox(
                    directory,
                    ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                ),
                cwd=directory,
                env=environment,
                stdout=stream,
                stderr=stderr,
                text=True,
                start_new_session=True,
            )
            try:
                deadline = time.monotonic() + 20
                while "POPUP_WINDOW_RUNTIME_PASS INITIAL" not in log.read_text():
                    output = log.read_text() + errors.read_text()
                    assert process.poll() is None, output
                    assert not re.search(
                        r"ERROR|TypeError|ReferenceError|Binding loop", output
                    ), output
                    assert time.monotonic() < deadline, output
                    time.sleep(0.05)
                # Actual file-watcher reload in the same private Quickshell process.
                shell = directory / "shell.qml"
                shell.write_text(
                    shell.read_text().replace(
                        'generation: "INITIAL"', 'generation: "RELOADED"'
                    )
                )
                process.wait(timeout=20)
                output = log.read_text() + errors.read_text()
                print(output, end="")
                assert process.returncode == 0, process.returncode
                assert_native_output(output)
                print("POPUP_WINDOW_PRIVATE_RELOAD_PASS")
            finally:
                display.stop_owned(process)
                assert process.poll() is not None, "private client still running"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument(
        "--out", type=Path, help="retain raw evidence in a fresh directory"
    )
    args = parser.parse_args()
    if args.out is not None:
        directory = args.out.absolute()
        directory.mkdir(mode=0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
    else:
        with tempfile.TemporaryDirectory(prefix="noctalia-popup-window-") as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            {"lint": lint, "runtime": runtime}[args.mode](directory)
