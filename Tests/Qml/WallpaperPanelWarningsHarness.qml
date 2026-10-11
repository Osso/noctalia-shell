import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Modules.Panels.Wallpaper

Item {
  id: scene
  width: 900
  height: 700

  Component {
    id: panelComponent
    WallpaperPanel {
      width: 900
      height: 700
    }
  }

  TestCase {
    name: "WallpaperPanelWarnings"
    when: windowShown
    property var panel

    function descendants(parent, predicate) {
      let found = [];
      for (const child of parent.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function control(predicate) {
      const matches = descendants(panel, predicate);
      compare(matches.length, 1);
      return matches[0];
    }

    function init() {
      Settings.data.wallpaper.useWallhaven = false;
      Settings.data.wallpaper.setWallpaperOnAllMonitors = false;
      Settings.data.wallpaper.hideWallpaperFilenames = false;
      Settings.data.wallpaper.wallhavenQuery = "forest";
      Settings.data.wallpaper.wallhavenResolutionWidth = "1920";
      Settings.data.wallpaper.wallhavenResolutionHeight = "1080";
      Settings.data.wallpaper.wallhavenResolutionMode = "atleast";
      WallhavenService.searches = [];
      WallhavenService.downloads = [];
      WallhavenService.initialSearchScheduled = false;
      WallhavenService.fetching = false;
      WallhavenService.currentPage = 1;
      WallpaperService.changes = [];
      WallpaperService.selected["DP-1"] = WallpaperService.files + "/forest.png";
      WallpaperService.lists["DP-1"] = [WallpaperService.files + "/forest.png", WallpaperService.files + "/desert.png"];
      panel = createTemporaryObject(panelComponent, scene, {
        "screen": Quickshell.screens[0]
      });
      verify(panel !== null);
      tryVerify(() => panel.contentItem !== null);
      wait(30);
    }

    function test_filter_refresh_and_screen_roles() {
      const content = panel.contentItem;
      const first = content.screenRepeater.itemAt(0);
      const second = content.screenRepeater.itemAt(1);
      compare(first.targetScreen.name, "DP-1");
      compare(second.targetScreen.name, "HDMI-A-1");
      compare(first.gridView.columns, 4);
      // Columns follow the panel screen, not the delegate target screen.
      compare(second.gridView.columns, 4);
      compare(first.filteredWallpapers, WallpaperService.lists["DP-1"]);
      compare(second.filteredWallpapers, [WallpaperService.files + "/ocean.png"]);
      const input = control(child => child.placeholderText !== undefined);
      input.text = "desert";
      tryCompare(content, "filterText", "desert");
      compare(first.filteredWallpapers, [WallpaperService.files + "/desert.png"]);
      compare(second.filteredWallpapers, []);
      input.text = "  ";
      tryCompare(content, "filterText", "  ");
      compare(first.filteredWallpapers.length, 2);
      WallpaperService.lists["DP-1"] = [WallpaperService.files + "/ocean.png"];
      WallpaperService.wallpaperListChanged("unrelated", 0);
      compare(first.filteredWallpapers.length, 2);
      WallpaperService.wallpaperDirectoryChanged("DP-1", WallpaperService.files);
      compare(first.filteredWallpapers, [WallpaperService.files + "/ocean.png"]);
    }

    function test_local_selection_keyboard_tap_and_options() {
      const view = panel.currentWallpaperView();
      const grid = view.gridView;
      tryCompare(grid, "count", 2);
      grid.currentIndex = 1;
      grid.forceActiveFocus();
      keyClick(Qt.Key_Return);
      compare(WallpaperService.changes, [
        {
          "path": WallpaperService.files + "/desert.png",
          "screen": "DP-1"
        }
      ]);
      compare(view.currentWallpaper, WallpaperService.files + "/desert.png");
      const items = descendants(grid.contentItem, child => child.wallpaperPath !== undefined);
      compare(items.length, 2);
      compare(items.map(child => child.filename), ["forest.png", "desert.png"]);
      compare(items.map(child => child.isSelected), [false, true]);
      mouseClick(items[0], items[0].width / 2, 20);
      compare(WallpaperService.changes[1], {
        "path": WallpaperService.files + "/forest.png",
        "screen": "DP-1"
      });
      const toggle = control(child => child.toggled !== undefined);
      toggle.toggled(true);
      verify(Settings.data.wallpaper.setWallpaperOnAllMonitors);
      grid.currentIndex = 1;
      grid.forceActiveFocus();
      panel.onReturnPressed();
      compare(WallpaperService.changes[2], {
        "path": WallpaperService.files + "/desert.png",
        "screen": "ALL"
      });
      Settings.data.wallpaper.hideWallpaperFilenames = true;
      wait(10);
      const labels = descendants(grid.contentItem, child => child.text === "forest.png" || child.text === "desert.png");
      compare(labels.length, 2);
      verify(labels.every(child => !child.visible));
      Settings.data.wallpaper.setWallpaperOnAllMonitors = false;
      panel.contentItem.currentScreenIndex = 1;
      wait(20);
      compare(panel.currentWallpaperView().targetScreen.name, "HDMI-A-1");
      panel.currentGridView().forceActiveFocus();
      panel.currentGridView().currentIndex = 0;
      panel.onReturnPressed();
      compare(WallpaperService.changes[3].screen, "HDMI-A-1");
    }

    function test_wallhaven_search_resolution_selection_and_pagination() {
      const combo = control(child => child.currentKey !== undefined);
      combo.selected("wallhaven");
      verify(Settings.data.wallpaper.useWallhaven);
      compare(WallhavenService.categories, Settings.data.wallpaper.wallhavenCategories);
      compare(WallhavenService.minResolution, "1920x1080");
      compare(WallhavenService.resolutions, "");
      verify(WallhavenService.searches.length > 0);
      const content = panel.contentItem;
      Settings.data.wallpaper.wallhavenResolutionMode = "exact";
      content.updateWallhavenResolution();
      compare(WallhavenService.minResolution, "");
      compare(WallhavenService.resolutions, "1920x1080");
      Settings.data.wallpaper.wallhavenResolutionWidth = "";
      content.updateWallhavenResolution();
      compare(WallhavenService.resolutions, "");
      const input = control(child => child.placeholderText !== undefined);
      input.text = "ocean";
      tryVerify(() => WallhavenService.searches.some(search => search.query === "ocean"));
      compare(Settings.data.wallpaper.wallhavenQuery, "ocean");
      const result = {
        "id": "fixture",
        "thumb": WallpaperService.files + "/ocean.png",
        "local": WallpaperService.files + "/ocean.png"
      };
      WallhavenService.searchCompleted([result], {});
      const view = control(child => child.wallpapers !== undefined);
      compare(view.wallpapers, [result]);
      compare(view.loading, false);
      tryCompare(view.gridView, "count", 1);
      view.gridView.currentIndex = 0;
      view.gridView.forceActiveFocus();
      keyClick(Qt.Key_Space);
      compare(WallhavenService.downloads, ["fixture"]);
      compare(WallpaperService.changes[0], {
        "path": result.local,
        "screen": "DP-1"
      });
      const next = control(child => child.icon === "chevron-right");
      next.clicked();
      compare(WallhavenService.currentPage, 2);
      WallhavenService.searchFailed("fixture failure");
      compare(view.errorMessage, "fixture failure");
      compare(view.loading, false);
      WallhavenService.searchCompleted([], {});
      compare(view.wallpapers, []);
      compare(view.errorMessage, "");
    }

    function test_disposal_cancels_pending_search_and_disconnects_services() {
      Settings.data.wallpaper.useWallhaven = true;
      const input = control(child => child.placeholderText !== undefined);
      input.text = "must-not-search";
      const before = WallhavenService.searches.length;
      panel.destroy();
      wait(20);
      compare(panel, null);
      WallhavenService.searchCompleted([], {});
      WallpaperService.wallpaperListChanged("DP-1", 0);
      wait(550);
      compare(WallhavenService.searches.length, before);
    }
  }
}
