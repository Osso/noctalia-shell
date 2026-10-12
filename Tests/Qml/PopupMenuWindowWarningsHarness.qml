import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Services.UI
import qs.Modules.MainScreen

ShellRoot {
  id: harness
  property var window

  Component {
    id: factory
    PopupMenuWindow {
      screen: Quickshell.screens[0]
    }
  }

  QtObject {
    id: hideMenuContent
    property int hiddenCount: 0
    property int closedCount: 0
    function hideMenu() {
      harness.check(!harness.window.visible && harness.window.contentItem === hideMenuContent, "hidden before content hides, restored afterward");
      hiddenCount++;
    }
    function close() {
      closedCount++;
    }
  }

  QtObject {
    id: closeContent
    property int closedCount: 0
    function close() {
      harness.check(!harness.window.visible && harness.window.contentItem === closeContent, "hidden before content closes, restored afterward");
      closedCount++;
    }
  }

  QtObject {
    id: inertContent
  }

  function check(condition, message) {
    if (!condition) {
      console.error(message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function exerciseLifecycle() {
    const tray = window.trayMenuLoader.item;
    check(tray !== null && tray.screen === window.screen, "tray Loader screen propagation");
    check(window.contentItem === tray, "default tray content");
    window.initializeTrayMenu(null);
    check(window.contentItem === tray, "null tray initialization leaves content unchanged");
    check(!window.visible, "initially closed");
    check(window.color.a === 0, "transparent window");
    check(window.anchors.top && window.anchors.bottom && window.anchors.left && window.anchors.right, "full-screen anchors");
    check(window.dialogParent.parent !== null, "dialog has visual parent");
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.None, "no dialog focus");
    window.hasDialog = true;
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.OnDemand, "dialog requests focus");
    window.hasDialog = false;
    check(window.WlrLayershell.keyboardFocus === WlrKeyboardFocus.None, "focus released");
    window.open();
    check(window.visible, "open");
    window.close();
    check(!window.visible && tray.hiddenCount === 1, "close hides tray");
    window.showContextMenu(hideMenuContent);
    check(window.visible && window.contentItem === hideMenuContent, "context replaces tray");
    window.showContextMenu(null);
    check(window.visible && window.contentItem === hideMenuContent, "null context unchanged");
    window.close();
    check(!window.visible && hideMenuContent.hiddenCount === 1 && hideMenuContent.closedCount === 0, "hideMenu takes precedence");
    check(window.contentItem === tray, "tray restored");
    window.showContextMenu(closeContent);
    window.close();
    check(closeContent.closedCount === 1 && window.contentItem === tray, "close-only content restored");
    window.showContextMenu(inertContent);
    window.close();
    check(!window.visible && window.contentItem === tray, "content without close method");
    window.contentItem = null;
    window.close();
    check(window.contentItem === tray, "null content restores tray");
    window.open();
    check(window.visible, "reopen");
  }

  Timer {
    id: geometryReady
    interval: 150
    onTriggered: {
      // Cage lacks layer-shell sizing. Drive the real visual parent to test
      // anchor propagation independently of compositor configure events.
      window.dialogParent.parent.width = 640;
      window.dialogParent.parent.height = 480;
      Qt.callLater(() => {
        check(window.dialogParent.width === 640 && window.dialogParent.height === 480, "dialog fills visual parent");
        exerciseOutsideClick();
        const key = window.registrationKey;
        window.destroy();
        Qt.callLater(() => {
          check(PanelService.registeredWindow === null && PanelService.removals === 1 && PanelService.removedKey === key, "destruction unregisters");
          console.log("POPUP_WINDOW_RUNTIME_PASS");
          Qt.quit();
        });
      });
    }
  }

  function exerciseOutsideClick() {
    const tray = window.trayMenuLoader.item;
    for (const child of window.dialogParent.parent.children) {
      if (child instanceof MouseArea) {
        check(child.width === 640 && child.height === 480, "outside catcher fills visual parent");
        check(child.acceptedButtons === (Qt.LeftButton | Qt.RightButton | Qt.MiddleButton), "outside buttons");
        child.clicked(null);
      }
    }
    check(!window.visible && tray.hiddenCount === 2, "outside click closes tray");
  }

  Component.onCompleted: {
    check(Quickshell.screens.length > 0, "offscreen screen");
    window = factory.createObject(harness);
    check(window !== null, "production popup created");
    check(PanelService.registeredWindow === window && PanelService.registeredScreen === window.screen, "registration");
    check(window.registrationKey === window.screen.name, "registration key");
    check(window.objectName === "popupMenuWindow-" + window.screen.name, "object name");
    check(window.WlrLayershell.namespace === "noctalia-popupmenu-" + window.screen.name, "namespace");
    exerciseLifecycle();
    geometryReady.start();
  }
}
