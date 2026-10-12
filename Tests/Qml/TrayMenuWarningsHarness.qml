import QtQuick
import QtTest
import Quickshell
import Quickshell.Services.SystemTray
import qs.Modules.Bar.Extras
import qs.Services.UI

Item {
  id: harness
  width: 800
  height: 600

  Component {
    id: menuFactory
    TrayMenu {}
  }
  Component {
    id: handleFactory
    QsMenuHandle {}
  }
  Component {
    id: trayFactory
    SystemTrayItem {}
  }
  Component {
    id: screenFactory
    ShellScreen {}
  }
  Component {
    id: panelFactory
    QtObject {
      property var screen
      property bool visible: true
      property int closes: 0
      function close() {
        closes++;
        visible = false;
      }
    }
  }

  TestCase {
    id: tests
    name: "TrayMenuWarnings"
    when: windowShown
    property var allocated: []
    property var events: []

    function allocate(factory, properties) {
      const object = factory.createObject(harness, properties || {});
      verify(object !== null, "fixture/production object created");
      allocated.push(object);
      return object;
    }

    function entry(label, enabled, separator) {
      return {
        text: label,
        enabled: enabled,
        isSeparator: separator,
        hasChildren: false,
        icon: "",
        triggered: function () {
          tests.events.push(label);
        }
      };
    }

    function createMenu(labels, x) {
      const handle = allocate(handleFactory, {
                                entries: labels
                              });
      const tray = allocate(trayFactory, {
                              menu: handle,
                              name: "synthetic"
                            });
      const screen = allocate(screenFactory);
      const panel = allocate(panelFactory, {
                               screen: screen
                             });
      PanelService.panels = PanelService.panels.concat([panel]);
      const menu = allocate(menuFactory, {
                              trayItem: tray,
                              screen: screen,
                              x: x || 0
                            });
      return {
        menu: menu,
        handle: handle,
        panel: panel
      };
    }

    function rows(item) {
      let found = [];
      for (const child of item.children) {
        if (child.menuText !== undefined)
          found.push(child);
        else
          found = found.concat(rows(child));
      }
      return found;
    }

    function mouseArea(row) {
      for (const child of row.children) {
        for (const nested of child.children) {
          if (nested instanceof MouseArea)
            return nested;
        }
      }
      fail("entry mouse area absent");
    }

    function clickEntry(row) {
      // Keep successive lifecycle clicks outside Qt's double-click interval.
      wait(500);
      mouseClick(mouseArea(row), 10, 10);
    }

    function open(owner, x, y) {
      owner.menu.showAt(harness, x, y);
      tryCompare(owner.menu, "visible", true);
      compare(owner.menu.anchorItem, harness);
      compare(owner.menu.anchorX, x);
      compare(owner.menu.anchorY, y);
      tryVerify(() => owner.menu.anchor.updates > 0);
      wait(0);
    }

    function cleanup() {
      for (let i = allocated.length - 1; i >= 0; i--)
        allocated[i].destroy();
      allocated = [];
      events = [];
      PanelService.panels = [];
      wait(0);
    }

    function test_order_reorder_clear() {
      const alpha = entry("Alpha\nAction", true, false);
      const separator = entry("", false, true);
      const zeta = entry("Zeta", true, false);
      const owner = createMenu([zeta, separator, alpha]);
      open(owner, 12, 34);
      let entries = rows(owner.menu);
      compare(entries.length, 3);
      compare(entries.map(row => row.menuText), ["Zeta", "...", "Alpha Action"]);
      verify(entries[0].y < entries[1].y && entries[1].y < entries[2].y, "rendered order follows handle order");
      verify(entries[1].isSeparator);
      owner.handle.entries = [alpha, zeta];
      tryVerify(() => rows(owner.menu).length === 2);
      compare(rows(owner.menu).map(row => row.menuText), ["Alpha Action", "Zeta"]);
      owner.handle.entries = [];
      tryVerify(() => rows(owner.menu).length === 0);
    }

    function test_activation_disabled_separator() {
      const owner = createMenu([entry("Disabled", false, false), entry("", false, true), entry("Run", true, false)]);
      open(owner, 20, 30);
      const entries = rows(owner.menu);
      verify(!mouseArea(entries[0]).enabled);
      verify(!mouseArea(entries[1]).enabled);
      mouseClick(mouseArea(entries[0]), 10, 10);
      compare(events, []);
      compare(owner.menu.visible, true);
      clickEntry(entries[2]);
      compare(events, ["Run"]);
      compare(owner.menu.visible, false);
      compare(owner.panel.closes, 1);
    }

    function test_reopen_and_recreate() {
      const owner = createMenu([entry("First", true, false)]);
      open(owner, 1, 2);
      clickEntry(rows(owner.menu)[0]);
      compare(events, ["First"]);
      owner.handle.entries = [entry("Second", true, false)];
      open(owner, 7, 9);
      compare(rows(owner.menu)[0].menuText, "Second");
      clickEntry(rows(owner.menu)[0]);
      compare(events, ["First", "Second"]);
      // Recreate delegates and popup after destroying the first creation context.
      owner.menu.destroy();
      allocated.splice(allocated.indexOf(owner.menu), 1);
      wait(0);
      const recreated = createMenu([entry("Recreated", true, false)]);
      open(recreated, 11, 13);
      clickEntry(rows(recreated.menu)[0]);
      compare(events, ["First", "Second", "Recreated"]);
      compare(recreated.menu.visible, false);
    }

    function test_multiple_owners() {
      const first = createMenu([entry("Owner A", true, false)], 0);
      const second = createMenu([entry("Owner B", true, false)], 300);
      open(first, 1, 2);
      open(second, 3, 4);
      clickEntry(rows(first.menu)[0]);
      compare(events, ["Owner A"]);
      compare(first.menu.visible, false);
      compare(second.menu.visible, true);
      compare(first.panel.closes, 1);
      compare(second.panel.closes, 0);
      second.handle.entries = [entry("Owner B replaced", true, false)];
      wait(0);
      clickEntry(rows(second.menu)[0]);
      compare(events, ["Owner A", "Owner B replaced"]);
      compare(second.menu.visible, false);
      compare(second.panel.closes, 1);
    }
  }
}
