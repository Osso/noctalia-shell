import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import Quickshell
import Quickshell.Wayland
import "Backgrounds" as Backgrounds

import qs.Commons

// All panels
import qs.Modules.Bar
import qs.Modules.Bar.Extras
import qs.Modules.Panels.Audio
import qs.Modules.Panels.Battery
import qs.Modules.Panels.Bluetooth
import qs.Modules.Panels.Brightness
import qs.Modules.Panels.Changelog
import qs.Modules.Panels.Clock
import qs.Modules.Panels.ControlCenter
import qs.Modules.Panels.Launcher
import qs.Modules.Panels.NotificationHistory
import qs.Modules.Panels.SessionMenu
import qs.Modules.Panels.Settings
import qs.Modules.Panels.SetupWizard
import qs.Modules.Panels.Process
import qs.Modules.Panels.Tray
import qs.Modules.Panels.Wallpaper
import qs.Modules.Panels.WiFi
import qs.Modules.Panels.VPN
import qs.Services.Compositor
import qs.Services.UI

/**
* MainScreen - Single PanelWindow per screen that manages all panels and the bar
*/
PanelWindow {
  id: root

  // Expose panels as nullable properties. Lazy loaders populate them on first access.
  readonly property Item audioPanel: audioPanelLoader.item
  readonly property Item batteryPanel: batteryPanelLoader.item
  readonly property Item bluetoothPanel: bluetoothPanelLoader.item
  readonly property Item brightnessPanel: brightnessPanelLoader.item
  readonly property Item clockPanel: clockPanelLoader.item
  readonly property Item changelogPanel: changelogPanelLoader.item
  readonly property Item controlCenterPanel: controlCenterPanelLoader.item
  readonly property Item launcherPanel: launcherPanelLoader.item
  readonly property Item notificationHistoryPanel: notificationHistoryPanelLoader.item
  readonly property Item sessionMenuPanel: sessionMenuPanelLoader.item
  readonly property Item settingsPanel: settingsPanelLoader.item
  readonly property Item setupWizardPanel: setupWizardPanelLoader.item
  readonly property Item trayDrawerPanel: trayDrawerPanelLoader.item
  readonly property Item wallpaperPanel: wallpaperPanelLoader.item
  readonly property Item wifiPanel: wifiPanelLoader.item
  readonly property Item vpnPanel: vpnPanelLoader.item
  readonly property Item processPanel: processPanelLoader.item
  readonly property string screenName: screen ? screen.name : "unknown"

  // Expose panel backgrounds for AllBackgrounds without forcing panel instantiation.
  readonly property Item audioPanelPlaceholder: audioPanelLoader.item ? audioPanelLoader.item.panelRegion : audioPanelPlaceholderItem
  readonly property Item batteryPanelPlaceholder: batteryPanelLoader.item ? batteryPanelLoader.item.panelRegion : batteryPanelPlaceholderItem
  readonly property Item bluetoothPanelPlaceholder: bluetoothPanelLoader.item ? bluetoothPanelLoader.item.panelRegion : bluetoothPanelPlaceholderItem
  readonly property Item brightnessPanelPlaceholder: brightnessPanelLoader.item ? brightnessPanelLoader.item.panelRegion : brightnessPanelPlaceholderItem
  readonly property Item clockPanelPlaceholder: clockPanelLoader.item ? clockPanelLoader.item.panelRegion : clockPanelPlaceholderItem
  readonly property Item changelogPanelPlaceholder: changelogPanelLoader.item ? changelogPanelLoader.item.panelRegion : changelogPanelPlaceholderItem
  readonly property Item controlCenterPanelPlaceholder: controlCenterPanelLoader.item ? controlCenterPanelLoader.item.panelRegion : controlCenterPanelPlaceholderItem
  readonly property Item launcherPanelPlaceholder: launcherPanelLoader.item ? launcherPanelLoader.item.panelRegion : launcherPanelPlaceholderItem
  readonly property Item notificationHistoryPanelPlaceholder: notificationHistoryPanelLoader.item ? notificationHistoryPanelLoader.item.panelRegion : notificationHistoryPanelPlaceholderItem
  readonly property Item sessionMenuPanelPlaceholder: sessionMenuPanelLoader.item ? sessionMenuPanelLoader.item.panelRegion : sessionMenuPanelPlaceholderItem
  readonly property Item settingsPanelPlaceholder: settingsPanelLoader.item ? settingsPanelLoader.item.panelRegion : settingsPanelPlaceholderItem
  readonly property Item setupWizardPanelPlaceholder: setupWizardPanelLoader.item ? setupWizardPanelLoader.item.panelRegion : setupWizardPanelPlaceholderItem
  readonly property Item trayDrawerPanelPlaceholder: trayDrawerPanelLoader.item ? trayDrawerPanelLoader.item.panelRegion : trayDrawerPanelPlaceholderItem
  readonly property Item wallpaperPanelPlaceholder: wallpaperPanelLoader.item ? wallpaperPanelLoader.item.panelRegion : wallpaperPanelPlaceholderItem
  readonly property Item wifiPanelPlaceholder: wifiPanelLoader.item ? wifiPanelLoader.item.panelRegion : wifiPanelPlaceholderItem
  readonly property Item vpnPanelPlaceholder: vpnPanelLoader.item ? vpnPanelLoader.item.panelRegion : vpnPanelPlaceholderItem
  readonly property Item processPanelPlaceholder: processPanelLoader.item ? processPanelLoader.item.panelRegion : processPanelPlaceholderItem

  Component.onCompleted: {
    const screenWidth = screen ? screen.width : 0;
    const screenHeight = screen ? screen.height : 0;
    const screenX = screen ? screen.x : 0;
    const screenY = screen ? screen.y : 0;
    Logger.d("MainScreen", "Initialized for screen:", screenName, "- Dimensions:", screenWidth, "x", screenHeight, "- Position:", screenX, ",", screenY);
  }

  function panelObjectName(panelName) {
    return panelName + "-" + root.screenName;
  }

  function registerLazyPanel(panelName, loader) {
    PanelService.registerPanelLoader(panelObjectName(panelName), loader);
  }

  // Wayland
  WlrLayershell.layer: WlrLayer.Top
  WlrLayershell.namespace: "noctalia-background-" + screenName
  WlrLayershell.exclusionMode: ExclusionMode.Ignore // Don't reserve space - BarExclusionZone handles that
  WlrLayershell.keyboardFocus: {
    if (!root.isPanelOpen) {
      return WlrKeyboardFocus.None;
    }
    return PanelService.openedPanel.exclusiveKeyboard ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.OnDemand;
  }

  anchors {
    top: true
    bottom: true
    left: true
    right: true
  }

  // Desktop dimming when panels are open
  property real dimmerOpacity: Settings.data.general.dimmerOpacity !== undefined ? Settings.data.general.dimmerOpacity : 0.8
  property bool isPanelOpen: (PanelService.openedPanel !== null) && (PanelService.openedPanel.screen === screen)
  property bool isPanelClosing: (PanelService.openedPanel !== null) && PanelService.openedPanel.isClosing

  color: {
    if (dimmerOpacity > 0 && isPanelOpen && !isPanelClosing) {
      return Qt.alpha(Color.mShadow, dimmerOpacity);
    }
    return Color.transparent;
  }

  Behavior on color {
    ColorAnimation {
      duration: isPanelClosing ? Style.animationFaster : Style.animationNormal
      easing.type: Easing.OutQuad
    }
  }

  // Check if bar should be visible on this screen
  readonly property bool barShouldShow: {
    // Check global bar visibility
    if (!BarService.isVisible)
      return false;

    // Check screen-specific configuration
    var monitors = Settings.data.bar.monitors || [];
    var currentScreenName = screen ? screen.name : "";

    // If no monitors specified, show on all screens
    // If monitors specified, only show if this screen is in the list
    return monitors.length === 0 || monitors.includes(currentScreenName);
  }

  // Make everything click-through except bar
  mask: Region {
    id: clickableMask

    // Cover entire window (everything is masked/click-through)
    x: 0
    y: 0
    width: root.width
    height: root.height
    intersection: Intersection.Xor

    // Only include regions that are actually needed
    // panelRegions is handled by PanelService, bar is local to this screen
    regions: [barMaskRegion, backgroundMaskRegion]

    // Bar region - subtract bar area from mask (only if bar should be shown on this screen)
    Region {
      id: barMaskRegion

      x: barPlaceholder.x
      y: barPlaceholder.y

      // Set width/height to 0 if bar shouldn't show on this screen (makes region empty)
      width: root.barShouldShow ? barPlaceholder.width : 0
      height: root.barShouldShow ? barPlaceholder.height : 0
      intersection: Intersection.Subtract
    }

    // Background region for click-to-close - reactive sizing
    Region {
      id: backgroundMaskRegion
      x: 0
      y: 0
      width: root.isPanelOpen && !isPanelClosing ? root.width : 0
      height: root.isPanelOpen && !isPanelClosing ? root.height : 0
      intersection: Intersection.Subtract
    }
  }

  // --------------------------------------
  // Container for all UI elements
  Item {
    id: container
    width: root.width
    height: root.height

    // Unified backgrounds container / unified shadow system
    // Renders all bar and panel backgrounds as ShapePaths within a single Shape
    // This allows the shadow effect to apply to all backgrounds in one render pass
    Backgrounds.AllBackgrounds {
      id: unifiedBackgrounds
      anchors.fill: parent
      bar: barPlaceholder.barItem || null
      windowRoot: root
      z: 0 // Behind all content
    }

    // Background MouseArea for closing panels when clicking outside
    // Active whenever a panel is open - the mask ensures it only receives clicks when panel is open
    MouseArea {
      anchors.fill: parent
      enabled: root.isPanelOpen
      acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
      onClicked: mouse => {
                   if (PanelService.openedPanel) {
                     PanelService.openedPanel.close();
                   }
                 }
      z: 0 // Behind panels and bar
    }

    // ---------------------------------------
    // Lazy panel placeholders and loaders
    // ---------------------------------------
    Item {
      id: audioPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: batteryPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: bluetoothPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: brightnessPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: controlCenterPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: changelogPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: clockPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: launcherPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: notificationHistoryPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: sessionMenuPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: settingsPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: setupWizardPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: trayDrawerPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: wallpaperPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: wifiPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: vpnPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Item {
      id: processPanelPlaceholderItem
      visible: false
      width: 0
      height: 0
    }

    Loader {
      id: audioPanelLoader
      active: false
      sourceComponent: AudioPanel {
        objectName: root.panelObjectName("audioPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("audioPanel", audioPanelLoader)
    }

    Loader {
      id: batteryPanelLoader
      active: false
      sourceComponent: BatteryPanel {
        objectName: root.panelObjectName("batteryPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("batteryPanel", batteryPanelLoader)
    }

    Loader {
      id: bluetoothPanelLoader
      active: false
      sourceComponent: BluetoothPanel {
        objectName: root.panelObjectName("bluetoothPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("bluetoothPanel", bluetoothPanelLoader)
    }

    Loader {
      id: brightnessPanelLoader
      active: false
      sourceComponent: BrightnessPanel {
        objectName: root.panelObjectName("brightnessPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("brightnessPanel", brightnessPanelLoader)
    }

    Loader {
      id: controlCenterPanelLoader
      active: false
      sourceComponent: ControlCenterPanel {
        objectName: root.panelObjectName("controlCenterPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("controlCenterPanel", controlCenterPanelLoader)
    }

    Loader {
      id: changelogPanelLoader
      active: false
      sourceComponent: ChangelogPanel {
        objectName: root.panelObjectName("changelogPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("changelogPanel", changelogPanelLoader)
    }

    Loader {
      id: clockPanelLoader
      active: false
      sourceComponent: ClockPanel {
        objectName: root.panelObjectName("clockPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("clockPanel", clockPanelLoader)
    }

    Loader {
      id: launcherPanelLoader
      active: false
      sourceComponent: Launcher {
        objectName: root.panelObjectName("launcherPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("launcherPanel", launcherPanelLoader)
    }

    Loader {
      id: notificationHistoryPanelLoader
      active: false
      sourceComponent: NotificationHistoryPanel {
        objectName: root.panelObjectName("notificationHistoryPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("notificationHistoryPanel", notificationHistoryPanelLoader)
    }

    Loader {
      id: sessionMenuPanelLoader
      active: false
      sourceComponent: SessionMenu {
        objectName: root.panelObjectName("sessionMenuPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("sessionMenuPanel", sessionMenuPanelLoader)
    }

    Loader {
      id: settingsPanelLoader
      active: false
      sourceComponent: SettingsPanel {
        objectName: root.panelObjectName("settingsPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("settingsPanel", settingsPanelLoader)
    }

    Loader {
      id: setupWizardPanelLoader
      active: false
      sourceComponent: SetupWizard {
        objectName: root.panelObjectName("setupWizardPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("setupWizardPanel", setupWizardPanelLoader)
    }

    Loader {
      id: trayDrawerPanelLoader
      active: false
      sourceComponent: TrayDrawerPanel {
        objectName: root.panelObjectName("trayDrawerPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("trayDrawerPanel", trayDrawerPanelLoader)
    }

    Loader {
      id: wallpaperPanelLoader
      active: false
      sourceComponent: WallpaperPanel {
        objectName: root.panelObjectName("wallpaperPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("wallpaperPanel", wallpaperPanelLoader)
    }

    Loader {
      id: wifiPanelLoader
      active: false
      sourceComponent: WiFiPanel {
        objectName: root.panelObjectName("wifiPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("wifiPanel", wifiPanelLoader)
    }

    Loader {
      id: vpnPanelLoader
      active: false
      sourceComponent: VPNPanel {
        objectName: root.panelObjectName("vpnPanel")
        screen: root.screen
        z: 50
      }
      Component.onCompleted: root.registerLazyPanel("vpnPanel", vpnPanelLoader)
    }

    Loader {
      id: processPanelLoader
      active: false
      sourceComponent: ProcessPanel {
        objectName: root.panelObjectName("processPanel")
        screen: root.screen
      }
      Component.onCompleted: root.registerLazyPanel("processPanel", processPanelLoader)
    }

    // ----------------------------------------------
    // Bar background placeholder - just for background positioning (actual bar content is in BarContentWindow)
    Item {
      id: barPlaceholder

      // Expose self as barItem for AllBackgrounds compatibility
      readonly property Item barItem: barPlaceholder

      // Screen reference
      property ShellScreen screen: root.screen
      readonly property real screenWidth: screen ? screen.width : 0
      readonly property real screenHeight: screen ? screen.height : 0

      // Bar background positioning properties
      readonly property string barPosition: Settings.data.bar.position || "top"
      readonly property bool barIsVertical: barPosition === "left" || barPosition === "right"
      readonly property bool barFloating: Settings.data.bar.floating || false
      readonly property real barMarginH: barFloating ? Math.round(Settings.data.bar.marginHorizontal * Style.marginXL) : 0
      readonly property real barMarginV: barFloating ? Math.round(Settings.data.bar.marginVertical * Style.marginXL) : 0
      readonly property real attachmentOverlap: 1 // Attachment overlap to fix hairline gap with fractional scaling

      // Expose bar dimensions directly on this Item for BarBackground
      // Use screen dimensions directly
      x: {
        if (barPosition === "right")
          return screenWidth - Style.barHeight - barMarginH - attachmentOverlap; // Extend left towards panels
        return barMarginH;
      }
      y: {
        if (barPosition === "bottom")
          return screenHeight - Style.barHeight - barMarginV - attachmentOverlap;
        return barMarginV;
      }
      width: {
        if (barIsVertical) {
          return Style.barHeight + attachmentOverlap;
        }
        return screenWidth - barMarginH * 2;
      }
      height: {
        if (barIsVertical) {
          return screenHeight - barMarginV * 2;
        }
        return Style.barHeight + attachmentOverlap;
      }

      // Corner states (same as Bar.qml)
      readonly property int topLeftCornerState: {
        if (barFloating)
          return 0;
        if (barPosition === "top")
          return -1;
        if (barPosition === "left")
          return -1;
        if (Settings.data.bar.outerCorners && (barPosition === "bottom" || barPosition === "right")) {
          return barIsVertical ? 1 : 2;
        }
        return -1;
      }

      readonly property int topRightCornerState: {
        if (barFloating)
          return 0;
        if (barPosition === "top")
          return -1;
        if (barPosition === "right")
          return -1;
        if (Settings.data.bar.outerCorners && (barPosition === "bottom" || barPosition === "left")) {
          return barIsVertical ? 1 : 2;
        }
        return -1;
      }

      readonly property int bottomLeftCornerState: {
        if (barFloating)
          return 0;
        if (barPosition === "bottom")
          return -1;
        if (barPosition === "left")
          return -1;
        if (Settings.data.bar.outerCorners && (barPosition === "top" || barPosition === "right")) {
          return barIsVertical ? 1 : 2;
        }
        return -1;
      }

      readonly property int bottomRightCornerState: {
        if (barFloating)
          return 0;
        if (barPosition === "bottom")
          return -1;
        if (barPosition === "right")
          return -1;
        if (Settings.data.bar.outerCorners && (barPosition === "top" || barPosition === "left")) {
          return barIsVertical ? 1 : 2;
        }
        return -1;
      }
    }

    /**
    *  Screen Corners
    */
    ScreenCorners {}
  }

  // ========================================
  // Centralized Keyboard Shortcuts
  // ========================================
  // These shortcuts delegate to the opened panel's handler functions
  // Panels can implement: onEscapePressed, onTabPressed, onShiftTabPressed,
  // onUpPressed, onDownPressed, onReturnPressed

  Shortcut {
    sequence: "Escape"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onEscapePressed) {
        PanelService.openedPanel.onEscapePressed();
      } else if (PanelService.openedPanel) {
        PanelService.openedPanel.close();
      }
    }
  }

  Shortcut {
    sequence: "Tab"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onTabPressed) {
        PanelService.openedPanel.onTabPressed();
      }
    }
  }

  Shortcut {
    sequence: "Shift+Tab"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onShiftTabPressed) {
        PanelService.openedPanel.onShiftTabPressed();
      }
    }
  }

  Shortcut {
    sequence: "Up"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onUpPressed) {
        PanelService.openedPanel.onUpPressed();
      }
    }
  }

  Shortcut {
    sequence: "Down"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onDownPressed) {
        PanelService.openedPanel.onDownPressed();
      }
    }
  }

  Shortcut {
    sequence: "Return"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onReturnPressed) {
        PanelService.openedPanel.onReturnPressed();
      }
    }
  }

  Shortcut {
    sequence: "Left"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onLeftPressed) {
        PanelService.openedPanel.onLeftPressed();
      }
    }
  }

  Shortcut {
    sequence: "Right"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onRightPressed) {
        PanelService.openedPanel.onRightPressed();
      }
    }
  }

  Shortcut {
    sequence: "Home"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onHomePressed) {
        PanelService.openedPanel.onHomePressed();
      }
    }
  }

  Shortcut {
    sequence: "End"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onEndPressed) {
        PanelService.openedPanel.onEndPressed();
      }
    }
  }

  Shortcut {
    sequence: "PgUp"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onPageUpPressed) {
        PanelService.openedPanel.onPageUpPressed();
      }
    }
  }

  Shortcut {
    sequence: "PgDown"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onPageDownPressed) {
        PanelService.openedPanel.onPageDownPressed();
      }
    }
  }

  Shortcut {
    sequence: "Backtab"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onBackTabPressed) {
        PanelService.openedPanel.onBackTabPressed();
      }
    }
  }

  Shortcut {
    sequence: "Ctrl+J"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onCtrlJPressed) {
        PanelService.openedPanel.onCtrlJPressed();
      }
    }
  }

  Shortcut {
    sequence: "Ctrl+K"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onCtrlKPressed) {
        PanelService.openedPanel.onCtrlKPressed();
      }
    }
  }

  Shortcut {
    sequence: "Ctrl+N"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onCtrlNPressed) {
        PanelService.openedPanel.onCtrlNPressed();
      }
    }
  }

  Shortcut {
    sequence: "Ctrl+P"
    enabled: root.isPanelOpen
    onActivated: {
      if (PanelService.openedPanel && PanelService.openedPanel.onCtrlPPressed) {
        PanelService.openedPanel.onCtrlPPressed();
      }
    }
  }
}
