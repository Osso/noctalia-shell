import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.System
import qs.Modules.Notification

ShellRoot {
  id: harness
  Notification {
    id: notifications
  }
  TestCase {
    id: clock
    when: false
  }

  function require(condition, message) {
    if (!condition) {
      console.error("NOTIFICATION_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function descendants(item, predicate) {
    let found = predicate(item) ? [item] : [];
    for (const child of item.children || [])
      found = found.concat(harness.descendants(child, predicate));
    return found;
  }

  function append(id, urgency, actions) {
    NotificationService.activeList.append({
      id: id,
      progress: 0.5,
      urgency: urgency,
      appName: "Fixture Mail",
      summary: "Message " + id,
      body: "Concrete body",
      originalImage: "",
      actionsJson: actions,
      timestamp: new Date("2026-10-11T12:34:56Z")
    });
    clock.wait(30);
  }

  function panel() {
    return notifications.instances[0].item;
  }
  function card(id) {
    const found = harness.descendants(harness.panel().contentItem, item => item.notificationId === id);
    harness.require(found.length === 1, "one card " + id);
    return found[0];
  }

  function exerciseContent() {
    harness.require(Quickshell.screens.length === 1, "private headless screen");
    harness.append("critical", 2, '[{"identifier":"open","text":"default,Read message"}]');
    clock.wait(140);
    const card = harness.card("critical");
    const texts = harness.descendants(card, item => item.text !== undefined).map(item => item.text);
    for (const text of ["Fixture Mail", "Message critical", "Concrete body", " 2026-10-11T12:34:56.000Z", "Read message"])
      harness.require(texts.includes(text), "content " + text);
    const bars = harness.descendants(card, item => item.height === 2 && item.color !== undefined && item.width > 0);
    const progress = bars.find(item => item.color === Qt.color("#ff0000"));
    harness.require(progress !== undefined, "critical urgency color");
    const availableWidth = progress.parent.width - 2 * progress.parent.parent.radius;
    harness.require(Math.abs(progress.width - availableWidth * 0.5) < 0.01, "half progress");
    NotificationService.activeList.setProperty(0, "progress", 0.25);
    clock.wait(140);
    harness.require(Math.abs(progress.width - availableWidth * 0.25) < 0.01, "progress update");
    for (const urgency of [0, 1]) {
      NotificationService.activeList.setProperty(0, "urgency", urgency);
      clock.wait(10);
      harness.require(progress.color === Qt.color(urgency === 0 ? "#ffffff" : "#00ff00"), "urgency " + urgency);
    }
    const panel = harness.panel();
    harness.require(panel.screen === Quickshell.screens[0], "screen route");
    // Cage lacks layer-shell: mask geometry/input delivery cannot be asserted here.
    card.hoverCount = 1;
    harness.require(NotificationService.events.includes("pause:critical"), "hover pauses expiry");
    card.hoverCount = 0;
    clock.wait(70);
    harness.require(NotificationService.events.includes("resume:critical"), "hover resumes expiry");
    const button = harness.descendants(card, item => item.text === "Read message")[0];
    button.clicked();
    harness.require(NotificationService.events.includes("action:critical:open"), "action id and notification id");
  }

  function exerciseClose() {
    const card = harness.card("critical");
    const close = harness.descendants(card, item => item.icon === "close")[0];
    close.clicked();
    harness.require(NotificationService.events.includes("history:critical"), "close removes history");
    harness.require(card.isRemoving && NotificationService.activeList.count === 1, "close delayed dismissal");
    clock.wait(120);
    harness.require(NotificationService.activeList.count === 0, "close timer dismisses");
    clock.wait(310);
    harness.require(!notifications.instances[0].active, "empty loader unloads");
    harness.append("expired", 1, "invalid json");
    harness.require(harness.descendants(harness.card("expired"), item => item.actionData !== undefined).length === 0, "invalid actions empty");
    NotificationService.animateAndRemove("expired");
    harness.require(harness.card("expired").isRemoving, "expiry enters removal");
    clock.wait(120);
    harness.require(NotificationService.activeList.count === 0, "expiry dismissal");
    clock.wait(310);
    NotificationService.events = [];
    NotificationService.animateAndRemove("gone");
    clock.wait(20);
    harness.require(NotificationService.events.length === 0, "unload disconnects handler");
    Settings.data = Object.assign({}, Settings.data, {
      general: Object.assign({}, Settings.data.general, {
        animationDisabled: false
      })
    });
    harness.append("fresh", 0, "[]");
    clock.wait(140);
    const fresh = harness.card("fresh");
    harness.require(fresh.slideOffset === 0 && fresh.scaleValue === 1 && fresh.opacityValue === 1, "animated entry targets");
    NotificationService.animateAndRemove("missing");
    harness.require(NotificationService.events.filter(event => event === "dismiss:missing").length === 1, "single reconnected handler");
    clock.mouseClick(fresh, fresh.width / 2, fresh.height / 2, Qt.RightButton);
    harness.require(fresh.isRemoving, "right click starts removal");
    harness.require(!NotificationService.events.includes("history:fresh"), "right click preserves history");
    clock.wait(120);
    harness.require(NotificationService.activeList.count === 0, "fresh lifecycle dismisses");
  }

  Timer {
    interval: 50
    running: true
    onTriggered: {
      harness.exerciseContent();
      harness.exerciseClose();
      console.log("NOTIFICATION_BEHAVIOR_PASS");
      Qt.exit(0);
    }
  }
}
