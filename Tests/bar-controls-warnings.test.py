#!/usr/bin/env python3
"""Eight production bar controls: bounded lint and inert offscreen QtTest.

Real buttons, pills, text, icons and widget handlers. Popup surface, shell,
settings and hardware/network boundaries record dispatch without desktop IO.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "ControlCenter",
    "Brightness",
    "Microphone",
    "Volume",
    "Bluetooth",
    "VPN",
    "LockKeys",
    "SessionMenu",
)


def load_helper():
    spec = importlib.util.spec_from_file_location(
        "pill", ROOT / "Tests/bar-pill-warnings.test.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def add_module(helper, directory, uri, sources):
    module = directory.joinpath(*uri.split("."))
    existing = {path.stem: path.read_text() for path in module.glob("*.qml")}
    helper.write_module(directory, uri, existing | sources)


def stage(directory):
    pill = load_helper()
    pill.stage_runtime(directory)
    (directory / "tst_bar_pill.qml").unlink()
    helper = pill.load_helper("workspace-runtime")
    singleton = helper.singleton
    add_module(
        helper,
        directory,
        "Quickshell",
        {
            "Quickshell": singleton(
                'property var commands: []\nproperty string shellDir: ""\nfunction execDetached(argv) { commands = commands.concat([argv]); }'
            ),
        },
    )
    for uri in ("Quickshell.Io", "Quickshell.Services.Pipewire"):
        add_module(
            helper, directory, uri, {"InertBoundary": "import QtQuick\nQtObject {}"}
        )
    add_module(
        helper,
        directory,
        "Quickshell.Widgets",
        {"IconImage": "import QtQuick\nImage {}"},
    )
    commons = directory / "qs/Commons"
    style = commons / "Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {",
            "QtObject {\nproperty real baseWidgetSize: 40\nproperty real opacityMedium: 0.5\nproperty real borderS: 1",
        )
    )
    colors = commons / "NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "QtObject {",
            "QtObject {\n"
            + "\n".join(
                f'property color {name}: "#808080"'
                for name in (
                    "mSurface",
                    "mSurfaceVariant",
                    "mOnSurfaceVariant",
                    "mPrimary",
                    "mSecondary",
                    "mTertiary",
                    "mError",
                    "mOutline",
                )
            ),
        )
    )
    add_module(
        helper,
        directory,
        "qs.Commons",
        {"I18n": singleton("function tr(key, values) { return key; }")},
    )
    add_module(
        helper,
        directory,
        "qs.Widgets",
        {
            "NIconButton": (ROOT / "Widgets/NIconButton.qml").read_text(),
            "NPopupContextMenu": """import QtQuick
Item {
  property var model: []
  property var lastAnchor: null
  property real lastX: 0
  property real lastY: 0
  signal triggered(string action)
  implicitWidth: 180
  implicitHeight: 120
  function openAtItem(item, x, y) { lastAnchor = item; lastX = x; lastY = y; }
}""",
        },
    )
    registry = (ROOT / "Services/UI/BarWidgetRegistry.qml").read_text()
    metadata = re.search(r"property var widgetMetadata: (\(\{.*?\}\))", registry, re.S)
    assert metadata
    add_module(
        helper,
        directory,
        "qs.Services.UI",
        {
            "BarWidgetRegistry": singleton(
                "property var widgetMetadata: " + metadata[1]
            ),
            "PanelService": singleton("""property var events: []
property var lastMenu: null
property var lastScreen: null
property var lastAnchor: null
property int requestedTab: -1
property var panel: ({
  toggle: function(anchor) { PanelService.lastAnchor = anchor || null; PanelService.events = PanelService.events.concat(["toggle"]); },
  open: function() { PanelService.events = PanelService.events.concat(["open"]); },
  requestedTab: -1
})
property var popup: ({
  close: function() { PanelService.events = PanelService.events.concat(["close"]); },
  showContextMenu: function(menu) { PanelService.lastMenu = menu; PanelService.events = PanelService.events.concat(["menu"]); }
})
function getPanel(name, screen) { lastScreen = screen; events = events.concat([name]); return panel; }
function getPopupMenuWindow(screen) { lastScreen = screen; return popup; }"""),
            "BarService": singleton("""property var settingsArgs: []
function getTooltipDirection() { return "bottom"; }
function getPillDirection(item) { return false; }
function getContextMenuPosition(item, width, height) { return {x: 7, y: 9}; }
function openWidgetSettings(...args) { settingsArgs = args; }"""),
        },
    )
    (directory / "qs/Modules/Bar/Extras/BarWidgetRegistry.qml").unlink(missing_ok=True)
    add_module(
        helper,
        directory,
        "qs.Services.System",
        {"HostService": singleton('property string osLogo: ""')},
    )
    add_module(
        helper,
        directory,
        "qs.Modules.Panels.Settings",
        {"SettingsPanel": "import QtQuick\nQtObject { enum Tab { Display } }"},
    )
    add_module(
        helper,
        directory,
        "qs.Services.Hardware",
        {
            "BrightnessService": singleton("""property QtObject monitor: QtObject {
  property real brightness: 0.4
  property bool brightnessControlAvailable: true
  signal brightnessUpdated()
  function increaseBrightness() { brightness += 0.1; brightnessUpdated(); }
  function decreaseBrightness() { brightness -= 0.1; brightnessUpdated(); }
}
function getMonitorForScreen(screen) { return monitor; }""")
        },
    )
    add_module(
        helper,
        directory,
        "qs.Services.Media",
        {
            "AudioService": singleton("""property real volume: 0.4
property real inputVolume: 0.3
property real stepVolume: 0.05
property bool muted: false
property bool inputMuted: false
property QtObject outputAudio: QtObject { property real volume: 0.4 }
property QtObject inputAudio: QtObject { property real volume: 0.3; property bool muted: false }
property var sink: ({audio: outputAudio})
property var source: ({audio: inputAudio})
function getOutputIcon() { return muted ? "volume-off" : "volume"; }
function getInputIcon() { return inputMuted ? "microphone-off" : "microphone"; }
function setOutputMuted(value) { muted = value; }
function setInputMuted(value) { inputMuted = value; inputAudio.muted = value; }
function setInputVolume(value) { inputVolume = value; inputAudio.volume = value; }
function increaseVolume() { volume += stepVolume; outputAudio.volume = volume; }
function decreaseVolume() { volume -= stepVolume; outputAudio.volume = volume; }""")
        },
    )
    add_module(
        helper,
        directory,
        "qs.Services.Networking",
        {
            "BluetoothService": singleton(
                'property bool enabled: true\nproperty var connectedDevices: [{name: "Headset"}, {name: "Keyboard"}]\nfunction setBluetoothEnabled(value) { enabled = value; }'
            ),
            "VPNService": singleton("""property int consumers: 0
property var commands: []
property var activeConnections: [{uuid: "active", name: "Office"}]
property var inactiveConnections: [{uuid: "idle", name: "Home"}]
property bool hasActiveConnection: true
property string connectingUuid: ""
property var connections: ({})
function beginPolling() { consumers++; }
function endPolling() { consumers--; }
function connect(uuid) { commands = commands.concat(["connect:" + uuid]); }
function disconnect(uuid) { commands = commands.concat(["disconnect:" + uuid]); }"""),
        },
    )
    add_module(
        helper,
        directory,
        "qs.Services.Keyboard",
        {
            "LockKeysService": singleton(
                "property bool capsLockOn: true\nproperty bool numLockOn: false\nproperty bool scrollLockOn: true"
            )
        },
    )
    add_module(
        helper,
        directory,
        "qs.Modules.Bar.Widgets",
        {
            name: (ROOT / f"Modules/Bar/Widgets/{name}.qml").read_text()
            for name in NAMES
        },
    )
    (directory / "tst_bar_controls.qml").write_text(HARNESS)


def behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=load_helper()
            .load_helper("media-mini-warnings")
            .isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        assert settings.read_bytes() == original, "real settings changed"
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
    ), output
    print("SETTINGS_SHA_UNCHANGED", hashlib.sha256(original).hexdigest())


def lint(directory):
    load_helper().load_helper("media-mini-warnings").stage_modules(directory)
    failures = []
    for name in NAMES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / f"qs/Modules/Bar/Widgets/{name}.qml"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            if "[" in line
            else "block-scope-var-declaration"
            for line in warnings
        )
        print("BAR_CONTROL_LINT_COUNTS", name, dict(counts))
        if counts or result.returncode:
            failures.append((name, dict(counts), result.returncode))
    assert not failures, failures


HARNESS = r"""import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets as W
import qs.Services.UI
import qs.Services.Media
import qs.Services.Hardware
import qs.Services.Networking

Item {
  id: scene
  width: 800
  height: 600
  ShellScreen { id: fixtureScreen; name: "inert" }
  Component { id: controlFactory; W.ControlCenter {} }
  Component { id: brightnessFactory; W.Brightness {} }
  Component { id: microphoneFactory; W.Microphone {} }
  Component { id: volumeFactory; W.Volume {} }
  Component { id: bluetoothFactory; W.Bluetooth {} }
  Component { id: vpnFactory; W.VPN {} }
  Component { id: locksFactory; W.LockKeys {} }
  Component { id: sessionFactory; W.SessionMenu {} }
  TestCase {
    id: tests
    name: "BarControls"
    when: windowShown
    property var widget
    SignalSpy { id: shown; signalName: "shown" }
    function rows() {
      return [
        {tag: "ControlCenter", factory: controlFactory, panel: "controlCenterPanel"},
        {tag: "Brightness", factory: brightnessFactory, panel: "brightnessPanel"},
        {tag: "Microphone", factory: microphoneFactory, panel: "audioPanel"},
        {tag: "Volume", factory: volumeFactory, panel: "audioPanel"},
        {tag: "Bluetooth", factory: bluetoothFactory, panel: "bluetoothPanel"},
        {tag: "VPN", factory: vpnFactory, panel: ""},
        {tag: "LockKeys", factory: locksFactory, panel: ""},
        {tag: "SessionMenu", factory: sessionFactory, panel: "sessionMenuPanel"}
      ];
    }
    function make(row) {
      const config = {id: row.tag, displayMode: "onHover"};
      Settings.data.bar.widgets.left = [config];
      Settings.data.bar.position = "top";
      Settings.data.controlCenter.position = "close_to_bar_button";
      Settings.dataChanged();
      widget = createTemporaryObject(row.factory, scene, {screen: fixtureScreen, widgetId: row.tag,
        section: "left", sectionWidgetIndex: 0, x: 200, y: 200});
      verify(widget !== null);
      wait(120);
      verify(widget.implicitWidth > 0 && widget.implicitHeight > 0);
      PanelService.events = [];
      return widget.children.find(child => child.wheel !== undefined && child.show !== undefined) || widget;
    }
    function test_click_context_data() { return rows(); }
    function test_click_context(row) {
      const button = make(row);
      if (row.panel) {
        mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton);
        compare(PanelService.events, [row.panel, "toggle"]);
        compare(PanelService.lastScreen, fixtureScreen);
        if (row.tag !== "SessionMenu") compare(PanelService.lastAnchor, button);
      }
      PanelService.events = [];
      mouseClick(button, button.width / 2, button.height / 2, Qt.RightButton);
      compare(PanelService.events, ["menu"]);
      compare(PanelService.lastScreen, fixtureScreen);
      const menu = PanelService.lastMenu;
      verify(menu !== null);
      compare(menu.lastAnchor, button);
      compare(menu.lastX, 7);
      compare(menu.lastY, 9);
      menu.triggered("widget-settings");
      compare(PanelService.events, ["menu", "close"]);
      compare(BarService.settingsArgs, [fixtureScreen, "left", 0, row.tag, widget.widgetSettings]);
      if (row.tag === "ControlCenter") {
        PanelService.events = [];
        menu.triggered("open-launcher");
        compare(PanelService.events, ["close", "launcherPanel", "toggle"]);
        PanelService.events = [];
        menu.triggered("open-settings");
        compare(PanelService.events, ["close", "settingsPanel", "toggle"]);
        PanelService.events = [];
        mouseClick(button, button.width / 2, button.height / 2, Qt.MiddleButton);
        compare(PanelService.events, ["launcherPanel", "toggle"]);
        Settings.data.controlCenter.position = "center";
        mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton);
        compare(PanelService.lastAnchor, null);
      } else if (row.tag === "Brightness") {
        PanelService.events = [];
        menu.triggered("open-display-settings");
        compare(PanelService.events, ["close", "settingsPanel", "open"]);
        compare(PanelService.panel.requestedTab, 0);
      } else if (row.tag === "Bluetooth") {
        const before = BluetoothService.enabled;
        menu.triggered("toggle-bluetooth");
        compare(BluetoothService.enabled, !before);
      } else if (row.tag === "VPN") {
        compare(VPNService.consumers, 1);
        menu.triggered("connect:idle");
        menu.triggered("disconnect:active");
        compare(VPNService.commands, ["connect:idle", "disconnect:active"]);
        widget.visible = false;
        compare(VPNService.consumers, 0);
        widget.visible = true;
        compare(VPNService.consumers, 1);
        PanelService.events = [];
        mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton);
        compare(PanelService.events, ["menu"]);
      } else if (row.tag === "Volume" || row.tag === "Microphone") {
        const input = row.tag === "Microphone";
        const before = input ? AudioService.inputMuted : AudioService.muted;
        menu.triggered("toggle-mute");
        compare(input ? AudioService.inputMuted : AudioService.muted, !before);
        Quickshell.commands = [];
        mouseClick(button, button.width / 2, button.height / 2, Qt.MiddleButton);
        menu.triggered("open-mixer");
        compare(Quickshell.commands, [["sh", "-c", Settings.data.audio.externalMixer], ["sh", "-c", Settings.data.audio.externalMixer]]);
      }
    }
    function test_wheel_and_update_data() { return rows().filter(row => ["Brightness", "Volume", "Microphone"].includes(row.tag)); }
    function test_wheel_and_update(row) {
      const button = make(row);
      shown.target = button;
      shown.clear();
      if (row.tag === "Brightness") {
        BrightnessService.monitor.brightnessUpdated();
        compare(widget.firstBrightnessReceived, true);
        compare(shown.count, 0);
        BrightnessService.monitor.brightnessUpdated();
        tryCompare(shown, "count", 1);
        const before = BrightnessService.monitor.brightness;
        button.wheel(120);
        fuzzyCompare(BrightnessService.monitor.brightness, before + 0.1, 0.00001);
        button.wheel(-120);
        fuzzyCompare(BrightnessService.monitor.brightness, before, 0.00001);
        BrightnessService.monitor.brightnessControlAvailable = false;
        button.wheel(120);
        fuzzyCompare(BrightnessService.monitor.brightness, before, 0.00001);
        BrightnessService.monitor.brightnessControlAvailable = true;
      } else {
        const input = row.tag === "Microphone";
        const audio = input ? AudioService.inputAudio : AudioService.outputAudio;
        audio.volumeChanged();
        compare(input ? widget.firstInputVolumeReceived : widget.firstVolumeReceived, true);
        compare(shown.count, 0);
        TooltipService.show(button, "old", "bottom");
        audio.volumeChanged();
        tryCompare(shown, "count", 1);
        compare(TooltipService.lastText, "");
        const before = input ? AudioService.inputVolume : AudioService.volume;
        button.wheel(60);
        fuzzyCompare(input ? AudioService.inputVolume : AudioService.volume, before, 0.00001);
        compare(widget.wheelAccumulator, 60);
        button.wheel(60);
        fuzzyCompare(input ? AudioService.inputVolume : AudioService.volume, before + AudioService.stepVolume, 0.00001);
        compare(widget.wheelAccumulator, 0);
        button.wheel(-120);
        fuzzyCompare(input ? AudioService.inputVolume : AudioService.volume, before, 0.00001);
        if (input) {
          button.hide();
          wait(150);
          shown.clear();
          audio.mutedChanged();
          tryCompare(shown, "count", 1);
        }
      }
      shown.target = null;
    }
    function test_display_modes_data() { return rows().filter(row => !["ControlCenter", "SessionMenu", "LockKeys"].includes(row.tag)); }
    function test_display_modes(row) {
      const button = make(row);
      widget.widgetSettings = {displayMode: "alwaysShow"};
      compare(button.forceOpen, true);
      widget.widgetSettings = {displayMode: "alwaysHide"};
      compare(button.forceClose, true);
      widget.widgetSettings = {displayMode: "alwaysShow"};
      Settings.data.bar.position = "left";
      Settings.dataChanged();
      wait(120);
      verify(widget.implicitWidth > 0 && widget.implicitHeight > 0);
      if (["Bluetooth", "VPN"].includes(row.tag)) {
        compare(button.forceOpen, false);
        compare(button.forceClose, true);
      }
    }
    function cleanup() { mouseMove(scene, 750, 550); }
  }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-controls-") as temporary:
        (lint if args.mode == "lint" else behavior)(Path(temporary))


if __name__ == "__main__":
    main()
