import QtQuick
import QtQuick.Controls
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Widgets

Item {
  id: root

  required property ShellScreen screen

  property string icon: ""
  property string text: ""
  property string suffix: ""
  property string tooltipText: ""
  property string density: ""
  property bool autoHide: false
  property bool forceOpen: false
  property bool forceClose: false
  property bool oppositeDirection: false
  property bool hovered: false
  property color customBackgroundColor: NColor.transparent
  property color customTextIconColor: NColor.transparent

  readonly property bool collapseToIcon: forceClose && !forceOpen

  // Effective shown state (true if hovered/animated open or forced)
  readonly property bool revealed: !forceClose && (forceOpen || showPill)

  signal shown
  signal hidden
  signal entered
  signal exited
  signal clicked
  signal rightClicked
  signal middleClicked
  signal wheel(int delta)

  // Internal state
  property bool showPill: false
  property bool shouldAnimateHide: false

  readonly property int pillHeight: Style.capsuleHeight
  readonly property int pillPaddingHorizontal: Math.round(Style.capsuleHeight * 0.2)
  readonly property int pillOverlap: Math.round(Style.capsuleHeight * 0.5)
  readonly property int pillMaxWidth: Math.max(1, Math.round(textItem.implicitWidth + pillPaddingHorizontal * 2 + pillOverlap))

  // Always prioritize hover color, then the custom one and finally the fallback color
  readonly property color bgColor: hovered ? NColor.mHover : (customBackgroundColor.a > 0) ? customBackgroundColor : Style.capsuleColor
  readonly property color fgColor: hovered ? NColor.mOnHover : (customTextIconColor.a > 0) ? customTextIconColor : NColor.mOnSurface

  readonly property real iconSize: {
    switch (root.density) {
    case "compact":
      return Math.max(1, Math.round(pillHeight * 0.65));
    default:
      return Math.max(1, Math.round(pillHeight * 0.48));
    }
  }

  readonly property real textSize: {
    switch (root.density) {
    case "compact":
      return Math.max(1, Math.round(pillHeight * 0.45));
    default:
      return Math.max(1, Math.round(pillHeight * 0.33));
    }
  }

  width: collapseToIcon ? pillHeight : pillHeight + Math.max(0, pill.width - pillOverlap)
  height: pillHeight

  Connections {
    target: root
    function onTooltipTextChanged() {
      if (root.hovered) {
        TooltipService.updateText(root.tooltipText);
      }
    }
  }

  // Unified background for the entire pill area to avoid overlapping opacity
  Rectangle {
    id: pillBackground
    width: root.collapseToIcon ? root.pillHeight : root.width
    height: root.pillHeight
    radius: Style.radiusM
    color: root.bgColor
    anchors.verticalCenter: parent.verticalCenter

    Behavior on color {
      ColorAnimation {
        duration: Style.animationFast
        easing.type: Easing.InOutQuad
      }
    }
  }

  Rectangle {
    id: pill

    width: root.revealed ? root.pillMaxWidth : 1
    height: root.pillHeight

    x: root.oppositeDirection ? (iconCircle.x + iconCircle.width / 2) : // Opens right
    (iconCircle.x + iconCircle.width / 2) - width // Opens left

    opacity: root.revealed ? Style.opacityFull : Style.opacityNone
    color: NColor.transparent // Make pill background transparent to avoid double opacity

    topLeftRadius: root.oppositeDirection ? 0 : Style.radiusM
    bottomLeftRadius: root.oppositeDirection ? 0 : Style.radiusM
    topRightRadius: root.oppositeDirection ? Style.radiusM : 0
    bottomRightRadius: root.oppositeDirection ? Style.radiusM : 0
    anchors.verticalCenter: parent.verticalCenter

    NText {
      id: textItem
      anchors.verticalCenter: parent.verticalCenter
      x: {
        // Better text horizontal centering
        var centerX = (pill.width - textItem.width) / 2;
        var offset = root.oppositeDirection ? Style.marginXS : -Style.marginXS;
        if (root.forceOpen) {
          // If its force open, the icon disc background is the same color as the bg pill move text slightly
          offset += root.oppositeDirection ? -Style.marginXXS : Style.marginXXS;
        }
        return centerX + offset;
      }
      text: root.text + root.suffix
      family: Settings.data.ui.fontFixed
      pointSize: root.textSize
      applyUiScale: false
      font.weight: Style.fontWeightBold
      color: root.fgColor
      visible: root.revealed
    }

    Behavior on width {
      enabled: showAnim.running || hideAnim.running
      NumberAnimation {
        duration: Style.animationNormal
        easing.type: Easing.OutCubic
      }
    }
    Behavior on opacity {
      enabled: showAnim.running || hideAnim.running
      NumberAnimation {
        duration: Style.animationFast
        easing.type: Easing.OutCubic
      }
    }
  }

  Rectangle {
    id: iconCircle
    width: root.pillHeight
    height: root.pillHeight
    radius: Math.min(Style.radiusL, iconCircle.width / 2)
    color: NColor.transparent // Make icon background transparent to avoid double opacity
    anchors.verticalCenter: parent.verticalCenter

    x: root.oppositeDirection ? 0 : (root.width - iconCircle.width)

    NIcon {
      id: iconGlyph
      icon: root.icon
      pointSize: root.iconSize
      applyUiScale: false
      color: root.fgColor
      // Center horizontally
      x: (iconCircle.width - iconGlyph.width) / 2
      // Center vertically accounting for font metrics
      y: (iconCircle.height - iconGlyph.height) / 2 + (iconGlyph.height - iconGlyph.contentHeight) / 2
    }
  }

  ParallelAnimation {
    id: showAnim
    running: false
    NumberAnimation {
      target: pill
      property: "width"
      from: 1
      to: root.pillMaxWidth
      duration: Style.animationNormal
      easing.type: Easing.OutCubic
    }
    NumberAnimation {
      target: pill
      property: "opacity"
      from: 0
      to: 1
      duration: Style.animationFast
      easing.type: Easing.OutCubic
    }
    onStarted: {
      root.showPill = true;
    }
    onStopped: {
      delayedHideAnim.start();
      root.shown();
    }
  }

  SequentialAnimation {
    id: delayedHideAnim
    running: false
    PauseAnimation {
      duration: 2500
    }
    ScriptAction {
      script: if (root.shouldAnimateHide) {
        hideAnim.start();
      }
    }
  }

  ParallelAnimation {
    id: hideAnim
    running: false
    NumberAnimation {
      target: pill
      property: "width"
      from: root.pillMaxWidth
      to: 1
      duration: Style.animationNormal
      easing.type: Easing.InCubic
    }
    NumberAnimation {
      target: pill
      property: "opacity"
      from: 1
      to: 0
      duration: Style.animationFast
      easing.type: Easing.InCubic
    }
    onStopped: {
      root.showPill = false;
      root.shouldAnimateHide = false;
      root.hidden();
    }
  }

  Timer {
    id: showTimer
    interval: Style.pillDelay
    onTriggered: {
      if (!root.showPill) {
        showAnim.start();
      }
    }
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
    onEntered: {
      root.hovered = true;
      root.entered();
      TooltipService.show(pill, root.tooltipText, BarService.getTooltipDirection(), (root.forceOpen || root.forceClose) ? Style.tooltipDelay : Style.tooltipDelayLong);
      if (root.forceClose) {
        return;
      }
      if (!root.forceOpen) {
        root.showDelayed();
      }
    }
    onExited: {
      root.hovered = false;
      root.exited();
      if (!root.forceOpen && !root.forceClose) {
        root.hide();
      }
      TooltipService.hide();
    }
    onClicked: function (mouse) {
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

  function show() {
    if (collapseToIcon)
      return;
    if (!showPill) {
      shouldAnimateHide = autoHide;
      showAnim.start();
    } else {
      hideAnim.stop();
      delayedHideAnim.restart();
    }
  }

  function hide() {
    if (collapseToIcon)
      return;
    if (forceOpen) {
      return;
    }
    if (showPill) {
      hideAnim.start();
    }
    showTimer.stop();
  }

  function showDelayed() {
    if (collapseToIcon)
      return;
    if (!showPill) {
      shouldAnimateHide = autoHide;
      showTimer.start();
    } else {
      hideAnim.stop();
      delayedHideAnim.restart();
    }
  }

  onForceOpenChanged: {
    if (forceOpen) {
      // Immediately lock open without animations
      showAnim.stop();
      hideAnim.stop();
      delayedHideAnim.stop();
      showPill = true;
    } else {
      hide();
    }
  }
}
