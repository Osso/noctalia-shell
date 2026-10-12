import QtQuick
import QtTest
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Modules.Dock

Item {
  width: 640
  height: 480

  Item {
    id: anchor
    x: 40
    y: 300
    width: 48
    height: 48
  }
  Toplevel {
    id: app
    appId: "fixture-app.desktop"
  }
  Toplevel {
    id: otherApp
    appId: "other-app"
  }
  DesktopEntry {
    id: entry
    actions: [
      DesktopAction {
        id: firstAction
        name: "First action"
      },
      DesktopAction {
        id: secondAction
        name: "Second action"
      }
    ]
  }
  DockMenu {
    id: menu
    x: 40
    y: 40
    onRequestClose: {
      tests.closeRequests++;
      hide();
    }
  }
  DockMenu {
    id: otherMenu
    x: 320
    y: 40
  }

  TestCase {
    id: tests
    name: "DockMenuWarnings"
    when: windowShown
    property int closeRequests: 0

    function init() {
      menu.hide();
      otherMenu.hide();
      Settings.data = {
        dock: {
          pinnedApps: []
        }
      };
      ToplevelManager.toplevels = {
        values: [app, otherApp]
      };
      entry.id = "fixture-app.desktop";
      DesktopEntries.entry = entry;
      app.activations = 0;
      app.closes = 0;
      firstAction.executions = 0;
      secondAction.executions = 0;
      closeRequests = 0;
      menu.hoveredItem = -1;
      menu.onAppClosed = null;
      menu.show(anchor, app);
      tryCompare(menu, "visible", true);
      wait(30);
    }

    function cleanup() {
      menu.hide();
      otherMenu.hide();
    }

    function test_selection_boundaries_and_labels() {
      compare(menu.items.map(item => item.text), ["dock.menu.focus", "dock.menu.pin", "dock.menu.close", "First action", "Second action"]);
      compare(menu.getHoveredItem(7), -1);
      compare(menu.getHoveredItem(8), 0);
      compare(menu.getHoveredItem(39), 0);
      compare(menu.getHoveredItem(40), 1);
      compare(menu.getHoveredItem(167), 4);
      compare(menu.getHoveredItem(168), -1);
      verify(menu.implicitWidth >= 160);
      compare(menu.implicitHeight, 176);
    }

    function rectangles(item, found) {
      if (item.height === 32 && item.menuText !== undefined)
        found.push(item);
      for (const child of item.children)
        rectangles(child, found);
      return found;
    }

    function test_hover_and_delegate_owners() {
      otherMenu.show(anchor, otherApp);
      wait(30);
      const rows = rectangles(menu, []);
      const otherRows = rectangles(otherMenu, []);
      compare(rows.length, 5);
      compare(otherRows.length, 5);
      mouseMove(menu, 20, 56);
      tryCompare(menu, "hoveredItem", 1);
      compare(rows[1].color, NColor.mHover);
      compare(rows[0].color, NColor.transparent);
      compare(otherRows[1].color, NColor.transparent);
      compare(rows[1].children[0].children[0].icon, "pin");
      compare(rows[1].children[0].children[1].text, "dock.menu.pin");
      compare(rows[1].children[0].children[1].color, NColor.mOnHover);
      mouseMove(menu, 20, 120);
      tryCompare(menu, "hoveredItem", 3);
      compare(rows[3].color, NColor.mHover);
      compare(rows[1].color, NColor.transparent);
    }

    function test_desktop_actions_keep_independent_selection() {
      mouseClick(menu, 20, 120);
      compare(firstAction.executions, 1);
      compare(secondAction.executions, 0);
      mouseClick(menu, 20, 152);
      compare(firstAction.executions, 1);
      compare(secondAction.executions, 1);
      compare(app.activations, 0);
    }

    function test_focus_and_pin_request_close_and_reopen() {
      mouseClick(menu, 20, 24);
      compare(app.activations, 1);
      compare(closeRequests, 1);
      compare(menu.visible, false);
      compare(menu.items.length, 0);
      menu.show(anchor, app);
      wait(30);
      mouseClick(menu, 20, 56);
      compare(Settings.data.dock.pinnedApps, ["fixture-app.desktop"]);
      compare(closeRequests, 2);
      compare(menu.visible, false);
      menu.show(anchor, app);
      wait(30);
      compare(menu.items[1].text, "dock.menu.unpin");
      mouseClick(menu, 20, 56);
      compare(Settings.data.dock.pinnedApps, []);
      compare(closeRequests, 3);
    }

    function test_close_only_running_owner_and_callback() {
      let callbacks = 0;
      menu.onAppClosed = function () {
        callbacks++;
      };
      mouseClick(menu, 20, 88);
      compare(app.closes, 1);
      compare(otherApp.closes, 0);
      compare(menu.visible, false);
      compare(closeRequests, 1);
      tryVerify(() => callbacks === 1);
      menu.show(anchor, app);
      wait(30);
      ToplevelManager.toplevels = {
        values: [otherApp]
      };
      menu.handleClose();
      compare(app.closes, 1);
      compare(callbacks, 1);
      compare(closeRequests, 2);
    }

    function test_exit_autoclose_after_grace() {
      menu.canAutoClose = true;
      mouseMove(menu, 20, 24);
      mouseMove(menu, -20, -20);
      tryCompare(menu, "hoveredItem", -1);
      tryCompare(menu, "visible", false, 1000);
      compare(menu.items.length, 0);
    }
  }
}
