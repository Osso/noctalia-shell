import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Services.UI
import qs.Widgets

Rectangle {
  id: root

  // Public properties
  property string icon: ""
  property string tooltipText: ""
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

  NIcon {
    id: tabIcon
    anchors.centerIn: parent
    icon: root.icon
    pointSize: Style.fontSizeL
    color: root.checked ? NColor.mOnPrimary : root.isHovered ? NColor.mOnHover : NColor.mOnSurface

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
    onEntered: {
      root.isHovered = true;
      if (root.tooltipText) {
        TooltipService.show(parent, root.tooltipText);
      }
    }
    onExited: {
      root.isHovered = false;
      if (root.tooltipText) {
        TooltipService.hide();
      }
    }
    onClicked: {
      if (root.tooltipText) {
        TooltipService.hide();
      }
      root.clicked();
      if (root.tabBar) {
        root.tabBar.currentIndex = root.tabIndex;
      }
    }
  }
}
