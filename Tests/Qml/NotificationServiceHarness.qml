import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import Quickshell.Services.Notifications
import qs.Commons
import qs.Services.Power
import qs.Services.System

TestCase {
  id: root
  name: "NotificationService"
  when: root.windowShown
  property var notifications: []
  property var expiryEvents: []

  Component {
    id: notificationFactory
    Notification {}
  }

  Connections {
    target: NotificationService
    function onAnimateAndRemove(notificationId) {
      root.expiryEvents = root.expiryEvents.concat([notificationId]);
    }
  }

  function notification(id, summary) {
    const object = notificationFactory.createObject(root, {
                                                      id: id,
                                                      summary: summary
                                                    });
    root.notifications.push(object);
    return object;
  }

  function rows(model) {
    return Array.from({
                        length: model.count
                      }, (_, index) => model.get(index).summary);
  }

  function surface() {
    return Array.from(NotificationService.children).find(child => child.mask !== undefined);
  }

  function assertEmptyInputContract() {
    const panel = root.surface();
    verify(panel !== undefined);
    verify(!panel.visible);
    verify(panel.mask.empty);
    compare(panel.implicitWidth, 1);
    compare(panel.implicitHeight, 1);
    compare(Quickshell.commands.length, 0);
  }

  function init() {
    Settings.isLoaded = false;
    Settings.data.notifications.enabled = true;
    NotificationService.updateNotificationServer();
    NotificationService.dismissAllActive();
    NotificationService.historyList.clear();
    NotificationService.doNotDisturb = false;
    NotificationService.maxVisible = 5;
    NotificationService.maxHistory = 100;
    NotificationService.imageQueue = [];
    PowerProfileService.noctaliaPerformanceMode = false;
    ShellState.isLoaded = false;
    root.expiryEvents = [];
    Quickshell.commands = [];
    root.assertEmptyInputContract();
  }

  function cleanup() {
    NotificationService.dismissAllActive();
    verify(Object.keys(NotificationService.activeNotifications).length === 0);
    verify(Object.keys(NotificationService.quickshellIdToInternalId).length === 0);
    for (const object of root.notifications)
      object.destroy();
    root.notifications = [];
    NotificationService.historyList.clear();
    Settings.isLoaded = false;
    NotificationService.updateNotificationServer();
    wait(1);
    root.assertEmptyInputContract();
  }

  function test_delivery_replacement_duplicate_and_stale_close_order() {
    Settings.isLoaded = true;
    Settings.settingsLoaded();
    const server = NotificationService.notificationServerLoader;
    verify(server !== null);
    const first = root.notification(1, "First");
    const second = root.notification(2, "Second");
    server.notification(first);
    server.notification(second);
    compare(root.rows(NotificationService.activeList), ["Second", "First"]);
    compare(root.rows(NotificationService.historyList), ["Second", "First"]);
    const internalId = NotificationService.activeList.get(1).id;
    const timestamp = NotificationService.activeList.get(1).timestamp.getTime();
    const duplicate = root.notification(3, "First");
    server.notification(duplicate);
    compare(NotificationService.activeList.get(1).id, internalId);
    compare(NotificationService.activeList.get(1).timestamp.getTime(), timestamp);
    compare(NotificationService.historyList.count, 2);
    verify(duplicate.tracked);
    first.closed();
    compare(NotificationService.activeList.count, 2);
    first.summary = "Stale sender";
    wait(1);
    compare(NotificationService.activeList.get(1).summary, "First");
    const replacement = root.notification(3, "Replacement");
    server.notification(replacement);
    compare(root.rows(NotificationService.activeList), ["Second", "Replacement"]);
    compare(NotificationService.activeList.get(1).timestamp.getTime(), timestamp);
    compare(root.rows(NotificationService.historyList), ["Replacement", "Second", "First"]);
    duplicate.closed();
    compare(NotificationService.activeList.count, 2);
    replacement.summary = "Live change";
    compare(NotificationService.activeList.get(1).summary, "Live change");
    replacement.body = "Changed body";
    replacement.appName = "Changed app";
    replacement.urgency = 2;
    replacement.actions = [
          {
            text: "Open",
            identifier: "open"
          }
        ];
    compare(NotificationService.activeList.get(1).body, "Changed body");
    compare(NotificationService.activeList.get(1).appName, "Changed");
    compare(NotificationService.activeList.get(1).urgency, 2);
    compare(JSON.parse(NotificationService.activeList.get(1).actionsJson)[0].identifier, "open");
    root.assertEmptyInputContract();
    replacement.closed();
    compare(root.rows(NotificationService.activeList), ["Second"]);
    verify(NotificationService.quickshellIdToInternalId[1] === undefined);
    verify(NotificationService.quickshellIdToInternalId[3] === undefined);
    replacement.summary = "After disposal";
    wait(1);
    compare(root.rows(NotificationService.activeList), ["Second"]);
  }

  function test_suppression_overflow_dismiss_and_action() {
    NotificationService.doNotDisturb = true;
    const silent = root.notification(10, "Silent history");
    NotificationService.handleNotification(silent);
    compare(NotificationService.activeList.count, 0);
    compare(NotificationService.historyList.get(0).summary, "Silent history");
    verify(!silent.tracked);
    NotificationService.doNotDisturb = false;
    NotificationService.maxVisible = 2;
    NotificationService.maxHistory = 2;
    const first = root.notification(11, "One");
    const second = root.notification(12, "Two");
    const third = root.notification(13, "Three");
    let invoked = 0;
    third.actions = [
          {
            text: "Open",
            identifier: "open",
            invoke: () => invoked++
          }
        ];
    for (const object of [first, second, third])
      NotificationService.handleNotification(object);
    compare(root.rows(NotificationService.activeList), ["Three", "Two"]);
    compare(root.rows(NotificationService.historyList), ["Three", "Two"]);
    compare(first.dismissals, 1);
    expectFailContinue("", "Retained overflow bug: removed ListModel row loses its id before cleanup");
    verify(NotificationService.quickshellIdToInternalId[11] === undefined);
    const thirdId = NotificationService.activeList.get(0).id;
    verify(NotificationService.invokeAction(thirdId, "open"));
    compare(invoked, 1);
    verify(!NotificationService.invokeAction(thirdId, "missing"));
    NotificationService.dismissOldestActive();
    compare(second.dismissals, 1);
    compare(root.rows(NotificationService.activeList), ["Three"]);
    NotificationService.dismissAllActive();
    compare(third.dismissals, 1);
    compare(NotificationService.activeList.count, 0);
    root.assertEmptyInputContract();
  }

  function test_progress_pause_resume_expiry_and_timer_shutdown() {
    const first = root.notification(20, "Expiring");
    first.expireTimeout = 10000;
    NotificationService.handleNotification(first);
    const id = NotificationService.activeList.get(0).id;
    const metadata = NotificationService.activeNotifications[id].metadata;
    metadata.timestamp = Date.now() - 5000;
    tryVerify(() => NotificationService.activeList.get(0).progress < 0.6);
    verify(NotificationService.activeList.get(0).progress > 0.4);
    NotificationService.pauseTimeout(id);
    const pausedProgress = NotificationService.activeList.get(0).progress;
    wait(100);
    compare(NotificationService.activeList.get(0).progress, pausedProgress);
    const oldTimestamp = metadata.timestamp;
    NotificationService.resumeTimeout(id);
    verify(metadata.timestamp >= oldTimestamp + 90);
    metadata.timestamp = Date.now() - 11000;
    tryVerify(() => root.expiryEvents.length > 0);
    compare(root.expiryEvents[0], id);
    compare(NotificationService.activeList.count, 1);
    NotificationService.dismissActiveNotification(id);
    compare(first.dismissals, 1);
    const timer = Array.from(NotificationService.resources).find(child => child.interval === 50);
    verify(!timer.running);
    root.expiryEvents = [];
    wait(100);
    compare(root.expiryEvents.length, 0);
    root.assertEmptyInputContract();
  }

  function test_server_settings_state_history_and_image_queue_lifecycle() {
    Settings.isLoaded = true;
    Settings.settingsLoaded();
    const oldServer = NotificationService.notificationServerLoader;
    verify(oldServer !== null);
    Settings.settingsSaved();
    verify(NotificationService.notificationServerLoader !== oldServer);
    Settings.data.notifications.enabled = false;
    Settings.settingsSaved();
    compare(NotificationService.notificationServerLoader, null);
    ShellState.lastSeenTs = 4567;
    ShellState.isLoaded = true;
    compare(NotificationService.lastSeenTs, 4567);
    NotificationService.updateLastSeenTs();
    compare(ShellState.lastSeenTs, 12000);
    NotificationService.handleNotification(root.notification(30, "Persisted"));
    const historyFile = Array.from(NotificationService.children).find(child => child.path === NotificationService.historyFile);
    const writes = FixtureIo.writes;
    historyFile.loadFailed(2);
    compare(FixtureIo.writes, writes + 1);
    tryVerify(() => FixtureIo.writes >= writes + 2);
    NotificationService.historyList.clear();
    historyFile.loaded();
    compare(root.rows(NotificationService.historyList), ["Persisted"]);
    NotificationService.imageQueue = [
          {
            src: "",
            imageId: "one"
          },
          {
            src: "",
            imageId: "two"
          }
        ];
    const image = root.surface().children[0];
    image.processNextImage();
    compare(NotificationService.imageQueue[0].imageId, "two");
    image.processNextImage();
    compare(NotificationService.imageQueue.length, 0);
    compare(image.source.toString(), "");
    root.assertEmptyInputContract();
  }
}
