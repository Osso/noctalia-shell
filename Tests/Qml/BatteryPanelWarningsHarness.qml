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
            items = items.concat(suite.descendants(child));
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
        const panel = suite.createTemporaryObject(panelComponent, suite, {
            "width": 360,
            "height": 460
        });
        suite.verify(panel !== null);
        suite.tryVerify(() => panel.contentItem !== null);
        return panel;
    }

    function texts(panel) {
        return suite.descendants(panel.contentItem).filter(item => item.text !== undefined).map(item => item.text);
    }

    function init() {
        suite.configure();
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
        const panel = suite.createPanel();
        suite.compare(panel.battery.changeRate, 12.5);
        suite.compare(panel.charging, data.state === UPowerDeviceState.Charging);
        suite.compare(panel.percent, 65);
        suite.compare(panel.deviceName, "");
        const expectedTime = data.timeKey + ':' + JSON.stringify({
            "time": data.seconds + " seconds"
        });
        suite.compare(panel.timeText, expectedTime);
        suite.verify(suite.texts(panel).includes("65%"), "Percentage must come from panel, not Loader context");
        suite.verify(suite.texts(panel).includes(panel.timeText), "Time must come from panel, not Loader context");
        suite.verify(suite.texts(panel).includes('battery.health:{"percent":85}'));
        const icon = suite.descendants(panel.contentItem).find(item => item.icon === panel.iconName);
        suite.verify(icon !== undefined, "Panel icon must ignore Loader context");
        suite.compare(icon.color, panel.charging ? NColor.mPrimary : NColor.mOnSurface);
        suite.compare(panel.iconName, data.icon);
    }

    function test_selectionAndHotplug() {
        suite.configure([
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
        const panel = suite.createPanel();
        suite.compare(panel.battery, mouse);
        suite.compare(panel.panelTitle, "battery.panel-title - Mouse battery");
        suite.compare(panel.percent, 42);
        UPower.devices.values = [UPower.displayDevice, replacement, linePower];
        suite.tryCompare(panel, "battery", replacement);
        suite.compare(panel.deviceName, "Replacement mouse");
        suite.compare(panel.percent, 77);
        UPower.devices.values = [UPower.displayDevice, linePower];
        suite.tryCompare(panel, "isDevicePresent", false);
        suite.compare(panel.percent, -1);
        suite.compare(panel.timeText, "battery.no-battery-detected");
        UPower.devices.values = [UPower.displayDevice, mouse, linePower];
        suite.tryCompare(panel, "battery", mouse);
        suite.compare(panel.isReady, true);
        suite.configure([], [
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
        suite.compare(panel.battery, mouse);
        suite.configure([], [], [
            {
                "id": "Battery",
                "deviceNativePath": "BAT0"
            }
        ]);
        suite.compare(panel.battery, UPower.displayDevice);
        suite.configure([
            {
                "id": "Battery",
                "deviceNativePath": "AC"
            }
        ]);
        suite.compare(panel.battery, UPower.displayDevice);
        suite.compare(panel.isReady, false);
        suite.configure([
            {
                "id": "Clock",
                "deviceNativePath": "mouse0"
            },
            {
                "id": "Battery"
            }
        ]);
        suite.compare(panel.deviceNativePath, "");
        suite.compare(panel.isReady, true);
    }

    function test_bluetoothAndReadiness() {
        mouse.nativePath = "bluetooth/aa:bb:cc:dd:ee:ff";
        suite.configure([
            {
                "id": "Battery",
                "deviceNativePath": mouse.nativePath
            }
        ]);
        BluetoothService.devices.values = [headphones];
        const panel = suite.createPanel();
        suite.compare(panel.percent, 43);
        suite.compare(panel.deviceName, "Headphones");
        headphones.connected = false;
        suite.compare(panel.isReady, false);
        suite.compare(panel.deviceName, "");
        headphones.connected = true;
        mouse.ready = false;
        suite.compare(panel.isReady, false);
        mouse.ready = true;
        headphones.batteryAvailable = false;
        suite.compare(panel.percent, 42);
        BluetoothService.devices.values = [];
        suite.compare(panel.deviceName, "Mouse battery");
        mouse.model = "";
        suite.compare(panel.deviceName, "");
    }

    function test_twoInstancesAndContentRecreation() {
        const first = suite.createPanel();
        const second = suite.createPanel();
        first.isPanelOpen = false;
        suite.tryCompare(first, "contentItem", null);
        UPower.displayDevice.percentage = 0.25;
        first.isPanelOpen = true;
        suite.tryVerify(() => first.contentItem !== null);
        suite.verify(suite.texts(first).includes("25%"));
        suite.verify(suite.texts(second).includes("25%"));
        const close = suite.descendants(first.contentItem).find(item => item.icon === "close");
        suite.verify(close !== undefined);
        close.clicked();
        suite.compare(first.closeCount, 1);
        suite.compare(second.closeCount, 0);
        suite.compare(second.isPanelOpen, true);
        suite.verify(suite.texts(second).includes("25%"));
    }

    function test_absentIdleAndHealth() {
        const panel = suite.createPanel();
        UPower.displayDevice.isPresent = false;
        suite.compare(panel.isReady, false);
        suite.compare(panel.timeText, "battery.no-battery-detected");
        UPower.displayDevice.isPresent = true;
        UPower.displayDevice.timeToEmpty = 0;
        suite.compare(panel.timeText, "battery.idle");
        UPower.displayDevice.healthSupported = false;
        suite.compare(panel.healthAvailable, false);
        suite.compare(panel.healthPercent, -1);
        const health = suite.descendants(panel.contentItem).find(item => item.text === 'battery.health:{"percent":-1}');
        suite.verify(health !== undefined);
        suite.compare(health.visible, false);
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
