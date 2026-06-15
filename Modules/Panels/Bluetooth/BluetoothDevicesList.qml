import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Bluetooth
import Quickshell.Wayland
import qs.Commons
import qs.Services.Networking
import qs.Widgets

NBox {
  id: root

  property string label: ""
  property string tooltipText: ""
  property var model: {}

  Layout.fillWidth: true
  Layout.preferredHeight: column.implicitHeight + Style.marginM * 2

  ColumnLayout {
    id: column
    anchors.fill: parent
    anchors.margins: Style.marginM

    spacing: Style.marginM

    NText {
      text: root.label
      pointSize: Style.fontSizeS
      color: Color.mSecondary
      font.weight: Style.fontWeightBold
      visible: root.model.length > 0
      Layout.fillWidth: true
      Layout.leftMargin: Style.marginM
    }

    Repeater {
      id: deviceList
      Layout.fillWidth: true
      model: root.model
      visible: BluetoothService.adapter && BluetoothService.adapter.enabled

      Rectangle {
        id: device

        required property BluetoothDevice modelData
        required property int index

        readonly property bool devicePairing: modelData.pairing === true
        readonly property bool deviceBlocked: modelData.blocked === true
        readonly property bool deviceConnected: modelData.connected === true
        readonly property bool deviceConnecting: modelData.state === BluetoothDeviceState.Connecting
        readonly property string deviceDisplayName: modelData.name || modelData.deviceName || ""
        readonly property bool hasSignalStrength: modelData.signalStrength !== undefined
        readonly property int deviceSignalStrength: modelData.signalStrength || 0
        readonly property bool showSignalStrength: deviceSignalStrength > 0 && !devicePairing && !deviceBlocked
        readonly property bool hasBattery: modelData.batteryAvailable === true
        readonly property bool canConnect: BluetoothService.canConnect(modelData)
        readonly property bool canDisconnect: BluetoothService.canDisconnect(modelData)
        readonly property bool isBusy: BluetoothService.isDeviceBusy(modelData)

        function getContentColor(defaultColor = Color.mOnSurface) {
          if (devicePairing || deviceConnecting)
            return Color.mPrimary;
          if (deviceBlocked)
            return Color.mError;
          return defaultColor;
        }

        Layout.fillWidth: true
        Layout.preferredHeight: deviceLayout.implicitHeight + (Style.marginM * 2)
        radius: Style.radiusM
        color: Color.mSurface
        border.width: Style.borderS
        border.color: getContentColor(Color.mOutline)

        RowLayout {
          id: deviceLayout
          anchors.fill: parent
          anchors.margins: Style.marginM
          spacing: Style.marginM
          Layout.alignment: Qt.AlignVCenter

          // One device BT icon
          NIcon {
            icon: BluetoothService.getDeviceIcon(modelData)
            pointSize: Style.fontSizeXXL
            color: getContentColor(Color.mOnSurface)
            Layout.alignment: Qt.AlignVCenter
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Style.marginXXS

            // Device name
            NText {
              text: deviceDisplayName
              pointSize: Style.fontSizeM
              font.weight: deviceConnected ? Style.fontWeightBold : Style.fontWeightMedium
              elide: Text.ElideRight
              color: getContentColor(Color.mOnSurface)
              Layout.fillWidth: true
            }

            // Status
            NText {
              text: BluetoothService.getStatusString(modelData)
              visible: text !== ""
              pointSize: Style.fontSizeXS
              color: getContentColor(Color.mOnSurfaceVariant)
            }

            // Signal Strength
            RowLayout {
              visible: hasSignalStrength
              Layout.fillWidth: true
              spacing: Style.marginXS

              // Device signal strength - "Unknown" when not connected
              NText {
                text: BluetoothService.getSignalStrength(modelData)
                pointSize: Style.fontSizeXS
                color: getContentColor(Color.mOnSurfaceVariant)
              }

              NIcon {
                visible: showSignalStrength
                icon: BluetoothService.getSignalIcon(modelData)
                pointSize: Style.fontSizeXS
                color: getContentColor(Color.mOnSurface)
              }

              NText {
                visible: showSignalStrength
                text: showSignalStrength ? deviceSignalStrength + "%" : ""
                pointSize: Style.fontSizeXS
                color: getContentColor(Color.mOnSurface)
              }
            }

            // Battery
            NText {
              visible: hasBattery
              text: BluetoothService.getBattery(modelData)
              pointSize: Style.fontSizeXS
              color: getContentColor(Color.mOnSurfaceVariant)
            }
          }

          // Spacer to push connect button to the right
          Item {
            Layout.fillWidth: true
          }

          // Call to action
          NButton {
            id: button
            visible: !deviceConnecting
            enabled: (canConnect || canDisconnect) && !isBusy
            outlined: !button.hovered
            fontSize: Style.fontSizeXS
            fontWeight: Style.fontWeightMedium
            backgroundColor: {
              if (device.canDisconnect && !isBusy) {
                return Color.mError;
              }
              return Color.mPrimary;
            }
            tooltipText: root.tooltipText
            text: {
              if (devicePairing) {
                return I18n.tr("bluetooth.panel.pairing");
              }
              if (deviceBlocked) {
                return I18n.tr("bluetooth.panel.blocked");
              }
              if (deviceConnected) {
                return I18n.tr("bluetooth.panel.disconnect");
              }
              return I18n.tr("bluetooth.panel.connect");
            }
            icon: (isBusy ? "busy" : null)
            onClicked: {
              if (deviceConnected) {
                BluetoothService.disconnectDevice(modelData);
              } else {
                BluetoothService.connectDeviceWithTrust(modelData);
              }
            }
            onRightClicked: {
              BluetoothService.forgetDevice(modelData);
            }
          }
        }
      }
    }
  }
}
