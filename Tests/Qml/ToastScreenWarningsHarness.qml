import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Toast
import qs.Services.UI

ShellRoot {
  id: harness

  function require(condition, message) {
    if (!condition) {
      console.error("TOAST_SCREEN_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function loader() {
    const loaders = toasts.children.filter(child => {
      return child.pendingToast !== undefined;
    });
    harness.require(loaders.length === 1, "one toast loader");
    return loaders[0];
  }

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(harness.descendants(child));
    return items;
  }

  function geometry(panel) {
    const toast = panel.toastItem;
    harness.require(panel.implicitWidth === Math.round(toast.width) && panel.implicitHeight === Math.round(toast.height), "requested window size follows toast");
    // Cage has no layer-shell backend; panel.mask is not the configured Region.
    const mouse = harness.descendants(toast).find(item => {
      return item.cursorShape !== undefined;
    });
    harness.require(mouse !== undefined && mouse.cursorShape === Qt.PointingHandCursor && mouse.acceptedButtons === Qt.LeftButton, "dismiss cursor/button policy");
    harness.require(mouse.width === toast.width - 16 && mouse.height === toast.height - 16, "dismiss hit area inset");
  }

  function locations(panel) {
    for (const location of ["top_right", "bottom_left", "top", "bottom", "top_left", "bottom_right"]) {
      for (const position of ["top", "bottom", "left", "right"]) {
        Settings.data = Object.assign({}, Settings.data, {
                                        "notifications": Object.assign({}, Settings.data.notifications, {
                                                                         "location": location
                                                                       }),
                                        "bar": Object.assign({}, Settings.data.bar, {
                                                               "position": position
                                                             })
                                      });
        clock.wait(5);
        const top = location.startsWith("top");
        const left = location.endsWith("_left");
        const right = location.endsWith("_right");
        harness.require(panel.anchors.top === top && panel.anchors.bottom === !top && panel.anchors.left === left && panel.anchors.right === right, "anchors " + location);
        harness.geometry(panel);
      }
    }
  }

  function exercise() {
    harness.require(!harness.loader().active && harness.loader().item === null, "idle has no window");
    ToastService.notify("first", "Concrete body", "toast-notice", "notice", 10000);
    clock.wait(30);
    const panel = harness.loader().item;
    harness.require(panel !== null && toasts.isShowingToast && toasts.messageQueue.length === 0, "signal activates window and drains queue");
    harness.require(panel.screen === toasts.screen && panel.toastItem.message === "first" && panel.toastItem.description === "Concrete body", "screen and content routing");
    harness.geometry(panel);
    harness.locations(panel);
    panel.toastItem.width = 460;
    panel.toastItem.height = 160;
    clock.wait(10);
    harness.geometry(panel);
    toasts.replaceOnNew = false;
    ToastService.notify("queued", "", "", "warning", 10000);
    harness.require(toasts.messageQueue.length === 1 && panel.toastItem.message === "first", "visible toast preserves FIFO");
    panel.hideToast();
    clock.wait(20);
    harness.require(!harness.loader().active && harness.loader().item === null && !toasts.isShowingToast, "hide unloads layer immediately");
    clock.wait(230);
    harness.require(harness.loader().item.toastItem.message === "queued", "delayed FIFO continuation");
    toasts.replaceOnNew = true;
    ToastService.notify("replacement", "last body", "", "error", 60);
    clock.wait(20);
    harness.require(!harness.loader().active && !toasts.isShowingToast, "replacement unloads before quick switch");
    clock.wait(45);
    harness.require(harness.loader().item.toastItem.message === "replacement" && toasts.messageQueue.length === 0, "replacement loads latest");
    harness.geometry(harness.loader().item);
    clock.wait(120);
    harness.require(!harness.loader().active && harness.loader().item === null && !toasts.isShowingToast, "expiry unloads layer");
    clock.wait(230);
    harness.require(!harness.loader().active, "empty queue stays unloaded");
  }

  ToastScreen {
    id: toasts

    screen: Quickshell.screens[0]
  }

  TestCase {
    id: clock

    when: false
  }

  Timer {
    interval: 50
    running: true
    onTriggered: {
      harness.exercise();
      console.log("TOAST_SCREEN_BEHAVIOR_PASS");
      Qt.exit(0);
    }
  }
}
