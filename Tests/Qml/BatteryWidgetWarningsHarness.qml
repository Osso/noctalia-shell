import QtQuick
import QtTest
import Quickshell.Services.UPower
import qs.Commons
import qs.BatteryWidget
import qs.Services.Networking
import qs.Services.UI

TestCase {
  id: testCase
  name: "BatteryWidgetWarnings"
  visible: true
  width: 400
  height: 100
  when: windowShown

  Component {
    id: widgetComponent
    Battery {
      widgetId: "Battery"
      section: "left"
      sectionWidgetIndex: 0
    }
  }

  function descendants(item) {
    let result = [item];
    for (const child of item.children || [])
      result = result.concat(descendants(child));
    return result;
  }

  function pill(widget) {
    const candidates = descendants(widget).filter(item => item.forceOpen !== undefined && item.density !== undefined && item.rotateText !== undefined);
    compare(candidates.length, 1);
    return candidates[0];
  }

  function visibleText(widget, text) {
    return descendants(widget).some(item => item.text === text && item.visible);
  }

  function configure(mode, nativePath) {
    Settings.data.bar.widgets.left = [
      {
        id: "Battery",
        displayMode: mode,
        warningThreshold: 20,
        deviceNativePath: nativePath || ""
      }
    ];
    Settings.dataChanged();
  }

  function test_production_widget() {
    configure("alwaysShow", "");
    const device = UPower.displayDevice;
    device.percentage = 0.65;
    device.state = UPowerDeviceState.Discharging;
    ToastService.warnings = [];
    const widget = createTemporaryObject(widgetComponent, testCase);
    verify(widget !== null);
    const barPill = pill(widget);
    compare(widget.isReady, false);
    compare(barPill.icon, "battery-exclamation");
    compare(barPill.text, "-");
    compare(ToastService.warnings.length, 0);
    tryCompare(widget, "initializationComplete", true);
    compare(widget.percent, 65);
    compare(widget.isReady, true);
    compare(barPill.icon, "battery-3");
    compare(barPill.forceOpen, true);
    verify(visibleText(widget, "65%"));
    verify(barPill.tooltipText.includes("7200 seconds"));
    verify(barPill.tooltipText.includes("12.50"));

    const thresholds = [
      {
        value: 0.90,
        icon: "battery-4"
      },
      {
        value: 0.50,
        icon: "battery-3"
      },
      {
        value: 0.25,
        icon: "battery-2"
      },
      {
        value: 0.21,
        icon: "battery-1"
      }
    ];
    for (const fixture of thresholds) {
      device.percentage = fixture.value;
      compare(barPill.icon, fixture.icon);
      compare(widget.isLowBattery, false);
    }
    device.percentage = 0.20;
    compare(widget.isLowBattery, true);
    compare(barPill.customBackgroundColor, NColor.mError);
    compare(barPill.customTextIconColor, NColor.mOnError);
    verify(visibleText(widget, "20%"));
    compare(ToastService.warnings.length, 1);
    compare(ToastService.warnings[0].title, "toast.battery.low");
    device.percentage = 0.18;
    compare(ToastService.warnings.length, 1);
    device.percentage = 0.25;
    compare(widget.hasNotifiedLowBattery, true);
    device.percentage = 0.26;
    compare(widget.hasNotifiedLowBattery, false);
    device.percentage = 0.15;
    compare(ToastService.warnings.length, 2);
    device.state = UPowerDeviceState.Charging;
    compare(widget.charging, true);
    compare(widget.hasNotifiedLowBattery, false);
    compare(widget.isLowBattery, false);
    compare(barPill.icon, "battery-charging");
    compare(barPill.customBackgroundColor, NColor.mPrimary);
    compare(barPill.customTextIconColor, NColor.mOnPrimary);
    compare(ToastService.warnings.length, 2);

    configure("alwaysHide", "");
    compare(barPill.forceClose, true);
    verify(!visibleText(widget, "15%"));
    compare(widget.implicitWidth, 32);
    configure("alwaysShow", "");
    device.ready = false;
    compare(widget.isReady, false);
    compare(barPill.icon, "battery-exclamation");
    compare(barPill.forceClose, true);
    verify(!visibleText(widget, "15%"));
    device.ready = true;
    device.isPresent = false;
    compare(widget.isDevicePresent, false);
    compare(barPill.tooltipText, "battery.no-battery-detected");
    device.isPresent = true;

    configure("alwaysShow", "bluetooth/aa:bb:cc:dd:ee:ff");
    compare(widget.battery, UPower.peripheral);
    compare(widget.bluetoothDevice, BluetoothService.headphones);
    compare(widget.percent, 43);
    compare(barPill.icon, "battery-2");
    BluetoothService.headphones.battery = 0.10;
    compare(widget.percent, 10);
    compare(widget.isLowBattery, true);
    compare(ToastService.warnings.length, 3);
    BluetoothService.headphones.connected = false;
    compare(widget.isDevicePresent, false);
    compare(barPill.forceClose, true);
    BluetoothService.headphones.connected = true;
    BluetoothService.headphones.batteryAvailable = false;
    compare(widget.percent, 65);
    configure("alwaysShow", "BAT0");
    compare(widget.battery, device);
    configure("alwaysShow", "missing");
    compare(widget.battery, device);
    compare(widget.isDevicePresent, false);
    console.log("BATTERY_WIDGET_BEHAVIOR_PASS");
  }
}
