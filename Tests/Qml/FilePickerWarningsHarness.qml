import QtQuick
import QtTest
import qs.Widgets

Item {
  id: harness
  width: 1000
  height: 800
  visible: true // qmltestrunner uses offscreen QPA only

  NFilePicker {
    id: picker
    initialPath: "@FILES@"
  }

  TestCase {
    name: "ProductionFilePicker"
    when: windowShown

    SignalSpy {
      id: acceptedSpy
      target: picker
      signalName: "accepted"
    }
    SignalSpy {
      id: cancelledSpy
      target: picker
      signalName: "cancelled"
    }

    function findChild(item, predicate) {
      if (predicate(item))
        return item;
      const children = item.children || [];
      for (let i = 0; i < children.length; i++) {
        const found = findChild(children[i], predicate);
        if (found)
          return found;
      }
      return null;
    }

    function entry(name, listMode) {
      return findChild(picker.contentItem, item => item.visible && item.fileName === name && item.height === (listMode ? 40 : grid().cellHeight));
    }

    function grid() {
      return findChild(picker.contentItem, item => item.cellWidth !== undefined);
    }

    function button(text, required = true) {
      const control = findChild(picker.contentItem, item => item.text === text && item.clicked !== undefined);
      if (required)
        verify(control !== null, "Missing picker button: " + text);
      return control;
    }

    function openPicker() {
      picker.openFilePicker();
      tryCompare(picker, "opened", true);
      tryVerify(() => grid().count === 3);
      tryVerify(() => entry("alpha.txt", false) !== null);
      verify(entry(".hidden.txt", false) === null);
    }

    function init() {
      acceptedSpy.clear();
      cancelledSpy.clear();
      picker.navigateToPath("@FILES@");
      picker.selectedPaths = [];
      picker.setSearchBarVisible(false);
      picker.openFilePicker();
      tryCompare(picker, "opened", true);
      const toggle = button("filepicker-layout-grid", false);
      if (toggle)
        mouseClick(toggle);
    }

    function cleanup() {
      picker.close();
      tryCompare(picker, "visible", false);
      wait(50); // Allow Popup exit and scenegraph disposal before the next case.
    }

    function test_model_lifecycle_data() {
      return [
            {
              tag: "grid",
              listMode: false
            },
            {
              tag: "list",
              listMode: true
            }
          ];
    }

    function test_model_lifecycle(data) {
      openPicker();
      if (data.listMode)
        mouseClick(button("filepicker-list"));
      tryVerify(() => entry("alpha.txt", data.listMode) !== null);
      const alpha = entry("alpha.txt", data.listMode);
      mouseClick(alpha, alpha.width / 2, alpha.height / 2);
      const select = button("widgets.file-picker.select-file");
      tryCompare(select, "enabled", true);

      picker.setSearchBarVisible(true);
      const search = findChild(picker.contentItem, item => item.inputIconName === "search");
      tryCompare(search, "activeFocus", true);
      keyClick(Qt.Key_N);
      tryCompare(grid(), "count", 0);
      keyClick(Qt.Key_A, Qt.ControlModifier);
      keyClick(Qt.Key_B);
      tryCompare(grid(), "count", 1);
      tryVerify(() => entry("beta.log", data.listMode) !== null);
      picker.setSearchBarVisible(false);
      tryCompare(grid(), "count", 3);

      const view = data.listMode ? findChild(picker.contentItem, item => item.model !== undefined && item.currentIndex !== undefined && item.cellWidth === undefined) : grid();
      verify(view !== null);
      const model = view.model;
      view.model = null;
      tryCompare(view, "count", 0);
      view.model = model;
      tryCompare(view, "count", 3);
      tryVerify(() => entry("child", data.listMode) !== null);
      wait(50); // Reassigned delegates need a layout pass before pointer events.

      const child = entry("child", data.listMode);
      mouseDoubleClickSequence(child, child.width / 2, child.height / 2);
      tryCompare(picker, "currentPath", "@FILES@/child");
      tryCompare(grid(), "count", 0);
      tryCompare(select, "enabled", false);
      picker.navigateToPath("@FILES@");
      tryCompare(grid(), "count", 3);
      tryVerify(() => entry("beta.log", data.listMode) !== null);
      const beta = entry("beta.log", data.listMode);
      compare(beta.filePath, "@FILES@/beta.log");
      wait(50); // Let asynchronous view layout place reassigned rows before clicking.
      mouseClick(beta, beta.width / 2, beta.height / 2);
      tryCompare(select, "enabled", true);
      mouseClick(button("widgets.file-picker.cancel"));
      tryCompare(cancelledSpy, "count", 1);
      compare(acceptedSpy.count, 0);
      compare(picker.selectedPaths.length, 0);
      tryCompare(picker, "visible", false);

      picker.openFilePicker();
      tryCompare(picker, "opened", true);
      tryCompare(select, "enabled", false);
      tryVerify(() => entry("alpha.txt", data.listMode) !== null);
      const reassignedAlpha = entry("alpha.txt", data.listMode);
      mouseClick(reassignedAlpha, reassignedAlpha.width / 2, reassignedAlpha.height / 2);
      mouseClick(select);
      tryCompare(acceptedSpy, "count", 1);
      compare(acceptedSpy.signalArguments[0][0][0], "@FILES@/alpha.txt");
    }

    function test_dispose_during_model_update() {
      const component = Qt.createComponent("qs/Widgets/NFilePicker.qml");
      compare(component.status, Component.Ready, component.errorString());
      for (let i = 0; i < 3; i++) {
        const temporaryPicker = component.createObject(picker.parent, {
                                                         initialPath: "@FILES@"
                                                       }) as NFilePicker;
        verify(temporaryPicker !== null);
        temporaryPicker.openFilePicker();
        tryCompare(temporaryPicker, "opened", true);
        temporaryPicker.navigateToPath("@FILES@/child");
        temporaryPicker.navigateToPath("@FILES@");
        temporaryPicker.close();
        temporaryPicker.destroy();
        wait(20);
      }
      component.destroy();
    }

    function test_search_navigation_controls() {
      openPicker();
      const search = findChild(picker.contentItem, item => item.inputIconName === "search");
      verify(search !== null);
      compare(search.visible, false);
      mouseClick(button("filepicker-search"));
      tryCompare(search, "visible", true);
      tryCompare(search, "activeFocus", true);
      keyClick(Qt.Key_A);
      tryCompare(grid(), "count", 1);
      keyClick(Qt.Key_Escape);
      tryCompare(search, "visible", false);
      compare(search.text, "");
      tryCompare(grid(), "count", 3);
      compare(picker.opened, true);
      picker.contentItem.forceActiveFocus();
      keyClick(Qt.Key_F, Qt.ControlModifier);
      tryCompare(search, "visible", true);
      tryCompare(search, "activeFocus", true);
      keyClick(Qt.Key_B);
      tryCompare(grid(), "count", 1);
      mouseClick(button("filepicker-x"));
      tryCompare(search, "visible", false);
      compare(search.text, "");
      tryCompare(grid(), "count", 3);
      const child = entry("child", false);
      mouseDoubleClickSequence(child, child.width / 2, child.height / 2);
      tryCompare(picker, "currentPath", "@FILES@/child");
      tryCompare(grid(), "count", 0);
      mouseClick(button("filepicker-arrow-up"));
      tryCompare(picker, "currentPath", "@FILES@");
      tryCompare(grid(), "count", 3);
      compare(acceptedSpy.count, 0);
    }

    function test_navigation_selection_cancel() {
      openPicker();
      const child = entry("child", false);
      compare(child.filePath, "@FILES@/child");
      verify(child.fileIsDir);
      mouseDoubleClickSequence(child, child.width / 2, child.height / 2);
      tryCompare(picker, "currentPath", "@FILES@/child");
      tryCompare(grid(), "count", 0);
      picker.navigateToPath("@FILES@");
      tryCompare(grid(), "count", 3);
      tryVerify(() => entry("alpha.txt", false) !== null);
      const alpha = entry("alpha.txt", false);
      compare(alpha.fileSize, 5);
      mouseClick(alpha, alpha.width / 2, alpha.height / 2);
      const select = button("widgets.file-picker.select-file");
      tryCompare(select, "enabled", true);
      mouseClick(select);
      tryCompare(acceptedSpy, "count", 1);
      compare(acceptedSpy.signalArguments[0][0][0], "@FILES@/alpha.txt");
      compare(picker.selectedPaths[0], "@FILES@/alpha.txt");
      tryCompare(picker, "visible", false);

      openPicker();
      compare(select.enabled, false);
      const toggle = button("filepicker-list");
      mouseClick(toggle);
      tryVerify(() => entry("beta.log", true) !== null);
      const beta = entry("beta.log", true);
      compare(beta.filePath, "@FILES@/beta.log");
      mouseDoubleClickSequence(beta, beta.width / 2, beta.height / 2);
      tryCompare(acceptedSpy, "count", 2);
      compare(picker.selectedPaths[0], "@FILES@/beta.log");

      picker.openFilePicker();
      tryCompare(picker, "opened", true);
      mouseClick(button("widgets.file-picker.cancel"));
      tryCompare(cancelledSpy, "count", 1);
      compare(acceptedSpy.count, 2);
      tryCompare(picker, "visible", false);
    }
  }
}
