import QtQuick
import QtQuick.Shapes
import qs.Commons
import qs.Widgets

/**
* AllBackgrounds - Unified Shape container for all bar and panel backgrounds
*
* Unified shadow system. This component contains a single Shape
* with multiple ShapePath children (one for bar, one for each panel type).
*
* Benefits:
* - Single GPU-accelerated rendering pass for all backgrounds
* - Unified shadow system (one MultiEffect for everything)
*/
Item {
  id: root

  // Reference Bar
  required property BackgroundRegion bar

  // Reference to MainScreen (for panel access)
  required property var windowRoot

  readonly property color panelBackgroundColor: Qt.alpha(NColor.mSurface, Settings.data.ui.panelBackgroundOpacity)

  anchors.fill: parent

  // Wrapper with layer caching for better shadow performance
  Item {
    anchors.fill: parent

    // Enable layer caching to prevent continuous re-rendering
    // This caches the Shape to a GPU texture, reducing GPU tessellation overhead
    layer.enabled: true

    // The unified Shape container
    Shape {
      id: backgroundsShape
      anchors.fill: parent

      // Use curve renderer for smooth corners (GPU-accelerated)
      preferredRendererType: Shape.CurveRenderer
      asynchronous: true

      enabled: false // Disable mouse input on the Shape itself

      Component.onCompleted: {
        Logger.d("AllBackgrounds", "AllBackgrounds initialized");
      }

      /**
      *  Bar
      */
      BarBackground {
        bar: root.bar
        shapeContainer: backgroundsShape
        windowRoot: root.windowRoot
        backgroundColor: Qt.alpha(NColor.mSurface, Settings.data.bar.backgroundOpacity)
      }

      /**
      *  Panels
      */

      // Audio
      PanelBackground {
        panel: root.windowRoot.audioPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Battery
      PanelBackground {
        panel: root.windowRoot.batteryPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Bluetooth
      PanelBackground {
        panel: root.windowRoot.bluetoothPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Brightness
      PanelBackground {
        panel: root.windowRoot.brightnessPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Clock
      PanelBackground {
        panel: root.windowRoot.clockPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Control Center
      PanelBackground {
        panel: root.windowRoot.controlCenterPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Changelog
      PanelBackground {
        panel: root.windowRoot.changelogPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Launcher
      PanelBackground {
        panel: root.windowRoot.launcherPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Notification History
      PanelBackground {
        panel: root.windowRoot.notificationHistoryPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Session Menu
      PanelBackground {
        panel: root.windowRoot.sessionMenuPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Settings
      PanelBackground {
        panel: root.windowRoot.settingsPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Setup Wizard
      PanelBackground {
        panel: root.windowRoot.setupWizardPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // TrayDrawer
      PanelBackground {
        panel: root.windowRoot.trayDrawerPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Wallpaper
      PanelBackground {
        panel: root.windowRoot.wallpaperPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // WiFi
      PanelBackground {
        panel: root.windowRoot.wifiPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // VPN
      PanelBackground {
        panel: root.windowRoot.vpnPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }

      // Process
      PanelBackground {
        panel: root.windowRoot.processPanelPlaceholder
        shapeContainer: backgroundsShape
        backgroundColor: root.panelBackgroundColor
      }
    }

    // Apply shadow to the cached layer
    NDropShadow {
      anchors.fill: parent
      source: backgroundsShape
    }
  }
}
