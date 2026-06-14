import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Widgets

NIconButtonHot {
  property ShellScreen screen

  enabled: Settings.data.wallpaper.enabled
  icon: "wallpaper-selector"
  tooltipText: I18n.tr("quickSettings.wallpaperSelector.tooltip.action")
  onClicked: {
    const panel = PanelService.getPanel("wallpaperPanel", screen);
    if (panel)
      panel.toggle();
  }
  onRightClicked: WallpaperService.setRandomWallpaper()
}
