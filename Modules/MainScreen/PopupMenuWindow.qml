import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Services.UI

// Generic full-screen popup window for menus and context menus
// This is a top-level PanelWindow (sibling to MainScreen, not nested inside it)
// Provides click-outside-to-close functionality for any popup content
// Loads TrayMenu by default but can show context menus via showContextMenu()
PanelWindow {
  id: root

  property string windowType: "popupmenu"  // Used for namespace and registration
  readonly property string screenName: screen ? screen.name : "unknown"
  property string registrationKey: ""

  // Content item to display (set by the popup that uses this window)
  property QtObject activeMenu: null

  // Expose the trayMenu Loader directly (for backward compatibility)
  readonly property alias trayMenuLoader: trayLoader

  anchors.top: true
  anchors.left: true
  anchors.right: true
  anchors.bottom: true
  visible: false
  color: NColor.transparent

  // Use Top layer (same as MainScreen) for proper event handling
  WlrLayershell.layer: WlrLayer.Top
  WlrLayershell.keyboardFocus: hasDialog ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
  WlrLayershell.namespace: "noctalia-" + windowType + "-" + screenName
  WlrLayershell.exclusionMode: ExclusionMode.Ignore

  // Track if a dialog is currently open (needed for keyboard focus)
  property bool hasDialog: false

  // Register with PanelService so widgets can find this window
  Component.onCompleted: {
    registrationKey = screenName;
    objectName = "popupMenuWindow-" + registrationKey;
    PanelService.registerPopupMenuWindow(screen, root);
  }

  Component.onDestruction: PanelService.unregisterPopupMenuWindow(registrationKey, root)

  // Load TrayMenu as the default content
  Loader {
    id: trayLoader
    source: Quickshell.shellDir + "/Modules/Bar/Extras/TrayMenu.qml"
    onLoaded: root.initializeTrayMenu(trayLoader.item)
  }

  function initializeTrayMenu(menu: var): void {
    if (menu) {
      menu.screen = root.screen;
      // Set the loaded item as default content
      root.activeMenu = menu;
    }
  }

  function open() {
    visible = true;
  }

  // Show a context menu (temporarily replaces TrayMenu as content)
  function showContextMenu(menu) {
    if (menu) {
      activeMenu = menu;
      open();
    }
  }

  function hideContent(menu: var): void {
    if (menu) {
      if (typeof menu.hideMenu === "function") {
        menu.hideMenu();
      } else if (typeof menu.close === "function") {
        menu.close();
      }
    }
  }

  function close() {
    root.visible = false;
    // Call close/hide method on current content
    root.hideContent(root.activeMenu);
    // Restore TrayMenu as default content
    if (trayLoader.item) {
      root.activeMenu = trayLoader.item;
    }
  }

  // Full-screen click catcher - click anywhere outside content closes the window
  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
    onClicked: root.close()
  }

  // Container for dialogs that need a full-screen Item parent (e.g., Qt Popup)
  Item {
    id: dialogContainer
    anchors.fill: parent
  }

  // Expose the dialog container for external use
  readonly property alias dialogParent: dialogContainer
}
