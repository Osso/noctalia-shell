import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Widgets

Item {
  id: scene
  width: 1000
  height: 800
  visible: true // Private offscreen QPA only.

  ListModel {
    id: available
    ListElement {
      key: "Clock"
      name: "Clock"
    }
    ListElement {
      key: "Battery"
      name: "Battery"
    }
  }

  Component {
    id: sectionFactory
    NSectionEditor {
      width: 900
      height: 300
      sectionId: "left"
      sectionName: "Fixture"
      availableWidgets: available
      widgetModel: [
        {
          id: "Clock"
        },
        {
          id: "Battery"
        },
        {
          id: "Media"
        }
      ]
    }
  }

  Component {
    id: pickerFactory
    NColorPicker {
      x: 20
      y: 350
      selectedColor: "#123456"
    }
  }

  TestCase {
    id: tests
    name: "SectionColorOwners"
    when: windowShown
    property NSectionEditor section
    property NColorPicker picker

    SignalSpy {
      id: addSpy
      signalName: "addWidget"
    }
    SignalSpy {
      id: removeSpy
      signalName: "removeWidget"
    }
    SignalSpy {
      id: reorderSpy
      signalName: "reorderWidget"
    }
    SignalSpy {
      id: startedSpy
      signalName: "dragPotentialStarted"
    }
    SignalSpy {
      id: endedSpy
      signalName: "dragPotentialEnded"
    }
    SignalSpy {
      id: colorSpy
      signalName: "colorSelected"
    }

    function findItems(item, predicate) {
      let matches = predicate(item) ? [item] : [];
      const children = item.children || [];
      for (let i = 0; i < children.length; i++)
        matches = matches.concat(findItems(children[i], predicate));
      return matches;
    }

    function init() {
      section = createTemporaryObject(sectionFactory, scene);
      picker = createTemporaryObject(pickerFactory, scene);
      verify(section !== null);
      verify(picker !== null);
      addSpy.target = section;
      removeSpy.target = section;
      reorderSpy.target = section;
      startedSpy.target = section;
      endedSpy.target = section;
      colorSpy.target = picker;
      for (const spy of [addSpy, removeSpy, reorderSpy, startedSpy, endedSpy, colorSpy])
        spy.clear();
      wait(30);
    }

    function test_section_add_remove_capacity() {
      const combo = findItems(section, item => item instanceof NSearchableComboBox)[0];
      const add = findItems(section, item => item instanceof NIconButton && item.icon === "add")[0];
      verify(!add.enabled);
      combo.selected("Clock");
      compare(combo.currentKey, "Clock");
      verify(add.enabled);
      mouseClick(add, add.width / 2, add.height / 2);
      compare(addSpy.count, 1);
      compare(Array.from(addSpy.signalArguments[0]), ["Clock", "left"]);
      compare(combo.currentKey, "");
      section.maxWidgets = 3;
      combo.selected("Battery");
      verify(!add.enabled);
      verify(!combo.enabled);
      const remove = findItems(section, item => item instanceof NIconButton && item.icon === "close");
      compare(remove.length, 3);
      mouseClick(remove[1], remove[1].width / 2, remove[1].height / 2);
      compare(removeSpy.count, 1);
      compare(Array.from(removeSpy.signalArguments[0]), ["left", 1]);
      section.widgetModel = [
        {
          id: "Clock"
        },
        {
          id: "Media"
        }
      ];
      tryCompare(combo, "enabled", true);
      verify(add.enabled);
    }

    function test_section_drag_reorder() {
      const flow = findItems(section, item => item instanceof Flow)[0];
      const tiles = findItems(flow, item => item.widgetIndex !== undefined);
      compare(tiles.length, 3);
      const area = findItems(section, item => item instanceof MouseArea && item.dragThreshold !== undefined)[0];
      const start = tiles[0].mapToItem(area, 10, tiles[0].height / 2);
      const end = tiles[2].mapToItem(area, tiles[2].width + 2, tiles[2].height / 2);
      mousePress(area, start.x, start.y);
      compare(startedSpy.count, 1);
      mouseMove(area, start.x + 20, start.y, 20);
      mouseMove(area, end.x, end.y, 20);
      mouseRelease(area, end.x, end.y);
      compare(reorderSpy.count, 1);
      compare(Array.from(reorderSpy.signalArguments[0]), ["left", 0, 2]);
      compare(endedSpy.count, 1);
      section.widgetModel = [
        {
          id: "Battery"
        },
        {
          id: "Media"
        },
        {
          id: "Clock"
        }
      ];
      tryCompare(findItems(flow, item => item.widgetIndex === 2)[0], "widgetId", "Clock");
      compare(area.dragStarted, false);
    }

    function findDialog() {
      return findChild(picker, "testColorDialog");
    }

    function openPicker() {
      mouseClick(picker, picker.width / 2, picker.height / 2);
      let dialog = null;
      tryVerify(function () {
        dialog = findDialog();
        return dialog !== null && dialog.opened;
      });
      return dialog;
    }

    function clickControl(dialog, control) {
      const flick = dialog.contentItem.contentItem;
      const position = control.mapToItem(flick, 0, 0);
      flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, flick.contentY + position.y - flick.height / 2));
      wait(30);
      mouseClick(control, control.width / 2, control.height / 2);
    }

    function test_color_controls_commit_cancel_reopen() {
      let dialog = openPicker();
      compare(dialog.selectedColor.toString(), "#123456");
      const spins = findItems(dialog.contentItem, item => item instanceof NSpinBox);
      compare(spins[0].value, 18);
      compare(spins[1].value, 52);
      compare(spins[2].value, 86);
      const input = findItems(spins[0], item => item instanceof TextInput)[0];
      clickControl(dialog, input);
      keyClick(Qt.Key_A, Qt.ControlModifier);
      keyClick(Qt.Key_1);
      keyClick(Qt.Key_2);
      keyClick(Qt.Key_8);
      keyClick(Qt.Key_Return);
      tryCompare(spins[0], "value", 128);
      compare(Math.round(dialog.selectedColor.r * 255), 128);
      compare(picker.selectedColor.toString(), "#123456");
      const apply = findItems(dialog.contentItem, item => item instanceof NButton && item.text === "widgets.color-picker.apply")[0];
      clickControl(dialog, apply);
      tryCompare(dialog, "visible", false);
      compare(colorSpy.count, 1);
      compare(picker.selectedColor.toString(), "#803456");
      compare(colorSpy.signalArguments[0][0], picker.selectedColor);
      const label = findItems(picker, item => item instanceof NText)[0];
      compare(label.text, "#803456");
      picker.selectedColor = "#abcdef";
      dialog = openPicker();
      compare(dialog.selectedColor.toString(), "#abcdef");
      dialog.selectedColor = "#fedcba";
      const cancel = findItems(dialog.contentItem, item => item instanceof NButton && item.text === "widgets.color-picker.cancel")[0];
      clickControl(dialog, cancel);
      tryCompare(dialog, "visible", false);
      compare(picker.selectedColor.toString(), "#abcdef");
      compare(colorSpy.count, 1);
      dialog = openPicker();
      compare(dialog.selectedColor.toString(), "#abcdef");
      dialog.close();
      tryCompare(dialog, "visible", false);
    }
  }
}
