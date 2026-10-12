import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Services.UI
import qs.Modules.Panels.Settings.Bar
import qs.Modules.Panels.Settings.Bar.WidgetSettings

TestCase {
  id: suite
  name: "ActiveWindowSettings"
  width: 720
  height: 900
  when: windowShown
  visible: true

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function control(editor, suffix) {
    const found = descendants(editor).find(item => item.label === "bar.widget-settings.active-window." + suffix + ".label");
    verify(found !== undefined, suffix);
    return found;
  }

  function createEditor(data) {
    const editor = createTemporaryObject(editorComponent, suite, {
      "widgetData": data || {},
      "widgetMetadata": BarWidgetRegistry.widgetMetadata.ActiveWindow
    });
    verify(editor !== null);
    wait(50);
    return editor;
  }

  function editWidth(editor, text) {
    const field = control(editor, "max-width").inputItem;
    field.forceActiveFocus();
    field.selectAll();
    keyClick(Qt.Key_Backspace);
    for (const character of text)
      keyClick(character);
    compare(field.text, text);
  }

  function choose(editor, suffix, index, expected) {
    const combo = control(editor, suffix);
    const nativeCombo = descendants(combo).find(item => item.popup !== undefined && item.currentIndex !== undefined);
    verify(nativeCombo !== undefined);
    nativeCombo.forceActiveFocus();
    keyClick(Qt.Key_Home);
    for (let step = 0; step < index; step++)
      keyClick(Qt.Key_Down);
    tryCompare(combo, "currentKey", expected);
    compare(nativeCombo.contentItem.text, combo.model[index].name);
  }

  function toggle(editor, suffix, expected) {
    const option = control(editor, suffix);
    const switcher = option.children[1];
    mouseClick(switcher, switcher.width / 2, switcher.height / 2);
    compare(option.checked, expected);
  }

  function init() {
    Settings.data.bar.widgets.left = [
      {
        "id": "ActiveWindow",
        "maxWidth": 180,
        "retained": 17
      }
    ];
  }

  function test_defaultsAndOptions() {
    const editor = createEditor();
    compare(control(editor, "max-width").text, "240");
    compare(control(editor, "max-width").placeholderText, "240");
    compare(control(editor, "use-fixed-width").checked, false);
    compare(control(editor, "scrolling-mode").currentKey, "hover");
    choose(editor, "hide-mode", 0, "visible");
    choose(editor, "hide-mode", 2, "transparent");
    choose(editor, "hide-mode", 1, "hidden");
    choose(editor, "scrolling-mode", 0, "always");
    choose(editor, "scrolling-mode", 2, "never");
    choose(editor, "scrolling-mode", 1, "hover");
    toggle(editor, "show-app-icon", false);
    toggle(editor, "colorize-icons", true);
    toggle(editor, "use-fixed-width", true);
    const saved = editor.saveSettings();
    compare(saved.showIcon, false);
    compare(saved.colorizeIcons, true);
    compare(saved.useFixedWidth, true);
    compare(saved.hideMode, "hidden");
    compare(saved.scrollingMode, "hover");
  }

  function test_pendingValuesAndCopySave() {
    const source = {
      "id": "ActiveWindow",
      "retained": 31,
      "hideMode": "transparent",
      "showIcon": false,
      "scrollingMode": "never",
      "maxWidth": 123,
      "useFixedWidth": true,
      "colorizeIcons": true
    };
    const original = JSON.stringify(source);
    const editor = createEditor(source);
    compare(control(editor, "hide-mode").currentKey, "transparent");
    compare(control(editor, "max-width").text, "123");
    compare(control(editor, "use-fixed-width").checked, true);
    editWidth(editor, "375");
    choose(editor, "scrolling-mode", 0, "always");
    toggle(editor, "use-fixed-width", false);
    compare(JSON.stringify(source), original);
    const saved = editor.saveSettings();
    compare(saved.maxWidth, 375);
    compare(saved.scrollingMode, "always");
    compare(saved.useFixedWidth, false);
    compare(saved.showIcon, false);
    compare(saved.colorizeIcons, true);
    compare(saved.hideMode, "transparent");
    compare(saved.retained, 31);
    saved.retained = 99;
    compare(JSON.stringify(source), original);
  }

  function test_widthFallbackAndReactivePreview() {
    const editor = createEditor({
      "maxWidth": 150,
      "useFixedWidth": true,
      "scrollingMode": "always"
    });
    editor.valueMaxWidth = 290;
    tryCompare(control(editor, "max-width"), "text", "290");
    editor.valueUseFixedWidth = false;
    tryCompare(control(editor, "use-fixed-width"), "checked", false);
    editor.valueScrollingMode = "never";
    tryCompare(control(editor, "scrolling-mode"), "currentKey", "never");
    editWidth(editor, "");
    compare(editor.saveSettings().maxWidth, 240);
    editWidth(editor, "invalid");
    compare(editor.saveSettings().maxWidth, 240);
    editWidth(editor, "0");
    compare(editor.saveSettings().maxWidth, 240);
  }

  function test_dialogCancelAndApplySyntheticOnly() {
    const original = JSON.stringify(Settings.data.bar.widgets.left);
    const dialog = createTemporaryObject(dialogComponent, suite, {
      "widgetId": "ActiveWindow",
      "widgetIndex": 0,
      "sectionId": "left",
      "widgetData": Settings.data.bar.widgets.left[0]
    });
    verify(dialog !== null);
    dialog.open();
    tryCompare(dialog, "opened", true);
    wait(100);
    const editor = descendants(dialog.contentItem).find(item => typeof item.saveSettings === "function");
    verify(editor !== undefined);
    editWidth(editor, "399");
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
    compare(control(reopened, "max-width").text, "180");
    editWidth(reopened, "420");
    choose(reopened, "scrolling-mode", 2, "never");
    toggle(reopened, "use-fixed-width", true);
    const apply = descendants(dialog.contentItem).find(item => item.text === "bar.widget-settings.dialog.apply");
    verify(apply !== undefined);
    mouseClick(apply, apply.width / 2, apply.height / 2);
    tryCompare(dialog, "opened", false);
    compare(dialog.updates.length, 1);
    compare(dialog.updates[0].section, "left");
    compare(dialog.updates[0].index, 0);
    compare(Settings.data.bar.widgets.left[0].maxWidth, 420);
    compare(Settings.data.bar.widgets.left[0].useFixedWidth, true);
    compare(Settings.data.bar.widgets.left[0].scrollingMode, "never");
    compare(Settings.data.bar.widgets.left[0].retained, 17);
  }

  Component {
    id: editorComponent
    ActiveWindowSettings {
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
            "section": section,
            "index": index,
            "settings": settings
          }
        ]);
        Settings.data.bar.widgets[section][index] = settings;
      }
    }
  }
}
