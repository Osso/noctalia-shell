#!/usr/bin/env python3
"""Exercise the unchanged device list offscreen, without host services or settings.

Presentation/service fixtures isolate bootstrap; Qt's layouts, Repeater and
Quickshell's BluetoothDevice type remain real. Null device slots exercise the
production delegate's null handling without contacting Bluetooth hardware.
"""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "Modules/Panels/Bluetooth/BluetoothDevicesList.qml"

HARNESS = """import QtQuick
import Quickshell
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


def stage_list(directory):
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
  function canConnect(device) { return false; }
  function canDisconnect(device) { return false; }
  function isDeviceBusy(device) { return false; }
  function getDeviceIcon(device) { return "bluetooth"; }
  function getStatusString(device) { return ""; }
  function getSignalStrength(device) { return ""; }
  function getSignalIcon(device) { return ""; }
  function getBattery(device) { return ""; }""",
    )
    (directory / "shell.qml").write_text(HARNESS)


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


def main():
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
        stage_list(directory)
        try:
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                env=isolate_environment(directory),
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
