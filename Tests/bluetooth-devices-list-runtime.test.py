#!/usr/bin/env python3
"""Exercise the unchanged device list offscreen, without host services or settings.

Presentation/service fixtures isolate bootstrap; Qt's layouts, Repeater and
Quickshell's BluetoothDevice type remain real. Null device slots exercise the
production delegate's null handling without contacting Bluetooth hardware.
Concrete devices redirect only the Bluetooth import to an inert QML module:
real device objects are uncreatable and obtaining them would require a BlueZ bus.
Both modes retain the production component body; null slots use the installed type.
Installed qmltypes constrain the inert device fixture's properties. A hypothetical
signalStrength extension must not add UI or alter the normal no-signal layout.
Neither harness creates a window.
"""

import argparse
from contextlib import contextmanager
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
import QtQuick.Layouts
import qs.Modules.Panels.Bluetooth
import qs.Services.Networking

ShellRoot {
  BluetoothDevice { id: headphones; name: "Studio Headphones"; paired: true; connected: true; state: BluetoothDeviceState.Connected; batteryAvailable: true; battery: 0.75; property int signalStrength: 85 }
  BluetoothDevice { id: keyboard; name: "Desk Keyboard"; paired: true }
  BluetoothDevice { id: phone; name: "Pocket Phone" }
  property var callerModel: [headphones, keyboard, phone]
  BluetoothDevicesList { id: supplied; width: 480; height: Layout.preferredHeight; model: callerModel; tooltipText: "Device action" }

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

  function assertPresentation(index, expectedTexts) {
    const row = rowAt(index);
    const layout = row.children[0];
    const details = layout.children[1];
    const displayed = Array.from(details.children).filter(child => child.visible);
    require(displayed.length === expectedTexts.length, "unexpected visible detail row for " + row.modelData.name);
    for (let i = 0; i < displayed.length; ++i)
      require(displayed[i].text === expectedTexts[i], "wrong device detail " + i);
    const textHeight = displayed.reduce((height, child) => height + child.implicitHeight, 0);
    const expectedHeight = textHeight + (displayed.length - 1) * 2;
    require(Math.abs(details.implicitHeight - expectedHeight) < 0.01, "detail layout gained extra height");
    const contentHeight = Math.max(layout.children[0].implicitHeight, expectedHeight);
    require(Math.abs(row.height - (contentHeight + 16)) < 0.01, "device row geometry changed");
    require(row.width === supplied.width - 16, "device row width changed");
    require(layout.x === 8 && layout.y === 8, "device content margins changed");
  }

  function assertStatePresentation() {
    const row = rowAt(2);
    const details = row.children[0].children[1];
    const button = row.children[0].children[3];
    keyboard.state = BluetoothDeviceState.Connecting;
    require(row.deviceConnecting && !button.visible, "connecting action must stay hidden");
    require(details.children[1].text === "Connecting" && details.children[1].visible, "connecting status lost");
    keyboard.state = BluetoothDeviceState.Connected;
    keyboard.pairing = true;
    require(row.devicePairing && button.text === "bluetooth.panel.pairing", "pairing state lost");
    keyboard.pairing = false;
    keyboard.blocked = true;
    require(row.deviceBlocked && button.text === "bluetooth.panel.blocked", "blocked state lost");
    keyboard.blocked = false;
    require(button.visible && button.text === "bluetooth.panel.disconnect", "connected action not restored");
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
        assertPresentation(0, ["Studio Headphones", "75%"]);
        assertPresentation(1, ["Desk Keyboard"]);
        assertPresentation(2, ["Pocket Phone"]);
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
        assertStatePresentation();
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


def assert_installed_device_contract():
    metadata = Path(
        "/usr/lib/qt6/qml/Quickshell/Bluetooth/quickshell-bluetooth.qmltypes"
    ).read_text()
    components = re.findall(r"^    Component \{(.*?)^    \}", metadata, re.M | re.S)
    device = next(
        component
        for component in components
        if re.search(
            r'^        name: "qs::bluetooth::BluetoothDevice"$', component, re.M
        )
    )
    properties = dict(
        re.findall(r'Property \{\s+name: "([^"]+)"\s+type: "([^"]+)"', device)
    )
    expected = {
        "name": "QString",
        "deviceName": "QString",
        "pairing": "bool",
        "blocked": "bool",
        "paired": "bool",
        "connected": "bool",
        "state": "BluetoothDeviceState::Enum",
        "batteryAvailable": "bool",
        "battery": "double",
    }
    assert {name: properties.get(name) for name in expected} == expected, properties
    assert "signalStrength" not in properties, properties
    print("BLUETOOTH_DEVICE_CONTRACT_PASS", properties)


@contextmanager
def fixture_settings(directory):
    home = directory / "fixture/home"
    settings = home / ".config/noctalia/settings.json"
    settings.parent.mkdir(parents=True, mode=0o700)
    original = (ROOT / "Assets/settings-default.json").read_bytes()
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        path.touch(mode=0o600)
        path.write_bytes(original)
        assert path.read_bytes() == original, "fixture copy differs"
    try:
        yield
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"


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
  function getStatusString(device) {
    if (!device) return "";
    if (device.state === 3) return "Connecting";
    if (device.pairing) return "Pairing";
    if (device.blocked) return "Blocked";
    return "";
  }
  function getSignalStrength(device) { return "Excellent"; }
  function getSignalIcon(device) { return "antenna"; }
  function getBattery(device) { return device ? Math.round(device.battery * 100) + "%" : ""; }""",
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
    home = directory / "fixture/home"
    environment.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        NOCTALIA_CONFIG_DIR=str(home / ".config/noctalia"),
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
    assert diagnostics == ["unresolved-type"], diagnostics
    assert 'Type "BluetoothDeviceState::Enum"' in output, output
    assert result.returncode == 0, result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("runtime", "devices", "lint"), nargs="?", default="runtime"
    )
    args = parser.parse_args()
    assert_installed_device_contract()
    with tempfile.TemporaryDirectory(prefix="noctalia-bluetooth-list-") as temporary:
        directory = Path(temporary)
        with fixture_settings(directory):
            if args.mode == "lint":
                lint(directory)
                return
            stage_list(directory, concrete=args.mode == "devices")
            environment = isolate_environment(directory)
            if args.mode == "devices":
                environment["QML_IMPORT_PATH"] = str(directory / "imports")
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
            )
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
