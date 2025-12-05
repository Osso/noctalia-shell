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

      VPNConnectionItem {
        required property var modelData
        connection: modelData
        Layout.fillWidth: true
      }
    }
  }
}
