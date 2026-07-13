import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland

PanelWindow {
  id: root

  required property ShellScreen targetScreen
  required property string message
  required property string settingsPath
  signal retryRequested

  screen: targetScreen
  implicitHeight: 208
  color: "transparent"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.exclusionMode: ExclusionMode.Ignore
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
  WlrLayershell.namespace: "noctalia-settings-load-error"

  anchors {
    top: true
    left: true
    right: true
  }

  mask: Region {
    x: errorCard.x
    y: errorCard.y
    width: errorCard.width
    height: errorCard.height
  }

  Rectangle {
    id: errorCard
    anchors.centerIn: parent
    width: Math.max(0, Math.min(parent.width - 48, 720))
    height: 168
    radius: 12
    color: "#2b1114"
    border.color: "#ffb4ab"
    border.width: 1

    ColumnLayout {
      anchors.fill: parent
      anchors.margins: 20
      spacing: 8

      Text {
        Layout.fillWidth: true
        text: "Noctalia could not load its settings"
        color: "#ffb4ab"
        font.pixelSize: 20
        font.bold: true
      }

      Text {
        Layout.fillWidth: true
        text: root.message
        color: "#f4dedc"
        wrapMode: Text.Wrap
        maximumLineCount: 3
        elide: Text.ElideRight
      }

      Text {
        Layout.fillWidth: true
        text: root.settingsPath
        color: "#d8c2c0"
        elide: Text.ElideMiddle
      }

      Button {
        id: retryButton
        implicitWidth: 96
        implicitHeight: 44
        text: "Retry"
        Accessible.name: "Retry loading Noctalia settings"
        Component.onCompleted: retryButton.forceActiveFocus()
        onClicked: root.retryRequested()
      }
    }
  }
}
