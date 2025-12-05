import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Services.Networking
import qs.Services.UI
import qs.Widgets

NIconButtonHot {
  property ShellScreen screen

  icon: VPNService.hasActiveConnection ? "shield-lock" : "shield"
  hot: VPNService.hasActiveConnection
  tooltipText: {
    if (VPNService.hasActiveConnection) {
      return VPNService.activeConnections.map(c => c.name).join(", ");
    }
    return I18n.tr("tooltips.manage-vpn");
  }

  onClicked: PanelService.getPanel("vpnPanel", screen)?.toggle(this)
}
