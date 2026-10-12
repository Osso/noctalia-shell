import QtQuick
import QtTest
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Modules.Toast

ShellRoot {
  id: harness

  function require(condition, message) {
    if (!condition) {
      console.error("TOAST_SCREEN_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function loader(view) {
    const loaders = view.children.filter(child => child.pendingToast !== undefined);
    harness.require(loaders.length === 1, "one loader per owner");
    return loaders[0];
  }

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(harness.descendants(child));
    return items;
  }

  function geometry(view, phase) {
    const panel = harness.loader(view).item;
    const toast = panel.toastItem;
    const region = panel.mask;
    console.log("TOAST_GEOMETRY", JSON.stringify({
                                                   owner: view.objectName,
                                                   phase: phase,
                                                   panel: [panel.width, panel.height],
                                                   toast: [toast.x, toast.y, toast.width, toast.height],
                                                   region: region ? [region.x, region.y, region.width, region.height] : null,
                                                   cutout: region && region.regions.length === 1 ? [region.regions[0].x, region.regions[0].y, region.regions[0].width, region.regions[0].height] : null
                                                 }));
    harness.require(panel.width > 0 && panel.height > 0, "nonzero native panel");
    harness.require(panel.width === Math.round(toast.width) && panel.height === Math.round(toast.height), "actual panel follows toast size");
    harness.require(panel.screen === view.screen, "owner screen binding");
    harness.require(region !== null, "native configured mask exists");
    harness.require(region.x === 0 && region.y === 0, "outer mask origin");
    harness.require(region.width === panel.width && region.height === panel.height, "nonzero Region follows actual panel");
    harness.require(region.intersection === Intersection.Xor && region.regions.length === 1, "single inverted cutout policy");
    const cutout = region.regions[0];
    harness.require(cutout.intersection === Intersection.Subtract, "cutout subtract policy");
    harness.require(cutout.x === toast.x && cutout.y === toast.y, "cutout follows position");
    harness.require(cutout.width === toast.width && cutout.height === toast.height, "cutout follows size");
    harness.require(panel.WlrLayershell.layer === WlrLayer.Overlay, "overlay layer");
    harness.require(panel.WlrLayershell.keyboardFocus === WlrKeyboardFocus.None, "no keyboard capture");
    harness.require(panel.WlrLayershell.exclusionMode === ExclusionMode.Ignore, "no exclusive zone");
    const mouse = harness.descendants(toast).find(item => item.cursorShape !== undefined);
    harness.require(mouse !== undefined, "dismiss hit area exists");
    harness.require(mouse.cursorShape === Qt.PointingHandCursor && mouse.acceptedButtons === Qt.LeftButton, "dismiss cursor/button policy");
    harness.require(mouse.x === 8 && mouse.y === 8, "dismiss hit area origin");
    harness.require(mouse.width === toast.width - 16 && mouse.height === toast.height - 16, "dismiss hit area inset");
  }

  function locations(view) {
    const panel = harness.loader(view).item;
    for (const location of ["top_right", "bottom_left", "top", "bottom", "top_left", "bottom_right"]) {
      for (const position of ["top", "bottom", "left", "right"]) {
        Settings.data = Object.assign({}, Settings.data, {
                                        notifications: Object.assign({}, Settings.data.notifications, {
                                                                       location: location
                                                                     }),
                                        bar: Object.assign({}, Settings.data.bar, {
                                                             position: position
                                                           })
                                      });
        clock.wait(50);
        const top = location.startsWith("top");
        const left = location.endsWith("_left");
        const right = location.endsWith("_right");
        harness.require(panel.anchors.top === top && panel.anchors.bottom === !top, "vertical anchors " + location);
        harness.require(panel.anchors.left === left && panel.anchors.right === right, "horizontal anchors " + location);
        harness.require(panel.margins.top === (top && position === "top" ? 64 : 0), "top margin");
        harness.require(panel.margins.bottom === (!top && position === "bottom" ? 64 : 0), "bottom margin");
        harness.require(panel.margins.left === (left && position === "left" ? 48 : 0), "left margin");
        harness.require(panel.margins.right === (right && position === "right" ? 48 : 0), "right margin");
        harness.geometry(view, location + "/" + position);
      }
    }
    Settings.data = Object.assign({}, Settings.data, {
                                    notifications: Object.assign({}, Settings.data.notifications, {
                                                                   location: "top_right"
                                                                 }),
                                    bar: Object.assign({}, Settings.data.bar, {
                                                         position: "top"
                                                       })
                                  });
    clock.wait(100);
  }

  function enqueue(view, message, duration) {
    view.enqueueToast({
                        message: message,
                        description: "Concrete body",
                        icon: "toast-notice",
                        type: "notice",
                        duration: duration
                      });
  }

  function unloaded(view, phase) {
    const windowLoader = harness.loader(view);
    harness.require(!windowLoader.active && windowLoader.item === null, phase + " removes native window");
    harness.require(!view.isShowingToast, phase + " reaches owning view");
    console.log("TOAST_UNLOADED", view.objectName, phase);
  }

  function exercise() {
    harness.unloaded(first, "idle");
    harness.unloaded(second, "idle");
    harness.enqueue(first, "first", 10000);
    harness.enqueue(second, "second", 10000);
    clock.wait(100);
    harness.geometry(first, "show");
    harness.geometry(second, "show");
    const firstPanel = harness.loader(first).item;
    const secondPanel = harness.loader(second).item;
    harness.require(firstPanel !== secondPanel, "two independent native windows");
    harness.require(firstPanel.toastItem.message === "first" && secondPanel.toastItem.message === "second", "independent content");
    harness.locations(first);
    firstPanel.toastItem.x = 13;
    firstPanel.toastItem.y = 17;
    firstPanel.toastItem.width = 460;
    firstPanel.toastItem.height = 160;
    clock.wait(100);
    harness.geometry(first, "update");
    harness.geometry(second, "unchanged");
    first.replaceOnNew = false;
    harness.enqueue(first, "queued", 10000);
    harness.require(first.messageQueue.length === 1, "FIFO waits for hide");
    firstPanel.hideToast();
    clock.wait(40);
    harness.unloaded(first, "hide");
    harness.require(second.isShowingToast && harness.loader(second).item === secondPanel, "hide affects only first owner");
    harness.geometry(second, "other-hide");
    clock.wait(250);
    harness.require(harness.loader(first).item.toastItem.message === "queued", "queue continuation");
    harness.geometry(first, "queue-show");
    secondPanel.hideToast();
    clock.wait(40);
    harness.unloaded(second, "hide");
    harness.require(first.isShowingToast, "second hide preserves first owner");
    first.replaceOnNew = true;
    harness.enqueue(first, "replacement", 250);
    clock.wait(20);
    harness.unloaded(first, "replacement-hide");
    clock.wait(130);
    harness.geometry(first, "replacement-show");
    harness.require(harness.loader(first).item.toastItem.message === "replacement", "latest content");
    clock.wait(250);
    harness.unloaded(first, "timeout");
    harness.unloaded(second, "still-idle");
    clock.wait(250);
    harness.unloaded(first, "empty-queue");
  }

  ToastScreen {
    id: first
    objectName: "first"
    screen: Quickshell.screens[0]
  }

  ToastScreen {
    id: second
    objectName: "second"
    screen: Quickshell.screens[0]
  }

  TestCase {
    id: clock
    when: false
  }

  Timer {
    interval: 100
    running: true
    onTriggered: {
      harness.exercise();
      console.log("TOAST_SCREEN_BEHAVIOR_PASS");
      Qt.quit();
    }
  }
}
