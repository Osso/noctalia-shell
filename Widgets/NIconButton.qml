import QtQuick
import Quickshell
import Quickshell.Widgets
import qs.Commons
import qs.Services.UI

Rectangle {
  id: root

  property real baseSize: Style.baseWidgetSize
  property bool applyUiScale: true

  property string icon
  property string tooltipText
  property string tooltipDirection: "auto"
  property string density: ""
  override property bool enabled: true
  property bool allowClickWhenDisabled: false
  property bool hovering: false

  property color colorBg: NColor.mSurfaceVariant
  property color colorFg: NColor.mPrimary
  property color colorBgHover: NColor.mHover
  property color colorFgHover: NColor.mOnHover
  property color colorBorder: NColor.mOutline
  property color colorBorderHover: NColor.mOutline

  signal entered
  signal exited
  signal clicked
  signal rightClicked
  signal middleClicked
  signal wheel(int angleDelta)

  implicitWidth: applyUiScale ? Math.round(baseSize * Style.uiScaleRatio) : Math.round(baseSize)
  implicitHeight: applyUiScale ? Math.round(baseSize * Style.uiScaleRatio) : Math.round(baseSize)

  opacity: root.enabled ? Style.opacityFull : Style.opacityMedium
  color: root.enabled && root.hovering ? colorBgHover : colorBg
  radius: Math.min(Style.radiusL, width / 2)
  border.color: root.enabled && root.hovering ? colorBorderHover : colorBorder
  border.width: Style.borderS

  Behavior on color {
    ColorAnimation {
      duration: Style.animationNormal
      easing.type: Easing.InOutQuad
    }
  }

  NIcon {
    icon: root.icon
    pointSize: {
      switch (root.density) {
      case "compact":
        return Math.max(1, root.width * 0.65);
      default:
        return Math.max(1, root.width * 0.48);
      }
    }
    applyUiScale: root.applyUiScale
    color: root.enabled && root.hovering ? root.colorFgHover : root.colorFg
    // Center horizontally
    x: (root.width - width) / 2
    // Center vertically accounting for font metrics
    y: (root.height - height) / 2 + (height - contentHeight) / 2

    Behavior on color {
      ColorAnimation {
        duration: Style.animationFast
        easing.type: Easing.InOutQuad
      }
    }
  }

  MouseArea {
    // Always enabled to allow hover/tooltip even when the button is disabled
    enabled: true
    anchors.fill: parent
    cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
    hoverEnabled: true
    onEntered: {
      root.hovering = root.enabled ? true : false;
      if (root.tooltipText) {
        TooltipService.show(parent, root.tooltipText, root.tooltipDirection);
      }
      root.entered();
    }
    onExited: {
      root.hovering = false;
      if (root.tooltipText) {
        TooltipService.hide();
      }
      root.exited();
    }
    onClicked: function (mouse) {
      if (root.tooltipText) {
        TooltipService.hide();
      }
      if (!root.enabled && !root.allowClickWhenDisabled) {
        return;
      }
      if (mouse.button === Qt.LeftButton) {
        root.clicked();
      } else if (mouse.button === Qt.RightButton) {
        root.rightClicked();
      } else if (mouse.button === Qt.MiddleButton) {
        root.middleClicked();
      }
    }
    onWheel: wheel => root.wheel(wheel.angleDelta.y)
  }
}
