import QtQuick
import QtTest
import Quickshell.Services.UPower
import qs.Modules.Panels.Settings.Bar.WidgetSettings

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

  function createEditor(data) {
    const editor = createTemporaryObject(editorComponent, suite, {
      "widgetData": data || {},
      "widgetMetadata": {
        "displayMode": "onhover",
        "warningThreshold": 20
      }
    });
    verify(editor !== null);
    wait(30);
    return editor;
  }

  function combos(editor) {
    return descendants(editor).filter(item => typeof item.activateCurrentIndex === "function");
  }

  function init() {
    UPower.devices.values = [];
  }

  function test_defaults() {
    const editor = createEditor();
    compare(editor.saveSettings(), {
      "displayMode": "onhover",
      "warningThreshold": 20
    });
    compare(editor.deviceModel, [
      {
        "key": "",
        "name": "bar.widget-settings.battery.device.default"
      }
    ]);
    compare(combos(editor)[0].currentKey, "");
  }

  function test_savePreservesSourceAndUnknownFields() {
    const source = {
      "id": "Battery",
      "retained": 17,
      "displayMode": "alwaysHide",
      "warningThreshold": 35,
      "deviceNativePath": "BAT1"
    };
    const original = JSON.stringify(source);
    const editor = createEditor(source);
    compare(editor.saveSettings(), source);
    editor.valueDeviceNativePath = "";
    const saved = editor.saveSettings();
    verify(saved.deviceNativePath === undefined);
    compare(saved.id, "Battery");
    compare(saved.retained, 17);
    saved.retained = 18;
    compare(JSON.stringify(source), original);
  }

  function test_controlsSaveSelectedValuesAndClampThreshold() {
    UPower.devices.values = [battery];
    const editor = createEditor();
    const controls = combos(editor);
    controls[0].activateCurrentIndex(1);
    controls[1].activateCurrentIndex(1);
    const spin = descendants(editor).find(item => typeof item.changeValue === "function");
    verify(spin !== undefined);
    compare(spin.minimum, 5);
    compare(spin.maximum, 50);
    compare(spin.suffix, "%");
    spin.changeValue(1, 100);
    compare(editor.saveSettings(), {
      "displayMode": "alwaysShow",
      "warningThreshold": 50,
      "deviceNativePath": "BAT0"
    });
    spin.changeValue(-1, 100);
    compare(editor.saveSettings().warningThreshold, 5);
  }

  function test_hotplugSameCountAndManualRefresh() {
    UPower.devices.values = [battery];
    const editor = createEditor({
      "deviceNativePath": "BAT0"
    });
    const combo = combos(editor)[0];
    UPower.devices.values = [mouse];
    tryCompare(editor, "_deviceCount", 1);
    compare(editor.deviceModel[1], {
      "key": "mouse0",
      "name": "mouse0"
    });
    compare(combo.currentKey, "BAT0");
    UPower.devices.values = [battery, mouse, linePower, unnamed];
    tryCompare(editor, "_deviceCount", 4);
    compare(editor.deviceModel.length, 4);
    compare(editor.deviceModel[3], {
      "key": "",
      "name": "Unknown"
    });
    battery.model = "Renamed battery";
    const refresh = descendants(editor).find(item => item.icon === "refresh" && item.clicked !== undefined);
    verify(refresh !== undefined);
    refresh.clicked();
    compare(editor.deviceModel[1], {
      "key": "BAT0",
      "name": "Renamed battery"
    });
    compare(combo.currentKey, "BAT0");
    UPower.devices.values = [];
    tryCompare(editor, "_deviceCount", 0);
    compare(editor.deviceModel.length, 1);
    compare(editor.saveSettings().deviceNativePath, "BAT0");
  }

  function test_positiveMagnitudeDevices_data() {
    return [
      {
        "tag": "charging",
        "state": UPowerDeviceState.Charging
      },
      {
        "tag": "discharging",
        "state": UPowerDeviceState.Discharging
      }
    ];
  }

  function test_positiveMagnitudeDevices(data) {
    battery.state = data.state;
    battery.changeRate = 12.5;
    UPower.devices.values = [battery, linePower];
    const editor = createEditor({
      "deviceNativePath": "BAT0"
    });
    compare(editor.deviceModel, [
      {
        "key": "",
        "name": "bar.widget-settings.battery.device.default"
      },
      {
        "key": "BAT0",
        "name": "Laptop battery"
      }
    ]);
    compare(combos(editor)[0].currentKey, "BAT0");
    compare(editor.saveSettings().deviceNativePath, "BAT0");
  }

  function cleanup() {
    battery.model = "Laptop battery";
    UPower.devices.values = [];
  }

  Component {
    id: editorComponent
    BatterySettings {
      width: 800
    }
  }

  QtObject {
    id: battery
    property int type: UPowerDeviceType.Battery
    property string nativePath: "BAT0"
    property string model: "Laptop battery"
    property int state: UPowerDeviceState.Discharging
    property real changeRate: 12.5
  }

  QtObject {
    id: mouse
    property int type: UPowerDeviceType.Mouse
    property string nativePath: "mouse0"
    property string model: ""
  }

  QtObject {
    id: linePower
    property int type: UPowerDeviceType.LinePower
    property string nativePath: "AC"
    property string model: "Adapter"
  }

  QtObject {
    id: unnamed
    property int type: UPowerDeviceType.Mouse
    property string nativePath: ""
    property string model: ""
  }
}
