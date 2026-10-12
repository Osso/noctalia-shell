import QtQuick
import QtTest
import Quickshell.Services.UPower
import qs.Commons
import qs.Services.Networking
import qs.Modules.Panels.Battery

TestCase {
  id: suite
  width: 800
  height: 600
  when: windowShown

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function configure(right, left, center) {
    Settings.data = {
      "ui": {
        "fontDefault": "Sans Serif",
        "fontFixed": "monospace",
        "fontDefaultScale": 1,
        "fontFixedScale": 1
      },
      "bar": {
        "widgets": {
          "right": right || [],
          "left": left || [],
          "center": center || []
        }
      }
    };
  }

  function createPanel() {
    const panel = createTemporaryObject(panelComponent, suite, {
      "width": 360,
      "height": 460
    });
    verify(panel !== null);
    tryVerify(() => panel.contentItem !== null);
    return panel;
  }

  function texts(panel) {
    return descendants(panel.contentItem).filter(item => item.text !== undefined).map(item => item.text);
  }

  function init() {
    configure();
    const display = UPower.displayDevice;
    display.ready = true;
    display.isPresent = true;
    display.percentage = 0.65;
    display.state = UPowerDeviceState.Discharging;
    display.changeRate = 12.5;
    display.healthSupported = true;
    display.healthPercentage = 85;
    display.timeToEmpty = 7200;
    display.timeToFull = 3600;
    mouse.ready = true;
    mouse.percentage = 0.42;
    mouse.model = "Mouse battery";
    UPower.devices.values = [display, mouse, replacement, linePower];
    BluetoothService.devices.values = [];
  }

  function test_positiveMagnitudePresentation_data() {
    return [
      {
        "tag": "charging",
        "state": UPowerDeviceState.Charging,
        "icon": "battery-charging",
        "timeKey": "battery.time-until-full",
        "seconds": 3600
      },
      {
        "tag": "discharging",
        "state": UPowerDeviceState.Discharging,
        "icon": "battery-3",
        "timeKey": "battery.time-left",
        "seconds": 7200
      }
    ];
  }

  function test_positiveMagnitudePresentation(data) {
    UPower.displayDevice.state = data.state;
    const panel = createPanel();
    compare(panel.battery.changeRate, 12.5);
    compare(panel.charging, data.state === UPowerDeviceState.Charging);
    compare(panel.percent, 65);
    compare(panel.deviceName, "");
    const expectedTime = data.timeKey + ':' + JSON.stringify({
      "time": data.seconds + " seconds"
    });
    compare(panel.timeText, expectedTime);
    verify(texts(panel).includes("65%"), "Percentage must come from panel, not Loader context");
    verify(texts(panel).includes(panel.timeText), "Time must come from panel, not Loader context");
    verify(texts(panel).includes('battery.health:{"percent":85}'));
    const icon = descendants(panel.contentItem).find(item => item.icon === panel.iconName);
    verify(icon !== undefined, "Panel icon must ignore Loader context");
    compare(icon.color, panel.charging ? NColor.mPrimary : NColor.mOnSurface);
    compare(panel.iconName, data.icon);
  }

  function test_selectionAndHotplug() {
    configure([
      {
        "id": "Battery",
        "deviceNativePath": "mouse0"
      }
    ], [
      {
        "id": "Battery",
        "deviceNativePath": "BAT0"
      }
    ]);
    const panel = createPanel();
    compare(panel.battery, mouse);
    compare(panel.panelTitle, "battery.panel-title - Mouse battery");
    compare(panel.percent, 42);
    UPower.devices.values = [UPower.displayDevice, replacement, linePower];
    tryCompare(panel, "battery", replacement);
    compare(panel.deviceName, "Replacement mouse");
    compare(panel.percent, 77);
    UPower.devices.values = [UPower.displayDevice, linePower];
    tryCompare(panel, "isDevicePresent", false);
    compare(panel.percent, -1);
    compare(panel.timeText, "battery.no-battery-detected");
    UPower.devices.values = [UPower.displayDevice, mouse, linePower];
    tryCompare(panel, "battery", mouse);
    compare(panel.isReady, true);
    configure([], [
      {
        "id": "Battery",
        "deviceNativePath": "mouse0"
      }
    ], [
      {
        "id": "Battery",
        "deviceNativePath": "BAT0"
      }
    ]);
    compare(panel.battery, mouse);
    configure([], [], [
      {
        "id": "Battery",
        "deviceNativePath": "BAT0"
      }
    ]);
    compare(panel.battery, UPower.displayDevice);
    configure([
      {
        "id": "Battery",
        "deviceNativePath": "AC"
      }
    ]);
    compare(panel.battery, UPower.displayDevice);
    compare(panel.isReady, false);
    configure([
      {
        "id": "Clock",
        "deviceNativePath": "mouse0"
      },
      {
        "id": "Battery"
      }
    ]);
    compare(panel.deviceNativePath, "");
    compare(panel.isReady, true);
  }

  function test_bluetoothAndReadiness() {
    mouse.nativePath = "bluetooth/aa:bb:cc:dd:ee:ff";
    configure([
      {
        "id": "Battery",
        "deviceNativePath": mouse.nativePath
      }
    ]);
    BluetoothService.devices.values = [headphones];
    const panel = createPanel();
    compare(panel.percent, 43);
    compare(panel.deviceName, "Headphones");
    headphones.connected = false;
    compare(panel.isReady, false);
    compare(panel.deviceName, "");
    headphones.connected = true;
    mouse.ready = false;
    compare(panel.isReady, false);
    mouse.ready = true;
    headphones.batteryAvailable = false;
    compare(panel.percent, 42);
    BluetoothService.devices.values = [];
    compare(panel.deviceName, "Mouse battery");
    mouse.model = "";
    compare(panel.deviceName, "");
  }

  function test_twoInstancesAndContentRecreation() {
    const first = createPanel();
    const second = createPanel();
    first.isPanelOpen = false;
    tryCompare(first, "contentItem", null);
    UPower.displayDevice.percentage = 0.25;
    first.isPanelOpen = true;
    tryVerify(() => first.contentItem !== null);
    verify(texts(first).includes("25%"));
    verify(texts(second).includes("25%"));
    const close = descendants(first.contentItem).find(item => item.icon === "close");
    verify(close !== undefined);
    close.clicked();
    compare(first.closeCount, 1);
    compare(second.closeCount, 0);
    compare(second.isPanelOpen, true);
    verify(texts(second).includes("25%"));
  }

  function test_absentIdleAndHealth() {
    const panel = createPanel();
    UPower.displayDevice.isPresent = false;
    compare(panel.isReady, false);
    compare(panel.timeText, "battery.no-battery-detected");
    UPower.displayDevice.isPresent = true;
    UPower.displayDevice.timeToEmpty = 0;
    compare(panel.timeText, "battery.idle");
    UPower.displayDevice.healthSupported = false;
    compare(panel.healthAvailable, false);
    compare(panel.healthPercent, -1);
    const health = descendants(panel.contentItem).find(item => item.text === 'battery.health:{"percent":-1}');
    verify(health !== undefined);
    compare(health.visible, false);
  }

  function cleanup() {
    mouse.nativePath = "mouse0";
    headphones.connected = true;
    headphones.batteryAvailable = true;
  }

  Component {
    id: panelComponent
    BatteryPanel {}
  }
  UPowerDevice {
    id: mouse
    nativePath: "mouse0"
    type: UPowerDeviceType.Mouse
    isLaptopBattery: false
    model: "Mouse battery"
    percentage: 0.42
  }
  UPowerDevice {
    id: replacement
    nativePath: "mouse0"
    type: UPowerDeviceType.Mouse
    isLaptopBattery: false
    model: "Replacement mouse"
    percentage: 0.77
  }
  UPowerDevice {
    id: linePower
    nativePath: "AC"
    type: UPowerDeviceType.LinePower
  }
  QtObject {
    id: headphones
    property string address: "AA:BB:CC:DD:EE:FF"
    property string name: "Headphones"
    property bool connected: true
    property bool batteryAvailable: true
    property real battery: 0.43
  }
}
