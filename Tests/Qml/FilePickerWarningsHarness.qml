import QtQuick
import QtQuick.Controls
import QtTest
import qs.Widgets

Item {
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
      return findChild(picker.contentItem, item => item.fileName === name && item.height === (listMode ? 40 : grid().cellHeight));
    }

    function grid() {
      return findChild(picker.contentItem, item => item.cellWidth !== undefined);
    }

    function button(text) {
      return findChild(picker.contentItem, item => item.text === text && item.clicked !== undefined);
    }

    function openPicker() {
      picker.openFilePicker();
      tryCompare(picker, "opened", true);
      tryVerify(() => grid().count === 3);
      tryVerify(() => entry("alpha.txt", false) !== null);
      verify(entry(".hidden.txt", false) === null);
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
