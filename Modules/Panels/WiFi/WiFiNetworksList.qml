// The Repeater delegate uses the list owner and declares its injected modelData role.
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Services.Networking
import qs.Widgets

NBox {
  id: root

  property string label: ""
  property var model: []
  property string passwordSsid: ""
  property string expandedSsid: ""

  signal passwordRequested(string ssid)
  signal passwordSubmitted(string ssid, string password)
  signal passwordCancelled
  signal forgetRequested(string ssid)
  signal forgetConfirmed(string ssid)
  signal forgetCancelled

  Layout.fillWidth: true
  Layout.preferredHeight: column.implicitHeight + Style.marginM * 2
  visible: root.model.length > 0

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
      Layout.leftMargin: Style.marginS
    }

    Repeater {
      model: root.model

      Rectangle {
        id: networkItem

        required property var modelData

        readonly property string networkSsid: networkItem.modelData ? (networkItem.modelData.ssid || "") : ""
        readonly property bool networkConnected: networkItem.modelData ? networkItem.modelData.connected === true : false
        readonly property int networkSignal: networkItem.modelData ? (networkItem.modelData.signal || 0) : 0
        readonly property string networkSecurity: networkItem.modelData ? (networkItem.modelData.security || "Open") : "Open"
        readonly property bool networkExisting: networkItem.modelData ? networkItem.modelData.existing === true : false
        readonly property bool networkCached: networkItem.modelData ? networkItem.modelData.cached === true : false
        readonly property bool connectingToNetwork: NetworkService.connectingTo === networkItem.networkSsid
        readonly property bool disconnectingFromNetwork: NetworkService.disconnectingFrom === networkItem.networkSsid
        readonly property bool forgettingNetwork: NetworkService.forgettingNetwork === networkItem.networkSsid
        readonly property bool networkBusy: networkItem.connectingToNetwork || networkItem.disconnectingFromNetwork || networkItem.forgettingNetwork
        readonly property bool savedNetwork: networkItem.networkExisting || networkItem.networkCached

        function submitPassword(password) {
          pwdInput.text = "";
          root.passwordSubmitted(networkItem.networkSsid, password);
        }

        function cancelPassword() {
          pwdInput.text = "";
          root.passwordCancelled();
        }

        Layout.fillWidth: true
        Layout.leftMargin: Style.marginXS
        Layout.rightMargin: Style.marginXS
        implicitHeight: netColumn.implicitHeight + (Style.marginM * 2)
        radius: Style.radiusM
        border.width: Style.borderS
        border.color: networkItem.networkConnected ? NColor.mPrimary : NColor.mOutline

        opacity: (networkItem.disconnectingFromNetwork || networkItem.forgettingNetwork) ? 0.6 : 1.0

        color: networkItem.networkConnected ? Qt.rgba(NColor.mPrimary.r, NColor.mPrimary.g, NColor.mPrimary.b, 0.05) : NColor.mSurface

        Behavior on opacity {
          NumberAnimation {
            duration: Style.animationNormal
          }
        }

        ColumnLayout {
          id: netColumn
          width: parent.width - (Style.marginM * 2)
          x: Style.marginM
          y: Style.marginM
          spacing: Style.marginS

          // Main row
          RowLayout {
            Layout.fillWidth: true
            spacing: Style.marginS

            NIcon {
              icon: NetworkService.signalIcon(networkItem.networkSignal, networkItem.networkConnected)
              pointSize: Style.fontSizeXXL
              color: networkItem.networkConnected ? NColor.mPrimary : NColor.mOnSurface
            }

            ColumnLayout {
              Layout.fillWidth: true
              spacing: 2

              NText {
                text: networkItem.networkSsid
                pointSize: Style.fontSizeM
                font.weight: networkItem.networkConnected ? Style.fontWeightBold : Style.fontWeightMedium
                color: NColor.mOnSurface
                elide: Text.ElideRight
                Layout.fillWidth: true
              }

              RowLayout {
                spacing: Style.marginXS

                NText {
                  text: I18n.tr("system.signal-strength", {
                    "signal": networkItem.networkSignal
                  })
                  pointSize: Style.fontSizeXXS
                  color: NColor.mOnSurfaceVariant
                }

                NText {
                  text: "•"
                  pointSize: Style.fontSizeXXS
                  color: NColor.mOnSurfaceVariant
                }

                NText {
                  text: NetworkService.isSecured(networkItem.networkSecurity) ? networkItem.networkSecurity : "Open"
                  pointSize: Style.fontSizeXXS
                  color: NColor.mOnSurfaceVariant
                }

                Item {
                  Layout.preferredWidth: Style.marginXXS
                }

                // Status badges
                Rectangle {
                  visible: networkItem.networkConnected && !networkItem.disconnectingFromNetwork
                  color: NColor.mPrimary
                  radius: height * 0.5
                  Layout.preferredWidth: connectedText.implicitWidth + (Style.marginS * 2)
                  Layout.preferredHeight: connectedText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: connectedText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.connected")
                    pointSize: Style.fontSizeXXS
                    color: NColor.mOnPrimary
                  }
                }

                Rectangle {
                  visible: networkItem.disconnectingFromNetwork
                  color: NColor.mError
                  radius: height * 0.5
                  Layout.preferredWidth: disconnectingText.implicitWidth + (Style.marginS * 2)
                  Layout.preferredHeight: disconnectingText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: disconnectingText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.disconnecting")
                    pointSize: Style.fontSizeXXS
                    color: NColor.mOnPrimary
                  }
                }

                Rectangle {
                  visible: networkItem.forgettingNetwork
                  color: NColor.mError
                  radius: height * 0.5
                  Layout.preferredWidth: forgettingText.implicitWidth + (Style.marginS * 2)
                  Layout.preferredHeight: forgettingText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: forgettingText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.forgetting")
                    pointSize: Style.fontSizeXXS
                    color: NColor.mOnPrimary
                  }
                }

                Rectangle {
                  visible: networkItem.networkCached && !networkItem.networkConnected && !networkItem.forgettingNetwork && !networkItem.disconnectingFromNetwork
                  color: NColor.transparent
                  border.color: NColor.mOutline
                  border.width: Style.borderS
                  radius: height * 0.5
                  Layout.preferredWidth: savedText.implicitWidth + (Style.marginS * 2)
                  Layout.preferredHeight: savedText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: savedText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.saved")
                    pointSize: Style.fontSizeXXS
                    color: NColor.mOnSurfaceVariant
                  }
                }
              }
            }

            // Action area
            RowLayout {
              spacing: Style.marginS

              NBusyIndicator {
                visible: networkItem.networkBusy
                running: visible
                color: NColor.mPrimary
                size: Style.baseWidgetSize * 0.5
              }

              NIconButton {
                visible: networkItem.savedNetwork && !networkItem.networkConnected && !networkItem.networkBusy
                icon: "trash"
                tooltipText: I18n.tr("tooltips.forget-network")
                baseSize: Style.baseWidgetSize * 0.8
                onClicked: root.forgetRequested(networkItem.networkSsid)
              }

              NButton {
                visible: !networkItem.networkConnected && !networkItem.networkBusy && root.passwordSsid !== networkItem.networkSsid
                text: {
                  if (networkItem.savedNetwork)
                    return I18n.tr("wifi.panel.connect");
                  if (!NetworkService.isSecured(networkItem.networkSecurity))
                    return I18n.tr("wifi.panel.connect");
                  return I18n.tr("wifi.panel.password");
                }
                outlined: !hovered
                fontSize: Style.fontSizeXS
                enabled: !NetworkService.connecting
                onClicked: {
                  if (networkItem.savedNetwork || !NetworkService.isSecured(networkItem.networkSecurity)) {
                    NetworkService.connect(networkItem.networkSsid);
                  } else {
                    root.passwordRequested(networkItem.networkSsid);
                  }
                }
              }

              NButton {
                visible: networkItem.networkConnected && !networkItem.disconnectingFromNetwork
                text: I18n.tr("wifi.panel.disconnect")
                outlined: !hovered
                fontSize: Style.fontSizeXS
                backgroundColor: NColor.mError
                onClicked: NetworkService.disconnect(networkItem.networkSsid)
              }
            }
          }

          // Password input
          Rectangle {
            visible: root.passwordSsid === networkItem.networkSsid && !networkItem.disconnectingFromNetwork && !networkItem.forgettingNetwork
            Layout.fillWidth: true
            Layout.preferredHeight: passwordRow.implicitHeight + Style.marginS * 2
            color: NColor.mSurfaceVariant
            border.color: NColor.mOutline
            border.width: Style.borderS
            radius: Style.radiusS

            RowLayout {
              id: passwordRow
              anchors.fill: parent
              anchors.margins: Style.marginS
              spacing: Style.marginM

              Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Style.radiusXS
                color: NColor.mSurface
                border.color: pwdInput.activeFocus ? NColor.mSecondary : NColor.mOutline
                border.width: Style.borderS

                TextInput {
                  id: pwdInput
                  anchors.left: parent.left
                  anchors.right: parent.right
                  anchors.verticalCenter: parent.verticalCenter
                  anchors.margins: Style.marginS
                  font.family: Settings.data.ui.fontFixed
                  font.pointSize: Style.fontSizeS
                  color: NColor.mOnSurface
                  echoMode: TextInput.Password
                  selectByMouse: true
                  focus: visible
                  passwordCharacter: "●"
                  onVisibleChanged: {
                    text = "";
                    if (visible) {
                      forceActiveFocus();
                    }
                  }
                  onAccepted: {
                    if (text && !NetworkService.connecting) {
                      networkItem.submitPassword(text);
                    }
                  }

                  NText {
                    visible: parent.text.length === 0
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.tr("wifi.panel.enter-password")
                    color: NColor.mOnSurfaceVariant
                    pointSize: Style.fontSizeS
                  }
                }
              }

              NButton {
                text: I18n.tr("wifi.panel.connect")
                fontSize: Style.fontSizeXXS
                enabled: pwdInput.text.length > 0 && !NetworkService.connecting
                outlined: true
                onClicked: networkItem.submitPassword(pwdInput.text)
              }

              NIconButton {
                icon: "close"
                baseSize: Style.baseWidgetSize * 0.8
                onClicked: networkItem.cancelPassword()
              }
            }
          }

          // Forget network
          Rectangle {
            visible: root.expandedSsid === networkItem.networkSsid && !networkItem.disconnectingFromNetwork && !networkItem.forgettingNetwork
            Layout.fillWidth: true
            Layout.preferredHeight: forgetRow.implicitHeight + Style.marginS * 2
            color: NColor.mSurfaceVariant
            radius: Style.radiusS
            border.width: Style.borderS
            border.color: NColor.mOutline

            RowLayout {
              id: forgetRow
              anchors.fill: parent
              anchors.margins: Style.marginS
              spacing: Style.marginM

              RowLayout {
                NIcon {
                  icon: "trash"
                  pointSize: Style.fontSizeL
                  color: NColor.mError
                }

                NText {
                  text: I18n.tr("wifi.panel.forget-network")
                  pointSize: Style.fontSizeS
                  color: NColor.mError
                  Layout.fillWidth: true
                }
              }

              NButton {
                id: forgetButton
                text: I18n.tr("wifi.panel.forget")
                fontSize: Style.fontSizeXXS
                backgroundColor: NColor.mError
                outlined: forgetButton.hovered ? false : true
                onClicked: root.forgetConfirmed(networkItem.networkSsid)
              }

              NIconButton {
                icon: "close"
                baseSize: Style.baseWidgetSize * 0.8
                onClicked: root.forgetCancelled()
              }
            }
          }
        }
      }
    }
  }
}
