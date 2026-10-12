import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Widgets

Rectangle {
  id: root

  // Public properties
  property int currentIndex: 0
  property int spacing: Style.marginS
  default property alias content: tabRow.children

  // Styling
  Layout.fillWidth: true
  implicitHeight: Style.baseWidgetSize + Style.marginXS * 2
  color: NColor.mSurfaceVariant
  radius: Style.radiusS

  RowLayout {
    id: tabRow
    anchors.fill: parent
    anchors.margins: Style.marginXS
    spacing: root.spacing

    onChildrenChanged: {
      for (const child of tabRow.children) {
        if (child instanceof NTabButton || child instanceof NIconTabButton) {
          child.tabBar = root;
        }
      }
    }
  }
}
