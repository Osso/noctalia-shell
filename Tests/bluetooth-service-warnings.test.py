#!/usr/bin/env python3
"""Targeted production BluetoothService lint and inert offscreen behavior.

Runtime substitutes Bluetooth, process, network and toast boundaries. Installed
Quickshell metadata is used unchanged for source lint, never runtime hardware.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/Networking/BluetoothService.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--json",
            "-",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    (directory / "lint.json").write_text(result.stdout)
    print(result.stderr, end="")
    warnings = json.loads(result.stdout)["files"][0]["warnings"]
    counts = Counter(w["id"] for w in warnings if w["type"] == "warning")
    for warning in warnings:
        print(warning["line"], warning["id"], warning["message"])
    print("BLUETOOTH_SERVICE_LINT", dict(counts))
    assert result.returncode == 0, result.returncode
    # Installed defaultAdapter and adapter-state enum metadata remain unresolved.
    assert counts == {"unresolved-type": 8}, dict(counts)


HARNESS = """import QtQuick
import QtTest
import Quickshell.Bluetooth
import Quickshell.Io
import qs.Services.Networking
import qs.Services.UI

TestCase {
  name: "BluetoothService"
  BluetoothAdapter { id: adapter }
  BluetoothAdapter { id: replacement }
  BluetoothDevice { id: headphones; name: "Studio Headphones" }
  BluetoothDevice { id: keyboard; name: "Desk Keyboard" }
  BluetoothDevice { id: phone; name: "Pocket Phone" }

  function init() {
    Bluetooth.defaultAdapter = null;
    adapter.state = BluetoothAdapterState.Disabled;
    adapter.enabled = false;
    adapter.discovering = false;
    adapter.devices.values = [];
    replacement.devices.values = [];
    headphones.paired = true;
    headphones.trusted = false;
    headphones.connected = true;
    headphones.pairing = false;
    headphones.blocked = false;
    headphones.batteryAvailable = true;
    headphones.battery = 0.75;
    headphones.events = [];
    keyboard.paired = false;
    keyboard.trusted = true;
    keyboard.connected = false;
    keyboard.batteryAvailable = true;
    keyboard.battery = 0;
    phone.paired = false;
    phone.trusted = false;
    phone.connected = false;
    phone.batteryAvailable = false;
    phone.events = [];
    BluetoothService.lastBluetoothBlocked = false;
    FixtureIo.starts = 0;
    NetworkService.requests = [];
    ToastService.notices = [];
  }

  function test_lists_follow_model_and_adapter_replacement() {
    compare(BluetoothService.available, false);
    compare(BluetoothService.devices, null);
    compare(BluetoothService.pairedDevices.length, 0);
    compare(BluetoothService.connectedDevices.length, 0);
    compare(BluetoothService.allDevicesWithBattery.length, 0);
    Bluetooth.defaultAdapter = adapter;
    adapter.devices.values = [headphones, keyboard, phone];
    compare(BluetoothService.devices, adapter.devices);
    compare(BluetoothService.pairedDevices, [headphones, keyboard]);
    compare(BluetoothService.connectedDevices, [headphones]);
    compare(BluetoothService.allDevicesWithBattery, [headphones]);
    adapter.devices.values = [phone, keyboard];
    compare(BluetoothService.pairedDevices, [keyboard]);
    compare(BluetoothService.connectedDevices.length, 0);
    compare(BluetoothService.allDevicesWithBattery.length, 0);
    replacement.devices.values = [headphones];
    Bluetooth.defaultAdapter = replacement;
    compare(BluetoothService.devices, replacement.devices);
    compare(BluetoothService.connectedDevices, [headphones]);
    replacement.devices.values = [];
    compare(BluetoothService.pairedDevices.length, 0);
    Bluetooth.defaultAdapter = null;
    compare(BluetoothService.devices, null);
    compare(BluetoothService.connectedDevices.length, 0);
  }

  function test_connect_trust_order_and_device_actions() {
    verify(BluetoothService.canConnect(phone));
    verify(!BluetoothService.canDisconnect(phone));
    BluetoothService.connectDeviceWithTrust(phone);
    compare(phone.events, ["connect:true"]);
    verify(phone.trusted);
    phone.connected = true;
    verify(!BluetoothService.canConnect(phone));
    verify(BluetoothService.canDisconnect(phone));
    BluetoothService.disconnectDevice(phone);
    compare(phone.events, ["connect:true", "disconnect"]);
    phone.pairing = true;
    verify(!BluetoothService.canDisconnect(phone));
    verify(BluetoothService.isDeviceBusy(phone));
    phone.pairing = false;
    phone.blocked = true;
    verify(!BluetoothService.canDisconnect(phone));
    BluetoothService.forgetDevice(phone);
    compare(phone.events, ["connect:true", "disconnect", "forget:false"]);
    verify(!phone.trusted);
    BluetoothService.connectDeviceWithTrust(null);
    BluetoothService.disconnectDevice(null);
    BluetoothService.forgetDevice(null);
    compare(phone.events.length, 3);
  }

  function test_adapter_state_signal_and_delayed_discovery() {
    Bluetooth.defaultAdapter = adapter;
    adapter.state = BluetoothAdapterState.Enabling;
    compare(ToastService.notices.length, 0);
    adapter.enabled = true;
    adapter.state = BluetoothAdapterState.Enabled;
    compare(BluetoothService.state, BluetoothAdapterState.Enabled);
    verify(BluetoothService.enabled);
    compare(ToastService.notices, ["toast.bluetooth.enabled"]);
    verify(!adapter.discovering);
    tryCompare(adapter, "discovering", true, 1800);
    verify(BluetoothService.discovering);
    adapter.state = BluetoothAdapterState.Disabling;
    compare(ToastService.notices.length, 1);
    adapter.enabled = false;
    adapter.state = BluetoothAdapterState.Disabled;
    compare(ToastService.notices, ["toast.bluetooth.enabled", "toast.bluetooth.disabled"]);
    compare(FixtureIo.starts, 0);
    compare(NetworkService.requests.length, 0);
  }

  function test_signal_helpers_preserve_unknown_and_thresholds() {
    compare(BluetoothService.getSignalStrength(phone), "Signal: Unknown");
    compare(BluetoothService.getSignalIcon(phone), "antenna-bars-off");
    const strengths = [0, 1, 20, 40, 60, 80];
    const labels = ["Unknown", "Very poor", "Poor", "Fair", "Good", "Excellent"];
    const icons = ["off", "1", "2", "3", "4", "5"];
    for (let i = 0; i < strengths.length; ++i) {
      const data = {signalStrength: strengths[i]};
      compare(BluetoothService.getSignalStrength(data), "Signal: " + labels[i]);
      compare(BluetoothService.getSignalIcon(data), "antenna-bars-" + icons[i]);
    }
    compare(BluetoothService.getBattery(headphones), "Battery: 75%");
  }
}
"""


def stage_runtime(directory):
    workspace = helper("workspace-runtime")
    write = workspace.write_module
    singleton = workspace.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem {}",
            "ObjectModel": "import QtQuick\nQtObject { property var values: [] }",
        },
    )
    write(
        directory,
        "Quickshell.Bluetooth",
        {
            "Bluetooth": singleton("property BluetoothAdapter defaultAdapter: null"),
            "BluetoothAdapter": """import QtQuick
import Quickshell
QtObject {
  property int state: BluetoothAdapterState.Disabled
  property bool enabled: false
  property bool discovering: false
  property ObjectModel devices: ObjectModel {}
}""",
            "BluetoothDevice": """import QtQuick
QtObject {
  property string name
  property bool paired: false
  property bool trusted: false
  property bool connected: false
  property bool pairing: false
  property bool blocked: false
  property bool batteryAvailable: false
  property real battery: 0
  property int state: BluetoothDeviceState.Disconnected
  property var events: []
  function connect() { events = events.concat(["connect:" + trusted]); }
  function disconnect() { events = events.concat(["disconnect"]); }
  function forget() { events = events.concat(["forget:" + trusted]); }
}""",
            "BluetoothAdapterState": "import QtQuick\nQtObject { enum State { Disabled, Enabled, Enabling, Disabling, Blocked } }",
            "BluetoothDeviceState": "import QtQuick\nQtObject { enum State { Disconnected, Connected, Disconnecting, Connecting } }",
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton("property int starts: 0"),
            "Process": """import QtQuick
Item {
  id: process
  property bool running: false
  property var command
  property QtObject stdout
  property QtObject stderr
  signal exited(int exitCode)
  Connections {
    target: process
    function onRunningChanged() { if (process.running) FixtureIo.starts++; }
  }
}""",
            "StdioCollector": 'import QtQuick\nQtObject { property string text: ""; signal streamFinished() }',
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Logger": singleton(
                "function i(...args) {}\nfunction d(...args) {}\nfunction w(...args) {}"
            ),
            "I18n": singleton("function tr(key) { return key; }"),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "ToastService": singleton(
                "property var notices: []; function showNotice(title, body, icon) { notices = notices.concat([body]); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.Networking",
        {
            "BluetoothService": (ROOT / TARGET).read_text(),
            "NetworkService": singleton(
                "property var requests: []; function setWifiEnabled(value) { requests = requests.concat([value]); }"
            ),
        },
    )
    (directory / "tst_bluetooth.qml").write_text(HARNESS)


def runtime(directory):
    stage_runtime(directory)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key
        not in (
            "HOME",
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
        )
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    with tempfile.TemporaryDirectory(prefix="noctalia-bluetooth-service-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        backup = directory / "settings.backup"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        digest = hashlib.sha256(original).hexdigest()
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
        try:
            globals()[args.mode](directory)
        finally:
            assert settings.read_bytes() == original, "real settings changed"
            print("SETTINGS_SHA256", digest)


if __name__ == "__main__":
    main()
