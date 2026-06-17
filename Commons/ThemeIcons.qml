pragma Singleton

import QtQuick
import Quickshell
import "../Helpers/ThemeIconResolver.js" as ThemeIconResolver

Singleton {
  id: root

  function iconFromName(iconName, fallbackName) {
    try {
      return ThemeIconResolver.resolveIconPath(Quickshell, iconName, fallbackName);
    } catch (e2) {
      return "";
    }
  }

  // Resolve icon path for a DesktopEntries appId - safe on missing entries
  function iconForAppId(appId: string, fallbackName) {
    const fallback = fallbackName || "application-x-executable";
    if (!appId)
      return iconFromName(fallback, fallback);
    try {
      if (typeof DesktopEntries === 'undefined' || !DesktopEntries.byId)
        return iconFromName(fallback, fallback);
      const entry = (DesktopEntries.heuristicLookup) ? DesktopEntries.heuristicLookup(appId) : DesktopEntries.byId(appId);
      const name = entry && entry.icon ? entry.icon : "";
      return iconFromName(name || fallback, fallback);
    } catch (e) {
      return iconFromName(fallback, fallback);
    }
  }

  // Distro logo helper (absolute path or empty string)
  function distroLogoPath() {
    try {
      return (typeof OSInfo !== 'undefined' && OSInfo.distroIconPath) ? OSInfo.distroIconPath : "";
    } catch (e) {
      return "";
    }
  }
}
