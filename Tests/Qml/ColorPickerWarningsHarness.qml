import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Widgets
import qs.Services.UI

Item {
  id: scene
  width: 1000
  height: 800
  visible: true // Offscreen QPA, not a desktop surface.

  Component {
    id: pickerFactory
    NColorPickerDialog {}
  }

  TestCase {
    name: "ProductionColorPicker"
    when: windowShown
    property var picker

    SignalSpy {
      id: selectedSpy
      signalName: "colorSelected"
    }

    function findItems(item, predicate) {
      let matches = predicate(item) ? [item] : [];
      const children = item.children || [];
      for (let i = 0; i < children.length; i++)
        matches = matches.concat(findItems(children[i], predicate));
      return matches;
    }

    function button(label) {
      return findItems(picker.contentItem, item => item instanceof NButton && item.text === "widgets.color-picker." + label)[0];
    }

    function palettes(target) {
      return findItems(target.contentItem, item => item instanceof Repeater);
    }

    function clickVisible(item) {
      const scroll = picker.contentItem;
      const flick = scroll.contentItem;
      const position = item.mapToItem(flick, 0, 0);
      flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, flick.contentY + position.y - flick.height / 2));
      wait(30);
      mouseClick(item, item.width / 2, item.height / 2);
    }

    function openPicker(color) {
      picker.selectedColor = color;
      picker.open();
      tryCompare(picker, "opened", true);
      verify(picker.height > 0);
      verify(picker.height <= scene.Screen.height);
    }

    function expandPalette() {
      const collapsible = findItems(picker.contentItem, item => item instanceof NCollapsible)[0];
      clickVisible(collapsible.children[0]);
      tryCompare(collapsible, "expanded", true);
    }

    function init() {
      picker = createTemporaryObject(pickerFactory, scene);
      verify(picker !== null);
      selectedSpy.target = picker;
      selectedSpy.clear();
    }

    function cleanup() {
      picker.close();
      tryCompare(picker, "visible", false);
      selectedSpy.target = null;
      wait(30);
    }

    function test_select_confirm_and_reopen() {
      openPicker("#123456");
      expandPalette();
      const theme = palettes(picker)[0];
      compare(theme.count, 7);
      clickVisible(theme.itemAt(1));
      compare(picker.selectedColor, NColor.mSecondary);
      compare(selectedSpy.count, 0);
      compare(theme.itemAt(1).border.width, Style.borderM);
      compare(theme.itemAt(0).border.width, Style.borderS);
      clickVisible(button("apply"));
      tryCompare(picker, "visible", false);
      compare(selectedSpy.count, 1);
      compare(selectedSpy.signalArguments[0][0], NColor.mSecondary);
      openPicker("#2468ac");
      compare(picker.selectedColor.toString(), "#2468ac");
      compare(theme.itemAt(1).border.width, Style.borderS);
      const spins = findItems(picker.contentItem, item => item instanceof NSpinBox);
      compare(spins[0].value, 36);
      compare(spins[1].value, 104);
      compare(spins[2].value, 172);
    }

    function test_cancel_and_reopen() {
      openPicker("#123456");
      expandPalette();
      const named = palettes(picker)[1];
      verify(named.count > 7);
      const swatch = named.itemAt(2);
      clickVisible(swatch);
      compare(picker.selectedColor, swatch.swatchColor);
      compare(swatch.border.width, 2);
      clickVisible(button("cancel"));
      tryCompare(picker, "visible", false);
      compare(selectedSpy.count, 0);
      openPicker("#abcdef");
      compare(picker.selectedColor.toString(), "#abcdef");
      compare(swatch.border.width, 1);
    }

    function test_recreated_delegates_keep_instance_owner() {
      openPicker("#123456");
      expandPalette();
      picker.close();
      tryCompare(picker, "visible", false);
      const other = createTemporaryObject(pickerFactory, scene, {
        selectedColor: "#654321"
      });
      verify(other !== null);
      other.open();
      tryCompare(other, "opened", true);
      other.close();
      tryCompare(other, "visible", false);
      openPicker("#123456");
      const repeaters = palettes(picker);
      for (let i = 0; i < repeaters.length; i++) {
        const repeater = repeaters[i];
        const count = repeater.count;
        const originalModel = [];
        for (let row = 0; row < count; row++) {
          const swatch = repeater.itemAt(row);
          originalModel.push({
            name: swatch.swatchName,
            color: swatch.swatchColor
          });
        }
        repeater.model = [];
        tryCompare(repeater, "count", 0);
        repeater.model = originalModel;
        tryCompare(repeater, "count", count);
        const swatch = repeater.itemAt(0);
        clickVisible(swatch);
        compare(picker.selectedColor, swatch.swatchColor);
        compare(other.selectedColor.toString(), "#654321");
        verify(swatch.border.width > 1);
        mouseMove(swatch, -3, -3);
        mouseMove(swatch, 12, 12);
        tryCompare(TooltipService, "lastText", swatch.swatchName + "\n" + swatch.swatchColor.toString().toUpperCase());
        compare(selectedSpy.count, 0);
      }
    }
  }
}
