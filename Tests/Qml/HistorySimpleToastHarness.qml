import QtQuick
import QtTest
import qs.Commons
import qs.Services.System
import qs.Services.UI
import qs.Modules.Bar.Widgets
import qs.Modules.Toast

Item {
  id: scene
  width: 800
  height: 600

  Component {
    id: historyFactory
    NotificationHistory {
      widgetId: "NotificationHistory"
    }
  }

  Component {
    id: toastFactory
    SimpleToast {}
  }

  ListModel {
    id: numericHistory
  }

  ListModel {
    id: datedHistory
  }

  SignalSpy {
    id: hiddenSpy
    signalName: "hidden"
  }

  TestCase {
    id: tests
    name: "HistorySimpleToast"
    when: windowShown
    property var toast

    function init() {
      numericHistory.clear();
      datedHistory.clear();
      NotificationService.historyList = numericHistory;
      NotificationService.lastSeenTs = 100;
      NotificationService.clearCount = 0;
      PanelService.closeCount = 0;
      hiddenSpy.target = null;
      hiddenSpy.clear();
    }

    function makeToast() {
      tests.toast = createTemporaryObject(toastFactory, scene, {
        x: 100,
        y: 100
      });
      verify(tests.toast !== null);
      hiddenSpy.target = tests.toast;
      return tests.toast;
    }

    function test_history_count_and_badge_lifecycle() {
      const widget = createTemporaryObject(historyFactory, scene);
      verify(widget !== null);
      const loader = widget.children.find(child => child.sourceComponent !== undefined);
      verify(loader !== undefined);
      compare(loader.active, false);
      NotificationService.historyList.append({
        timestamp: 50
      });
      NotificationService.historyList.append({
        timestamp: 100
      });
      NotificationService.historyList.append({
        timestamp: 200
      });
      NotificationService.historyList.append({
        timestamp: 300
      });
      compare(widget.computeUnreadCount(), 2);
      // Production model mutation alone is not a binding dependency; advance
      // lastSeenTs through the existing reactive service boundary.
      NotificationService.lastSeenTs = 150;
      tryCompare(loader, "active", true);
      compare(loader.item.count, 2);
      compare(loader.item.width, 8);
      NotificationService.lastSeenTs = 250;
      tryCompare(loader.item, "count", 1);
      NotificationService.lastSeenTs = 300;
      tryCompare(loader, "active", false);
      compare(loader.item, null);
      widget.widgetSettings = {
        showUnreadBadge: true,
        hideWhenZero: false
      };
      tryCompare(loader, "active", true);
      compare(loader.item.count, 0);
      compare(loader.item.visible, true);
      widget.widgetSettings = {
        showUnreadBadge: false,
        hideWhenZero: false
      };
      tryCompare(loader, "active", false);
      widget.widgetSettings = {
        showUnreadBadge: true,
        hideWhenZero: true
      };
      NotificationService.lastSeenTs = 150;
      tryCompare(loader, "active", true);
      compare(loader.item.count, 2);
      compare(loader.item.visible, true);
    }

    function test_history_date_count_and_clear_signal() {
      NotificationService.historyList = datedHistory;
      const widget = createTemporaryObject(historyFactory, scene);
      NotificationService.historyList.append({
        timestamp: new Date(50)
      });
      NotificationService.historyList.append({
        timestamp: new Date(200)
      });
      compare(widget.computeUnreadCount(), 1);
      const menu = widget.children.find(child => child.triggered !== undefined);
      verify(menu !== undefined);
      menu.triggered("clear-history");
      compare(NotificationService.clearCount, 1);
      compare(NotificationService.historyList.count, 0);
      compare(widget.computeUnreadCount(), 0);
      compare(PanelService.closeCount, 1);
    }

    function test_toast_display_types_and_description() {
      const item = makeToast();
      const row = item.children.find(child => child.spacing === Style.marginL);
      verify(row !== undefined);
      const icon = row.children.find(child => child.icon !== undefined);
      verify(icon !== undefined);
      const column = row.children.find(child => child.spacing === Style.marginXXS);
      verify(column !== undefined);
      item.show("Saved", "Three records", "", "warning", 5000);
      compare(item.message, "Saved");
      compare(item.description, "Three records");
      compare(item.visible, true);
      tryCompare(item, "opacity", 1);
      tryCompare(item, "scale", 1);
      compare(icon.icon, "toast-warning");
      compare(icon.color, NColor.mPrimary);
      compare(column.children[0].text, "Saved");
      compare(column.children[1].text, "Three records");
      item.show("Failed", "", "", "error", 5000);
      compare(icon.icon, "toast-error");
      compare(icon.color, NColor.mError);
      compare(column.children[1].visible, false);
      item.show("Done", "", "custom", "notice", 5000);
      compare(icon.icon, "custom");
      compare(icon.color, NColor.mOnSurface);
      item.hideImmediately();
      compare(hiddenSpy.count, 1);
      compare(item.visible, false);
    }

    function test_toast_timeout_and_replacement() {
      const item = makeToast();
      item.show("First", "", "", "notice", 80);
      wait(30);
      item.show("Replacement", "", "", "notice", 160);
      wait(90);
      compare(hiddenSpy.count, 0);
      compare(item.visible, true);
      compare(item.message, "Replacement");
      tryCompare(hiddenSpy, "count", 1, 1000);
      compare(item.visible, false);
      tryCompare(item, "opacity", 0);
      tryCompare(item, "scale", item.initialScale);
      wait(100);
      compare(hiddenSpy.count, 1);
    }

    function test_toast_hit_area_and_click_dismissal() {
      const item = makeToast();
      item.show("Clickable", "Description", "", "notice", 5000);
      tryCompare(item, "scale", 1);
      const hit = item.children.find(child => child.acceptedButtons !== undefined);
      verify(hit !== undefined);
      tryCompare(hit, "width", item.width - Style.marginM * 2);
      compare(hit.height, item.height - Style.marginM * 2);
      compare(hit.x, Style.marginM);
      compare(hit.y, Style.marginM);
      verify(hit.height > 0);
      mouseClick(item, 1, 1, Qt.LeftButton);
      wait(60);
      compare(hiddenSpy.count, 0);
      mouseClick(hit, hit.width / 2, hit.height / 2, Qt.RightButton);
      wait(60);
      compare(hiddenSpy.count, 0);
      mouseClick(hit, hit.width / 2, hit.height / 2, Qt.LeftButton);
      tryCompare(hiddenSpy, "count", 1);
      compare(item.visible, false);
    }

    function test_toast_hide_cancel_and_destroy_running_timers() {
      const item = makeToast();
      item.show("Old", "", "", "notice", 5000);
      item.hide();
      item.show("New", "", "", "notice", 5000);
      wait(100);
      compare(item.visible, true);
      compare(hiddenSpy.count, 0);
      item.hideImmediately();
      compare(hiddenSpy.count, 1);
      wait(100);
      compare(hiddenSpy.count, 1);
      item.show("Destroy", "", "", "notice", 60);
      item.destroy();
      wait(150);
      compare(hiddenSpy.count, 1);
    }
  }
}
