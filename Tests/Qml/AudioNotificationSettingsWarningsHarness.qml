import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Services.UI
import qs.Modules.Panels.Settings.Bar
import qs.Modules.Panels.Settings.Bar.WidgetSettings

TestCase {
  id: suite
  name: "AudioNotificationSettings"
  width: 720
  height: 800
  when: windowShown
  visible: true

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function cases() {
    return [
      {
        tag: "audio",
        widget: "AudioVisualizer",
        prefix: "audio-visualizer",
        toggles: ["hide-when-idle"],
        fields: ["hideWhenIdle"],
        defaults: [false],
        component: audioComponent
      },
      {
        tag: "notifications",
        widget: "NotificationHistory",
        prefix: "notification-history",
        toggles: ["show-unread-badge", "hide-badge-when-zero"],
        fields: ["showUnreadBadge", "hideWhenZero"],
        defaults: [true, false],
        component: notificationComponent
      }
    ];
  }

  function control(editor, data, suffix) {
    const found = descendants(editor).find(item => item.label === "bar.widget-settings." + data.prefix + "." + suffix + ".label");
    verify(found !== undefined, suffix);
    return found;
  }

  function toggle(editor, data, index, expected) {
    const option = control(editor, data, data.toggles[index]);
    const switcher = option.children[1];
    mouseClick(switcher, switcher.width / 2, switcher.height / 2);
    compare(option.checked, expected);
  }

  function createEditor(data, source) {
    const editor = createTemporaryObject(data.component, suite, {
      widgetData: source,
      widgetMetadata: BarWidgetRegistry.widgetMetadata[data.widget]
    });
    verify(editor !== null);
    wait(50);
    return editor;
  }

  function test_defaultsToggleSave_data() {
    return cases();
  }

  function test_defaultsToggleSave(data) {
    const editor = createEditor(data, {});
    for (let index = 0; index < data.fields.length; index++) {
      compare(control(editor, data, data.toggles[index]).checked, data.defaults[index]);
      toggle(editor, data, index, !data.defaults[index]);
    }
    const saved = editor.saveSettings();
    for (let index = 0; index < data.fields.length; index++)
      compare(saved[data.fields[index]], !data.defaults[index]);
    if (data.widget === "AudioVisualizer") {
      compare(control(editor, data, "width").text, "96");
      compare(saved.width, 96);
      compare(saved.colorName, "primary");
    }
  }

  function test_pendingCopySave_data() {
    return cases();
  }

  function test_pendingCopySave(data) {
    const source = {
      id: data.widget,
      retained: 31
    };
    for (let index = 0; index < data.fields.length; index++)
      source[data.fields[index]] = !data.defaults[index];
    if (data.widget === "AudioVisualizer") {
      source.width = 123;
      source.colorName = "error";
    }
    const original = JSON.stringify(source);
    const editor = createEditor(data, source);
    for (let index = 0; index < data.fields.length; index++) {
      compare(control(editor, data, data.toggles[index]).checked, !data.defaults[index]);
      toggle(editor, data, index, data.defaults[index]);
    }
    if (data.widget === "AudioVisualizer") {
      const width = control(editor, data, "width");
      compare(width.text, "123");
      width.inputItem.text = "invalid";
      compare(editor.saveSettings().width, 96);
      width.inputItem.text = "240";
      const combo = control(editor, data, "color-name");
      compare(combo.currentKey, "error");
      const nativeCombo = descendants(combo).find(item => item.popup !== undefined && item.currentIndex !== undefined);
      verify(nativeCombo !== undefined);
      nativeCombo.forceActiveFocus();
      keyClick(Qt.Key_Home);
      keyClick(Qt.Key_Down);
      tryCompare(combo, "currentKey", "secondary");
    }
    compare(JSON.stringify(source), original);
    const saved = editor.saveSettings();
    compare(saved.retained, 31);
    for (let index = 0; index < data.fields.length; index++)
      compare(saved[data.fields[index]], data.defaults[index]);
    if (data.widget === "AudioVisualizer") {
      compare(saved.width, 240);
      compare(saved.colorName, "secondary");
    }
    saved.retained = 99;
    compare(JSON.stringify(source), original);
  }

  function test_dialogCancelApply_data() {
    return cases();
  }

  function test_dialogCancelApply(data) {
    Settings.data.bar.widgets.left = [
      {
        id: data.widget,
        retained: 17
      }
    ];
    const original = JSON.stringify(Settings.data.bar.widgets.left);
    const dialog = createTemporaryObject(dialogComponent, suite, {
      widgetId: data.widget,
      widgetIndex: 0,
      sectionId: "left",
      widgetData: Settings.data.bar.widgets.left[0]
    });
    verify(dialog !== null);
    dialog.open();
    tryCompare(dialog, "opened", true);
    wait(100);
    const editor = descendants(dialog.contentItem).find(item => typeof item.saveSettings === "function");
    verify(editor !== undefined);
    toggle(editor, data, 0, !data.defaults[0]);
    const cancel = descendants(dialog.contentItem).find(item => item.text === "bar.widget-settings.dialog.cancel");
    verify(cancel !== undefined);
    mouseClick(cancel, cancel.width / 2, cancel.height / 2);
    tryCompare(dialog, "opened", false);
    compare(dialog.updates.length, 0);
    compare(JSON.stringify(Settings.data.bar.widgets.left), original);
    dialog.open();
    tryCompare(dialog, "opened", true);
    wait(100);
    const reopened = descendants(dialog.contentItem).find(item => typeof item.saveSettings === "function");
    verify(reopened !== undefined);
    compare(control(reopened, data, data.toggles[0]).checked, data.defaults[0]);
    toggle(reopened, data, 0, !data.defaults[0]);
    const apply = descendants(dialog.contentItem).find(item => item.text === "bar.widget-settings.dialog.apply");
    verify(apply !== undefined);
    mouseClick(apply, apply.width / 2, apply.height / 2);
    tryCompare(dialog, "opened", false);
    compare(dialog.updates.length, 1);
    compare(dialog.updates[0].section, "left");
    compare(dialog.updates[0].index, 0);
    compare(Settings.data.bar.widgets.left[0][data.fields[0]], !data.defaults[0]);
    compare(Settings.data.bar.widgets.left[0].retained, 17);
  }

  Component {
    id: audioComponent
    AudioVisualizerSettings {
      width: 680
    }
  }
  Component {
    id: notificationComponent
    NotificationHistorySettings {
      width: 680
    }
  }
  Component {
    id: dialogComponent
    BarWidgetSettingsDialog {
      id: dialogRoot
      property var updates: []
      onUpdateWidgetSettings: (section, index, settings) => {
        dialogRoot.updates = dialogRoot.updates.concat([
          {
            section: section,
            index: index
          }
        ]);
        Settings.data.bar.widgets[section][index] = settings;
      }
    }
  }
}
