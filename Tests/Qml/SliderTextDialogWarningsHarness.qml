import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Services.UI
import qs.Widgets
import qs.Modules.Panels.Settings.ControlCenter

Item {
  id: scene
  width: 900
  height: 700

  Component {
    id: sliderFactory
    NColorSlider {
      width: 60
      height: 240
      from: 0
      to: 1
      stepSize: 0.1
    }
  }
  Component {
    id: inputFactory
    NTextInput {
      width: 440
      text: "abcdefghij"
    }
  }
  Component {
    id: dialogFactory
    ControlCenterWidgetSettingsDialog {}
  }

  TestCase {
    id: tests
    name: "SliderTextDialog"
    when: windowShown

    SignalSpy {
      id: updates
      signalName: "updateWidgetSettings"
    }
    SignalSpy {
      id: edits
      signalName: "editingFinished"
    }

    function create(factory, properties) {
      const item = createTemporaryObject(factory, scene, properties || {});
      verify(item !== null);
      wait(30);
      return item;
    }

    function descendants(item, predicate) {
      let matches = predicate(item) ? [item] : [];
      const children = item.children || [];
      for (let i = 0; i < children.length; i++)
        matches = matches.concat(descendants(children[i], predicate));
      return matches;
    }

    function colorClose(actual, expected) {
      fuzzyCompare(actual.r, expected.r, 0.005);
      fuzzyCompare(actual.g, expected.g, 0.005);
      fuzzyCompare(actual.b, expected.b, 0.005);
      fuzzyCompare(actual.a, 1, 0.005);
    }

    function test_slider_linear_edits() {
      const slider = create(sliderFactory, {
        topColor: "#ff0000",
        bottomColor: "#0000ff"
      });
      const knob = slider.handle.children[0];
      const values = [0, 0.25, 0.5, 1, 0.75];
      for (let i = 0; i < values.length; i++) {
        slider.value = values[i];
        const position = slider.visualPosition;
        colorClose(knob.color, Qt.rgba(1 - position, 0, position, 1));
      }
      slider.topColor = "#00ff00";
      slider.bottomColor = "#ffffff";
      colorClose(knob.color, Qt.rgba(slider.visualPosition, 1, slider.visualPosition, 1));
      const other = create(sliderFactory, {
        value: 0,
        topColor: "black",
        bottomColor: "white"
      });
      colorClose(other.handle.children[0].color, Qt.rgba(1, 1, 1, 1));
      slider.value = 1;
      colorClose(knob.color, Qt.rgba(0, 1, 0, 1));
      colorClose(other.handle.children[0].color, Qt.rgba(1, 1, 1, 1));
    }

    function test_slider_rainbow_switch() {
      const slider = create(sliderFactory, {
        value: 0.25,
        rainbowMode: true,
        topColor: "black",
        bottomColor: "white"
      });
      const knob = slider.handle.children[0];
      colorClose(knob.color, Qt.hsva(0.25, 1, 1, 1));
      slider.value = 0.75;
      colorClose(knob.color, Qt.hsva(0.75, 1, 1, 1));
      slider.rainbowMode = false;
      colorClose(knob.color, Qt.rgba(0.25, 0.25, 0.25, 1));
      slider.rainbowMode = true;
      colorClose(knob.color, Qt.hsva(0.75, 1, 1, 1));
    }

    function test_slider_drag_keyboard_tooltip() {
      const slider = create(sliderFactory, {
        value: 0.2,
        tooltipText: "fixture slider"
      });
      const hover = descendants(slider.handle, item => item instanceof MouseArea)[0];
      hover.entered();
      compare(TooltipService.lastText, "fixture slider");
      mousePress(slider, slider.width / 2, slider.handle.y + slider.handle.height / 2);
      verify(slider.pressed);
      compare(TooltipService.lastText, "");
      mouseMove(slider, slider.width / 2, slider.topPadding + slider.knobDiameter / 2, 30);
      mouseRelease(slider, slider.width / 2, slider.topPadding + slider.knobDiameter / 2);
      verify(slider.value >= 0.9);
      colorClose(slider.handle.children[0].color, Qt.rgba(slider.value, slider.value, slider.value, 1));
      slider.forceActiveFocus();
      const before = slider.value;
      keyClick(Qt.Key_Down);
      fuzzyCompare(slider.value, before - 0.1, 0.001);
      hover.exited();
      compare(TooltipService.lastText, "");
    }

    function test_text_background_caret_boundaries() {
      const widget = create(inputFactory);
      const field = widget.inputItem;
      const frame = descendants(widget, item => item instanceof Control && !(item instanceof TextField) && item.contentItem !== null)[0];
      const background = frame.contentItem.children[0];
      const container = frame.contentItem.children[1];
      const rectangle = field.positionToRectangle(4);
      // Raise the production background area to exercise its pointer handler,
      // normally covered here by the field's own production MouseArea.
      background.z = 2;
      mouseClick(background, container.x + Style.marginM + rectangle.x, field.height / 2);
      verify(field.activeFocus);
      compare(field.cursorPosition, 4);
      mouseClick(background, container.x + 2, 1);
      compare(field.cursorPosition, 4);
      mouseClick(background, container.x - 1, 1);
      compare(field.cursorPosition, 4);
      mouseDoubleClickSequence(background, container.x + 20, field.height / 2);
      compare(field.selectedText, "abcdefghij");
    }

    function test_text_drag_selection_and_caret() {
      const widget = create(inputFactory);
      const field = widget.inputItem;
      const start = field.positionToRectangle(2).x;
      const end = field.positionToRectangle(7).x;
      mousePress(field, start, field.height / 2);
      compare(field.cursorPosition, 2);
      mouseMove(field, end, field.height / 2, 30);
      mouseRelease(field, end, field.height / 2);
      compare(field.selectedText, "cdefg");
      mousePress(field, end, field.height / 2);
      mouseMove(field, start, field.height / 2, 30);
      mouseRelease(field, start, field.height / 2);
      compare(field.selectedText, "cdefg");
      mouseClick(field, field.positionToRectangle(9).x, field.height / 2);
      compare(field.cursorPosition, 9);
      compare(field.selectedText, "");
      mouseMove(field, end, field.height / 2);
      compare(field.cursorPosition, 9);
    }

    function test_text_edit_select_clear_readonly() {
      const widget = create(inputFactory);
      const field = widget.inputItem;
      edits.target = widget;
      edits.clear();
      mouseDoubleClickSequence(field, field.width / 2, field.height / 2);
      compare(field.selectedText, "abcdefghij");
      keyClick(Qt.Key_Z);
      compare(widget.text, "z");
      keyClick(Qt.Key_Return);
      compare(edits.count, 1);
      const clear = descendants(widget, item => item instanceof NIconButton && item.icon === "x")[0];
      mouseClick(clear, clear.width / 2, clear.height / 2);
      compare(widget.text, "");
      verify(field.activeFocus);
      widget.text = "locked";
      widget.readOnly = true;
      verify(!clear.visible);
      keyClick(Qt.Key_Z);
      compare(widget.text, "locked");
      edits.target = null;
    }

    function button(dialog, suffix) {
      return descendants(dialog.contentItem, item => item instanceof NButton && item.text.endsWith("." + suffix))[0];
    }

    function clickButton(dialog, suffix) {
      const target = button(dialog, suffix);
      verify(target.width > 0);
      mouseClick(target, target.width / 2, target.height / 2);
    }

    function openDialog(properties) {
      const dialog = create(dialogFactory, properties);
      dialog.open();
      tryCompare(dialog, "opened", true);
      updates.target = dialog;
      updates.clear();
      return dialog;
    }

    function test_dialog_save_edits_reopen() {
      const original = {
        id: "CustomButton",
        caption: "initial",
        enabled: true
      };
      const dialog = openDialog({
        widgetId: "CustomButton",
        widgetData: original,
        widgetIndex: 3,
        sectionId: "left"
      });
      const loader = descendants(dialog.contentItem, item => item instanceof Loader)[0];
      tryCompare(loader, "status", Loader.Ready);
      const widget = descendants(loader.item, item => item instanceof NTextInput)[0];
      widget.inputItem.forceActiveFocus();
      widget.inputItem.selectAll();
      keyClick(Qt.Key_Z);
      compare(widget.text, "z");
      clickButton(dialog, "apply");
      tryCompare(dialog, "visible", false);
      compare(updates.count, 1);
      compare(updates.signalArguments[0][0], "left");
      compare(updates.signalArguments[0][1], 3);
      const saved = updates.signalArguments[0][2];
      compare(Object.keys(saved).sort().join(","), "caption,enabled,id");
      compare(saved.id, "CustomButton");
      compare(saved.caption, "z");
      compare(saved.enabled, true);
      compare(original.caption, "initial");
      compare(loader.item.saves, 1);
      dialog.widgetData = {
        id: "CustomButton",
        caption: "reopened",
        enabled: false
      };
      dialog.widgetIndex = 5;
      dialog.sectionId = "right";
      dialog.open();
      tryCompare(dialog, "opened", true);
      tryCompare(loader, "status", Loader.Ready);
      const reopened = descendants(loader.item, item => item instanceof NTextInput)[0];
      compare(reopened.text, "reopened");
      clickButton(dialog, "apply");
      tryCompare(dialog, "visible", false);
      compare(updates.count, 2);
      compare(updates.signalArguments[1][0], "right");
      compare(updates.signalArguments[1][1], 5);
      compare(updates.signalArguments[1][2].caption, "reopened");
      compare(updates.signalArguments[1][2].enabled, false);
      updates.target = null;
    }

    function test_dialog_cancel_and_empty_apply() {
      const dialog = openDialog({
        widgetId: "CustomButton",
        widgetData: {
          id: "CustomButton",
          enabled: true
        },
        widgetIndex: 1,
        sectionId: "left"
      });
      const loader = descendants(dialog.contentItem, item => item instanceof Loader)[0];
      tryCompare(loader, "status", Loader.Ready);
      const widget = descendants(loader.item, item => item instanceof NTextInput)[0];
      compare(widget.text, "fixture-default");
      widget.text = "discarded";
      clickButton(dialog, "cancel");
      tryCompare(dialog, "visible", false);
      compare(updates.count, 0);
      compare(loader.item.saves, 0);
      const empty = openDialog({
        widgetId: "Unsupported",
        widgetData: {
          id: "Unsupported"
        }
      });
      clickButton(empty, "apply");
      verify(empty.visible);
      compare(updates.count, 0);
      empty.close();
      tryCompare(empty, "visible", false);
      updates.target = null;
    }
  }
}
