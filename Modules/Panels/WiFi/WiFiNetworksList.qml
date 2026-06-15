import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
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
      color: Color.mSecondary
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

        readonly property string networkSsid: modelData ? (modelData.ssid || "") : ""
        readonly property bool networkConnected: modelData ? modelData.connected === true : false
        readonly property int networkSignal: modelData ? (modelData.signal || 0) : 0
        readonly property string networkSecurity: modelData ? (modelData.security || "Open") : "Open"
        readonly property bool networkExisting: modelData ? modelData.existing === true : false
        readonly property bool networkCached: modelData ? modelData.cached === true : false
        readonly property bool connectingToNetwork: NetworkService.connectingTo === networkSsid
        readonly property bool disconnectingFromNetwork: NetworkService.disconnectingFrom === networkSsid
        readonly property bool forgettingNetwork: NetworkService.forgettingNetwork === networkSsid
        readonly property bool networkBusy: connectingToNetwork || disconnectingFromNetwork || forgettingNetwork
        readonly property bool savedNetwork: networkExisting || networkCached

        Layout.fillWidth: true
        Layout.leftMargin: Style.marginXS
        Layout.rightMargin: Style.marginXS
        implicitHeight: netColumn.implicitHeight + (Style.marginM * 2)
        radius: Style.radiusM
        border.width: Style.borderS
        border.color: networkConnected ? Color.mPrimary : Color.mOutline

        opacity: (disconnectingFromNetwork || forgettingNetwork) ? 0.6 : 1.0

        color: networkConnected ? Qt.rgba(Color.mPrimary.r, Color.mPrimary.g, Color.mPrimary.b, 0.05) : Color.mSurface

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
              icon: NetworkService.signalIcon(networkSignal, networkConnected)
              pointSize: Style.fontSizeXXL
              color: networkConnected ? Color.mPrimary : Color.mOnSurface
            }

            ColumnLayout {
              Layout.fillWidth: true
              spacing: 2

              NText {
                text: networkSsid
                pointSize: Style.fontSizeM
                font.weight: networkConnected ? Style.fontWeightBold : Style.fontWeightMedium
                color: Color.mOnSurface
                elide: Text.ElideRight
                Layout.fillWidth: true
              }

              RowLayout {
                spacing: Style.marginXS

                NText {
                  text: I18n.tr("system.signal-strength", {
                                  "signal": networkSignal
                                })
                  pointSize: Style.fontSizeXXS
                  color: Color.mOnSurfaceVariant
                }

                NText {
                  text: "•"
                  pointSize: Style.fontSizeXXS
                  color: Color.mOnSurfaceVariant
                }

                NText {
                  text: NetworkService.isSecured(networkSecurity) ? networkSecurity : "Open"
                  pointSize: Style.fontSizeXXS
                  color: Color.mOnSurfaceVariant
                }

                Item {
                  Layout.preferredWidth: Style.marginXXS
                }

                // Status badges
                Rectangle {
                  visible: networkConnected && !disconnectingFromNetwork
                  color: Color.mPrimary
                  radius: height * 0.5
                  width: connectedText.implicitWidth + (Style.marginS * 2)
                  height: connectedText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: connectedText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.connected")
                    pointSize: Style.fontSizeXXS
                    color: Color.mOnPrimary
                  }
                }

                Rectangle {
                  visible: disconnectingFromNetwork
                  color: Color.mError
                  radius: height * 0.5
                  width: disconnectingText.implicitWidth + (Style.marginS * 2)
                  height: disconnectingText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: disconnectingText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.disconnecting")
                    pointSize: Style.fontSizeXXS
                    color: Color.mOnPrimary
                  }
                }

                Rectangle {
                  visible: forgettingNetwork
                  color: Color.mError
                  radius: height * 0.5
                  width: forgettingText.implicitWidth + (Style.marginS * 2)
                  height: forgettingText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: forgettingText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.forgetting")
                    pointSize: Style.fontSizeXXS
                    color: Color.mOnPrimary
                  }
                }

                Rectangle {
                  visible: networkCached && !networkConnected && !forgettingNetwork && !disconnectingFromNetwork
                  color: Color.transparent
                  border.color: Color.mOutline
                  border.width: Style.borderS
                  radius: height * 0.5
                  width: savedText.implicitWidth + (Style.marginS * 2)
                  height: savedText.implicitHeight + (Style.marginXXS * 2)

                  NText {
                    id: savedText
                    anchors.centerIn: parent
                    text: I18n.tr("wifi.panel.saved")
                    pointSize: Style.fontSizeXXS
                    color: Color.mOnSurfaceVariant
                  }
                }
              }
            }

            // Action area
            RowLayout {
              spacing: Style.marginS

              NBusyIndicator {
                visible: networkBusy
                running: visible
                color: Color.mPrimary
                size: Style.baseWidgetSize * 0.5
              }

              NIconButton {
                visible: savedNetwork && !networkConnected && !networkBusy
                icon: "trash"
                tooltipText: I18n.tr("tooltips.forget-network")
                baseSize: Style.baseWidgetSize * 0.8
                onClicked: root.forgetRequested(networkSsid)
              }

              NButton {
                visible: !networkConnected && !networkBusy && root.passwordSsid !== networkSsid
                text: {
                  if (savedNetwork)
                    return I18n.tr("wifi.panel.connect");
                  if (!NetworkService.isSecured(networkSecurity))
                    return I18n.tr("wifi.panel.connect");
                  return I18n.tr("wifi.panel.password");
                }
                outlined: !hovered
                fontSize: Style.fontSizeXS
                enabled: !NetworkService.connecting
                onClicked: {
                  if (savedNetwork || !NetworkService.isSecured(networkSecurity)) {
                    NetworkService.connect(networkSsid);
                  } else {
                    root.passwordRequested(networkSsid);
                  }
                }
              }

              NButton {
                visible: networkConnected && !disconnectingFromNetwork
                text: I18n.tr("wifi.panel.disconnect")
                outlined: !hovered
                fontSize: Style.fontSizeXS
                backgroundColor: Color.mError
                onClicked: NetworkService.disconnect(networkSsid)
              }
            }
          }

          // Password input
          Rectangle {
            visible: root.passwordSsid === networkSsid && !disconnectingFromNetwork && !forgettingNetwork
            Layout.fillWidth: true
            height: passwordRow.implicitHeight + Style.marginS * 2
            color: Color.mSurfaceVariant
            border.color: Color.mOutline
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
                color: Color.mSurface
                border.color: pwdInput.activeFocus ? Color.mSecondary : Color.mOutline
                border.width: Style.borderS

                TextInput {
                  id: pwdInput
                  anchors.left: parent.left
                  anchors.right: parent.right
                  anchors.verticalCenter: parent.verticalCenter
                  anchors.margins: Style.marginS
                  font.family: Settings.data.ui.fontFixed
                  font.pointSize: Style.fontSizeS
                  color: Color.mOnSurface
                  echoMode: TextInput.Password
                  selectByMouse: true
                  focus: visible
                  passwordCharacter: "●"
                  onVisibleChanged: if (visible) {
                                      text = "";
                                      forceActiveFocus();
                                    }
                  onAccepted: {
                    if (text && !NetworkService.connecting) {
                      root.passwordSubmitted(networkSsid, text);
                    }
                  }

                  NText {
                    visible: parent.text.length === 0
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.tr("wifi.panel.enter-password")
                    color: Color.mOnSurfaceVariant
                    pointSize: Style.fontSizeS
                  }
                }
              }

              NButton {
                text: I18n.tr("wifi.panel.connect")
                fontSize: Style.fontSizeXXS
                enabled: pwdInput.text.length > 0 && !NetworkService.connecting
                outlined: true
                onClicked: root.passwordSubmitted(networkSsid, pwdInput.text)
              }

              NIconButton {
                icon: "close"
                baseSize: Style.baseWidgetSize * 0.8
                onClicked: root.passwordCancelled()
              }
            }
          }

          // Forget network
          Rectangle {
            visible: root.expandedSsid === networkSsid && !disconnectingFromNetwork && !forgettingNetwork
            Layout.fillWidth: true
            height: forgetRow.implicitHeight + Style.marginS * 2
            color: Color.mSurfaceVariant
            radius: Style.radiusS
            border.width: Style.borderS
            border.color: Color.mOutline

            RowLayout {
              id: forgetRow
              anchors.fill: parent
              anchors.margins: Style.marginS
              spacing: Style.marginM

              RowLayout {
                NIcon {
                  icon: "trash"
                  pointSize: Style.fontSizeL
                  color: Color.mError
                }

                NText {
                  text: I18n.tr("wifi.panel.forget-network")
                  pointSize: Style.fontSizeS
                  color: Color.mError
                  Layout.fillWidth: true
                }
              }

              NButton {
                id: forgetButton
                text: I18n.tr("wifi.panel.forget")
                fontSize: Style.fontSizeXXS
                backgroundColor: Color.mError
                outlined: forgetButton.hovered ? false : true
                onClicked: root.forgetConfirmed(networkSsid)
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
