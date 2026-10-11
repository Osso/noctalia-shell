import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.UPower
import qs.Commons
import qs.Modules.Bar.Extras
import qs.Services.Hardware
import qs.Services.Networking
import qs.Services.UI
import qs.Widgets

Item {
  id: root

  property ShellScreen screen

  // Widget properties passed from Bar.qml for per-instance settings
  property string widgetId: ""
  property string section: ""
  property int sectionWidgetIndex: -1
  property int sectionWidgetsCount: 0

  property var widgetMetadata: BarWidgetRegistry.widgetMetadata[widgetId]
  property var widgetSettings: {
    if (section && sectionWidgetIndex >= 0) {
      var widgets = Settings.data.bar.widgets[section];
      if (widgets && sectionWidgetIndex < widgets.length) {
        return widgets[sectionWidgetIndex];
      }
    }
    return {};
  }

  readonly property bool isBarVertical: Settings.data.bar.position === "left" || Settings.data.bar.position === "right"
  readonly property string displayMode: widgetSettings.displayMode !== undefined ? widgetSettings.displayMode : widgetMetadata.displayMode
  readonly property real warningThreshold: widgetSettings.warningThreshold !== undefined ? widgetSettings.warningThreshold : widgetMetadata.warningThreshold
  // Only show low battery warning if device is ready (prevents false positive during initialization)
  readonly property bool isLowBattery: isReady && !charging && percent <= warningThreshold

  // Test mode
  readonly property bool testMode: false
  readonly property int testPercent: 35
  readonly property bool testCharging: false

  readonly property string deviceNativePath: widgetSettings.deviceNativePath || ""

  function findBatteryDevice(nativePath) {
    if (!nativePath || !UPower.devices) {
      return UPower.displayDevice;
    }
    var devices = UPower.devices.values || [];
    for (var i = 0; i < devices.length; i++) {
      var device = devices[i];
      if (device && device.nativePath === nativePath && device.type !== UPowerDeviceType.LinePower && device.percentage !== undefined) {
        return device;
      }
    }
    return UPower.displayDevice;
  }

  function findBluetoothDevice(nativePath) {
    if (!nativePath || !BluetoothService.devices) {
      return null;
    }
    var macMatch = nativePath.match(/([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})/);
    if (!macMatch) {
      return null;
    }
    var macAddress = macMatch[1].toUpperCase();
    var devices = BluetoothService.devices.values || [];
    for (var i = 0; i < devices.length; i++) {
      var device = devices[i];
      if (device && device.address && device.address.toUpperCase() === macAddress) {
        return device;
      }
    }
    return null;
  }

  readonly property UPowerDevice battery: findBatteryDevice(deviceNativePath)
  readonly property var bluetoothDevice: deviceNativePath ? findBluetoothDevice(deviceNativePath) : null
  readonly property bool hasBluetoothBattery: bluetoothDevice && bluetoothDevice.batteryAvailable && bluetoothDevice.battery !== undefined
  readonly property bool isBluetoothConnected: bluetoothDevice && bluetoothDevice.connected === true

  property bool initializationComplete: false
  Timer {
    interval: 500
    running: true
    onTriggered: root.initializationComplete = true
  }

  readonly property bool isDevicePresent: {
    if (testMode)
      return true;
    if (deviceNativePath) {
      if (bluetoothDevice) {
        return isBluetoothConnected;
      }
      if (battery && battery.nativePath === deviceNativePath) {
        if (battery.type === UPowerDeviceType.Battery && battery.isPresent !== undefined) {
          return battery.isPresent;
        }
        return battery.ready && battery.percentage !== undefined && (battery.percentage > 0 || battery.state === UPowerDeviceState.Charging);
      }
      return false;
    }
    if (battery) {
      return (battery.type === UPowerDeviceType.Battery && battery.isPresent !== undefined) ? battery.isPresent : (battery.ready && battery.percentage !== undefined);
    }
    return false;
  }

  readonly property bool isReady: testMode ? true : (initializationComplete && battery && battery.ready && isDevicePresent && (battery.percentage !== undefined || hasBluetoothBattery))
  readonly property real percent: testMode ? testPercent : (isReady ? (hasBluetoothBattery ? (bluetoothDevice.battery * 100) : (battery.percentage * 100)) : 0)
  readonly property bool charging: testMode ? testCharging : (isReady ? battery.state === UPowerDeviceState.Charging : false)
  property bool hasNotifiedLowBattery: false

  implicitWidth: pill.width
  implicitHeight: pill.height

  function maybeNotify(currentPercent, isCharging) {
    if (!isCharging && !hasNotifiedLowBattery && currentPercent <= warningThreshold) {
      hasNotifiedLowBattery = true;
      ToastService.showWarning(I18n.tr("toast.battery.low"), I18n.tr("toast.battery.low-desc", {
        "percent": Math.round(currentPercent)
      }));
    } else if (hasNotifiedLowBattery && (isCharging || currentPercent > warningThreshold + 5)) {
      hasNotifiedLowBattery = false;
    }
  }

  function getCurrentPercent() {
    return hasBluetoothBattery ? (bluetoothDevice.battery * 100) : (battery ? battery.percentage * 100 : 0);
  }

  Connections {
    target: root.battery
    function onPercentageChanged() {
      if (root.battery) {
        root.maybeNotify(root.getCurrentPercent(), root.battery.state === UPowerDeviceState.Charging);
      }
    }
    function onStateChanged() {
      if (root.battery) {
        if (root.battery.state === UPowerDeviceState.Charging) {
          root.hasNotifiedLowBattery = false;
        }
        root.maybeNotify(root.getCurrentPercent(), root.battery.state === UPowerDeviceState.Charging);
      }
    }
  }

  Connections {
    target: root.bluetoothDevice
    function onBatteryChanged() {
      if (root.bluetoothDevice && root.hasBluetoothBattery) {
        root.maybeNotify(root.bluetoothDevice.battery * 100, root.battery ? root.battery.state === UPowerDeviceState.Charging : false);
      }
    }
  }

  NPopupContextMenu {
    id: contextMenu

    model: [
      {
        "label": I18n.tr("context-menu.widget-settings"),
        "action": "widget-settings",
        "icon": "settings"
      },
    ]

    onTriggered: action => {
      var popupMenuWindow = PanelService.getPopupMenuWindow(screen);
      if (popupMenuWindow) {
        popupMenuWindow.close();
      }

      if (action === "widget-settings") {
        BarService.openWidgetSettings(screen, root.section, root.sectionWidgetIndex, root.widgetId, root.widgetSettings);
      }
    }
  }

  BarPill {
    id: pill

    screen: root.screen
    density: Settings.data.bar.density
    oppositeDirection: BarService.getPillDirection(root)
    icon: root.testMode ? BatteryService.getIcon(root.testPercent, root.testCharging, true) : BatteryService.getIcon(root.percent, root.charging, root.isReady)
    text: (root.isReady || root.testMode) ? Math.round(root.percent) : "-"
    suffix: "%"
    autoHide: false
    forceOpen: root.isReady && root.displayMode === "alwaysShow"
    forceClose: root.displayMode === "alwaysHide" || (root.initializationComplete && !root.isReady)
    customBackgroundColor: !root.initializationComplete ? NColor.transparent : (root.charging ? NColor.mPrimary : (root.isLowBattery ? NColor.mError : NColor.transparent))
    customTextIconColor: !root.initializationComplete ? NColor.transparent : (root.charging ? NColor.mOnPrimary : (root.isLowBattery ? NColor.mOnError : NColor.transparent))

    tooltipText: {
      let lines = [];
      if (root.testMode) {
        lines.push(`Time left: ${Time.formatVagueHumanReadableDuration(12345)}.`);
        return lines.join("\n");
      }
      if (!root.isReady || !root.isDevicePresent) {
        return I18n.tr("battery.no-battery-detected");
      }
      if (root.battery.timeToEmpty > 0) {
        lines.push(I18n.tr("battery.time-left", {
          "time": Time.formatVagueHumanReadableDuration(root.battery.timeToEmpty)
        }));
      }
      if (root.battery.timeToFull > 0) {
        lines.push(I18n.tr("battery.time-until-full", {
          "time": Time.formatVagueHumanReadableDuration(root.battery.timeToFull)
        }));
      }
      if (root.battery.changeRate !== undefined) {
        const rate = root.battery.changeRate;
        if (rate > 0) {
          lines.push(root.charging ? I18n.tr("battery.charging-rate", {
            "rate": rate.toFixed(2)
          }) : I18n.tr("battery.discharging-rate", {
            "rate": rate.toFixed(2)
          }));
        } else if (rate < 0) {
          lines.push(I18n.tr("battery.discharging-rate", {
            "rate": Math.abs(rate).toFixed(2)
          }));
        } else {
          // Rate is 0 - check if plugged in (charging state) or idle
          lines.push(root.charging ? I18n.tr("battery.plugged-in") : I18n.tr("battery.idle"));
        }
      } else {
        lines.push(root.charging ? I18n.tr("battery.charging") : I18n.tr("battery.discharging"));
      }
      if (root.battery.healthPercentage !== undefined && root.battery.healthPercentage > 0) {
        lines.push(I18n.tr("battery.health", {
          "percent": Math.round(root.battery.healthPercentage)
        }));
      }
      return lines.join("\n");
    }
    onClicked: {
      const panel = PanelService.getPanel("batteryPanel", screen);
      if (panel)
        panel.toggle(this);
    }
    onRightClicked: {
      var popupMenuWindow = PanelService.getPopupMenuWindow(screen);
      if (popupMenuWindow) {
        popupMenuWindow.showContextMenu(contextMenu);
        const pos = BarService.getContextMenuPosition(pill, contextMenu.implicitWidth, contextMenu.implicitHeight);
        contextMenu.openAtItem(pill, pos.x, pos.y);
      }
    }
  }
}
