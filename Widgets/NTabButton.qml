import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Widgets

Rectangle {
  id: root

  // Public properties
  property string text: ""
  property bool checked: false
  property int tabIndex: 0
  property NTabBar tabBar: null

  // Internal state
  property bool isHovered: false

  signal clicked

  // Sizing
  Layout.fillWidth: true
  Layout.fillHeight: true

  // Styling
  radius: Style.radiusXS
  color: root.checked ? NColor.mPrimary : (root.isHovered ? NColor.mHover : NColor.mSurface)

  Behavior on color {
    ColorAnimation {
      duration: Style.animationFast
      easing.type: Easing.OutCubic
    }
  }

  NText {
    id: tabText
    anchors.centerIn: parent
    text: root.text
    pointSize: Style.fontSizeM
    font.weight: root.checked ? Style.fontWeightSemiBold : Style.fontWeightRegular
    color: root.checked ? NColor.mOnPrimary : root.isHovered ? NColor.mOnHover : NColor.mOnSurface
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter

    Behavior on color {
      ColorAnimation {
        duration: Style.animationFast
        easing.type: Easing.OutCubic
      }
    }
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onEntered: root.isHovered = true
    onExited: root.isHovered = false
    onClicked: {
      root.clicked();
      if (root.tabBar) {
        root.tabBar.currentIndex = root.tabIndex;
      }
    }
  }
}
