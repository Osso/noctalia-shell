import QtQuick
import QtTest
import Quickshell.Services.UPower
import qs.Commons
import qs.Services.UI
import qs.Services.Power
import qs.Modules.Panels.Wallpaper

Item {
  id: scene
  width: 900
  height: 900
  Component {
    id: popupComponent
    WallhavenSettingsPopup {}
  }
  TestCase {
    id: suite
    name: "WallhavenPowerWarnings"
    when: windowShown
    property var popup

    function descendants(item) {
      let found = [];
      for (const child of item.children) {
        found.push(child);
        found = found.concat(suite.descendants(child));
      }
      return found;
    }

    function combo(key) {
      const matches = suite.descendants(suite.popup.contentItem).filter(item => item.currentKey === key);
      compare(matches.length, 1);
      return matches[0];
    }

    function init() {
      Settings.data.wallpaper.wallhavenSorting = "relevance";
      Settings.data.wallpaper.wallhavenResolutionMode = "atleast";
      Settings.data.wallpaper.wallhavenResolutionWidth = "1920";
      Settings.data.wallpaper.wallhavenResolutionHeight = "1080";
      Settings.data.wallpaper.useWallhaven = true;
      WallhavenService.searches = [];
      PowerProfiles.hasPerformanceProfile = true;
      PowerProfiles.profile = PowerProfile.Balanced;
      PowerProfileService.setNoctaliaPerformance(false);
      ToastService.notices = [];
      suite.popup = createTemporaryObject(popupComponent, scene);
      verify(suite.popup !== null);
    }

    function test_selection() {
      suite.combo("relevance").selected("random");
      compare(Settings.data.wallpaper.wallhavenSorting, "random");
      compare(WallhavenService.sorting, "random");
      compare(WallhavenService.searches, [
        {
          query: "forest",
          page: 1
        }
      ]);
      suite.combo("desc").selected("asc");
      compare(Settings.data.wallpaper.wallhavenOrder, "asc");
      compare(WallhavenService.order, "asc");
      suite.combo("100").selected("010");
      compare(Settings.data.wallpaper.wallhavenPurity, "010");
      compare(WallhavenService.purity, "010");
    }

    function test_resolution_cache() {
      suite.popup.updateResolution(false);
      compare(WallhavenService.minResolution, "1920x1080");
      compare(WallhavenService.resolutions, "");
      compare(WallhavenService.searches.length, 0);
      suite.combo("atleast").selected("exact");
      compare(WallhavenService.minResolution, "");
      compare(WallhavenService.resolutions, "1920x1080");
      compare(WallhavenService.searches.length, 0);
      Settings.data.wallpaper.wallhavenResolutionWidth = "2560";
      Settings.data.wallpaper.wallhavenResolutionHeight = "1440";
      const inputs = suite.descendants(suite.popup.contentItem).filter(item => item.inputItem !== undefined);
      compare(inputs.length, 2);
      compare(inputs[0].text, "2560");
      compare(inputs[1].text, "1440");
      inputs[0].text = "3840";
      inputs[0].editingFinished();
      inputs[1].text = "2160";
      inputs[1].editingFinished();
      compare(Settings.data.wallpaper.wallhavenResolutionWidth, "3840");
      compare(Settings.data.wallpaper.wallhavenResolutionHeight, "2160");
      compare(WallhavenService.resolutions, "3840x2160");
      suite.popup.updateResolution(true);
      compare(WallhavenService.resolutions, "3840x2160");
      compare(WallhavenService.searches.length, 1);
      Settings.data.wallpaper.useWallhaven = false;
      Settings.data.wallpaper.wallhavenResolutionHeight = "";
      suite.popup.updateResolution(true);
      compare(WallhavenService.resolutions, "");
      compare(WallhavenService.minResolution, "");
      compare(WallhavenService.searches.length, 1);
      Settings.data.wallpaper.useWallhaven = true;
      Settings.data.wallpaper.wallhavenResolutionHeight = "2160";
      const apply = suite.descendants(suite.popup.contentItem).filter(item => item.text === "wallpaper.panel.wallhaven-settings.apply");
      compare(apply.length, 1);
      apply[0].clicked();
      compare(WallhavenService.resolutions, "3840x2160");
      compare(WallhavenService.searches.length, 2);
      wait(0);
      compare(suite.popup.visible, false);
    }

    function test_power_backend_state() {
      compare(PowerProfileService.available, true);
      compare(PowerProfileService.isDefault(), true);
      PowerProfileService.cycleProfile();
      compare(PowerProfiles.profile, PowerProfile.Performance);
      compare(PowerProfileService.profile, PowerProfile.Performance);
      compare(PowerProfileService.getName(), "Performance");
      compare(PowerProfileService.getIcon(), "performance");
      compare(ToastService.notices[0].icon, "performance");
      PowerProfileService.cycleProfile();
      compare(PowerProfiles.profile, PowerProfile.PowerSaver);
      PowerProfileService.cycleProfile();
      compare(PowerProfiles.profile, PowerProfile.Balanced);
      PowerProfiles.profile = PowerProfile.PowerSaver;
      compare(PowerProfileService.getName(), "Power saver");
      compare(PowerProfileService.getIcon(), "powersaver");
      compare(PowerProfileService.getName(99), "Unknown");
      compare(PowerProfileService.getIcon(99), "balanced");
      PowerProfiles.hasPerformanceProfile = false;
      PowerProfileService.setProfile(PowerProfile.Performance);
      PowerProfileService.cycleProfile();
      compare(PowerProfiles.profile, PowerProfile.PowerSaver);
      compare(PowerProfileService.getName(), "Unknown");
      compare(PowerProfileService.getIcon(), "balanced");
      compare(PowerProfileService.isDefault(), true);
    }

    function test_performance_toasts() {
      PowerProfileService.toggleNoctaliaPerformance();
      compare(PowerProfileService.noctaliaPerformanceMode, true);
      compare(ToastService.notices[0].icon, "rocket");
      PowerProfileService.setNoctaliaPerformance(false);
      compare(PowerProfileService.noctaliaPerformanceMode, false);
      compare(ToastService.notices[1].icon, "rocket-off");
    }
  }
}
