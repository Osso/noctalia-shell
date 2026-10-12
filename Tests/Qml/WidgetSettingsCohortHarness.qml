pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Services.UI
import qs.Modules.Panels.Settings.Bar

TestCase {
  id: suite
  name: "WidgetSettingsCohort"
  width: 1100
  height: 1800
  when: windowShown
  property var updates: []

  Component {
    id: dialogComponent
    BarWidgetSettingsDialog {
      onUpdateWidgetSettings: (section, index, settings) => {
        suite.updates.push({
          section: section,
          index: index,
          settings: settings
        });
        Settings.data.bar.widgets[section][index] = settings;
      }
    }
  }

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function cases() {
    return ["LockKeys", "ControlCenter", "SystemMonitor", "MediaMini", "Workspace"].map(name => ({
          tag: name,
          name: name
        }));
  }

  function fixture(name) {
    const settings = Object.assign({
      id: name,
      retained: 73
    }, BarWidgetRegistry.widgetMetadata[name]);
    for (const key of Object.keys(settings)) {
      if (typeof settings[key] === "boolean")
        settings[key] = !settings[key];
    }
    if (name === "MediaMini")
      settings.hideMode = "idle";
    return settings;
  }

  function openDialog(name, settings) {
    suite.updates = [];
    Settings.data.bar.widgets.left = [settings];
    const dialog = createTemporaryObject(dialogComponent, suite, {
      widgetId: name,
      widgetIndex: 0,
      sectionId: "left",
      widgetData: settings
    });
    verify(dialog !== null);
    dialog.open();
    tryCompare(dialog, "opened", true);
    tryVerify(() => editor(dialog) !== undefined);
    wait(50);
    return dialog;
  }

  function editor(dialog) {
    return descendants(dialog.contentItem).find(item => typeof item.saveSettings === "function");
  }

  function controls(item, signal) {
    return descendants(item).filter(child => child[signal] !== undefined && child.label !== undefined);
  }

  function button(dialog, action) {
    const control = descendants(dialog.contentItem).find(item => item.text === "bar.widget-settings.dialog." + action);
    verify(control !== undefined);
    control.clicked();
    tryCompare(dialog, "opened", false);
  }

  function test_togglesAndSave_data() {
    return cases();
  }

  function test_togglesAndSave(data) {
    const source = fixture(data.name);
    const original = JSON.stringify(source);
    const dialog = openDialog(data.name, source);
    const loaded = editor(dialog);
    const initial = loaded.saveSettings();
    for (const key of Object.keys(source))
      compare(initial[key], source[key], key);
    const toggles = controls(loaded, "toggled");
    const counts = {
      LockKeys: 3,
      ControlCenter: 2,
      SystemMonitor: 8,
      MediaMini: 5,
      Workspace: 2
    };
    compare(toggles.length, counts[data.name]);
    const initialValues = toggles.map(toggle => toggle.checked);
    for (const toggle of toggles)
      toggle.toggled(!toggle.checked);
    wait(0);
    const saved = loaded.saveSettings();
    for (let index = 0; index < toggles.length; index++)
      compare(toggles[index].checked, !initialValues[index]);
    for (const key of Object.keys(source)) {
      if (typeof source[key] === "boolean" && key !== "hideWhenIdle")
        compare(saved[key], !source[key], key);
    }
    compare(saved.retained, 73);
    compare(JSON.stringify(source), original);
    saved.retained = 99;
    compare(source.retained, 73);
    dialog.close();
    tryCompare(dialog, "opened", false);
    compare(suite.updates.length, 0);
  }

  function test_cancelReopenAndApply_data() {
    return cases();
  }

  function test_cancelReopenAndApply(data) {
    const source = fixture(data.name);
    const original = JSON.stringify(source);
    const dialog = openDialog(data.name, source);
    const toggle = controls(editor(dialog), "toggled")[0];
    const initial = toggle.checked;
    toggle.toggled(!initial);
    button(dialog, "cancel");
    compare(suite.updates.length, 0);
    compare(JSON.stringify(Settings.data.bar.widgets.left[0]), original);
    dialog.open();
    tryCompare(dialog, "opened", true);
    wait(50);
    const reopened = editor(dialog);
    compare(controls(reopened, "toggled")[0].checked, initial);
    controls(reopened, "toggled")[0].toggled(!initial);
    const expected = reopened.saveSettings();
    button(dialog, "apply");
    compare(suite.updates.length, 1);
    compare(suite.updates[0].section, "left");
    compare(suite.updates[0].index, 0);
    compare(suite.updates[0].settings, expected);
    compare(Settings.data.bar.widgets.left[0], expected);
    compare(JSON.stringify(source), original);
  }

  function test_metadataDefaults_data() {
    return cases();
  }

  function test_metadataDefaults(data) {
    const dialog = openDialog(data.name, {
      id: data.name,
      retained: 73
    });
    const saved = editor(dialog).saveSettings();
    const metadata = BarWidgetRegistry.widgetMetadata[data.name];
    for (const key of Object.keys(metadata)) {
      if (key !== "hideWhenIdle")
        compare(saved[key], metadata[key], key);
    }
    if (data.name === "MediaMini")
      compare(saved.hideMode, "hidden");
    button(dialog, "cancel");
    compare(suite.updates.length, 0);
  }

  function test_dependentControlsAndValidation() {
    const monitorDialog = openDialog("SystemMonitor", fixture("SystemMonitor"));
    const monitor = editor(monitorDialog);
    const monitorToggles = controls(monitor, "toggled");
    compare(monitorToggles[4].visible, false);
    monitorToggles[3].toggled(true);
    compare(monitorToggles[4].visible, true);
    const disk = controls(monitor, "selected")[0];
    compare(disk.visible, false);
    monitorToggles[6].toggled(true);
    compare(disk.visible, true);
    compare(disk.model.map(entry => entry.key), ["/", "/data"]);
    disk.selected("/data");
    compare(monitor.saveSettings().diskPath, "/data");
    button(monitorDialog, "cancel");

    const controlDialog = openDialog("ControlCenter", fixture("ControlCenter"));
    const center = editor(controlDialog);
    const color = controls(center, "selected")[0];
    compare(color.visible, true);
    controls(center, "toggled")[1].toggled(false);
    compare(color.visible, false);
    color.selected("secondary");
    compare(center.saveSettings().colorizeSystemIcon, "secondary");
    const browse = descendants(center).filter(item => item.clicked !== undefined && typeof item.text === "string" && item.text.startsWith("bar.widget-settings.control-center.browse-"));
    compare(browse.length, 2);
    verify(browse.every(item => item.enabled));
    controls(center, "toggled")[0].toggled(true);
    verify(browse.every(item => !item.enabled));
    button(controlDialog, "cancel");

    const mediaDialog = openDialog("MediaMini", fixture("MediaMini"));
    const media = editor(mediaDialog);
    const combos = controls(media, "selected");
    compare(combos[1].visible, false);
    controls(media, "toggled")[2].toggled(true);
    compare(combos[1].visible, true);
    combos[0].selected("transparent");
    combos[1].selected("wave");
    combos[2].selected("never");
    const width = descendants(media).find(item => item.inputItem !== undefined && item.label === "bar.widget-settings.media-mini.max-width.label");
    verify(width !== undefined);
    width.text = "315";
    compare(media.saveSettings().maxWidth, 315);
    for (const invalid of ["", "nonsense", "0"]) {
      width.text = invalid;
      compare(media.saveSettings().maxWidth, 240);
    }
    compare(media.saveSettings().hideMode, "transparent");
    compare(media.saveSettings().visualizerType, "wave");
    compare(media.saveSettings().scrollingMode, "never");
    button(mediaDialog, "cancel");

    const workspaceDialog = openDialog("Workspace", fixture("Workspace"));
    const workspace = editor(workspaceDialog);
    const spin = descendants(workspace).find(item => typeof item.changeValue === "function");
    verify(spin !== undefined);
    compare(spin.visible, true);
    spin.changeValue(1, 100);
    compare(workspace.saveSettings().characterCount, 10);
    spin.changeValue(1, 1);
    compare(workspace.saveSettings().characterCount, 10);
    spin.changeValue(-1, 100);
    compare(workspace.saveSettings().characterCount, 1);
    spin.changeValue(-1, 1);
    compare(workspace.saveSettings().characterCount, 1);
    controls(workspace, "selected")[0].selected("index");
    compare(spin.visible, false);
    compare(workspace.saveSettings().labelMode, "index");
    button(workspaceDialog, "cancel");
  }
}
