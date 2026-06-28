import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.System
import qs.Widgets

SmartPanel {
  id: root

  preferredWidth: Math.round(500 * Style.uiScaleRatio)
  preferredHeight: Math.round(600 * Style.uiScaleRatio)

  // Local binding to ProcessService data
  property var processList: ProcessService.processes
  property int processCount: ProcessService.processCount

  readonly property int processCpuColumnWidth: 55
  readonly property int processMemoryColumnWidth: 65
  readonly property int processPidColumnWidth: 50
  readonly property real processSortColumnWidth: Style.baseWidgetSize * 0.6

  // Activate/deactivate process monitoring when panel opens/closes
  onOpened: {
    ProcessService.addRef();
  }

  onClosed: {
    ProcessService.removeRef();
  }

  panelContent: Item {
    property real contentPreferredHeight: mainLayout.implicitHeight + Style.marginL * 2

    ColumnLayout {
      id: mainLayout
      anchors.fill: parent
      anchors.margins: Style.marginS
      spacing: 2

      // HEADER
      NBox {
        Layout.fillWidth: true
        implicitHeight: headerRow.implicitHeight + (Style.marginM * 2)

        RowLayout {
          id: headerRow
          anchors.fill: parent
          anchors.margins: Style.marginM
          spacing: Style.marginM

          NIcon {
            pointSize: Style.fontSizeXXL
            color: Color.mPrimary
            icon: "process"
          }

          ColumnLayout {
            spacing: Style.marginXXS
            Layout.fillWidth: true

            NText {
              text: I18n.tr("process.panel-title")
              pointSize: Style.fontSizeL
              font.weight: Style.fontWeightBold
              color: Color.mOnSurface
              Layout.fillWidth: true
            }

            NText {
              text: I18n.tr("process.process-count", { count: ProcessService.processCount })
              pointSize: Style.fontSizeS
              color: Color.mOnSurfaceVariant
              wrapMode: Text.Wrap
              Layout.fillWidth: true
            }
          }

          NIconButton {
            icon: "close"
            tooltipText: I18n.tr("tooltips.close")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: root.close()
          }
        }
      }

      // SYSTEM OVERVIEW - CPU, Memory, Processes cards
      NBox {
        Layout.fillWidth: true
        implicitHeight: overviewRow.implicitHeight + Style.marginM * 2

        RowLayout {
          id: overviewRow
          anchors.fill: parent
          anchors.margins: Style.marginM
          spacing: Style.marginS

          // CPU Card
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            radius: Style.radiusS
            color: ProcessService.sortBy === "cpu"
                   ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.16)
                   : cpuMouseArea.containsMouse
                     ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.12)
                     : Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.08)
            border.color: ProcessService.sortBy === "cpu"
                          ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.4)
                          : Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.2)
            border.width: ProcessService.sortBy === "cpu" ? 2 : 1

            MouseArea {
              id: cpuMouseArea
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: ProcessService.setSortBy("cpu")
            }

            ColumnLayout {
              anchors.left: parent.left
              anchors.leftMargin: Style.marginS
              anchors.verticalCenter: parent.verticalCenter
              spacing: 2

              NText {
                text: "CPU"
                pointSize: Style.fontSizeXS
                font.weight: Style.fontWeightMedium
                color: ProcessService.sortBy === "cpu" ? Color.mPrimary : Color.mOnSurfaceVariant
              }

              NText {
                text: SystemStatService.cpuUsage.toFixed(1) + "%"
                pointSize: Style.fontSizeL
                family: Settings.data.ui.fontFixed
                font.weight: Style.fontWeightBold
                color: Color.mOnSurface
              }
            }

            Behavior on color { ColorAnimation { duration: Style.animationFaster } }
            Behavior on border.color { ColorAnimation { duration: Style.animationFaster } }
          }

          // Memory Card
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            radius: Style.radiusS
            color: ProcessService.sortBy === "memory"
                   ? Qt.rgba(Color.mSecondary.r, Color.mSecondary.g, Color.mSecondary.b, 0.16)
                   : memMouseArea.containsMouse
                     ? Qt.rgba(Color.mSecondary.r, Color.mSecondary.g, Color.mSecondary.b, 0.12)
                     : Qt.rgba(Color.mSecondary.r, Color.mSecondary.g, Color.mSecondary.b, 0.08)
            border.color: ProcessService.sortBy === "memory"
                          ? Qt.rgba(Color.mSecondary.r, Color.mSecondary.g, Color.mSecondary.b, 0.4)
                          : Qt.rgba(Color.mSecondary.r, Color.mSecondary.g, Color.mSecondary.b, 0.2)
            border.width: ProcessService.sortBy === "memory" ? 2 : 1

            MouseArea {
              id: memMouseArea
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: ProcessService.setSortBy("memory")
            }

            ColumnLayout {
              anchors.left: parent.left
              anchors.leftMargin: Style.marginS
              anchors.verticalCenter: parent.verticalCenter
              spacing: 2

              NText {
                text: I18n.tr("process.memory")
                pointSize: Style.fontSizeXS
                font.weight: Style.fontWeightMedium
                color: ProcessService.sortBy === "memory" ? Color.mSecondary : Color.mOnSurfaceVariant
              }

              NText {
                text: SystemStatService.memGb + " GB"
                pointSize: Style.fontSizeL
                family: Settings.data.ui.fontFixed
                font.weight: Style.fontWeightBold
                color: Color.mOnSurface
              }
            }

            Behavior on color { ColorAnimation { duration: Style.animationFaster } }
            Behavior on border.color { ColorAnimation { duration: Style.animationFaster } }
          }

          // Processes Card
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            radius: Style.radiusS
            color: ProcessService.sortBy === "pid"
                   ? Qt.rgba(Color.mTertiary.r, Color.mTertiary.g, Color.mTertiary.b, 0.16)
                   : pidMouseArea.containsMouse
                     ? Qt.rgba(Color.mTertiary.r, Color.mTertiary.g, Color.mTertiary.b, 0.12)
                     : Qt.rgba(Color.mTertiary.r, Color.mTertiary.g, Color.mTertiary.b, 0.08)
            border.color: ProcessService.sortBy === "pid"
                          ? Qt.rgba(Color.mTertiary.r, Color.mTertiary.g, Color.mTertiary.b, 0.4)
                          : Qt.rgba(Color.mTertiary.r, Color.mTertiary.g, Color.mTertiary.b, 0.2)
            border.width: ProcessService.sortBy === "pid" ? 2 : 1

            MouseArea {
              id: pidMouseArea
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: ProcessService.setSortBy("pid")
            }

            ColumnLayout {
              anchors.left: parent.left
              anchors.leftMargin: Style.marginS
              anchors.verticalCenter: parent.verticalCenter
              spacing: 2

              NText {
                text: I18n.tr("process.processes")
                pointSize: Style.fontSizeXS
                font.weight: Style.fontWeightMedium
                color: ProcessService.sortBy === "pid" ? Color.mTertiary : Color.mOnSurfaceVariant
              }

              NText {
                text: ProcessService.processCount.toString()
                pointSize: Style.fontSizeL
                family: Settings.data.ui.fontFixed
                font.weight: Style.fontWeightBold
                color: Color.mOnSurface
              }
            }

            Behavior on color { ColorAnimation { duration: Style.animationFaster } }
            Behavior on border.color { ColorAnimation { duration: Style.animationFaster } }
          }
        }
      }

      // COLUMN HEADERS
      NBox {
        Layout.fillWidth: true
        implicitHeight: headerLayout.implicitHeight + Style.marginS * 2

        RowLayout {
          id: headerLayout
          anchors.fill: parent
          anchors.margins: Style.marginS
          spacing: Style.marginS

          NIcon {
            icon: "process"
            pointSize: Style.fontSizeM
            opacity: 0
          }

          // Process name header
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 24
            radius: Style.radiusXS
            color: ProcessService.sortBy === "name"
                   ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.2)
                   : nameHeaderMouse.containsMouse
                     ? Qt.rgba(Color.mOnSurface.r, Color.mOnSurface.g, Color.mOnSurface.b, 0.08)
                     : "transparent"

            MouseArea {
              id: nameHeaderMouse
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: ProcessService.setSortBy("name")
            }

            NText {
              anchors.left: parent.left
              anchors.leftMargin: Style.marginXS
              anchors.verticalCenter: parent.verticalCenter
              text: I18n.tr("process.header-process")
              pointSize: Style.fontSizeXS
              font.weight: Style.fontWeightMedium
              color: ProcessService.sortBy === "name" ? Color.mPrimary : Color.mOnSurfaceVariant
            }
          }

          // CPU header
          Rectangle {
            Layout.preferredWidth: root.processCpuColumnWidth
            Layout.preferredHeight: 24
            radius: Style.radiusXS
            color: ProcessService.sortBy === "cpu"
                   ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.2)
                   : cpuHeaderMouse.containsMouse
                     ? Qt.rgba(Color.mOnSurface.r, Color.mOnSurface.g, Color.mOnSurface.b, 0.08)
                     : "transparent"

            MouseArea {
              id: cpuHeaderMouse
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: ProcessService.setSortBy("cpu")
            }

            NText {
              anchors.centerIn: parent
              text: "CPU"
              pointSize: Style.fontSizeXS
              font.weight: Style.fontWeightMedium
              color: ProcessService.sortBy === "cpu" ? Color.mPrimary : Color.mOnSurfaceVariant
            }
          }

          // Memory header
          Rectangle {
            Layout.preferredWidth: root.processMemoryColumnWidth
            Layout.preferredHeight: 24
            radius: Style.radiusXS
            color: ProcessService.sortBy === "memory"
                   ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.2)
                   : memHeaderMouse.containsMouse
                     ? Qt.rgba(Color.mOnSurface.r, Color.mOnSurface.g, Color.mOnSurface.b, 0.08)
                     : "transparent"

            MouseArea {
              id: memHeaderMouse
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: ProcessService.setSortBy("memory")
            }

            NText {
              anchors.centerIn: parent
              text: I18n.tr("process.header-memory")
              pointSize: Style.fontSizeXS
              font.weight: Style.fontWeightMedium
              color: ProcessService.sortBy === "memory" ? Color.mPrimary : Color.mOnSurfaceVariant
            }
          }

          // PID header
          Rectangle {
            Layout.preferredWidth: root.processPidColumnWidth
            Layout.preferredHeight: 24
            radius: Style.radiusXS
            color: ProcessService.sortBy === "pid"
                   ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.2)
                   : pidHeaderMouse.containsMouse
                     ? Qt.rgba(Color.mOnSurface.r, Color.mOnSurface.g, Color.mOnSurface.b, 0.08)
                     : "transparent"

            MouseArea {
              id: pidHeaderMouse
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: ProcessService.setSortBy("pid")
            }

            NText {
              anchors.centerIn: parent
              text: "PID"
              pointSize: Style.fontSizeXS
              font.weight: Style.fontWeightMedium
              color: ProcessService.sortBy === "pid" ? Color.mPrimary : Color.mOnSurfaceVariant
            }
          }

          // Sort direction toggle
          NIconButton {
            icon: ProcessService.sortDescending ? "arrow-down" : "arrow-up"
            baseSize: root.processSortColumnWidth
            onClicked: ProcessService.toggleSortDirection()
            tooltipText: ProcessService.sortDescending ? I18n.tr("process.sort-descending") : I18n.tr("process.sort-ascending")
          }
        }
      }

      // PROCESS LIST - Repeater directly in ColumnLayout (only way that works)
      Repeater {
        id: processRepeater
        model: root.processList

        delegate: Rectangle {
          required property var modelData
          required property int index

          readonly property string processCommand: modelData ? (modelData.command || "") : ""
          readonly property string processName: modelData ? (modelData.displayName || processCommand) : processCommand
          readonly property real processCpu: modelData ? (modelData.cpu || 0) : 0
          readonly property int processMemoryKb: modelData ? (modelData.memoryKB || 0) : 0
          readonly property int processPid: modelData ? (modelData.pid || 0) : 0
          readonly property color processCpuColor: {
            if (processCpu > 50)
              return Color.mError;
            if (processCpu > 20)
              return Color.mWarning;
            return Color.mOnSurfaceVariant;
          }

          Layout.fillWidth: true
          Layout.preferredHeight: 32
          Layout.topMargin: index === 0 ? 0 : -2
          radius: Style.radiusS
          color: delegateMouseArea.containsMouse
                 ? Qt.rgba(Color.mOnSurface.r, Color.mOnSurface.g, Color.mOnSurface.b, 0.12)
                 : Color.mSurfaceVariant

          MouseArea {
            id: delegateMouseArea
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.RightButton
            onClicked: mouse => {
              if (mouse.button === Qt.RightButton) {
                processContextMenu.processData = modelData;
                processContextMenu.popup();
              }
            }
          }

          RowLayout {
            id: processRowLayout
            anchors.fill: parent
            anchors.leftMargin: Style.marginS
            anchors.rightMargin: Style.marginS
            spacing: Style.marginS

            // Process icon
            NIcon {
              icon: ProcessService.getProcessIcon(processCommand)
              pointSize: Style.fontSizeM
              color: Color.mOnSurfaceVariant
            }

            // Process name
            NText {
              Layout.fillWidth: true
              text: processName
              pointSize: Style.fontSizeS
              color: Color.mOnSurface
              elide: Text.ElideRight
            }

            // CPU usage
            NText {
              Layout.preferredWidth: root.processCpuColumnWidth
              text: ProcessService.formatCpu(processCpu)
              pointSize: Style.fontSizeS
              family: Settings.data.ui.fontFixed
              color: processCpuColor
              horizontalAlignment: Text.AlignRight
            }

            // Memory usage
            NText {
              Layout.preferredWidth: root.processMemoryColumnWidth
              text: ProcessService.formatMemory(processMemoryKb)
              pointSize: Style.fontSizeS
              family: Settings.data.ui.fontFixed
              color: Color.mOnSurfaceVariant
              horizontalAlignment: Text.AlignRight
            }

            // PID
            NText {
              Layout.preferredWidth: root.processPidColumnWidth
              text: processPid.toString()
              pointSize: Style.fontSizeXS
              family: Settings.data.ui.fontFixed
              color: Color.mOnSurfaceVariant
              horizontalAlignment: Text.AlignRight
            }

            Item {
              Layout.preferredWidth: root.processSortColumnWidth
            }
          }

          Behavior on color { ColorAnimation { duration: Style.animationFaster } }
        }
      }

      // Context menu for process actions
      Menu {
          id: processContextMenu
          property var processData: null

          MenuItem {
            text: I18n.tr("process.kill")
            icon.name: "process-stop"
            onTriggered: {
              if (processContextMenu.processData) {
                ProcessService.killProcess(processContextMenu.processData.pid);
              }
            }
          }

          MenuItem {
            text: I18n.tr("process.force-kill")
            icon.name: "edit-delete"
            onTriggered: {
              if (processContextMenu.processData) {
                ProcessService.forceKillProcess(processContextMenu.processData.pid);
              }
            }
          }

          MenuSeparator {}

          MenuItem {
            text: I18n.tr("process.copy-pid")
            icon.name: "edit-copy"
            onTriggered: {
              if (processContextMenu.processData) {
                // Copy PID to clipboard
                Quickshell.execDetached(["wl-copy", processContextMenu.processData.pid.toString()]);
              }
            }
          }

          MenuItem {
            text: I18n.tr("process.copy-command")
            icon.name: "edit-copy"
            onTriggered: {
              if (processContextMenu.processData) {
                Quickshell.execDetached(["wl-copy", processContextMenu.processData.fullCommand]);
              }
            }
          }
      }
    }
  }
}
