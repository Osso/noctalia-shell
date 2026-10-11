pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell.Bluetooth
import qs.Commons
import qs.Services.Networking
import qs.Widgets

NBox {
  id: root

  property string label: ""
  property string tooltipText: ""
  property var model: []

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
      color: NColor.mSecondary
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

        readonly property bool devicePairing: modelData ? modelData.pairing === true : false
        readonly property bool deviceBlocked: modelData ? modelData.blocked === true : false
        readonly property bool deviceConnected: modelData ? modelData.connected === true : false
        readonly property bool deviceConnecting: modelData ? modelData.state === BluetoothDeviceState.Connecting : false
        readonly property string deviceDisplayName: modelData ? (modelData.name || modelData.deviceName || "") : ""
        readonly property bool hasBattery: modelData ? modelData.batteryAvailable === true : false
        readonly property bool canConnect: BluetoothService.canConnect(modelData)
        readonly property bool canDisconnect: BluetoothService.canDisconnect(modelData)
        readonly property bool isBusy: BluetoothService.isDeviceBusy(modelData)

        function getContentColor(defaultColor = NColor.mOnSurface) {
          if (devicePairing || deviceConnecting)
            return NColor.mPrimary;
          if (deviceBlocked)
            return NColor.mError;
          return defaultColor;
        }

        Layout.fillWidth: true
        Layout.preferredHeight: deviceLayout.implicitHeight + (Style.marginM * 2)
        radius: Style.radiusM
        color: NColor.mSurface
        border.width: Style.borderS
        border.color: getContentColor(NColor.mOutline)

        RowLayout {
          id: deviceLayout
          anchors.fill: parent
          anchors.margins: Style.marginM
          spacing: Style.marginM
          Layout.alignment: Qt.AlignVCenter

          // One device BT icon
          NIcon {
            icon: BluetoothService.getDeviceIcon(device.modelData)
            pointSize: Style.fontSizeXXL
            color: device.getContentColor(NColor.mOnSurface)
            Layout.alignment: Qt.AlignVCenter
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Style.marginXXS

            // Device name
            NText {
              text: device.deviceDisplayName
              pointSize: Style.fontSizeM
              font.weight: device.deviceConnected ? Style.fontWeightBold : Style.fontWeightMedium
              elide: Text.ElideRight
              color: device.getContentColor(NColor.mOnSurface)
              Layout.fillWidth: true
            }

            // Status
            NText {
              text: BluetoothService.getStatusString(device.modelData)
              visible: text !== ""
              pointSize: Style.fontSizeXS
              color: device.getContentColor(NColor.mOnSurfaceVariant)
            }

            // Battery
            NText {
              visible: device.hasBattery
              text: BluetoothService.getBattery(device.modelData)
              pointSize: Style.fontSizeXS
              color: device.getContentColor(NColor.mOnSurfaceVariant)
            }
          }

          // Spacer to push connect button to the right
          Item {
            Layout.fillWidth: true
          }

          // Call to action
          NButton {
            id: button
            visible: !device.deviceConnecting
            enabled: (device.canConnect || device.canDisconnect) && !device.isBusy
            outlined: !button.hovered
            fontSize: Style.fontSizeXS
            fontWeight: Style.fontWeightMedium
            backgroundColor: {
              if (device.canDisconnect && !device.isBusy) {
                return NColor.mError;
              }
              return NColor.mPrimary;
            }
            tooltipText: root.tooltipText
            text: {
              if (device.devicePairing) {
                return I18n.tr("bluetooth.panel.pairing");
              }
              if (device.deviceBlocked) {
                return I18n.tr("bluetooth.panel.blocked");
              }
              if (device.deviceConnected) {
                return I18n.tr("bluetooth.panel.disconnect");
              }
              return I18n.tr("bluetooth.panel.connect");
            }
            icon: (device.isBusy ? "busy" : null)
            onClicked: {
              if (device.deviceConnected) {
                BluetoothService.disconnectDevice(device.modelData);
              } else {
                BluetoothService.connectDeviceWithTrust(device.modelData);
              }
            }
            onRightClicked: {
              BluetoothService.forgetDevice(device.modelData);
            }
          }
        }
      }
    }
  }
}
