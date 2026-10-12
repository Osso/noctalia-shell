pragma ComponentBehavior: Bound

import QtQuick
import QtTest
import qs.Commons
import qs.Modules.Panels.SessionMenu
import qs.Services.Compositor
import qs.Services.UI

Item {
  id: scene
  width: 600
  height: 600

  Component {
    id: menuComponent
    SessionMenu {
      width: preferredWidth
      height: preferredHeight
    }
  }

  TestCase {
    name: "SessionMenuWarnings"
    when: true
    property var menu

    function descendants(parent, predicate) {
      let found = [];
      for (const child of parent.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function options() {
      const repeaters = descendants(menu.contentItem, child => child.itemAt !== undefined);
      compare(repeaters.length, 1);
      return repeaters[0];
    }

    function headerButton() {
      const buttons = descendants(menu.contentItem, child => child.tooltipText !== undefined);
      compare(buttons.length, 1);
      return buttons[0];
    }

    function init() {
      Settings.data.sessionMenu.showHeader = true;
      Settings.data.sessionMenu.position = "center";
      Settings.data.sessionMenu.countdownDuration = 60000;
      Settings.data.sessionMenu.enableCountdown = true;
      Settings.data.general.lockOnSuspend = false;
      Settings.data.sessionMenu.powerOptions = [
        {
          action: "logout",
          enabled: false
        },
        {
          action: "unknown",
          enabled: true
        },
        {
          action: "lock",
          enabled: true
        },
        {
          action: "shutdown",
          enabled: true,
          countdownEnabled: true
        },
        {
          action: "suspend",
          enabled: true,
          countdownEnabled: false
        }
      ];
      CompositorService.events = [];
      PanelService.lockScreen.active = false;
      menu = menuComponent.createObject(scene);
      verify(menu !== null);
      tryVerify(() => menu.contentItem !== null);
      tryCompare(options(), "count", 3);
      wait(0);
    }

    function cleanup() {
      menu.destroy();
      menu = null;
      wait(0);
      // Notify after disposal; no timer or Connections may act on dead menu.
      Settings.data.sessionMenu.powerOptions = [];
      wait(120);
      compare(CompositorService.events, []);
    }

    function test_options_layout_and_live_settings() {
      compare(menu.powerOptions.map(option => option.action), ["lock", "shutdown", "suspend"]);
      compare(menu.powerOptions.map(option => option.countdownEnabled), [true, true, false]);
      compare(menu.preferredWidth, 400);
      compare(menu.preferredHeight, 228);
      for (let i = 0; i < 3; i++) {
        const row = options().itemAt(i);
        compare(row.action, menu.powerOptions[i].action);
        compare(row.icon, menu.powerOptions[i].icon);
        compare(row.title, "session-menu." + row.action);
        compare(row.isShutdown, i === 1);
        compare(row.isSelected, i === 0);
        verify(row.width > 0);
        verify(row.height > 0);
        if (i > 0)
          verify(row.y >= options().itemAt(i - 1).y + options().itemAt(i - 1).height);
      }
      verify(headerButton().visible);
      Settings.data.sessionMenu.showHeader = false;
      compare(menu.preferredHeight, 181);
      verify(!headerButton().visible);
      Settings.data.sessionMenu.position = "bottom_right";
      verify(menu.panelAnchorBottom && menu.panelAnchorRight);
      verify(!menu.panelAnchorTop && !menu.panelAnchorLeft);
      verify(!menu.panelAnchorHorizontalCenter && !menu.panelAnchorVerticalCenter);
      Settings.data.sessionMenu.powerOptions = [
        {
          action: "hibernate",
          enabled: true
        }
      ];
      tryCompare(options(), "count", 1);
      compare(options().itemAt(0).title, "session-menu.hibernate");
      compare(menu.preferredHeight, 90);
      Settings.data.sessionMenu.powerOptions = [];
      tryCompare(options(), "count", 0);
      compare(menu.preferredHeight, 48);
      menu.onEndPressed();
      menu.onReturnPressed();
      menu.onTabPressed();
      compare(menu.selectedIndex, 0);
      verify(!menu.timerActive);
    }

    function test_navigation_click_pending_cancel_and_lifecycle() {
      menu.selectedIndex = 2;
      menu.opened();
      compare(menu.selectedIndex, 0);
      menu.onUpPressed();
      compare(menu.selectedIndex, 2);
      menu.onDownPressed();
      compare(menu.selectedIndex, 0);
      menu.onTabPressed();
      compare(menu.selectedIndex, 1);
      menu.onBackTabPressed();
      compare(menu.selectedIndex, 0);
      menu.onEndPressed();
      compare(menu.selectedIndex, 2);
      menu.onHomePressed();
      menu.onCtrlKPressed();
      compare(menu.selectedIndex, 2);
      menu.onCtrlJPressed();
      compare(menu.selectedIndex, 0);
      menu.contentItem.selectLast();
      compare(menu.selectedIndex, 2);
      menu.contentItem.selectFirst();
      menu.contentItem.selectNextWrapped();
      compare(menu.selectedIndex, 1);
      menu.contentItem.selectPreviousWrapped();
      compare(menu.selectedIndex, 0);
      options().itemAt(1).clicked();
      compare(menu.selectedIndex, 1);
      verify(options().itemAt(1).isSelected);
      verify(options().itemAt(1).pending);
      compare(menu.pendingAction, "shutdown");
      compare(headerButton().icon, "stop");
      const counters = descendants(options().itemAt(1), child => child.text === "60");
      compare(counters.length, 1);
      verify(counters[0].visible);
      headerButton().clicked();
      verify(!menu.timerActive);
      compare(menu.pendingAction, "");
      compare(menu.timeRemaining, 0);
      compare(menu.closeCount, 0);
      menu.onReturnPressed();
      verify(menu.timerActive);
      menu.onEscapePressed();
      verify(!menu.timerActive);
      compare(menu.closeCount, 0);
      menu.contentItem.activate();
      verify(menu.timerActive);
      menu.closed();
      compare(menu.selectedIndex, 0);
      verify(!menu.timerActive);
      menu.onEscapePressed();
      compare(menu.closeCount, 1);
      headerButton().clicked();
      compare(menu.closeCount, 2);
    }

    function test_inert_confirmation_and_countdown_dispatch() {
      options().itemAt(1).clicked();
      compare(CompositorService.events, []);
      options().itemAt(1).clicked();
      compare(CompositorService.events, ["shutdown"]);
      verify(!menu.timerActive);
      compare(menu.closeCount, 1);
      CompositorService.events = [];
      options().itemAt(2).clicked();
      compare(CompositorService.events, ["suspend"]);
      compare(menu.closeCount, 2);
      CompositorService.events = [];
      Settings.data.sessionMenu.countdownDuration = 100;
      menu.startTimer("reboot");
      tryCompare(menu, "timerActive", false, 1000);
      compare(CompositorService.events, ["reboot"]);
      compare(menu.closeCount, 3);
      CompositorService.events = [];
      Settings.data.sessionMenu.countdownDuration = 100;
      menu.startTimer("logout");
      // cleanup waits past the destroyed timer's deadline; no dispatch may survive.
    }

    function test_inert_action_routing() {
      Settings.data.sessionMenu.enableCountdown = false;
      menu.startTimer("lock");
      verify(PanelService.lockScreen.active);
      compare(CompositorService.events, []);
      menu.startTimer("lock");
      compare(menu.closeCount, 2);
      for (const action of ["suspend", "hibernate", "reboot", "logout", "shutdown"])
        menu.startTimer(action);
      Settings.data.general.lockOnSuspend = true;
      menu.startTimer("suspend");
      compare(CompositorService.events, ["suspend", "hibernate", "reboot", "logout", "shutdown", "lockAndSuspend"]);
      compare(menu.closeCount, 8);
      compare(menu.pendingAction, "");
      compare(menu.timeRemaining, 0);
      verify(!menu.timerActive);
      CompositorService.events = [];
    }
  }
}
