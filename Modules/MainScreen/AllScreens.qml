import QtQuick
import Quickshell
import Quickshell.Wayland

import qs.Commons
import qs.Modules.MainScreen
import qs.Services.UI

// ------------------------------
// MainScreen for each screen (manages bar + all panels)
// Wrapped in Loader to optimize memory - only loads when screen needs it
Variants {
  model: Quickshell.screens
  delegate: Item {
    required property ShellScreen modelData

    function screenName() {
      return modelData ? modelData.name : "";
    }

    function screenHasBar() {
      const name = screenName();
      if (!name) {
        return false;
      }
      var monitors = Settings.data.bar.monitors || [];
      return monitors.length === 0 || monitors.includes(name);
    }

    property bool shouldBeActive: {
      const name = screenName();
      if (!name) {
        return false;
      }

      let shouldLoad = true;
      if (!Settings.data.general.allowPanelsOnScreenWithoutBar) {
        shouldLoad = screenHasBar();
      }

      if (shouldLoad) {
        Logger.d("AllScreens", "Screen activated: ", name);
      }
      return shouldLoad;
    }

    property bool windowLoaded: false

    // Main Screen loader - Bar and panels backgrounds
    Loader {
      id: windowLoader
      active: parent.shouldBeActive
      asynchronous: false

      property ShellScreen loaderScreen: modelData

      onLoaded: {
        // Signal that window is loaded so exclusion zone can be created
        parent.windowLoaded = true;
      }

      sourceComponent: MainScreen {
        screen: windowLoader.loaderScreen
      }
    }

    // Bar content in separate windows to prevent fullscreen redraws
    Loader {
      active: {
        if (!parent.windowLoaded || !parent.shouldBeActive || !BarService.isVisible)
          return false;

        return parent.screenHasBar();
      }
      asynchronous: false

      sourceComponent: BarContentWindow {
        screen: modelData
      }

      onLoaded: {
        Logger.d("AllScreens", "BarContentWindow created for", parent.screenName());
      }
    }

    // BarExclusionZone - created after MainScreen has fully loaded
    // Disabled when bar is hidden or not configured for this screen
    Loader {
      active: {
        if (!parent.windowLoaded || !parent.shouldBeActive || !BarService.isVisible)
          return false;

        return parent.screenHasBar();
      }
      asynchronous: false

      sourceComponent: BarExclusionZone {
        screen: modelData
      }

      onLoaded: {
        Logger.d("AllScreens", "BarExclusionZone created for", parent.screenName());
      }
    }

    // PopupMenuWindow - reusable popup window for both tray menus and context menus
    // Disabled when bar is hidden or not configured for this screen
    Loader {
      active: {
        if (!parent.windowLoaded || !parent.shouldBeActive || !BarService.isVisible)
          return false;

        return parent.screenHasBar();
      }
      asynchronous: false

      sourceComponent: PopupMenuWindow {
        screen: modelData
      }

      onLoaded: {
        Logger.d("AllScreens", "PopupMenuWindow created for", parent.screenName());
      }
    }
  }
}
