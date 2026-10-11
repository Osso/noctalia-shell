import QtQuick
import QtTest
import qs.Modules.Panels.Settings.Bar.WidgetSettings

Item {
  id: scene
  width: 600
  height: 700

  Component {
    id: factory
    CustomButtonSettings {}
  }

  TestCase {
    name: "CustomButtonBarSettings"
    when: windowShown
    property var editor
    property var stored
    property var metadata: ({
        icon: "terminal",
        textStream: false,
        parseJson: false,
        maxTextLength: {
          horizontal: 20,
          vertical: 6
        },
        textIntervalMs: 1500,
        leftClickExec: "fixture-left",
        rightClickExec: "fixture-right",
        middleClickExec: "fixture-middle",
        wheelMode: "unified",
        wheelExec: "fixture-wheel",
        wheelUpExec: "fixture-up",
        wheelDownExec: "fixture-down",
        textCommand: "fixture-status",
        textCollapse: "idle"
      })

    function descendants(item) {
      let result = [];
      for (const child of item.children || [])
        result = result.concat([child], descendants(child));
      return result;
    }

    function control(label) {
      const matches = descendants(editor).filter(item => item.label === label && (item.inputItem !== undefined || item.toggled !== undefined || item.value !== undefined));
      compare(matches.length, 1, label);
      return matches[0];
    }

    function input(key) {
      return control("bar.widget-settings.custom-button." + key + ".label");
    }

    function init() {
      stored = {
        id: "CustomButton",
        keep: "unchanged",
        icon: "star",
        textStream: false,
        parseJson: false,
        leftClickExec: "",
        leftClickUpdateText: false,
        maxTextLength: {
          horizontal: 12
        },
        textIntervalMs: 2500
      };
      editor = createTemporaryObject(factory, scene, {
        widgetData: stored,
        widgetMetadata: metadata
      });
      verify(editor !== null);
      wait(10);
    }

    function test_initial_serialization_and_fallbacks() {
      const saved = editor.saveSettings();
      compare(saved.id, "CustomButton");
      compare(saved.keep, "unchanged");
      compare(saved.icon, "star");
      compare(saved.leftClickExec, "fixture-left");
      compare(saved.rightClickExec, "fixture-right");
      compare(saved.middleClickExec, "fixture-middle");
      compare(saved.wheelExec, "fixture-wheel");
      compare(saved.wheelUpExec, "fixture-up");
      compare(saved.wheelDownExec, "fixture-down");
      compare(saved.wheelMode, "unified");
      compare(saved.textCommand, "fixture-status");
      compare(saved.textCollapse, "idle");
      compare(saved.maxTextLength, {
        horizontal: 12,
        vertical: 6
      });
      compare(saved.textIntervalMs, 2500);
      compare(saved.leftClickUpdateText, false);
      compare(editor.settingValue("missing", 42), 42);
      compare(editor.valueOrDefault({
        value: 0
      }, "value", 5), 0);
      compare(editor.valueOrDefault({
        value: ""
      }, "value", "default"), "");
    }

    function test_edit_commands_stream_and_wheel_modes() {
      for (const key of ["left-click", "right-click", "middle-click", "wheel", "wheel-up", "wheel-down"])
        input(key).text = "fixture-" + key + " --never-execute";
      input("display-command-output").text = "fixture-json";
      input("collapse-condition").text = "offline";
      const wheelMode = control("Separate wheel commands");
      wheelMode.toggled(true);
      compare(input("wheel").visible, false);
      compare(input("wheel-up").visible, true);
      input("text-stream").toggled(true);
      control("Parse output as JSON").toggled(true);
      compare(input("collapse-condition").visible, true);
      compare(input("refresh-interval").visible, false);
      const commandRows = [input("left-click").parent, input("right-click").parent, input("middle-click").parent, input("wheel").parent, input("wheel-up").parent, input("wheel-down").parent];
      for (const row of commandRows) {
        const toggle = row.children.find(item => item.checked !== undefined);
        verify(toggle !== undefined);
        compare(toggle.enabled, false);
      }
      const saved = editor.saveSettings();
      compare(saved.wheelMode, "separate");
      compare(saved.leftClickExec, "fixture-left-click --never-execute");
      compare(saved.rightClickExec, "fixture-right-click --never-execute");
      compare(saved.middleClickExec, "fixture-middle-click --never-execute");
      compare(saved.wheelExec, "fixture-wheel --never-execute");
      compare(saved.wheelUpExec, "fixture-wheel-up --never-execute");
      compare(saved.wheelDownExec, "fixture-wheel-down --never-execute");
      compare(saved.textCommand, "fixture-json");
      compare(saved.textCollapse, "offline");
      compare(saved.textStream, true);
      compare(saved.parseJson, true);
      wheelMode.toggled(false);
      input("text-stream").toggled(false);
      compare(editor.saveSettings().wheelMode, "unified");
      compare(input("wheel").visible, true);
      compare(input("refresh-interval").visible, true);
    }

    function test_control_constraints_and_interval_conversion() {
      const horizontal = control("Max text length (horizontal)");
      const vertical = control("Max text length (vertical)");
      compare(horizontal.from, 0);
      compare(horizontal.to, 100);
      compare(vertical.from, 0);
      compare(vertical.to, 100);
      horizontal.value = 0;
      vertical.value = 100;
      input("refresh-interval").text = "";
      compare(editor.saveSettings().textIntervalMs, 1500);
      input("refresh-interval").text = "4500";
      const saved = editor.saveSettings();
      compare(saved.textIntervalMs, 4500);
      compare(saved.maxTextLength, {
        horizontal: 0,
        vertical: 100
      });
    }

    function test_save_copy_discard_and_reopen() {
      const before = JSON.stringify(stored);
      input("left-click").text = "fixture-unsaved";
      const saved = editor.saveSettings();
      compare(JSON.stringify(stored), before);
      compare(saved.leftClickExec, "fixture-unsaved");
      saved.maxTextLength.horizontal = 99;
      compare(stored.maxTextLength.horizontal, 12);
      editor.destroy();
      wait(1);
      editor = createTemporaryObject(factory, scene, {
        widgetData: stored,
        widgetMetadata: metadata
      });
      compare(input("left-click").text, "fixture-left");
      editor.destroy();
      wait(1);
      editor = createTemporaryObject(factory, scene, {
        widgetData: saved,
        widgetMetadata: metadata
      });
      compare(input("left-click").text, "fixture-unsaved");
      compare(editor.saveSettings().maxTextLength.horizontal, 99);
    }
  }
}
