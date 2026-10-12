import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Services.System
import qs.Modules.Panels.Settings.Tabs

TestCase {
  id: suite
  name: "NotificationsHooks"
  width: 800
  height: 1800
  when: windowShown
  visible: true

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function control(editor, label) {
    const found = descendants(editor).find(item => item.label === label);
    verify(found !== undefined, label);
    return found;
  }

  function editor(component) {
    const loader = createTemporaryObject(loaderComponent, suite, {
      sourceComponent: component
    });
    verify(loader !== null);
    tryCompare(loader, "status", Loader.Ready);
    wait(50);
    return loader.item;
  }

  function toggle(option, checked, checkbox) {
    const target = option.children[checkbox ? 2 : 1];
    mouseClick(target, target.width / 2, target.height / 2);
    tryCompare(option, "checked", checked);
  }

  function init() {
    Settings.data.notifications = notificationFixture;
    notificationFixture.enabled = true;
    notificationFixture.overlayLayer = false;
    notificationFixture.respectExpireTimeout = true;
    notificationFixture.enableKeyboardLayoutToast = true;
    notificationFixture.monitors = ["TEST-A"];
    Settings.data.hooks = hookFixture;
    hookFixture.enabled = true;
    hookFixture.wallpaperChange = "fixture-wallpaper";
    hookFixture.darkModeChange = "fixture-theme";
    NotificationService.doNotDisturb = false;
  }

  function test_notificationsToggleSaveAndReopen() {
    const tab = editor(notificationsComponent);
    toggle(control(tab, "settings.notifications.settings.enabled.label"), false, false);
    toggle(control(tab, "settings.notifications.settings.always-on-top.label"), true, false);
    toggle(control(tab, "settings.notifications.duration.respect-expire.label"), false, false);
    toggle(control(tab, "settings.notifications.toast.keyboard.label"), false, false);
    toggle(control(tab, "settings.notifications.settings.do-not-disturb.label"), true, false);
    compare(notificationFixture.enabled, false);
    compare(notificationFixture.overlayLayer, true);
    compare(notificationFixture.respectExpireTimeout, false);
    compare(notificationFixture.enableKeyboardLayoutToast, false);
    compare(NotificationService.doNotDisturb, true);
    tab.parent.visible = false;
    const reopened = editor(notificationsComponent);
    compare(control(reopened, "settings.notifications.settings.enabled.label").checked, false);
    compare(control(reopened, "settings.notifications.settings.always-on-top.label").checked, true);
  }

  function test_monitorSelectionUsesEditorOwner() {
    const tab = editor(notificationsComponent);
    const original = notificationFixture.monitors;
    compare(control(tab, "TEST-A").checked, true);
    const second = control(tab, "TEST-B");
    compare(second.monitorWidth, 2560);
    compare(second.monitorHeight, 1440);
    compare(second.monitorModel, "Fixture B");
    toggle(second, true, true);
    compare(JSON.stringify(notificationFixture.monitors), JSON.stringify(["TEST-A", "TEST-B"]));
    compare(JSON.stringify(original), JSON.stringify(["TEST-A"]));
    verify(notificationFixture.monitors !== original);
    toggle(control(tab, "TEST-A"), false, true);
    compare(JSON.stringify(notificationFixture.monitors), JSON.stringify(["TEST-B"]));
    toggle(second, false, true);
    compare(notificationFixture.monitors.length, 0);
  }

  function test_hooksListFollowsLoaderWidth() {
    const tab = editor(hooksComponent);
    compare(tab.width, 750);
    tab.parent.width = 620;
    tryCompare(tab, "width", 620);
    const wallpaper = control(tab, "settings.hooks.wallpaper-changed.label");
    const theme = control(tab, "settings.hooks.theme-changed.label");
    verify(wallpaper.visible);
    verify(theme.visible);
    toggle(control(tab, "settings.hooks.system-hooks.enable.label"), false, false);
    compare(hookFixture.enabled, false);
    tryCompare(wallpaper, "visible", false);
    tryCompare(theme, "visible", false);
  }

  function test_hooksEditSaveAndReopenWithoutExecution() {
    const tab = editor(hooksComponent);
    const wallpaper = control(tab, "settings.hooks.wallpaper-changed.label");
    const theme = control(tab, "settings.hooks.theme-changed.label");
    compare(wallpaper.text, "fixture-wallpaper");
    compare(theme.text, "fixture-theme");
    const input = descendants(wallpaper).find(item => item.inputItem !== undefined);
    verify(input !== undefined);
    input.inputItem.forceActiveFocus();
    input.inputItem.selectAll();
    keyClick(Qt.Key_Backspace);
    for (const character of "synthetic-command")
      keyClick(character);
    keyClick(Qt.Key_Return);
    tryCompare(hookFixture, "wallpaperChange", "synthetic-command");
    compare(hookFixture.darkModeChange, "fixture-theme");
    tab.parent.visible = false;
    const reopened = editor(hooksComponent);
    compare(control(reopened, "settings.hooks.wallpaper-changed.label").text, "synthetic-command");
    compare(control(reopened, "settings.hooks.theme-changed.label").text, "fixture-theme");
  }

  QtObject {
    id: notificationFixture
    property bool enabled
    property bool overlayLayer
    property bool respectExpireTimeout
    property bool enableKeyboardLayoutToast
    property var monitors
    property string location: "top_right"
    property real backgroundOpacity: 0.8
    property int lowUrgencyDuration: 3
    property int normalUrgencyDuration: 8
    property int criticalUrgencyDuration: 15
  }

  QtObject {
    id: hookFixture
    property bool enabled
    property string wallpaperChange
    property string darkModeChange
  }

  Component {
    id: loaderComponent
    Loader {
      width: 750
    }
  }

  Component {
    id: notificationsComponent
    NotificationsTab {}
  }

  Component {
    id: hooksComponent
    HooksTab {}
  }
}
