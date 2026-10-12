import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Modules.OSD
import qs.Modules.Panels.Settings.Bar.WidgetSettings
import qs.Modules.Panels.Settings.Tabs

TestCase {
  id: suite
  name: "GroupedOsdSettings"
  width: 800
  height: 1600
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

  function grouped(data, metadata) {
    const editor = createTemporaryObject(groupedComponent, suite, {
                                           widgetData: data || {
                                             labelMode: "none"
                                           },
                                           widgetMetadata: metadata || {
                                             hideUnoccupied: false,
                                             labelMode: "none",
                                             showLabelsOnlyWhenOccupied: false,
                                             colorizeIcons: false
                                           }
                                         });
    verify(editor !== null);
    wait(50);
    return editor;
  }

  function osd() {
    const editor = createTemporaryObject(osdComponent, suite);
    verify(editor !== null);
    wait(50);
    return editor;
  }

  function choose(option, index) {
    const combo = descendants(option).find(item => item.popup !== undefined && item.currentIndex !== undefined);
    verify(combo !== undefined);
    combo.forceActiveFocus();
    keyClick(Qt.Key_Home);
    for (let step = 0; step < index; step++)
      keyClick(Qt.Key_Down);
    compare(combo.contentItem.text, option.model[index].name);
  }

  function toggle(option, expected, checkbox) {
    const target = option.children[checkbox ? 2 : 1];
    mouseClick(target, target.width / 2, target.height / 2);
    tryCompare(option, "checked", expected);
  }

  function init() {
    Settings.data.osd = fixtureOsd;
    fixtureOsd.location = "top_right";
    fixtureOsd.enabled = true;
    fixtureOsd.overlayLayer = false;
    fixtureOsd.backgroundOpacity = 0.8;
    fixtureOsd.autoHideMs = 2000;
    fixtureOsd.enabledTypes = [OSD.Type.Volume];
    fixtureOsd.monitors = ["TEST-A"];
  }

  function test_groupedDefaultsAndOptions() {
    const editor = grouped();
    compare(editor.valueHideUnoccupied, false);
    compare(editor.valueLabelMode, "none");
    const combo = control(editor, "bar.widget-settings.workspace.label-mode.label");
    compare(JSON.stringify(combo.model.map(option => option.key)), JSON.stringify(["none", "index", "name", "index+name"]));
    for (let index = 0; index < combo.model.length; index++) {
      choose(combo, index);
      compare(editor.saveSettings().labelMode, combo.model[index].key);
    }
    const defaults = grouped({
                               labelMode: "name"
                             }, {
                               hideUnoccupied: true,
                               labelMode: "name",
                               showLabelsOnlyWhenOccupied: true,
                               colorizeIcons: true
                             });
    compare(defaults.saveSettings().hideUnoccupied, true);
    compare(defaults.saveSettings().labelMode, "name");
    compare(defaults.saveSettings().showLabelsOnlyWhenOccupied, true);
    compare(defaults.saveSettings().colorizeIcons, true);
  }

  function test_groupedPendingCopySaveAndIndependentInstances() {
    const source = {
      id: "TaskbarGrouped",
      retained: 23,
      hideUnoccupied: true,
      labelMode: "index",
      showLabelsOnlyWhenOccupied: true,
      colorizeIcons: true
    };
    const original = JSON.stringify(source);
    const editor = grouped(source);
    const other = grouped({
                            labelMode: "name"
                          });
    other.visible = false;
    const combo = control(editor, "bar.widget-settings.workspace.label-mode.label");
    compare(combo.currentKey, "index");
    toggle(control(editor, "bar.widget-settings.workspace.hide-unoccupied.label"), false, false);
    toggle(control(editor, "bar.widget-settings.taskbar-grouped.show-labels-only-when-occupied.label"), false, false);
    toggle(control(editor, "bar.widget-settings.active-window.colorize-icons.label"), false, false);
    choose(combo, 3);
    compare(JSON.stringify(source), original);
    const saved = editor.saveSettings();
    compare(saved.hideUnoccupied, false);
    compare(saved.labelMode, "index+name");
    compare(saved.showLabelsOnlyWhenOccupied, false);
    compare(saved.colorizeIcons, false);
    compare(saved.retained, 23);
    saved.retained = 99;
    saved.labelMode = "none";
    compare(JSON.stringify(source), original);
    compare(other.saveSettings().labelMode, "name");
    compare(editor.saveSettings().labelMode, "index+name");
    editor.valueHideUnoccupied = true;
    tryCompare(control(editor, "bar.widget-settings.workspace.hide-unoccupied.label"), "checked", true);
  }

  function test_osdLocationAndGeneralOptions() {
    const editor = osd();
    const combo = control(editor, "settings.osd.location.label");
    compare(JSON.stringify(combo.model.map(option => option.key)), JSON.stringify(["top", "top_left", "top_right", "bottom", "bottom_left", "bottom_right", "left", "right"]));
    compare(combo.currentKey, "top_right");
    choose(combo, 7);
    tryCompare(combo, "currentKey", "right");
    compare(Settings.data.osd.location, "right");
    toggle(control(editor, "settings.osd.enabled.label"), false, false);
    toggle(control(editor, "settings.osd.always-on-top.label"), true, false);
    compare(Settings.data.osd.enabled, false);
    compare(Settings.data.osd.overlayLayer, true);
  }

  function test_osdTypesImmutableSelection() {
    const editor = osd();
    const original = Settings.data.osd.enabledTypes;
    const option = control(editor, "settings.osd.types.brightness.label");
    compare(option.checked, false);
    toggle(option, true, true);
    compare(JSON.stringify(Settings.data.osd.enabledTypes), JSON.stringify([OSD.Type.Volume, OSD.Type.Brightness]));
    compare(JSON.stringify(original), JSON.stringify([OSD.Type.Volume]));
    verify(Settings.data.osd.enabledTypes !== original);
    toggle(control(editor, "settings.osd.types.volume.label"), false, true);
    compare(JSON.stringify(Settings.data.osd.enabledTypes), JSON.stringify([OSD.Type.Brightness]));
    toggle(option, false, true);
    compare(Settings.data.osd.enabledTypes.length, 0);
    const types = [OSD.Type.LockKey];
    compare(JSON.stringify(editor.addType(types, OSD.Type.LockKey)), JSON.stringify(types));
    compare(types.length, 1);
  }

  function test_osdMonitorsImmutableSelection() {
    const editor = osd();
    const original = Settings.data.osd.monitors;
    compare(control(editor, "TEST-A").checked, true);
    const second = control(editor, "TEST-B");
    compare(second.monitorWidth, 2560);
    compare(second.monitorHeight, 1440);
    compare(second.monitorModel, "Fixture B");
    toggle(second, true, true);
    compare(JSON.stringify(Settings.data.osd.monitors), JSON.stringify(["TEST-A", "TEST-B"]));
    compare(JSON.stringify(original), JSON.stringify(["TEST-A"]));
    verify(Settings.data.osd.monitors !== original);
    toggle(control(editor, "TEST-A"), false, true);
    compare(JSON.stringify(Settings.data.osd.monitors), JSON.stringify(["TEST-B"]));
    toggle(second, false, true);
    compare(Settings.data.osd.monitors.length, 0);
    const names = ["TEST-A"];
    compare(JSON.stringify(editor.addMonitor(names, "TEST-A")), JSON.stringify(names));
    compare(names.length, 1);
  }

  QtObject {
    id: fixtureOsd
    property string location
    property bool enabled
    property bool overlayLayer
    property real backgroundOpacity
    property int autoHideMs
    property var enabledTypes
    property var monitors
  }

  Component {
    id: groupedComponent
    TaskbarGroupedSettings {
      width: 750
    }
  }

  Component {
    id: osdComponent
    OsdTab {
      width: 750
    }
  }
}
