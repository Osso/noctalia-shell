import QtQuick
import QtQuick.Controls
import QtTest
import qs.Widgets

Item {
  id: scene
  width: 1000
  height: 800
  visible: true // Offscreen QPA; never a desktop surface.

  Component {
    id: pickerFactory
    NIconPicker {}
  }

  TestCase {
    name: "ProductionIconPicker"
    when: windowShown
    property var picker

    SignalSpy {
      id: selectedSpy
      signalName: "iconSelected"
    }

    function findItem(item, predicate) {
      if (predicate(item))
        return item;
      const children = item.children || [];
      for (let i = 0; i < children.length; i++) {
        const found = findItem(children[i], predicate);
        if (found)
          return found;
      }
      return null;
    }

    function grid() {
      return findItem(picker.contentItem, item => item instanceof NGridView);
    }

    function search() {
      return findItem(picker.contentItem, item => item instanceof NTextInput);
    }

    function button(label) {
      return findItem(picker.contentItem, item => item instanceof NButton && item.text === "widgets.icon-picker." + label);
    }

    function openPicker(initial) {
      picker.initialIcon = initial;
      picker.open();
      tryCompare(picker, "opened", true);
      grid().forceLayout();
      wait(30);
    }

    function clickIcon(index, doubleClick) {
      grid().forceLayout();
      const delegate = grid().itemAtIndex(index);
      verify(delegate !== null);
      if (doubleClick)
        mouseDoubleClickSequence(delegate, delegate.width / 2, delegate.height / 2);
      else
        mouseClick(delegate, delegate.width / 2, delegate.height / 2);
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

    function test_keyboard_search_and_escape() {
      openPicker("");
      compare(grid().count, 4);
      tryCompare(search().inputItem, "activeFocus", true);
      keyClick(Qt.Key_B, Qt.ShiftModifier);
      keyClick(Qt.Key_E);
      keyClick(Qt.Key_T);
      keyClick(Qt.Key_A);
      tryCompare(picker, "query", "beta");
      tryCompare(grid(), "count", 2);
      compare(picker.filteredIcons.join(","), "beta,beta-outline");
      keyClick(Qt.Key_Escape);
      tryCompare(picker, "visible", false);
      compare(selectedSpy.count, 0);
    }

    function test_click_apply_and_reopen() {
      openPicker("");
      compare(button("apply").enabled, false);
      clickIcon(1, false);
      compare(picker.selectedIcon, "beta");
      compare(selectedSpy.count, 0);
      compare(grid().itemAtIndex(1).border.width, 1);
      compare(grid().itemAtIndex(0).border.width, 0);
      mouseClick(button("apply"));
      tryCompare(picker, "visible", false);
      compare(selectedSpy.count, 1);
      compare(selectedSpy.signalArguments[0][0], "beta");
      openPicker("gamma");
      compare(picker.selectedIcon, "gamma");
      compare(picker.query, "gamma");
      compare(search().text, "gamma");
      tryCompare(grid(), "count", 1);
      compare(button("apply").enabled, true);
    }

    function test_search_recreates_delegates_and_double_clicks() {
      openPicker("");
      search().text = "  BeTa  ";
      tryCompare(picker, "query", "beta");
      tryCompare(grid(), "count", 2);
      clickIcon(1, false);
      compare(picker.selectedIcon, "beta-outline");
      search().text = "no-match";
      tryCompare(grid(), "count", 0);
      search().text = "";
      tryCompare(grid(), "count", 4);
      clickIcon(0, true);
      tryCompare(picker, "visible", false);
      compare(selectedSpy.count, 1);
      compare(selectedSpy.signalArguments[0][0], "alpha");
    }

    function test_cancel_preserves_no_emission() {
      openPicker("beta");
      tryCompare(grid(), "count", 2);
      clickIcon(1, false);
      mouseClick(button("cancel"));
      tryCompare(picker, "visible", false);
      compare(selectedSpy.count, 0);
      openPicker("alpha");
      compare(picker.selectedIcon, "alpha");
      compare(picker.filteredIcons.join(","), "alpha");
    }

    function test_two_instances_keep_delegate_owners() {
      openPicker("");
      picker.close();
      tryCompare(picker, "visible", false);
      const other = createTemporaryObject(pickerFactory, scene, {
        initialIcon: "gamma"
      });
      verify(other !== null);
      other.open();
      tryCompare(other, "opened", true);
      other.close();
      tryCompare(other, "visible", false);
      openPicker("");
      clickIcon(2, false);
      compare(picker.selectedIcon, "beta-outline");
      compare(other.selectedIcon, "gamma");
      compare(selectedSpy.count, 0);
    }
  }
}
