import Qt.labs.folderlistmodel
import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.UI

TestCase {
  id: test
  name: "WallpaperService"
  when: true

  property ShellScreen firstScreen: ShellScreen {
    name: "DP-1"
  }
  property ShellScreen secondScreen: ShellScreen {
    name: "DP-2"
  }

  SignalSpy {
    id: wallpaperSpy
    target: WallpaperService
    signalName: "wallpaperChanged"
  }
  SignalSpy {
    id: listSpy
    target: WallpaperService
    signalName: "wallpaperListChanged"
  }

  function init() {
    Quickshell.screens = [test.firstScreen, test.secondScreen];
    tryVerify(() => FixtureFolders.scanners.length === 2);
    Settings.data.wallpaper.enableMultiMonitorDirectories = false;
    Settings.data.wallpaper.randomEnabled = false;
    Settings.data.wallpaper.recursiveSearch = false;
    WallpaperService.currentWallpapers = {};
    WallpaperService.wallpaperLists = {};
    WallpaperService.scanningCount = 0;
    wallpaperSpy.clear();
    listSpy.clear();
  }

  function test_randomTimerRoutesToService() {
    Settings.data.wallpaper.enableMultiMonitorDirectories = true;
    WallpaperService.wallpaperLists = {
      "DP-1": ["/fixture/random.jpg"],
      "DP-2": []
    };
    Settings.data.wallpaper.randomIntervalSec = 0.02;
    Settings.data.wallpaper.randomEnabled = true;
    compare(WallpaperService.getWallpaper("DP-1"), "/fixture/random.jpg");
    WallpaperService.changeWallpaper("/fixture/manual.jpg", "DP-1");
    tryCompare(WallpaperService.currentWallpapers, "DP-1", "/fixture/random.jpg");
    compare(wallpaperSpy.count, 3);
    Settings.data.wallpaper.randomEnabled = false;
  }

  function test_wallpaperSignalsAndDebouncedCache() {
    const writesBefore = FixtureIo.writes;
    WallpaperService.changeWallpaper("/fixture/first.png", "DP-1");
    compare(WallpaperService.getWallpaper("DP-1"), "/fixture/first.png");
    compare(wallpaperSpy.count, 1);
    compare(Array.from(wallpaperSpy.signalArguments[0]), ["DP-1", "/fixture/first.png"]);
    WallpaperService.changeWallpaper("/fixture/first.png", "DP-1");
    WallpaperService.changeWallpaper("", "DP-1");
    compare(wallpaperSpy.count, 1);
    WallpaperService.changeWallpaper("/fixture/shared.jpg");
    compare(wallpaperSpy.count, 3);
    compare(WallpaperService.getWallpaper("DP-2"), "/fixture/shared.jpg");
    tryCompare(FixtureIo, "writes", writesBefore + 1);
    compare(FixtureIo.cache.adapter.wallpapers["DP-1"], "/fixture/shared.jpg");
    compare(FixtureIo.cache.adapter.wallpapers["DP-2"], "/fixture/shared.jpg");
  }

  function test_scannerStatusUpdates() {
    const scanner = FixtureFolders.scanners[0];
    scanner.status = FolderListModel.Loading;
    compare(WallpaperService.scanningCount, 1);
    verify(WallpaperService.scanning);
    scanner.files = ["a.jpg", "b.png"];
    scanner.status = FolderListModel.Ready;
    compare(WallpaperService.getWallpapersList("DP-1"), ["/fixture/images/a.jpg", "/fixture/images/b.png"]);
    compare(WallpaperService.scanningCount, 0);
    compare(Array.from(listSpy.signalArguments[listSpy.count - 1]), ["DP-1", 2]);
    scanner.status = FolderListModel.Null;
    compare(WallpaperService.getWallpapersList("DP-1"), []);
    compare(Array.from(listSpy.signalArguments[listSpy.count - 1]), ["DP-1", 0]);
  }

  function test_directoryRoutingAndScannerLifecycle() {
    WallpaperService.wallpaperDirectoryChanged("DP-1", "/fixture/custom");
    compare(FixtureFolders.scanners[0].folder, "file:///fixture/custom");
    compare(FixtureFolders.scanners[1].folder, "file:///fixture/images");
    Quickshell.screens = [test.firstScreen];
    tryVerify(() => FixtureFolders.scanners.length === 1);
    WallpaperService.wallpaperDirectoryChanged("DP-2", "/fixture/removed");
    WallpaperService.wallpaperDirectoryChanged("DP-1", "/fixture/remaining");
    compare(FixtureFolders.scanners[0].folder, "file:///fixture/remaining");
    Quickshell.screens = [test.firstScreen, test.secondScreen];
    tryVerify(() => FixtureFolders.scanners.length === 2);
    WallpaperService.wallpaperDirectoryChanged("DP-2", "/fixture/restored");
    compare(FixtureFolders.scanners[1].folder, "file:///fixture/restored");
  }

  function test_recursiveCompletionAndReplacement() {
    WallpaperService.scanDirectoryRecursive("DP-1", "/fixture/recursive");
    compare(FixtureIo.processes.length, 1);
    compare(WallpaperService.scanningCount, 1);
    WallpaperService.scanDirectoryRecursive("DP-1", "/fixture/replacement");
    tryVerify(() => FixtureIo.processes.length === 1);
    compare(WallpaperService.scanningCount, 1);
    FixtureIo.processes[0].finish(0, " /fixture/z.jpg\n/fixture/a.png\n\n");
    compare(WallpaperService.getWallpapersList("DP-1"), ["/fixture/a.png", "/fixture/z.jpg"]);
    compare(Array.from(listSpy.signalArguments[listSpy.count - 1]), ["DP-1", 2]);
    compare(WallpaperService.scanningCount, 0);
    tryVerify(() => FixtureIo.processes.length === 0);
    WallpaperService.scanDirectoryRecursive("DP-1", "/fixture/failure");
    FixtureIo.processes[0].finish(1, "");
    compare(WallpaperService.getWallpapersList("DP-1"), []);
    compare(WallpaperService.scanningCount, 0);
    tryVerify(() => FixtureIo.processes.length === 0);
  }

  function test_cacheLoadAndFailure() {
    FixtureIo.cache.adapter.wallpapers = {
      "DP-1": "/fixture/cached.jpg"
    };
    FixtureIo.cache.adapter.defaultWallpaper = "/fixture/default.png";
    FixtureIo.cache.loaded();
    verify(WallpaperService.isInitialized);
    compare(WallpaperService.getWallpaper("DP-1"), "/fixture/cached.jpg");
    compare(WallpaperService.getWallpaper("missing"), "/fixture/default.png");
    FixtureIo.cache.loadFailed(1);
    compare(WallpaperService.currentWallpapers, {});
    verify(WallpaperService.isInitialized);
  }
}
