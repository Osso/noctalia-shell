import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Services.Compositor
import qs.Tabs

TestCase {
  id: testCase
  name: "WallpaperTabWarnings"
  width: 1100
  height: 2400
  visible: true
  when: windowShown

  ShellScreen {
    id: fixtureScreen
    name: "fixture"
  }
  ShellScreen {
    id: secondScreen
    name: "second"
  }

  Component {
    id: tabFactory
    WallpaperTab {
      width: 1000
    }
  }

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function control(tab, label) {
    const matches = descendants(tab).filter(item => item.label === label && (item.toggled !== undefined || item.inputEditingFinished !== undefined || item.editingFinished !== undefined || item.selected !== undefined));
    compare(matches.length, 1, label);
    return matches[0];
  }

  function init() {
    Settings.data.wallpaper.enabled = true;
    Settings.data.wallpaper.randomEnabled = true;
    Settings.data.wallpaper.randomIntervalSec = 300;
    Settings.data.wallpaper.enableMultiMonitorDirectories = true;
    Settings.data.wallpaper.directory = "/private-fixture/main";
    Settings.data.wallpaper.panelPosition = "follow_bar";
    Settings.data.wallpaper.fillMode = "crop";
    Settings.data.wallpaper.transitionType = "fade";
    Settings.dataChanged();
    CompositorService.isNiri = true;
    WallpaperService.restarts = 0;
    WallpaperService.directories = {
      fixture: "/private-fixture/monitor",
      second: "/private-fixture/second"
    };
    Quickshell.screens = [fixtureScreen, secondScreen];
  }

  function newTab() {
    const tab = createTemporaryObject(tabFactory, testCase);
    verify(tab !== null);
    wait(20);
    verify(tab.implicitHeight > 0);
    return tab;
  }

  function test_layoutAndSwitches() {
    const tab = newTab();
    const management = control(tab, "settings.wallpaper.settings.enable-management.label");
    const overview = control(tab, "settings.wallpaper.settings.enable-overview.label");
    const directory = control(tab, "settings.wallpaper.settings.folder.label");
    verify(directory.visible);
    verify(directory.width > 0);
    management.toggled(false);
    compare(Settings.data.wallpaper.enabled, false);
    Settings.dataChanged();
    compare(directory.visible, false);
    compare(overview.visible, false);
    management.toggled(true);
    Settings.dataChanged();
    compare(directory.visible, true);
    compare(overview.visible, true);
    CompositorService.isNiri = false;
    compare(overview.visible, false);
    const random = control(tab, "settings.wallpaper.automation.random-wallpaper.label");
    const custom = control(tab, "settings.wallpaper.automation.custom-interval.label");
    random.toggled(false);
    compare(Settings.data.wallpaper.randomEnabled, false);
    Settings.dataChanged();
    compare(custom.parent.parent.visible, false);
  }

  function test_selectionsAndReopen() {
    const tab = newTab();
    const position = control(tab, "settings.wallpaper.settings.selector-position.label");
    position.activateCurrentIndex(position.findIndexByKey("bottom_right"));
    compare(Settings.data.wallpaper.panelPosition, "bottom_right");
    const fill = control(tab, "settings.wallpaper.look-feel.fill-mode.label");
    fill.activateCurrentIndex(fill.findIndexByKey("fit"));
    compare(Settings.data.wallpaper.fillMode, "fit");
    const transition = control(tab, "settings.wallpaper.look-feel.transition-type.label");
    transition.activateCurrentIndex(transition.findIndexByKey("none"));
    compare(Settings.data.wallpaper.transitionType, "none");
    tab.destroy();
    wait(0);
    const reopened = newTab();
    compare(control(reopened, "settings.wallpaper.settings.selector-position.label").currentKey, "bottom_right");
    compare(control(reopened, "settings.wallpaper.look-feel.fill-mode.label").currentKey, "fit");
  }

  function test_presetChipClickAndCustomEntry() {
    const tab = newTab();
    const chips = descendants(tab).filter(item => item.seconds !== undefined && item.clicked !== undefined);
    compare(chips.length, 9);
    const selected = chips.filter(item => item.seconds === 300)[0];
    const next = chips.filter(item => item.seconds === 900)[0];
    compare(selected.selected, true);
    mouseClick(next, next.width / 2, next.height / 2);
    compare(Settings.data.wallpaper.randomIntervalSec, 900);
    compare(WallpaperService.restarts, 1);
    Settings.dataChanged();
    compare(next.selected, true);
    compare(selected.selected, false);
    const label = descendants(next).filter(item => item.text === "900 seconds")[0];
    verify(label !== undefined);
    compare(label.color, Qt.color("#ffffff"));
    const customChip = chips.filter(item => item.seconds === 0)[0];
    mouseClick(customChip, customChip.width / 2, customChip.height / 2);
    const custom = control(tab, "settings.wallpaper.automation.custom-interval.label");
    compare(custom.parent.visible, true);
    custom.inputItem.forceActiveFocus();
    custom.inputItem.text = "1:23";
    keyClick(Qt.Key_Return);
    compare(Settings.data.wallpaper.randomIntervalSec, 4980);
    compare(WallpaperService.restarts, 2);
    Settings.dataChanged();
    compare(custom.parent.visible, true);
    custom.inputItem.text = "invalid";
    keyClick(Qt.Key_Return);
    compare(Settings.data.wallpaper.randomIntervalSec, 4980);
    compare(WallpaperService.restarts, 2);
  }

  function test_delegateOwnersStayInstanceLocal() {
    const first = newTab();
    const second = newTab();
    const firstChips = descendants(first).filter(item => item.seconds !== undefined && item.clicked !== undefined);
    const secondChips = descendants(second).filter(item => item.seconds !== undefined && item.clicked !== undefined);
    firstChips.filter(item => item.seconds === 0)[0].clicked();
    compare(control(first, "settings.wallpaper.automation.custom-interval.label").parent.visible, true);
    compare(control(second, "settings.wallpaper.automation.custom-interval.label").parent.visible, false);
    secondChips.filter(item => item.seconds === 900)[0].clicked();
    compare(Settings.data.wallpaper.randomIntervalSec, 900);
    Settings.dataChanged();
    compare(control(first, "settings.wallpaper.automation.custom-interval.label").parent.visible, true);
    compare(control(second, "settings.wallpaper.automation.custom-interval.label").parent.visible, false);
    const firstMonitor = descendants(first).filter(item => item.text === "/private-fixture/second" && item.buttonClicked !== undefined)[0];
    firstMonitor.buttonClicked();
    compare(first.specificFolderMonitorName, "second");
    compare(second.specificFolderMonitorName, "");
    const firstPicker = descendants(first).filter(item => item.title === "settings.wallpaper.settings.select-monitor-folder")[0];
    const secondPicker = descendants(second).filter(item => item.title === "settings.wallpaper.settings.select-monitor-folder")[0];
    compare(firstPicker.opens, 1);
    compare(secondPicker.opens, 0);
  }

  function test_privateFolderSelections() {
    const tab = newTab();
    const mainInput = control(tab, "settings.wallpaper.settings.folder.label");
    mainInput.text = "/private-fixture/edited";
    mainInput.inputEditingFinished();
    compare(Settings.data.wallpaper.directory, "/private-fixture/edited");
    const pickers = descendants(tab).filter(item => item.selectionMode === "folders");
    compare(pickers.length, 2);
    const mainPicker = pickers.filter(item => item.title === "settings.wallpaper.settings.select-folder")[0];
    const monitorPicker = pickers.filter(item => item.title === "settings.wallpaper.settings.select-monitor-folder")[0];
    mainInput.buttonClicked();
    compare(mainPicker.opens, 1);
    mainPicker.accepted([]);
    compare(Settings.data.wallpaper.directory, "/private-fixture/edited");
    mainPicker.accepted(["/private-fixture/chosen"]);
    compare(Settings.data.wallpaper.directory, "/private-fixture/chosen");
    const monitorInput = descendants(tab).filter(item => item.text === "/private-fixture/second" && item.inputEditingFinished !== undefined)[0];
    monitorInput.text = "/private-fixture/second-edited";
    monitorInput.inputEditingFinished();
    compare(WallpaperService.directories.second, "/private-fixture/second-edited");
    monitorInput.buttonClicked();
    compare(tab.specificFolderMonitorName, "second");
    compare(monitorPicker.opens, 1);
    compare(monitorPicker.initialPath, "/private-fixture/second-edited");
    monitorPicker.accepted([]);
    compare(WallpaperService.directories.second, "/private-fixture/second-edited");
    monitorPicker.accepted(["/private-fixture/second-picked"]);
    compare(WallpaperService.directories.second, "/private-fixture/second-picked");
    compare(WallpaperService.directories.fixture, "/private-fixture/monitor");
  }
}
