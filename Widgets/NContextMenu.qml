pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons

Popup {
  id: root

  property alias model: listView.model
  property real itemHeight: 36
  property real itemPadding: Style.marginM
  property int verticalPolicy: ScrollBar.AsNeeded
  property int horizontalPolicy: ScrollBar.AsNeeded

  signal triggered(string action)

  width: 180
  padding: Style.marginS

  background: Rectangle {
    color: NColor.mSurfaceVariant
    border.color: NColor.mOutline
    border.width: Style.borderS
    radius: Style.radiusM
  }

  contentItem: NListView {
    id: listView
    implicitHeight: contentHeight
    spacing: Style.marginXXS
    interactive: contentHeight > root.height
    verticalPolicy: root.verticalPolicy
    horizontalPolicy: root.horizontalPolicy

    delegate: ItemDelegate {
      id: menuItem
      required property var modelData
      required property int index
      readonly property bool itemVisible: modelData ? modelData.visible !== false : false
      readonly property bool itemEnabled: modelData ? modelData.enabled !== false : false
      readonly property string itemIcon: modelData ? (modelData.icon || "") : ""
      readonly property bool hasIcon: itemIcon !== ""
      readonly property string itemText: modelData ? (modelData.label || modelData.text || "") : ""
      readonly property string itemAction: modelData ? (modelData.action || modelData.key || index.toString()) : index.toString()

      width: listView.width
      height: itemVisible ? root.itemHeight : 0
      visible: itemVisible
      opacity: itemEnabled ? 1.0 : 0.5
      enabled: itemEnabled

      background: Rectangle {
        color: menuItem.hovered && menuItem.enabled ? NColor.mHover : NColor.transparent
        radius: Style.radiusS

        Behavior on color {
          ColorAnimation {
            duration: Style.animationFast
          }
        }
      }

      contentItem: RowLayout {
        spacing: Style.marginS

        // Optional icon
        NIcon {
          visible: menuItem.hasIcon
          icon: menuItem.itemIcon
          pointSize: Style.fontSizeM
          color: menuItem.hovered && menuItem.enabled ? NColor.mOnHover : NColor.mOnSurface
          Layout.leftMargin: root.itemPadding

          Behavior on color {
            ColorAnimation {
              duration: Style.animationFast
            }
          }
        }

        NText {
          text: menuItem.itemText
          pointSize: Style.fontSizeM
          color: menuItem.hovered && menuItem.enabled ? NColor.mOnHover : NColor.mOnSurface
          verticalAlignment: Text.AlignVCenter
          Layout.fillWidth: true
          Layout.leftMargin: menuItem.hasIcon ? 0 : root.itemPadding

          Behavior on color {
            ColorAnimation {
              duration: Style.animationFast
            }
          }
        }
      }

      onClicked: {
        if (enabled) {
          root.triggered(menuItem.itemAction);
          root.close();
        }
      }
    }
  }

  // Helper function to open at mouse position
  function openAt(x, y) {
    root.x = x;
    root.y = y;
    root.open();
  }

  // Helper function to open at item
  function openAtItem(item, mouseX, mouseY) {
    var pos = item.mapToItem(root.parent, mouseX || 0, mouseY || 0);
    openAt(pos.x, pos.y);
  }
}
