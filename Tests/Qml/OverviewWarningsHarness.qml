import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.Compositor
import qs.Services.UI
import qs.Modules.Background

TestCase {
  id: test
  name: "Overview"
  when: true

  property Overview overview
  Component {
    id: factory
    Overview {}
  }

  function init() {
    CompositorService.isNiri = true;
    Settings.data.wallpaper.enabled = true;
    Settings.data.wallpaper.overviewEnabled = true;
    Settings.data.colorSchemes.darkMode = true;
    overview = factory.createObject(test);
    verify(overview !== null);
    tryVerify(() => overview.item !== null);
    compare(overview.item.instances.count, 2);
    wait(0); // Flush anchor layout on invisible fixture Windows.
  }

  function cleanup() {
    overview.destroy();
    wait(0);
  }

  function panel(index) {
    return overview.item.instances.objectAt(index);
  }

  function preview(window) {
    return window.contentItem.children[0];
  }

  function test_cover_screen_and_geometry() {
    for (let index = 0; index < 2; index++) {
      const window = panel(index);
      const screen = Quickshell.screens[index];
      compare(window.screen, screen);
      compare(window.namespace, "noctalia-overview-" + screen.name);
      compare(window.width, screen.width);
      compare(window.height, screen.height);
      const image = preview(window);
      compare(image.x, 0);
      compare(image.y, 0);
      compare(image.width, screen.width);
      compare(image.height, screen.height);
      compare(image.children[0].width, image.width);
      compare(image.children[0].height, image.height);
      compare(image.children[0].opacity, 0.8);
      compare(image.sourceSize, Qt.size(1280, 720));
    }
    Quickshell.screens[0].width = 960;
    Quickshell.screens[0].height = 540;
    tryCompare(preview(panel(0)), "width", 960);
    compare(preview(panel(0)).height, 540);
    Quickshell.screens[0].width = 800;
    Quickshell.screens[0].height = 450;
    Settings.data.colorSchemes.darkMode = false;
    compare(preview(panel(0)).children[0].color, NColor.mOnSurface);
  }

  function test_matching_wallpaper_owner() {
    compare(panel(0).wallpaper, "fixture-wide");
    WallpaperService.wallpaperChanged("tall", "changed-tall");
    compare(panel(0).wallpaper, "fixture-wide");
    compare(panel(1).wallpaper, "changed-tall");
    compare(preview(panel(1)).source.toString(), "changed-tall");
    WallpaperService.wallpaperChanged("missing", "ignored");
    compare(panel(1).wallpaper, "changed-tall");
  }

  function test_visibility_and_recreation() {
    const oldPanel = panel(0);
    const gates = [Settings.data.wallpaper, Settings.data.wallpaper, CompositorService];
    const names = ["overviewEnabled", "enabled", "isNiri"];
    for (let index = 0; index < gates.length; index++) {
      gates[index][names[index]] = false;
      tryCompare(overview, "item", null);

      WallpaperService.wallpaperChanged("wide", "while-disabled");
      gates[index][names[index]] = true;
      tryVerify(() => overview.item !== null);
      compare(overview.item.instances.count, 2);
      verify(panel(0) !== oldPanel);
      compare(panel(0).wallpaper, "fixture-wide");
      compare(preview(panel(0)).source.toString(), "fixture-wide");
      tryCompare(preview(panel(0)), "width", Quickshell.screens[0].width);
    }
    // Removing/readding screens also exercises delegate destruction, not only Loader.
    const screens = Array.from(Quickshell.screens);
    Quickshell.screens = [];
    tryCompare(overview.item.instances, "count", 0);
    Quickshell.screens = screens;
    tryCompare(overview.item.instances, "count", 2);
    WallpaperService.wallpaperChanged("wide", "after-recreate");
    compare(preview(panel(0)).source.toString(), "after-recreate");
  }
}
