pragma Singleton

import QtQuick
import Quickshell
import "../Helpers/ThemeIconResolver.js" as ThemeIconResolver

Singleton {
  id: root

  function iconFromName(iconName, fallbackName) {
    const fallback = fallbackName || "application-x-executable";
    const safeIconName = sanitizeDesktopEntryIcon(iconName, fallback);
    try {
      return ThemeIconResolver.resolveIconPath(Quickshell, safeIconName, fallback);
    } catch (e2) {
      return "";
    }
  }

  function sanitizeDesktopEntryIcon(iconName, fallbackName) {
    const fallback = fallbackName || "application-x-executable";
    if (!iconName) {
      return fallback;
    }
    if (iconName.startsWith("/") || iconName.startsWith("file:")) {
      return fallback;
    }
    return iconName;
  }

  // Resolve icon path for a DesktopEntries appId - safe on missing entries
  function iconForAppId(appId, fallbackName) {
    const fallback = fallbackName || "application-x-executable";
    if (!appId)
      return iconFromName(fallback, fallback);
    try {
      if (typeof DesktopEntries === 'undefined' || !DesktopEntries.byId)
        return iconFromName(fallback, fallback);
      const entry = (DesktopEntries.heuristicLookup) ? DesktopEntries.heuristicLookup(appId) : DesktopEntries.byId(appId);
      const name = sanitizeDesktopEntryIcon(entry && entry.icon ? entry.icon : "", fallback);
      return iconFromName(name, fallback);
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
