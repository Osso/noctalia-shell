import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Services.Hardware
import qs.Services.System
import qs.Widgets

ColumnLayout {
  id: root
  spacing: Style.marginM

  // Properties to receive data from parent
  property var widgetData: null
  property var widgetMetadata: null

  // Local, editable state for checkboxes
  property bool valueUsePrimaryColor: widgetData.usePrimaryColor !== undefined ? widgetData.usePrimaryColor : widgetMetadata.usePrimaryColor
  property bool valueShowCpuUsage: widgetData.showCpuUsage !== undefined ? widgetData.showCpuUsage : widgetMetadata.showCpuUsage
  property bool valueShowCpuTemp: widgetData.showCpuTemp !== undefined ? widgetData.showCpuTemp : widgetMetadata.showCpuTemp
  property bool valueShowMemoryUsage: widgetData.showMemoryUsage !== undefined ? widgetData.showMemoryUsage : widgetMetadata.showMemoryUsage
  property bool valueShowMemoryAsPercent: widgetData.showMemoryAsPercent !== undefined ? widgetData.showMemoryAsPercent : widgetMetadata.showMemoryAsPercent
  property bool valueShowNetworkStats: widgetData.showNetworkStats !== undefined ? widgetData.showNetworkStats : widgetMetadata.showNetworkStats
  property bool valueShowDiskUsage: widgetData.showDiskUsage !== undefined ? widgetData.showDiskUsage : widgetMetadata.showDiskUsage
  property string valueDiskPath: widgetData.diskPath !== undefined ? widgetData.diskPath : widgetMetadata.diskPath
  property bool valueShowFanSpeed: widgetData.showFanSpeed !== undefined ? widgetData.showFanSpeed : widgetMetadata.showFanSpeed

  function saveSettings() {
    var settings = Object.assign({}, widgetData || {});
    settings.usePrimaryColor = valueUsePrimaryColor;
    settings.showCpuUsage = valueShowCpuUsage;
    settings.showCpuTemp = valueShowCpuTemp;
    settings.showMemoryUsage = valueShowMemoryUsage;
    settings.showMemoryAsPercent = valueShowMemoryAsPercent;
    settings.showNetworkStats = valueShowNetworkStats;
    settings.showDiskUsage = valueShowDiskUsage;
    settings.diskPath = valueDiskPath;
    settings.showFanSpeed = valueShowFanSpeed;

    return settings;
  }

  NToggle {
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.clock.use-primary-color.label")
    description: I18n.tr("bar.widget-settings.clock.use-primary-color.description")
    checked: root.valueUsePrimaryColor
    onToggled: checked => root.valueUsePrimaryColor = checked
  }

  NToggle {
    id: showCpuUsage
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.system-monitor.cpu-usage.label")
    description: I18n.tr("bar.widget-settings.system-monitor.cpu-usage.description")
    checked: root.valueShowCpuUsage
    onToggled: checked => root.valueShowCpuUsage = checked
  }

  NToggle {
    id: showCpuTemp
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.system-monitor.cpu-temperature.label")
    description: I18n.tr("bar.widget-settings.system-monitor.cpu-temperature.description")
    checked: root.valueShowCpuTemp
    onToggled: checked => root.valueShowCpuTemp = checked
  }

  NToggle {
    id: showMemoryUsage
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.system-monitor.memory-usage.label")
    description: I18n.tr("bar.widget-settings.system-monitor.memory-usage.description")
    checked: root.valueShowMemoryUsage
    onToggled: checked => root.valueShowMemoryUsage = checked
  }

  NToggle {
    id: showMemoryAsPercent
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.system-monitor.memory-percentage.label")
    description: I18n.tr("bar.widget-settings.system-monitor.memory-percentage.description")
    checked: root.valueShowMemoryAsPercent
    onToggled: checked => root.valueShowMemoryAsPercent = checked
    visible: root.valueShowMemoryUsage
  }

  NToggle {
    id: showNetworkStats
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.system-monitor.network-traffic.label")
    description: I18n.tr("bar.widget-settings.system-monitor.network-traffic.description")
    checked: root.valueShowNetworkStats
    onToggled: checked => root.valueShowNetworkStats = checked
  }

  NToggle {
    id: showDiskUsage
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.system-monitor.storage-usage.label")
    description: I18n.tr("bar.widget-settings.system-monitor.storage-usage.description")
    checked: root.valueShowDiskUsage
    onToggled: checked => root.valueShowDiskUsage = checked
  }

  NComboBox {
    id: diskPathComboBox
    Layout.fillWidth: true
    label: I18n.tr("bar.widget-settings.system-monitor.disk-path.label")
    description: I18n.tr("bar.widget-settings.system-monitor.disk-path.description")
    visible: root.valueShowDiskUsage
    model: {
      const paths = Object.keys(SystemStatService.diskPercents).sort();
      return paths.map(path => ({
            key: path,
            name: path
          }));
    }
    currentKey: root.valueDiskPath
    onSelected: key => root.valueDiskPath = key
  }

  NToggle {
    id: showFanSpeed
    Layout.fillWidth: true
    label: "Fan Speed"
    description: "Show fan RPM in the system monitor"
    checked: root.valueShowFanSpeed
    onToggled: checked => root.valueShowFanSpeed = checked
    visible: FanService.available
  }
}
