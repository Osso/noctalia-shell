import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

Scope {
  id: root

  SettingsData {
    id: settings
  }

  FileView {
    id: file
    path: Quickshell.env("SETTINGS_TYPES_PATH")
    adapter: settings
    preload: true
    onLoaded: {
      console.log("LOADED_UI", JSON.stringify({
                                                fontDefault: settings.ui.fontDefault,
                                                fontFixed: settings.ui.fontFixed,
                                                fontDefaultScale: settings.ui.fontDefaultScale,
                                                fontFixedScale: settings.ui.fontFixedScale,
                                                tooltipsEnabled: settings.ui.tooltipsEnabled,
                                                panelBackgroundOpacity: settings.ui.panelBackgroundOpacity,
                                                panelsAttachedToBar: settings.ui.panelsAttachedToBar,
                                                settingsPanelAttachToBar: settings.ui.settingsPanelAttachToBar
                                              }));
      console.log("LOADED_WIDGETS", JSON.stringify({
                                                     left: settings.bar.widgets.left,
                                                     center: settings.bar.widgets.center,
                                                     right: settings.bar.widgets.right
                                                   }));
      if (Quickshell.env("SETTINGS_TYPES_MUTATE") === "1") {
        settings.ui.fontDefault = "Mutated Sans";
        settings.ui.fontDefaultScale = 1.25;
        settings.ui.tooltipsEnabled = false;
        settings.bar.widgets.left = [
              {
                id: "Clock",
                options: {
                  labels: ["a", "b"],
                  enabled: true
                }
              }
            ];
        settings.bar.widgets.center = [];
        settings.bar.widgets.right = [
              {
                id: "Tray",
                items: [[1, 2], [3]]
              }
            ];
      }
      Qt.callLater(() => file.writeAdapter());
    }
    onSaved: {
      console.log("SETTINGS_TYPES_PASS");
      Qt.quit();
    }
    onLoadFailed: function (error) {
      console.error("load failed", error);
      Qt.quit();
    }
    onSaveFailed: function (error) {
      console.error("save failed", error);
      Qt.quit();
    }
  }
}
