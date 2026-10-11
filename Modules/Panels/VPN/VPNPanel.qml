pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.Networking
import qs.Services.UI
import qs.Widgets

SmartPanel {
  id: root

  readonly property bool hasConnections: Object.keys(VPNService.connections).length > 0

  preferredHeight: Math.round(400 * Style.uiScaleRatio)
  preferredWidth: Math.round(400 * Style.uiScaleRatio)

  panelContent: Rectangle {
    property real calculatedHeight: headerHeight + connectionsHeight + Style.marginL * 2 + Style.marginM
    property real connectionsHeight: connectionsList.implicitHeight
    property real contentPreferredHeight: root.hasConnections ? Math.min(root.preferredHeight, calculatedHeight) : Math.min(root.preferredHeight, 280 * Style.uiScaleRatio)

    // Calculate content height based on header + connections list (or minimum for empty state)
    property real headerHeight: headerRow.implicitHeight + Style.marginM * 2

    color: NColor.transparent

    ColumnLayout {
      id: mainColumn

      anchors.fill: parent
      anchors.margins: Style.marginL
      spacing: Style.marginM

      // Header
      NBox {
        Layout.fillWidth: true
        Layout.preferredHeight: headerRow.implicitHeight + Style.marginM * 2

        RowLayout {
          id: headerRow

          anchors.fill: parent
          anchors.margins: Style.marginM
          spacing: Style.marginM

          NIcon {
            color: NColor.mPrimary
            icon: "shield-lock"
            pointSize: Style.fontSizeXXL
          }
          NText {
            Layout.fillWidth: true
            color: NColor.mOnSurface
            font.weight: Style.fontWeightBold
            pointSize: Style.fontSizeL
            text: I18n.tr("vpn.panel.title")
          }
          NIconButton {
            baseSize: Style.baseWidgetSize * 0.8
            icon: VPNService.refreshing ? "stop" : "refresh"
            tooltipText: I18n.tr("tooltips.refresh")

            onClicked: VPNService.refresh()
          }
          NIconButton {
            baseSize: Style.baseWidgetSize * 0.8
            icon: "close"
            tooltipText: I18n.tr("tooltips.close")

            onClicked: root.close()
          }
        }
      }

      // No VPN connections configured
      NBox {
        id: emptyBox

        Layout.fillHeight: true
        Layout.fillWidth: true
        visible: !root.hasConnections

        ColumnLayout {
          anchors.fill: parent
          spacing: Style.marginM

          Item {
            Layout.fillHeight: true
          }
          NIcon {
            Layout.alignment: Qt.AlignHCenter
            color: NColor.mOnSurfaceVariant
            icon: "shield"
            pointSize: 48
          }
          NText {
            Layout.alignment: Qt.AlignHCenter
            color: NColor.mOnSurfaceVariant
            pointSize: Style.fontSizeL
            text: I18n.tr("vpn.panel.no-connections")
          }
          NText {
            Layout.fillWidth: true
            color: NColor.mOnSurfaceVariant
            horizontalAlignment: Text.AlignHCenter
            pointSize: Style.fontSizeS
            text: I18n.tr("vpn.panel.configure-message")
            wrapMode: Text.WordWrap
          }
          Item {
            Layout.fillHeight: true
          }
        }
      }

      // VPN connections list
      NScrollView {
        Layout.fillHeight: true
        Layout.fillWidth: true
        clip: true
        horizontalPolicy: ScrollBar.AlwaysOff
        verticalPolicy: ScrollBar.AsNeeded
        visible: root.hasConnections

        ColumnLayout {
          id: connectionsList

          spacing: Style.marginM
          width: parent.width

          // Active connections
          VPNConnectionsList {
            label: I18n.tr("vpn.panel.active-connections")
            model: VPNService.activeConnections
          }

          // Inactive connections
          VPNConnectionsList {
            label: I18n.tr("vpn.panel.available-connections")
            model: VPNService.inactiveConnections
          }
        }
      }
    }
  }

  onClosed: VPNService.endPolling()
  onOpened: VPNService.beginPolling()
}
