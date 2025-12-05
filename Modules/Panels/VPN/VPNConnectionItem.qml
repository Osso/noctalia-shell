import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Services.Networking
import qs.Widgets

Rectangle {
  id: root

  required property var connection

  readonly property bool isActive: connection && connection.active
  readonly property bool isConnecting: VPNService.connectingUuid === connection?.uuid
  readonly property bool isDisconnecting: VPNService.disconnectingUuid === connection?.uuid
  readonly property bool isBusy: isConnecting || isDisconnecting

  Layout.fillWidth: true
  Layout.preferredHeight: itemLayout.implicitHeight + (Style.marginM * 2)
  radius: Style.radiusM
  color: Color.mSurface
  border.width: Style.borderS
  border.color: isActive ? Color.mPrimary : Color.mOutline

  RowLayout {
    id: itemLayout
    anchors.fill: parent
    anchors.margins: Style.marginM
    spacing: Style.marginM

    NIcon {
      icon: isActive ? "shield-lock" : "shield"
      pointSize: Style.fontSizeXXL
      color: isActive ? Color.mPrimary : Color.mOnSurface
      Layout.alignment: Qt.AlignVCenter
    }

    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.marginXXS

      NText {
        text: connection?.name || ""
        pointSize: Style.fontSizeM
        font.weight: isActive ? Style.fontWeightBold : Style.fontWeightMedium
        elide: Text.ElideRight
        color: isActive ? Color.mPrimary : Color.mOnSurface
        Layout.fillWidth: true
      }

      NText {
        text: {
          if (isConnecting) return I18n.tr("vpn.panel.connecting");
          if (isDisconnecting) return I18n.tr("vpn.panel.disconnecting");
          if (isActive) return I18n.tr("vpn.panel.connected");
          return I18n.tr("vpn.panel.disconnected");
        }
        pointSize: Style.fontSizeXS
        color: isActive ? Color.mPrimary : Color.mOnSurfaceVariant
      }
    }

    Item {
      Layout.fillWidth: true
    }

    NButton {
      enabled: !isBusy
      outlined: !hovered
      fontSize: Style.fontSizeXS
      fontWeight: Style.fontWeightMedium
      backgroundColor: isActive ? Color.mError : Color.mPrimary
      text: {
        if (isConnecting) return I18n.tr("vpn.panel.connecting");
        if (isDisconnecting) return I18n.tr("vpn.panel.disconnecting");
        if (isActive) return I18n.tr("vpn.panel.disconnect");
        return I18n.tr("vpn.panel.connect");
      }
      icon: isBusy ? "busy" : null
      onClicked: {
        if (isActive) {
          VPNService.disconnect(connection.uuid);
        } else {
          VPNService.connect(connection.uuid);
        }
      }
    }
  }
}
