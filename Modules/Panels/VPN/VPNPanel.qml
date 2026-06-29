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

  preferredWidth: Math.round(400 * Style.uiScaleRatio)
  preferredHeight: Math.round(400 * Style.uiScaleRatio)

  readonly property bool hasConnections: Object.keys(VPNService.connections).length > 0

  panelContent: Rectangle {
    color: Color.transparent

    // Calculate content height based on header + connections list (or minimum for empty state)
    property real headerHeight: headerRow.implicitHeight + Style.marginM * 2
    property real connectionsHeight: connectionsList.implicitHeight
    property real calculatedHeight: headerHeight + connectionsHeight + Style.marginL * 2 + Style.marginM
    property real contentPreferredHeight: root.hasConnections ? Math.min(root.preferredHeight, calculatedHeight) : Math.min(root.preferredHeight, 280 * Style.uiScaleRatio)

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
            icon: "shield-lock"
            pointSize: Style.fontSizeXXL
            color: Color.mPrimary
          }

          NText {
            text: I18n.tr("vpn.panel.title")
            pointSize: Style.fontSizeL
            font.weight: Style.fontWeightBold
            color: Color.mOnSurface
            Layout.fillWidth: true
          }

          NIconButton {
            icon: VPNService.refreshing ? "stop" : "refresh"
            tooltipText: I18n.tr("tooltips.refresh")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: VPNService.refresh()
          }

          NIconButton {
            icon: "close"
            tooltipText: I18n.tr("tooltips.close")
            baseSize: Style.baseWidgetSize * 0.8
            onClicked: root.close()
          }
        }
      }

      // No VPN connections configured
      NBox {
        id: emptyBox
        visible: !root.hasConnections
        Layout.fillWidth: true
        Layout.fillHeight: true

        ColumnLayout {
          anchors.fill: parent
          spacing: Style.marginM

          Item {
            Layout.fillHeight: true
          }

          NIcon {
            icon: "shield"
            pointSize: 48
            color: Color.mOnSurfaceVariant
            Layout.alignment: Qt.AlignHCenter
          }

          NText {
            text: I18n.tr("vpn.panel.no-connections")
            pointSize: Style.fontSizeL
            color: Color.mOnSurfaceVariant
            Layout.alignment: Qt.AlignHCenter
          }

          NText {
            text: I18n.tr("vpn.panel.configure-message")
            pointSize: Style.fontSizeS
            color: Color.mOnSurfaceVariant
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
          }

          Item {
            Layout.fillHeight: true
          }
        }
      }

      // VPN connections list
      NScrollView {
        visible: root.hasConnections
        Layout.fillWidth: true
        Layout.fillHeight: true
        horizontalPolicy: ScrollBar.AlwaysOff
        verticalPolicy: ScrollBar.AsNeeded
        clip: true

        ColumnLayout {
          id: connectionsList
          width: parent.width
          spacing: Style.marginM

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
}
