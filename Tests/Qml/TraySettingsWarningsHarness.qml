import QtQuick
import QtQuick.Controls
import QtTest
import qs.Modules.Panels.Settings.Bar.WidgetSettings

TestCase {
  id: suite
  name: "TraySettings"
  width: 720
  height: 600
  when: windowShown
  visible: true

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function createEditor(data, metadata) {
    const editor = createTemporaryObject(editorComponent, suite, {
      "widgetData": data || {},
      "widgetMetadata": metadata || {
        colorizeIcons: false,
        drawerEnabled: true
      }
    });
    verify(editor !== null);
    wait(50);
    return editor;
  }

  function control(editor, suffix) {
    const option = descendants(editor).find(item => item.label === "bar.widget-settings.tray." + suffix + ".label");
    verify(option !== undefined);
    return option;
  }

  function toggle(editor, suffix, expected) {
    const option = control(editor, suffix);
    const switcher = option.children[1];
    mouseClick(switcher, switcher.width / 2, switcher.height / 2);
    compare(option.checked, expected);
  }

  function list(editor) {
    const view = descendants(editor).find(item => item.contentItem !== undefined && item.count !== undefined);
    verify(view !== undefined);
    return view;
  }

  function addRule(editor, text) {
    const input = descendants(editor).find(item => item.placeholderText === "settings.bar.tray.blacklist.placeholder");
    verify(input !== undefined);
    input.text = text;
    const button = descendants(input).find(item => item.icon === "add");
    verify(button !== undefined);
    mouseClick(button, button.width / 2, button.height / 2);
    wait(50);
    return input;
  }

  function test_defaultsAndToggleSave() {
    const editor = createEditor();
    compare(control(editor, "colorize-icons").checked, false);
    compare(control(editor, "drawer-enabled").checked, true);
    toggle(editor, "colorize-icons", true);
    toggle(editor, "drawer-enabled", false);
    const saved = editor.saveSettings();
    compare(saved.colorizeIcons, true);
    compare(saved.drawerEnabled, false);
    compare(saved.blacklist.length, 0);
    const metadataEditor = createEditor({}, {
      colorizeIcons: true
    });
    compare(control(metadataEditor, "colorize-icons").checked, true);
    compare(control(metadataEditor, "drawer-enabled").checked, true);
  }

  function test_orderingRemoveAddAndCopySave() {
    const source = {
      id: "Tray",
      retained: 17,
      colorizeIcons: true,
      drawerEnabled: false,
      blacklist: ["alpha", "beta", "gamma"]
    };
    const original = JSON.stringify(source);
    const editor = createEditor(source);
    compare(control(editor, "colorize-icons").checked, true);
    compare(control(editor, "drawer-enabled").checked, false);
    const view = list(editor);
    compare(view.count, 3);
    const row = view.itemAtIndex(1);
    verify(row !== null);
    const close = descendants(row).find(item => item.icon === "close");
    verify(close !== undefined);
    mouseClick(close, close.width / 2, close.height / 2);
    tryCompare(view, "count", 2);
    compare(addRule(editor, " delta ").text, "");
    tryCompare(view, "count", 3);
    addRule(editor, "alpha");
    compare(view.count, 3);
    addRule(editor, "");
    compare(view.count, 3);
    const saved = editor.saveSettings();
    compare(JSON.stringify(saved.blacklist), JSON.stringify(["alpha", "gamma", "delta"]));
    compare(saved.retained, 17);
    compare(JSON.stringify(source), original);
    saved.blacklist.push("external");
    saved.retained = 99;
    compare(JSON.stringify(source), original);
    compare(editor.saveSettings().blacklist.length, 3);
  }

  function test_delegateGeometryAndLabels() {
    const editor = createEditor({
      blacklist: ["alpha", "beta"]
    });
    const view = list(editor);
    compare(view.count, 2);
    for (let index = 0; index < view.count; index++) {
      const row = view.itemAtIndex(index);
      verify(row !== null);
      compare(row.width, view.width);
      verify(row.width > 0);
      const label = descendants(row).find(item => item.text === ["alpha", "beta"][index]);
      verify(label !== undefined);
    }
    editor.valueColorizeIcons = true;
    tryCompare(control(editor, "colorize-icons"), "checked", true);
    editor.valueDrawerEnabled = false;
    tryCompare(control(editor, "drawer-enabled"), "checked", false);
  }

  Component {
    id: editorComponent
    TraySettings {
      width: 680
    }
  }
}
