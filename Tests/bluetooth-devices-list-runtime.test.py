#!/usr/bin/env python3
"""Exercise the unchanged device list offscreen, without host services or settings.

Presentation/service fixtures isolate bootstrap; Qt's layouts, Repeater and
Quickshell's BluetoothDevice type remain real. Null device slots exercise the
production delegate's null handling without contacting Bluetooth hardware.
Concrete devices redirect only the Bluetooth import to an inert QML module:
real device objects are uncreatable and obtaining them would require a BlueZ bus.
Both modes retain the production component body; null slots use the installed type.
"""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "Modules/Panels/Bluetooth/BluetoothDevicesList.qml"

HARNESS = """import QtQuick
import Quickshell
import Quickshell.Bluetooth
import qs.Modules.Panels.Bluetooth

ShellRoot {
  property var callerModel: [null, null]
  BluetoothDevicesList { id: defaults; visible: false }
  BluetoothDevicesList { id: supplied; visible: false; model: callerModel }

  function require(condition, message) {
    if (!condition) throw new Error(message);
  }

  function assertRows(list, expected) {
    const column = list.children[0];
    const repeater = column.children[column.children.length - 1];
    require(repeater.count === expected, "expected " + expected + " rows, got " + repeater.count);
    for (let i = 0; i < expected; ++i)
      require(repeater.itemAt(i) !== null, "missing device row " + i);
    require(repeater.itemAt(expected) === null, "unexpected extra device row");
    require(column.children.length === expected + 2, "unexpected child rows");
  }

  Timer {
    interval: 100
    running: true
    onTriggered: {
      try {
        require(BluetoothDeviceState.Disconnected === 0 && BluetoothDeviceState.Connected === 1
                && BluetoothDeviceState.Disconnecting === 2 && BluetoothDeviceState.Connecting === 3,
                "installed Bluetooth state enum unavailable");
        require(Array.isArray(defaults.model), "default model must be an array; got " + defaults.model);
        require(defaults.model.length === 0, "default model must contain zero devices");
        assertRows(defaults, 0);
        require(supplied.model === callerModel, "caller-provided model was replaced");
        assertRows(supplied, 2);
        callerModel = [];
        require(supplied.model === callerModel, "caller model replacement was ignored");
        assertRows(supplied, 0);
        console.log("BLUETOOTH_DEVICES_LIST_PASS");
        Qt.quit();
      } catch (error) {
        console.error("BLUETOOTH_DEVICES_LIST_FAIL: " + error.message);
        Qt.exit(1);
      }
    }
  }
}
"""

DEVICE_HARNESS = """import QtQuick
import Quickshell
import Quickshell.Bluetooth
import qs.Modules.Panels.Bluetooth
import qs.Services.Networking

ShellRoot {
  BluetoothDevice { id: headphones; name: "Studio Headphones"; paired: true; connected: true; state: BluetoothDeviceState.Connected; batteryAvailable: true; battery: 0.75 }
  BluetoothDevice { id: keyboard; name: "Desk Keyboard"; paired: true }
  BluetoothDevice { id: phone; name: "Pocket Phone" }
  property var callerModel: [headphones, keyboard, phone]
  BluetoothDevicesList { id: supplied; model: callerModel; tooltipText: "Device action" }

  function require(condition, message) {
    if (!condition) throw new Error(message);
  }

  function rowAt(index) {
    const column = supplied.children[0];
    const repeater = column.children[column.children.length - 1];
    require(repeater.count === callerModel.length, "wrong row count after replacement");
    return repeater.itemAt(index);
  }

  function assertRow(index, expected, label) {
    const row = rowAt(index);
    const layout = row.children[0];
    const name = layout.children[1].children[0];
    const button = layout.children[3];
    require(row.modelData === expected, "wrong device at row " + index);
    require(row.index === index, "delegate index injection changed");
    require(name.text === expected.name, "wrong visible device name");
    require(button.text === "bluetooth.panel." + label, "wrong action label");
    require(button.enabled && button.visible, "idle device action unavailable");
    require(button.tooltipText === supplied.tooltipText, "owner tooltip lost");
    return button;
  }

  function assertRequest(index, action, expected) {
    const request = BluetoothService.requests[index];
    require(request.action === action && request.device === expected, "action targeted wrong device");
  }

  Timer {
    interval: 100
    running: true
    onTriggered: {
      try {
        const disconnect = assertRow(0, headphones, "disconnect");
        disconnect.clicked();
        assertRequest(0, "disconnect", headphones);
        assertRow(1, keyboard, "connect").clicked();
        assertRequest(1, "connect", keyboard);
        assertRow(2, phone, "connect").rightClicked();
        assertRequest(2, "forget", phone);
        callerModel = [phone, headphones, keyboard];
        supplied.tooltipText = "Reordered device action";
        assertRow(0, phone, "connect").clicked();
        assertRequest(3, "connect", phone);
        assertRow(1, headphones, "disconnect").rightClicked();
        assertRequest(4, "forget", headphones);
        assertRow(2, keyboard, "connect");
        keyboard.connected = true;
        keyboard.state = BluetoothDeviceState.Connected;
        assertRow(2, keyboard, "disconnect").clicked();
        assertRequest(5, "disconnect", keyboard);
        require(BluetoothService.requests.length === 6, "unexpected action dispatch");
        callerModel = [];
        const column = supplied.children[0];
        require(column.children[column.children.length - 1].count === 0, "rows survived model clear");
        console.log("BLUETOOTH_DEVICES_LIST_PASS");
        Qt.quit();
      } catch (error) {
        console.error("BLUETOOTH_DEVICES_LIST_FAIL: " + error.message);
        Qt.exit(1);
      }
    }
  }
}
"""

WIDGETS = {
    "NBox": "import QtQuick\nRectangle {}\n",
    "NText": "import QtQuick\nText { property real pointSize: 12; font.pointSize: pointSize }\n",
    "NIcon": 'import QtQuick\nText { property string icon: ""; property real pointSize: 12 }\n',
    "NButton": """import QtQuick
Item {
  property bool hovered: false
  property bool outlined: false
  property real fontSize: 12
  property int fontWeight: 500
  property color backgroundColor: "transparent"
  property string tooltipText: ""
  property string text: ""
  property var icon
  signal clicked()
  signal rightClicked()
}
""",
}


def write_singleton(directory, name, body):
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"
    )


def stage_list(directory, concrete=False):
    commons = directory / "Commons"
    widgets = directory / "Widgets"
    bluetooth = directory / "Modules/Panels/Bluetooth"
    networking = directory / "Services/Networking"
    for path in (commons, widgets, bluetooth, networking):
        path.mkdir(parents=True, mode=0o700)
    shutil.copyfile(TARGET, bluetooth / TARGET.name)
    for name, source in WIDGETS.items():
        (widgets / f"{name}.qml").write_text(source)
    style = {
        "marginM": 8,
        "marginXXS": 2,
        "marginXS": 3,
        "radiusM": 12,
        "borderS": 1,
        "fontSizeS": 10,
        "fontSizeXS": 9,
        "fontSizeM": 12,
        "fontSizeXXL": 22,
        "fontWeightBold": 700,
        "fontWeightMedium": 500,
    }
    write_singleton(
        commons,
        "Style",
        "\n".join(
            f"  readonly property real {name}: {value}" for name, value in style.items()
        ),
    )
    write_singleton(
        commons,
        "NColor",
        "\n".join(
            f'  readonly property color {name}: "#808080"'
            for name in (
                "mSecondary",
                "mPrimary",
                "mError",
                "mOnSurface",
                "mSurface",
                "mOutline",
                "mOnSurfaceVariant",
            )
        ),
    )
    write_singleton(commons, "I18n", "  function tr(key) { return key; }")
    write_singleton(
        networking,
        "BluetoothService",
        """  readonly property var adapter: ({enabled: true})
  property var requests: []
  function canConnect(device) { return device !== null && !device.connected; }
  function canDisconnect(device) { return device !== null && device.connected; }
  function connectDeviceWithTrust(device) { requests = requests.concat([{action: "connect", device: device}]); }
  function disconnectDevice(device) { requests = requests.concat([{action: "disconnect", device: device}]); }
  function forgetDevice(device) { requests = requests.concat([{action: "forget", device: device}]); }
  function isDeviceBusy(device) { return false; }
  function getDeviceIcon(device) { return "bluetooth"; }
  function getStatusString(device) { return ""; }
  function getSignalStrength(device) { return ""; }
  function getSignalIcon(device) { return ""; }
  function getBattery(device) { return ""; }""",
    )
    if concrete:
        staged = bluetooth / TARGET.name
        staged.write_text(
            staged.read_text().replace(
                "import Quickshell.Bluetooth", "import TestBluetooth"
            )
        )
        module = directory / "imports/TestBluetooth"
        module.mkdir(parents=True)
        (module / "qmldir").write_text(
            "module TestBluetooth\nBluetoothDevice 1.0 BluetoothDevice.qml\n"
            "singleton BluetoothDeviceState 1.0 BluetoothDeviceState.qml\n"
        )
        (module / "BluetoothDevice.qml").write_text("""import QtQuick
QtObject {
  property string name: ""
  property string deviceName: ""
  property bool pairing: false
  property bool blocked: false
  property bool paired: false
  property bool connected: false
  property int state: 0
  property bool batteryAvailable: false
  property real battery: 0
}
""")
        write_singleton(
            module,
            "BluetoothDeviceState",
            """enum Enum {
    Disconnected, Connected, Disconnecting, Connecting
  }""",
        )
    harness = (
        DEVICE_HARNESS.replace("import Quickshell.Bluetooth", "import TestBluetooth")
        if concrete
        else HARNESS
    )
    (directory / "shell.qml").write_text(harness)


def isolate_environment(directory):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_", "QS_"))
        and key
        not in (
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
            "HOME",
        )
    }
    for variable, name in {
        "HOME": "home",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "XDG_DATA_HOME": "data",
        "XDG_STATE_HOME": "state",
        "XDG_RUNTIME_DIR": "runtime",
        "NOCTALIA_CONFIG_DIR": "noctalia-config",
        "NOCTALIA_CACHE_DIR": "noctalia-cache",
    }.items():
        path = directory / name
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/noctalia-test-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/noctalia-test-system",
    )
    return environment


def lint(directory):
    spec = importlib.util.spec_from_file_location(
        "bluetooth_lint_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.stage_modules(directory)
    target = directory / "qs" / TARGET.relative_to(ROOT)
    result = subprocess.run(
        ["/usr/lib/qt6/bin/qmllint", "-I", str(directory), str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    diagnostics = re.findall(r"^Warning:.*\[([^]]+)\]$", output, re.M)
    print("BLUETOOTH_LIST_LINT_DIAGNOSTICS", diagnostics)
    # Keep installed API gaps visible; no warning options or suppression applied.
    assert sorted(diagnostics) == [
        "missing-property",
        "missing-property",
        "unresolved-type",
    ], diagnostics
    assert output.count('Member "signalStrength" not found') == 2, output
    assert 'Type "BluetoothDeviceState::Enum"' in output, output
    assert result.returncode == 0, result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("runtime", "devices", "lint"), nargs="?", default="runtime"
    )
    args = parser.parse_args()
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    with tempfile.TemporaryDirectory(prefix="noctalia-bluetooth-list-") as temporary:
        directory = Path(temporary)
        if original is not None:
            backup = directory / "settings.backup.json"
            backup.touch(mode=0o600)
            backup.write_bytes(original)
            assert (
                hashlib.sha256(backup.read_bytes()).digest()
                == hashlib.sha256(original).digest()
            )
        if args.mode == "lint":
            try:
                lint(directory)
            finally:
                if original is not None:
                    assert settings.read_bytes() == original, "real settings changed"
            return
        stage_list(directory, concrete=args.mode == "devices")
        environment = isolate_environment(directory)
        if args.mode == "devices":
            environment["QML_IMPORT_PATH"] = str(directory / "imports")
        try:
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            if original is not None:
                assert settings.read_bytes() == original, "real settings changed"
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, (
            f"device list runtime failed (exit {result.returncode})"
        )
        assert "BLUETOOTH_DEVICES_LIST_PASS" in output, (
            "device list assertions did not finish"
        )
        assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
            output
        )


if __name__ == "__main__":
    main()
