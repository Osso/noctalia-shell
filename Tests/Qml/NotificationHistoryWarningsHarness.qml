import QtQuick
import QtTest
import qs.Modules.Panels.NotificationHistory
import qs.Services.System

Item {
  id: scene
  width: 600
  height: 600

  Component {
    id: panelComponent
    NotificationHistoryPanel {
      width: 420
      height: 540
    }
  }

  TestCase {
    name: "NotificationHistoryWarnings"
    when: true
    property var panel
    // Counters belong to the inert runtime fixture, not the production service.
    property var fixtureService: NotificationService

    function descendants(parent, predicate) {
      let found = [];
      for (const child of parent.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function list() {
      const repeaters = descendants(panel.contentItem, child => child.itemAt !== undefined);
      compare(repeaters.length, 2);
      return repeaters[1];
    }

    function tabs() {
      return descendants(panel.contentItem, child => child.itemAt !== undefined)[0];
    }

    function button(parent, tooltip) {
      const buttons = descendants(parent, child => child.tooltipText === tooltip);
      compare(buttons.length, 1);
      return buttons[0];
    }

    function texts(parent) {
      return descendants(parent, child => child.textFormat !== undefined).map(child => child.text);
    }

    function append(id, days, urgency) {
      const date = new Date();
      date.setHours(12, 0, 0, 0);
      date.setDate(date.getDate() - days);
      NotificationService.historyList.append({
        id: id,
        timestamp: date,
        urgency: urgency,
        appName: "App " + id,
        summary: "Summary " + id,
        body: "Body " + id,
        cachedImage: "cached-" + id,
        originalImage: "original-" + id
      });
    }

    function init() {
      NotificationService.historyList.clear();
      fixtureService.removed = [];
      fixtureService.seenCount = 0;
      NotificationService.doNotDisturb = false;
      // Service order is newest first; production panel must preserve it.
      append("new", 0, 2);
      append("yesterday", 1, 0);
      append("old", 4, 1);
      panel = panelComponent.createObject(scene);
      verify(panel !== null);
      tryVerify(() => panel.contentItem !== null);
      tryCompare(list(), "count", 3);
    }

    function cleanup() {
      panel.destroy();
      panel = null;
      wait(0);
      // Emit countChanged after disposal, then recreate in the next test.
      NotificationService.historyList.clear();
      append("after-disposal", 0, 1);
      wait(0);
    }

    function test_order_roles_filter_and_counts() {
      compare(panel.currentRange, 1);
      compare(panel.rangeCounts, [3, 1, 1, 1]);
      const ids = ["new", "yesterday", "old"];
      for (let i = 0; i < 3; i++) {
        const row = list().itemAt(i);
        compare(row.notificationId, ids[i]);
        verify(texts(row).indexOf("App " + ids[i]) !== -1);
        verify(texts(row).indexOf("Summary " + ids[i]) !== -1);
        verify(texts(row).indexOf("Body " + ids[i]) !== -1);
        compare(descendants(row, child => child.imagePath !== undefined)[0].imagePath, "cached-" + ids[i]);
      }
      for (let range = 0; range < 4; range++) {
        const tab = tabs().itemAt(range);
        verify(tab.text.endsWith(range === 0 ? "(3)" : "(1)"));
        tab.clicked();
        compare(panel.currentRange, range);
        verify(tab.isActive);
        for (let i = 0; i < 3; i++) {
          const row = list().itemAt(i);
          compare(row.visible, range === 0 || range === i + 1);
          if (range !== 0 && range !== i + 1)
            compare(row.height, 0);
        }
      }
      NotificationService.historyList.setProperty(0, "summary", "Updated summary");
      verify(texts(list().itemAt(0)).indexOf("Updated summary") !== -1);
    }

    function test_dismiss_clear_open_and_teardown() {
      panel.opened();
      compare(fixtureService.seenCount, 1);
      tabs().itemAt(0).clicked();
      button(list().itemAt(1), "tooltips.delete-notification").clicked();
      compare(fixtureService.removed, ["yesterday"]);
      tryCompare(list(), "count", 2);
      compare(list().itemAt(0).notificationId, "new");
      compare(list().itemAt(1).notificationId, "old");
      compare(panel.rangeCounts, [2, 1, 0, 1]);
      button(panel.contentItem, "tooltips.do-not-disturb-disabled").clicked();
      compare(NotificationService.doNotDisturb, true);
      button(panel.contentItem, "tooltips.clear-history").clicked();
      compare(NotificationService.historyList.count, 0);
      tryCompare(list(), "count", 0);
      compare(panel.rangeCounts, [0, 0, 0, 0]);
      compare(panel.closeCount, 1);
      const empty = descendants(panel.contentItem, child => child.text === "notifications.panel.no-notifications");
      compare(empty.length, 1);
      verify(empty[0].visible);
      append("replacement", 0, 1);
      tryCompare(list(), "count", 1);
      compare(list().itemAt(0).notificationId, "replacement");
      compare(panel.rangeCounts, [1, 1, 0, 0]);
      button(panel.contentItem, "tooltips.close").clicked();
      compare(panel.closeCount, 2);
    }
  }
}
