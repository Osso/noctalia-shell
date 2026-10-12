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

  function exerciseGeometry() {
    const panel = harness.panel();
    const card = harness.card("critical");
    const mouse = harness.descendants(card, item => item.acceptedButtons !== undefined)[0];
    harness.require(mouse.acceptedButtons === Qt.RightButton && mouse.hoverEnabled, "right-click hover policy");
    harness.require(mouse.width === card.width && mouse.height === card.height, "dismiss hit area follows card");
    for (const location of ["top_right", "bottom_left", "top", "bottom", "top_left", "bottom_right"]) {
      Settings.data = Object.assign({}, Settings.data, {
        notifications: Object.assign({}, Settings.data.notifications, {
          location: location
        })
      });
      clock.wait(20);
      harness.require(panel.anchors.top === location.startsWith("top") && panel.anchors.bottom === location.startsWith("bottom"), "vertical anchors " + location);
      harness.require(panel.anchors.left === location.endsWith("_left") && panel.anchors.right === location.endsWith("_right"), "horizontal anchors " + location);
      harness.require(panel.implicitWidth === 400 && card.width === 400, "requested width " + location);
      harness.require(panel.implicitHeight === card.parent.implicitHeight + Style.marginL, "requested height follows stack");
    }
    Settings.data = Object.assign({}, Settings.data, {
      notifications: Object.assign({}, Settings.data.notifications, {
        location: "top_right"
      })
    });
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
    // Cage lacks layer-shell: configured Region/input delivery cannot be observed.
    harness.exerciseGeometry();
    card.hoverCount = 1;
    harness.require(NotificationService.events.includes("pause:critical"), "hover pauses expiry");
    card.hoverCount = 0;
    clock.wait(70);
    harness.require(NotificationService.events.includes("resume:critical"), "hover resumes expiry");
    const button = harness.descendants(card, item => item.text === "Read message")[0];
    button.entered();
    harness.require(card.hoverCount === 1, "action hover belongs to card");
    button.exited();
    harness.require(card.hoverCount === 0, "action exit belongs to card");
    button.clicked();
    harness.require(NotificationService.events.includes("action:critical:open"), "action id and notification id");
    harness.append("second", 0, '[{"identifier":"reply","text":"Reply"}]');
    const second = harness.card("second");
    const reply = harness.descendants(second, item => item.text === "Reply")[0];
    reply.entered();
    harness.require(second.hoverCount === 1 && card.hoverCount === 0, "nested hover stays with second card");
    reply.exited();
    reply.clicked();
    harness.require(NotificationService.events.includes("action:second:reply") && !NotificationService.events.includes("action:critical:reply"), "nested action stays with second card");
    NotificationService.animateAndRemove("second");
    harness.require(second.isRemoving && !card.isRemoving, "removal selects second card");
    clock.wait(120);
    harness.require(NotificationService.activeList.count === 1 && harness.card("critical") === card, "first card survives second dismissal");
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
    clock.wait(1200);
    const fresh = harness.card("fresh");
    harness.require(Math.abs(fresh.slideOffset) < 0.1 && Math.abs(fresh.scale - 1) < 0.01 && fresh.opacity > 0.99, "animated entry settles");
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
