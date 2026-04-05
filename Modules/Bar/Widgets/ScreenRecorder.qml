import QtQuick
import Quickshell
import qs.Commons
import qs.Modules.Bar.Extras
import qs.Services.Media
import qs.Services.System
import qs.Services.UI
import qs.Widgets

// Screen Recording Indicator
NIconButton {
  id: root

  property ShellScreen screen

  icon: ScreenRecorderService.isPending ? "" : "camera-video"
  tooltipText: ScreenRecorderService.isRecording ? I18n.tr("tooltips.click-to-stop-recording") : I18n.tr("tooltips.click-to-start-recording")
  tooltipDirection: BarService.getTooltipDirection()
  density: Settings.data.bar.density
  baseSize: Style.capsuleHeight
  applyUiScale: false
  colorBg: ScreenRecorderService.isRecording ? Color.mPrimary : Style.capsuleColor
  colorFg: ScreenRecorderService.isRecording ? Color.mOnPrimary : Color.mOnSurface
  colorBorder: Color.transparent
  colorBorderHover: Color.transparent

  function handleClick() {
    if (!ScreenRecorderService.isAvailable) {
      ToastService.showError(I18n.tr("toast.recording.not-installed"), I18n.tr("toast.recording.not-installed-desc"));
      return;
    }
    if (ScreenRecorderService.isRecording || ScreenRecorderService.isPending) {
      ScreenRecorderService.stopRecording();
      return;
    }
    // Show source picker menu
    sourceMenu.model = ScreenRecorderService.captureSources;
    var popupMenuWindow = PanelService.getPopupMenuWindow(screen);
    if (popupMenuWindow) {
      popupMenuWindow.showContextMenu(sourceMenu);
      const pos = BarService.getContextMenuPosition(root, sourceMenu.implicitWidth, sourceMenu.implicitHeight);
      sourceMenu.openAtItem(root, pos.x, pos.y);
    }
  }

  NPopupContextMenu {
    id: sourceMenu
    model: ScreenRecorderService.captureSources
    onTriggered: action => {
      var popupMenuWindow = PanelService.getPopupMenuWindow(screen);
      if (popupMenuWindow) {
        popupMenuWindow.close();
      }
      Settings.data.screenRecorder.videoSource = action;
      ScreenRecorderService.toggleRecording();
    }
  }

  onClicked: handleClick()

  // Custom spinner shown only during pending start
  NIcon {
    id: pendingSpinner
    icon: "loader-2"
    visible: ScreenRecorderService.isPending
    pointSize: {
      switch (root.density) {
      case "compact":
        return Math.max(1, root.width * 0.65);
      default:
        return Math.max(1, root.width * 0.48);
      }
    }
    applyUiScale: root.applyUiScale
    color: root.enabled && root.hovering ? colorFgHover : colorFg
    anchors.centerIn: parent
    transformOrigin: Item.Center

    RotationAnimation on rotation {
      running: ScreenRecorderService.isPending
      from: 0
      to: 360
      duration: Style.animationSlow
      loops: Animation.Infinite
      onStopped: pendingSpinner.rotation = 0
    }
  }
}
