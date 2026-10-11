import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Services.System
import qs.Widgets

// Unified system card: monitors CPU, temp, memory, disk
NBox {
  id: root

  Item {
    id: content
    anchors.fill: parent
    anchors.margins: Style.marginS

    property int widgetHeight: Math.round(65 * Style.uiScaleRatio)

    ColumnLayout {
      anchors.centerIn: parent
      spacing: 0

      NCircleStat {
        value: SystemStatService.cpuUsage
        icon: "cpu-usage"
        flat: true
        contentScale: 0.8
        Layout.preferredHeight: content.widgetHeight
        Layout.alignment: Qt.AlignHCenter
        // Highlight color based on thresholds
        fillColor: (SystemStatService.cpuUsage > Settings.data.systemMonitor.cpuCriticalThreshold) ? (Settings.data.systemMonitor.useCustomColors ? (Settings.data.systemMonitor.criticalColor || NColor.mError) : NColor.mError) : (SystemStatService.cpuUsage > Settings.data.systemMonitor.cpuWarningThreshold) ? (Settings.data.systemMonitor.useCustomColors ? (
                                                                                                                                                                                                                                                                                                                                                                    Settings.data.systemMonitor.warningColor
                                                                                                                                                                                                                                                                                                                                                                    || NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                                                                  NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                   NColor.mPrimary
        textColor: (SystemStatService.cpuUsage > Settings.data.systemMonitor.cpuCriticalThreshold) ? NColor.mSurfaceVariant : (SystemStatService.cpuUsage > Settings.data.systemMonitor.cpuWarningThreshold) ? NColor.mSurfaceVariant : NColor.mOnSurface
      }
      NCircleStat {
        value: SystemStatService.cpuTemp
        suffix: "°C"
        icon: "cpu-temperature"
        flat: true
        contentScale: 0.8
        Layout.preferredHeight: content.widgetHeight
        Layout.alignment: Qt.AlignHCenter
        // Highlight color based on thresholds
        fillColor: (SystemStatService.cpuTemp > Settings.data.systemMonitor.tempCriticalThreshold) ? (Settings.data.systemMonitor.useCustomColors ? (Settings.data.systemMonitor.criticalColor || NColor.mError) : NColor.mError) : (SystemStatService.cpuTemp > Settings.data.systemMonitor.tempWarningThreshold) ? (Settings.data.systemMonitor.useCustomColors ? (
                                                                                                                                                                                                                                                                                                                                                                    Settings.data.systemMonitor.warningColor
                                                                                                                                                                                                                                                                                                                                                                    || NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                                                                  NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                   NColor.mPrimary
        textColor: (SystemStatService.cpuTemp > Settings.data.systemMonitor.tempCriticalThreshold) ? NColor.mSurfaceVariant : (SystemStatService.cpuTemp > Settings.data.systemMonitor.tempWarningThreshold) ? NColor.mSurfaceVariant : NColor.mOnSurface
      }
      NCircleStat {
        value: SystemStatService.memPercent
        icon: "memory"
        flat: true
        contentScale: 0.8
        Layout.preferredHeight: content.widgetHeight
        Layout.alignment: Qt.AlignHCenter
        // Highlight color based on thresholds
        fillColor: (SystemStatService.memPercent > Settings.data.systemMonitor.memCriticalThreshold) ? (Settings.data.systemMonitor.useCustomColors ? (Settings.data.systemMonitor.criticalColor || NColor.mError) : NColor.mError) : (SystemStatService.memPercent > Settings.data.systemMonitor.memWarningThreshold) ? (Settings.data.systemMonitor.useCustomColors ? (
                                                                                                                                                                                                                                                                                                                                                                        Settings.data.systemMonitor.warningColor
                                                                                                                                                                                                                                                                                                                                                                        || NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                                                                      NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                       NColor.mPrimary
        textColor: (SystemStatService.memPercent > Settings.data.systemMonitor.memCriticalThreshold) ? NColor.mSurfaceVariant : (SystemStatService.memPercent > Settings.data.systemMonitor.memWarningThreshold) ? NColor.mSurfaceVariant : NColor.mOnSurface
      }
      NCircleStat {
        value: SystemStatService.diskPercents["/"] ?? 0
        icon: "storage"
        flat: true
        contentScale: 0.8
        Layout.preferredHeight: content.widgetHeight
        Layout.alignment: Qt.AlignHCenter
        // Highlight color based on thresholds
        fillColor: ((SystemStatService.diskPercents["/"] ?? 0) > Settings.data.systemMonitor.diskCriticalThreshold) ? (Settings.data.systemMonitor.useCustomColors ? (Settings.data.systemMonitor.criticalColor || NColor.mError) : NColor.mError) : ((SystemStatService.diskPercents["/"] ?? 0) > Settings.data.systemMonitor.diskWarningThreshold) ? (
                                                                                                                                                                                                                                                                                                                                                       Settings.data.systemMonitor.useCustomColors
                                                                                                                                                                                                                                                                                                                                                       ? (Settings.data.systemMonitor.warningColor
                                                                                                                                                                                                                                                                                                                                                          || NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                                                         NColor.mTertiary) :
                                                                                                                                                                                                                                                                                                                                                     NColor.mPrimary
        textColor: ((SystemStatService.diskPercents["/"] ?? 0) > Settings.data.systemMonitor.diskCriticalThreshold) ? NColor.mSurfaceVariant : ((SystemStatService.diskPercents["/"] ?? 0) > Settings.data.systemMonitor.diskWarningThreshold) ? NColor.mSurfaceVariant : NColor.mOnSurface
      }
    }
  }
}
