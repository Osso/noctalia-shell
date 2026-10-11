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
      Layout.fillWidth: true
      Layout.leftMargin: Style.marginS
      color: NColor.mSecondary
      font.weight: Style.fontWeightBold
      pointSize: Style.fontSizeS
      text: root.label
      visible: root.model.length > 0
    }
    Repeater {
      model: root.model

      VPNConnectionItem {
        id: connectionDelegate

        required property bool active
        required property string name
        required property string uuid

        Layout.fillWidth: true
        connectionActive: connectionDelegate.active
        connectionName: connectionDelegate.name
        connectionUuid: connectionDelegate.uuid
      }
    }
  }
}
