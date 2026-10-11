import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Services.Networking
import qs.Widgets

Rectangle {
  id: root

  required property bool connectionActive
  required property string connectionName
  required property string connectionUuid
  readonly property bool isActive: root.connectionActive
  readonly property bool isBusy: root.isConnecting || root.isDisconnecting
  readonly property bool isConnecting: VPNService.connectingUuid === root.connectionUuid
  readonly property bool isDisconnecting: VPNService.disconnectingUuid === root.connectionUuid

  Layout.fillWidth: true
  Layout.preferredHeight: itemLayout.implicitHeight + (Style.marginM * 2)
  border.color: root.isActive ? NColor.mPrimary : NColor.mOutline
  border.width: Style.borderS
  color: NColor.mSurface
  radius: Style.radiusM

  RowLayout {
    id: itemLayout

    anchors.fill: parent
    anchors.margins: Style.marginM
    spacing: Style.marginM

    NIcon {
      Layout.alignment: Qt.AlignVCenter
      color: root.isActive ? NColor.mPrimary : NColor.mOnSurface
      icon: root.isActive ? "shield-lock" : "shield"
      pointSize: Style.fontSizeXXL
    }
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.marginXXS

      NText {
        Layout.fillWidth: true
        color: root.isActive ? NColor.mPrimary : NColor.mOnSurface
        elide: Text.ElideRight
        font.weight: root.isActive ? Style.fontWeightBold : Style.fontWeightMedium
        pointSize: Style.fontSizeM
        text: root.connectionName
      }
      NText {
        color: root.isActive ? NColor.mPrimary : NColor.mOnSurfaceVariant
        pointSize: Style.fontSizeXS
        text: {
          if (root.isConnecting)
            return I18n.tr("vpn.panel.connecting");

          if (root.isDisconnecting)
            return I18n.tr("vpn.panel.disconnecting");

          if (root.isActive)
            return I18n.tr("vpn.panel.connected");

          return I18n.tr("vpn.panel.disconnected");
        }
      }
    }
    Item {
      Layout.fillWidth: true
    }
    NButton {
      backgroundColor: root.isActive ? NColor.mError : NColor.mPrimary
      enabled: !root.isBusy
      fontSize: Style.fontSizeXS
      fontWeight: Style.fontWeightMedium
      icon: root.isBusy ? "busy" : null
      outlined: !hovered
      text: {
        if (root.isConnecting)
          return I18n.tr("vpn.panel.connecting");

        if (root.isDisconnecting)
          return I18n.tr("vpn.panel.disconnecting");

        if (root.isActive)
          return I18n.tr("vpn.panel.disconnect");

        return I18n.tr("vpn.panel.connect");
      }

      onClicked: {
        if (root.isActive)
          VPNService.disconnect(root.connectionUuid);
        else
          VPNService.connect(root.connectionUuid);
      }
    }
  }
}
