pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.Bar.Extras
import qs.Modules.Panels.Settings
import qs.Services.Hardware
import qs.Services.System
import qs.Services.UI
import qs.Widgets

Rectangle {
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
      const widgets = Settings.data.bar.widgets[section];
      if (widgets && sectionWidgetIndex < widgets.length) {
        return widgets[sectionWidgetIndex];
      }
    }
    return {};
  }

  readonly property string barPosition: Settings.data.bar.position
  readonly property bool isVertical: barPosition === "left" || barPosition === "right"
  readonly property string density: Settings.data.bar.density

  readonly property bool usePrimaryColor: widgetSettings.usePrimaryColor !== undefined ? widgetSettings.usePrimaryColor : widgetMetadata.usePrimaryColor
  readonly property bool showCpuUsage: (widgetSettings.showCpuUsage !== undefined) ? widgetSettings.showCpuUsage : widgetMetadata.showCpuUsage
  readonly property bool showCpuTemp: (widgetSettings.showCpuTemp !== undefined) ? widgetSettings.showCpuTemp : widgetMetadata.showCpuTemp
  readonly property bool showMemoryUsage: (widgetSettings.showMemoryUsage !== undefined) ? widgetSettings.showMemoryUsage : widgetMetadata.showMemoryUsage
  readonly property bool showMemoryAsPercent: (widgetSettings.showMemoryAsPercent !== undefined) ? widgetSettings.showMemoryAsPercent : widgetMetadata.showMemoryAsPercent
  readonly property bool showNetworkStats: (widgetSettings.showNetworkStats !== undefined) ? widgetSettings.showNetworkStats : widgetMetadata.showNetworkStats
  readonly property bool showDiskUsage: (widgetSettings.showDiskUsage !== undefined) ? widgetSettings.showDiskUsage : widgetMetadata.showDiskUsage
  readonly property string diskPath: (widgetSettings.diskPath !== undefined) ? widgetSettings.diskPath : widgetMetadata.diskPath
  readonly property bool showFanSpeed: (widgetSettings.showFanSpeed !== undefined) ? widgetSettings.showFanSpeed : widgetMetadata.showFanSpeed

  readonly property real iconSize: textSize * 1.4
  readonly property real textSize: {
    var base = isVertical ? width * 0.82 : height;
    return Math.max(1, (density === "compact") ? base * 0.43 : base * 0.33);
  }

  // Match Workspace widget pill sizing: base ratio depends on bar density
  readonly property real pillBaseRatio: (density === "compact") ? 0.85 : 0.65
  readonly property real pillHeight: Style.capsuleHeight * pillBaseRatio

  // Highlight colors
  readonly property color warningColor: Settings.data.systemMonitor.useCustomColors ? (Settings.data.systemMonitor.warningColor || NColor.mTertiary) : NColor.mTertiary
  readonly property color criticalColor: Settings.data.systemMonitor.useCustomColors ? (Settings.data.systemMonitor.criticalColor || NColor.mError) : NColor.mError

  readonly property int percentTextWidth: Math.ceil(percentMetrics.boundingRect.width + 3)
  readonly property int tempTextWidth: Math.ceil(tempMetrics.boundingRect.width + 3)
  readonly property int memTextWidth: Math.ceil(memMetrics.boundingRect.width + 3)
  readonly property bool diskHovered: diskHoverArea ? diskHoverArea.containsMouse : false
  readonly property bool fanHovered: fanHoverArea ? fanHoverArea.containsMouse : false
  readonly property bool isHovered: mainMouseArea.containsMouse || diskHovered || fanHovered
  readonly property color textColor: isHovered ? NColor.mOnHover : (usePrimaryColor ? NColor.mPrimary : NColor.mOnSurface)
  readonly property color iconColor: isHovered ? NColor.mOnHover : NColor.mOnSurface

  // Threshold settings from global configuration
  readonly property int cpuWarningThreshold: Settings.data.systemMonitor.cpuWarningThreshold
  readonly property int cpuCriticalThreshold: Settings.data.systemMonitor.cpuCriticalThreshold
  readonly property int tempWarningThreshold: Settings.data.systemMonitor.tempWarningThreshold
  readonly property int tempCriticalThreshold: Settings.data.systemMonitor.tempCriticalThreshold
  readonly property int memWarningThreshold: Settings.data.systemMonitor.memWarningThreshold
  readonly property int memCriticalThreshold: Settings.data.systemMonitor.memCriticalThreshold
  readonly property int diskWarningThreshold: Settings.data.systemMonitor.diskWarningThreshold
  readonly property int diskCriticalThreshold: Settings.data.systemMonitor.diskCriticalThreshold
  property var registeredSystemStatMetrics: ({})
  property bool fanPollingRegistered: false

  function setFanPolling(shouldPoll) {
    if (shouldPoll && (!fanPollingRegistered || !FanService.isPollingActive())) {
      FanService.beginPolling();
      fanPollingRegistered = true;
    } else if (!shouldPoll && fanPollingRegistered) {
      FanService.endPolling();
      fanPollingRegistered = false;
    }
  }

  function setSystemStatPolling(metric, shouldPoll) {
    const isRegistered = registeredSystemStatMetrics[metric] === true;
    if (shouldPoll && !isRegistered) {
      SystemStatService.beginPolling(metric);
      let refs = Object.assign({}, registeredSystemStatMetrics);
      refs[metric] = true;
      registeredSystemStatMetrics = refs;
    } else if (!shouldPoll && isRegistered) {
      SystemStatService.endPolling(metric);
      let nextRefs = Object.assign({}, registeredSystemStatMetrics);
      nextRefs[metric] = false;
      registeredSystemStatMetrics = nextRefs;
    }
  }

  function refreshSystemStatPolling() {
    const widgetVisible = visible;
    setFanPolling(widgetVisible && showFanSpeed);
    setSystemStatPolling("cpu", widgetVisible && showCpuUsage);
    setSystemStatPolling("temp", widgetVisible && showCpuTemp);
    setSystemStatPolling("memory", widgetVisible && showMemoryUsage);
    setSystemStatPolling("disk", widgetVisible && showDiskUsage);
    setSystemStatPolling("network", widgetVisible && showNetworkStats);
  }

  function clearSystemStatPolling() {
    setFanPolling(false);
    setSystemStatPolling("cpu", false);
    setSystemStatPolling("temp", false);
    setSystemStatPolling("memory", false);
    setSystemStatPolling("disk", false);
    setSystemStatPolling("network", false);
  }

  Component.onCompleted: refreshSystemStatPolling()
  Component.onDestruction: clearSystemStatPolling()
  onVisibleChanged: refreshSystemStatPolling()
  onShowCpuUsageChanged: refreshSystemStatPolling()
  onShowCpuTempChanged: refreshSystemStatPolling()
  onShowMemoryUsageChanged: refreshSystemStatPolling()
  onShowDiskUsageChanged: refreshSystemStatPolling()
  onShowNetworkStatsChanged: refreshSystemStatPolling()
  onShowFanSpeedChanged: refreshSystemStatPolling()

  Connections {
    target: FanService
    function onSensorDetectedChanged() {
      root.refreshSystemStatPolling();
    }
  }

  // Warning threshold calculation properties
  readonly property bool cpuWarning: showCpuUsage && SystemStatService.cpuUsage > cpuWarningThreshold
  readonly property bool cpuCritical: showCpuUsage && SystemStatService.cpuUsage > cpuCriticalThreshold
  readonly property bool tempWarning: showCpuTemp && SystemStatService.cpuTemp > tempWarningThreshold
  readonly property bool tempCritical: showCpuTemp && SystemStatService.cpuTemp > tempCriticalThreshold
  readonly property bool memWarning: showMemoryUsage && SystemStatService.memPercent > memWarningThreshold
  readonly property bool memCritical: showMemoryUsage && SystemStatService.memPercent > memCriticalThreshold
  readonly property bool diskWarning: showDiskUsage && SystemStatService.diskPercents[diskPath] > diskWarningThreshold
  readonly property bool diskCritical: showDiskUsage && SystemStatService.diskPercents[diskPath] > diskCriticalThreshold

  TextMetrics {
    id: percentMetrics
    font.family: Settings.data.ui.fontFixed
    font.weight: Style.fontWeightMedium
    font.pointSize: root.textSize * Settings.data.ui.fontFixedScale
    text: "99%" // Use the longest possible string for measurement
  }

  TextMetrics {
    id: tempMetrics
    font.family: Settings.data.ui.fontFixed
    font.weight: Style.fontWeightMedium
    font.pointSize: root.textSize * Settings.data.ui.fontFixedScale
    text: "99°" // Use the longest possible string for measurement
  }

  TextMetrics {
    id: memMetrics
    font.family: Settings.data.ui.fontFixed
    font.weight: Style.fontWeightMedium
    font.pointSize: root.textSize * Settings.data.ui.fontFixedScale
    text: "99.9K" // Longest value part of network speed
  }

  TextMetrics {
    id: fanMetrics
    font.family: Settings.data.ui.fontFixed
    font.weight: Style.fontWeightMedium
    font.pointSize: root.textSize * Settings.data.ui.fontFixedScale
    text: "9.9k" // Fan RPM format
  }

  readonly property int fanTextWidth: Math.ceil(fanMetrics.boundingRect.width + 3)

  function shouldShowFanSpeedMetric(enabled, fanAvailable, sensorDetected) {
    return enabled && (fanAvailable || sensorDetected);
  }

  function formatFanSpeedText(maxRpm) {
    return FanService.formatRpm(maxRpm);
  }

  function fanTooltipText(fans) {
    return fans.map(f => f.label + ": " + f.rpm + " RPM").join("\n");
  }

  anchors.centerIn: parent
  implicitWidth: isVertical ? Style.capsuleHeight : Math.round(mainGrid.implicitWidth + Style.marginM * 2)
  implicitHeight: isVertical ? Math.round(mainGrid.implicitHeight + Style.marginM * 2) : Style.capsuleHeight
  radius: Style.radiusM
  color: isHovered ? NColor.mHover : Style.capsuleColor

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
      var popupMenuWindow = PanelService.getPopupMenuWindow(contextMenu.screen);
      if (popupMenuWindow) {
        popupMenuWindow.close();
      }

      if (action === "widget-settings") {
        BarService.openWidgetSettings(contextMenu.screen, root.section, root.sectionWidgetIndex, root.widgetId, root.widgetSettings);
      }
    }
  }

  MouseArea {
    id: mainMouseArea
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: mouse => {
      if (mouse.button === Qt.LeftButton) {
        // Open process panel on left click
        const processPanel = PanelService.getPanel("processPanel", root.screen);
        if (processPanel) {
          processPanel.toggle(root);
        }
      } else if (mouse.button === Qt.RightButton) {
        const popupMenuWindow = PanelService.getPopupMenuWindow(root.screen);
        if (popupMenuWindow) {
          popupMenuWindow.showContextMenu(contextMenu);
          const pos = BarService.getContextMenuPosition(root, contextMenu.implicitWidth, contextMenu.implicitHeight);
          contextMenu.openAtItem(root, pos.x, pos.y);
        }
      }
    }
  }

  // Status indicator component definition
  component StatusIndicator: Rectangle {
    id: statusIndicator
    property bool warning: false
    property bool critical: false
    property int indicatorWidth: Style.capsuleHeight
    property color warningColor: NColor.mTertiary
    property color criticalColor: NColor.mError

    width: root.isVertical ? Math.max(0, indicatorWidth - Style.marginS * 2) : Math.max(0, indicatorWidth + Style.marginXS * 2)
    height: root.isVertical ? Math.max(0, Style.capsuleHeight + Style.marginXS * 2) : root.pillHeight
    radius: Style.radiusM
    // Hide the rectangular indicator when the bar is vertical; keep it available for horizontal layout
    visible: !root.isVertical
    color: critical ? criticalColor : warningColor
    scale: (warning || critical) ? 1.0 : 0.0
    opacity: (warning || critical) ? 1.0 : 0.0

    // Smooth appearance/disappearance animation
    Behavior on scale {
      NumberAnimation {
        duration: Style.animationNormal
        easing.type: Easing.OutCubic
      }
    }

    Behavior on opacity {
      NumberAnimation {
        duration: Style.animationNormal
        easing.type: Easing.OutCubic
      }
    }

    Behavior on color {
      ColorAnimation {
        duration: Style.animationNormal
        easing.type: Easing.OutCubic
      }
    }
  }

  GridLayout {
    id: mainGrid
    anchors.centerIn: parent
    flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
    rows: root.isVertical ? -1 : 1
    columns: root.isVertical ? 1 : -1
    rowSpacing: root.isVertical ? (Style.marginM) : 0
    columnSpacing: root.isVertical ? 0 : (Style.marginM)

    // CPU Usage Component
    Item {
      id: cpuUsageContainer
      Layout.preferredWidth: root.isVertical ? root.width : root.iconSize + root.percentTextWidth + (Style.marginXXS)
      Layout.preferredHeight: Style.capsuleHeight
      Layout.alignment: root.isVertical ? Qt.AlignHCenter : Qt.AlignVCenter
      visible: root.showCpuUsage

      // Status indicator covering the entire component
      StatusIndicator {
        anchors.centerIn: parent
        warning: root.cpuWarning
        critical: root.cpuCritical
        indicatorWidth: cpuUsageContainer.width
        warningColor: root.warningColor
        criticalColor: root.criticalColor
      }

      GridLayout {
        id: cpuUsageContent
        anchors.centerIn: parent
        flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rows: root.isVertical ? 2 : 1
        columns: root.isVertical ? 1 : 2
        rowSpacing: Style.marginXXS
        columnSpacing: Style.marginXXS

        Item {
          Layout.alignment: Qt.AlignCenter
          Layout.row: root.isVertical ? 1 : 0
          Layout.column: 0
          Layout.fillWidth: root.isVertical
          implicitWidth: root.iconSize
          implicitHeight: root.iconSize

          NIcon {
            icon: "cpu-usage"
            pointSize: root.iconSize
            applyUiScale: false
            anchors.centerIn: parent
            // Invert color to bar background when indicator active
            color: root.isVertical ? (root.cpuCritical ? root.criticalColor : (root.cpuWarning ? root.warningColor : root.iconColor)) : ((root.cpuWarning || root.cpuCritical) ? NColor.mSurfaceVariant : root.iconColor)
          }
        }

        NText {
          text: {
            let usage = Math.round(SystemStatService.cpuUsage);
            if (usage < 100) {
              return `${usage}%`;
            } else {
              return usage;
            }
          }
          family: Settings.data.ui.fontFixed
          pointSize: root.textSize
          applyUiScale: false
          font.weight: Style.fontWeightMedium
          Layout.alignment: Qt.AlignCenter
          Layout.preferredWidth: root.isVertical ? -1 : root.percentTextWidth
          horizontalAlignment: root.isVertical ? Text.AlignHCenter : Text.AlignRight
          verticalAlignment: Text.AlignVCenter
          // Use highlight colors in vertical bar; otherwise invert text color to bar background when indicator active
          color: root.isVertical ? (root.cpuCritical ? root.criticalColor : (root.cpuWarning ? root.warningColor : root.textColor)) : ((root.cpuWarning || root.cpuCritical) ? NColor.mSurfaceVariant : root.textColor)
          Layout.row: root.isVertical ? 0 : 0
          Layout.column: root.isVertical ? 0 : 1
          scale: root.isVertical ? Math.min(1.0, root.width / implicitWidth) : 1.0
        }
      }
    }

    // CPU Temperature Component
    Item {
      id: cpuTempContainer
      Layout.preferredWidth: root.isVertical ? root.width : (root.iconSize + root.tempTextWidth) + (Style.marginXXS)
      Layout.preferredHeight: Style.capsuleHeight
      Layout.alignment: root.isVertical ? Qt.AlignHCenter : Qt.AlignVCenter
      visible: root.showCpuTemp

      // Status indicator covering the entire component
      StatusIndicator {
        anchors.centerIn: parent
        warning: root.tempWarning
        critical: root.tempCritical
        indicatorWidth: cpuTempContainer.width
        warningColor: root.warningColor
        criticalColor: root.criticalColor
      }

      GridLayout {
        id: cpuTempContent
        anchors.centerIn: parent
        flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rows: root.isVertical ? 2 : 1
        columns: root.isVertical ? 1 : 2
        rowSpacing: Style.marginXXS
        columnSpacing: Style.marginXXS

        Item {
          Layout.alignment: Qt.AlignCenter
          Layout.row: root.isVertical ? 1 : 0
          Layout.column: 0
          Layout.fillWidth: root.isVertical
          implicitWidth: root.iconSize
          implicitHeight: root.iconSize

          NIcon {
            icon: "cpu-temperature"
            pointSize: root.iconSize
            applyUiScale: false
            anchors.centerIn: parent
            // Invert color when temp indicator active
            color: root.isVertical ? (root.tempCritical ? root.criticalColor : (root.tempWarning ? root.warningColor : root.iconColor)) : ((root.tempWarning || root.tempCritical) ? NColor.mSurfaceVariant : root.iconColor)
          }
        }

        NText {
          text: `${Math.round(SystemStatService.cpuTemp)}°`
          family: Settings.data.ui.fontFixed
          pointSize: root.textSize
          applyUiScale: false
          font.weight: Style.fontWeightMedium
          Layout.alignment: Qt.AlignCenter
          Layout.preferredWidth: root.isVertical ? -1 : root.tempTextWidth
          horizontalAlignment: root.isVertical ? Text.AlignHCenter : Text.AlignRight
          verticalAlignment: Text.AlignVCenter
          // Use highlight colors in vertical bar; otherwise invert text color to bar background when temp indicator active
          color: root.isVertical ? (root.tempCritical ? root.criticalColor : (root.tempWarning ? root.warningColor : root.textColor)) : ((root.tempWarning || root.tempCritical) ? NColor.mSurfaceVariant : root.textColor)
          Layout.row: root.isVertical ? 0 : 0
          Layout.column: root.isVertical ? 0 : 1
          scale: root.isVertical ? Math.min(1.0, root.width / implicitWidth) : 1.0
        }
      }
    }

    // Memory Usage Component
    Item {
      id: memoryContainer
      Layout.preferredWidth: root.isVertical ? root.width : root.iconSize + (root.showMemoryAsPercent ? root.percentTextWidth : root.memTextWidth) + (Style.marginXXS)
      Layout.preferredHeight: Style.capsuleHeight
      Layout.alignment: root.isVertical ? Qt.AlignHCenter : Qt.AlignVCenter
      visible: root.showMemoryUsage

      // Status indicator covering the entire component
      StatusIndicator {
        anchors.centerIn: parent
        warning: root.memWarning
        critical: root.memCritical
        indicatorWidth: memoryContainer.width
        warningColor: root.warningColor
        criticalColor: root.criticalColor
      }

      GridLayout {
        id: memoryContent
        anchors.centerIn: parent
        flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rows: root.isVertical ? 2 : 1
        columns: root.isVertical ? 1 : 2
        rowSpacing: Style.marginXXS
        columnSpacing: Style.marginXXS

        Item {
          Layout.alignment: Qt.AlignCenter
          Layout.row: root.isVertical ? 1 : 0
          Layout.column: 0
          Layout.fillWidth: root.isVertical
          implicitWidth: root.iconSize
          implicitHeight: root.iconSize

          NIcon {
            icon: "memory"
            pointSize: root.iconSize
            applyUiScale: false
            anchors.centerIn: parent
            // Invert color when memory indicator active
            color: root.isVertical ? (root.memCritical ? root.criticalColor : (root.memWarning ? root.warningColor : root.iconColor)) : ((root.memWarning || root.memCritical) ? NColor.mSurfaceVariant : root.iconColor)
          }
        }

        NText {
          text: root.showMemoryAsPercent ? `${Math.round(SystemStatService.memPercent)}%` : `${SystemStatService.memGb.toFixed(1)}G`
          family: Settings.data.ui.fontFixed
          pointSize: root.textSize
          applyUiScale: false
          font.weight: Style.fontWeightMedium
          Layout.alignment: Qt.AlignCenter
          Layout.preferredWidth: root.isVertical ? -1 : (root.showMemoryAsPercent ? root.percentTextWidth : root.memTextWidth)
          horizontalAlignment: root.isVertical ? Text.AlignHCenter : Text.AlignRight
          verticalAlignment: Text.AlignVCenter
          // Use highlight colors in vertical bar; otherwise invert text color to bar background when memory indicator active
          color: root.isVertical ? (root.memCritical ? root.criticalColor : (root.memWarning ? root.warningColor : root.textColor)) : ((root.memWarning || root.memCritical) ? NColor.mSurfaceVariant : root.textColor)
          Layout.row: root.isVertical ? 0 : 0
          Layout.column: root.isVertical ? 0 : 1
          scale: root.isVertical ? Math.min(1.0, root.width / implicitWidth) : 1.0
        }
      }
    }

    // Network Download Speed Component
    Item {
      Layout.preferredWidth: root.isVertical ? root.width : root.iconSize + root.memTextWidth + (Style.marginXXS)
      Layout.preferredHeight: Style.capsuleHeight
      Layout.alignment: root.isVertical ? Qt.AlignHCenter : Qt.AlignVCenter
      visible: root.showNetworkStats

      GridLayout {
        id: downloadContent
        anchors.centerIn: parent
        flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rows: root.isVertical ? 2 : 1
        columns: root.isVertical ? 1 : 2
        rowSpacing: Style.marginXXS
        columnSpacing: Style.marginXXS

        Item {
          Layout.alignment: Qt.AlignCenter
          Layout.row: root.isVertical ? 1 : 0
          Layout.column: 0
          Layout.fillWidth: root.isVertical
          implicitWidth: root.iconSize
          implicitHeight: root.iconSize

          NIcon {
            icon: "download-speed"
            pointSize: root.iconSize
            applyUiScale: false
            anchors.centerIn: parent
            color: root.iconColor
          }
        }

        NText {
          text: root.isVertical ? SystemStatService.formatCompactSpeed(SystemStatService.rxSpeed) : SystemStatService.formatSpeed(SystemStatService.rxSpeed)
          family: Settings.data.ui.fontFixed
          pointSize: root.textSize
          applyUiScale: false
          font.weight: Style.fontWeightMedium
          Layout.alignment: Qt.AlignCenter
          Layout.preferredWidth: root.isVertical ? -1 : root.memTextWidth
          horizontalAlignment: root.isVertical ? Text.AlignHCenter : Text.AlignRight
          verticalAlignment: Text.AlignVCenter
          color: root.textColor
          Layout.row: root.isVertical ? 0 : 0
          Layout.column: root.isVertical ? 0 : 1
          scale: root.isVertical ? Math.min(1.0, root.width / implicitWidth) : 1.0
        }
      }
    }

    // Network Upload Speed Component
    Item {
      Layout.preferredWidth: root.isVertical ? root.width : root.iconSize + root.memTextWidth + (Style.marginXXS)
      Layout.preferredHeight: Style.capsuleHeight
      Layout.alignment: root.isVertical ? Qt.AlignHCenter : Qt.AlignVCenter
      visible: root.showNetworkStats

      GridLayout {
        id: uploadContent
        anchors.centerIn: parent
        flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rows: root.isVertical ? 2 : 1
        columns: root.isVertical ? 1 : 2
        rowSpacing: Style.marginXXS
        columnSpacing: Style.marginXXS

        Item {
          Layout.alignment: Qt.AlignCenter
          Layout.row: root.isVertical ? 1 : 0
          Layout.column: 0
          Layout.fillWidth: root.isVertical
          implicitWidth: root.iconSize
          implicitHeight: root.iconSize

          NIcon {
            icon: "upload-speed"
            pointSize: root.iconSize
            applyUiScale: false
            anchors.centerIn: parent
            color: root.iconColor
          }
        }

        NText {
          text: root.isVertical ? SystemStatService.formatCompactSpeed(SystemStatService.txSpeed) : SystemStatService.formatSpeed(SystemStatService.txSpeed)
          family: Settings.data.ui.fontFixed
          pointSize: root.textSize
          applyUiScale: false
          font.weight: Style.fontWeightMedium
          Layout.alignment: Qt.AlignCenter
          Layout.preferredWidth: root.isVertical ? -1 : root.memTextWidth
          horizontalAlignment: root.isVertical ? Text.AlignHCenter : Text.AlignRight
          verticalAlignment: Text.AlignVCenter
          color: root.textColor
          Layout.row: root.isVertical ? 0 : 0
          Layout.column: root.isVertical ? 0 : 1
          scale: root.isVertical ? Math.min(1.0, root.width / implicitWidth) : 1.0
        }
      }
    }

    // Disk Usage Component (primary drive)
    Item {
      id: diskContainer
      Layout.preferredWidth: root.isVertical ? root.width : root.iconSize + root.percentTextWidth + (Style.marginXXS)
      Layout.preferredHeight: Style.capsuleHeight
      Layout.alignment: root.isVertical ? Qt.AlignHCenter : Qt.AlignVCenter
      visible: root.showDiskUsage

      // Status indicator covering the entire component
      StatusIndicator {
        anchors.centerIn: parent
        warning: root.diskWarning
        critical: root.diskCritical
        indicatorWidth: diskContainer.width
        warningColor: root.warningColor
        criticalColor: root.criticalColor
      }

      GridLayout {
        id: diskContent
        anchors.centerIn: parent
        flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rows: root.isVertical ? 2 : 1
        columns: root.isVertical ? 1 : 2
        rowSpacing: Style.marginXXS
        columnSpacing: Style.marginXXS

        Item {
          Layout.alignment: Qt.AlignCenter
          Layout.row: root.isVertical ? 1 : 0
          Layout.column: 0
          Layout.fillWidth: root.isVertical
          implicitWidth: root.iconSize
          implicitHeight: root.iconSize

          NIcon {
            icon: "storage"
            pointSize: root.iconSize
            applyUiScale: false
            anchors.centerIn: parent
            // Invert color when disk indicator active (vertical uses highlight colors)
            color: root.isVertical ? (root.diskCritical ? root.criticalColor : (root.diskWarning ? root.warningColor : root.iconColor)) : ((root.diskWarning || root.diskCritical) ? NColor.mSurfaceVariant : root.iconColor)
          }
        }

        NText {
          id: toto
          text: SystemStatService.diskPercents[root.diskPath] ? `${SystemStatService.diskPercents[root.diskPath]}%` : "n/a"
          family: Settings.data.ui.fontFixed
          pointSize: root.textSize
          applyUiScale: false
          font.weight: Style.fontWeightMedium
          Layout.alignment: Qt.AlignCenter
          Layout.preferredWidth: root.isVertical ? -1 : root.percentTextWidth
          horizontalAlignment: root.isVertical ? Text.AlignHCenter : Text.AlignRight
          verticalAlignment: Text.AlignVCenter
          // Use highlight colors in vertical bar; otherwise invert text color to bar background when disk indicator active
          color: root.isVertical ? (root.diskCritical ? root.criticalColor : (root.diskWarning ? root.warningColor : root.textColor)) : ((root.diskWarning || root.diskCritical) ? NColor.mSurfaceVariant : root.textColor)
          Layout.row: root.isVertical ? 0 : 0
          Layout.column: root.isVertical ? 0 : 1
          scale: root.isVertical ? Math.min(1.0, root.width / implicitWidth) : 1.0
        }
      }

      MouseArea {
        id: diskHoverArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        cursorShape: Qt.PointingHandCursor
        onEntered: {
          TooltipService.show(diskContent, root.diskPath, BarService.getTooltipDirection());
        }
        onExited: {
          TooltipService.hide();
        }
      }
    }

    // Fan Speed Component
    Item {
      id: fanContainer
      Layout.preferredWidth: root.isVertical ? root.width : root.iconSize + root.fanTextWidth + (Style.marginXXS)
      Layout.preferredHeight: Style.capsuleHeight
      Layout.alignment: root.isVertical ? Qt.AlignHCenter : Qt.AlignVCenter
      visible: root.shouldShowFanSpeedMetric(root.showFanSpeed, FanService.available, FanService.sensorDetected)

      GridLayout {
        id: fanContent
        anchors.centerIn: parent
        flow: root.isVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rows: root.isVertical ? 2 : 1
        columns: root.isVertical ? 1 : 2
        rowSpacing: Style.marginXXS
        columnSpacing: Style.marginXXS

        Item {
          Layout.alignment: Qt.AlignCenter
          Layout.row: root.isVertical ? 1 : 0
          Layout.column: 0
          Layout.fillWidth: root.isVertical
          implicitWidth: root.iconSize
          implicitHeight: root.iconSize

          NIcon {
            icon: "propeller"
            pointSize: root.iconSize
            applyUiScale: false
            anchors.centerIn: parent
            color: root.iconColor
          }
        }

        NText {
          text: root.formatFanSpeedText(FanService.getMaxRpm())
          family: Settings.data.ui.fontFixed
          pointSize: root.textSize
          applyUiScale: false
          font.weight: Style.fontWeightMedium
          Layout.alignment: Qt.AlignCenter
          Layout.preferredWidth: root.isVertical ? -1 : root.fanTextWidth
          horizontalAlignment: root.isVertical ? Text.AlignHCenter : Text.AlignRight
          verticalAlignment: Text.AlignVCenter
          color: root.textColor
          Layout.row: root.isVertical ? 0 : 0
          Layout.column: root.isVertical ? 0 : 1
          scale: root.isVertical ? Math.min(1.0, root.width / implicitWidth) : 1.0
        }
      }

      MouseArea {
        id: fanHoverArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        cursorShape: Qt.PointingHandCursor
        onEntered: {
          var tooltipText = root.fanTooltipText(FanService.fans);
          TooltipService.show(fanContent, tooltipText, BarService.getTooltipDirection());
        }
        onExited: {
          TooltipService.hide();
        }
      }
    }
  }
}
