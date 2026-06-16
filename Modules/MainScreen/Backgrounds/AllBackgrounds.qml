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
  required property Item bar

  // Reference to MainScreen (for panel access)
  required property Item windowRoot

  readonly property color panelBackgroundColor: Qt.alpha(Color.mSurface, Settings.data.ui.panelBackgroundOpacity)

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
        backgroundColor: Qt.alpha(Color.mSurface, Settings.data.bar.backgroundOpacity)
      }

      /**
      *  Panels
      */

      // Audio
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.audioPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Battery
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.batteryPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Bluetooth
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.bluetoothPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Brightness
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.brightnessPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Clock
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.clockPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Control Center
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.controlCenterPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Changelog
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.changelogPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Launcher
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.launcherPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Notification History
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.notificationHistoryPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Session Menu
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.sessionMenuPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Settings
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.settingsPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Setup Wizard
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.setupWizardPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // TrayDrawer
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.trayDrawerPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Wallpaper
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.wallpaperPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // WiFi
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.wifiPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // VPN
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.vpnPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }

      // Process
      PanelBackground {
        panel: root.windowRoot ? root.windowRoot.processPanelPlaceholder : null
        shapeContainer: backgroundsShape
        backgroundColor: panelBackgroundColor
      }
    }

    // Apply shadow to the cached layer
    NDropShadow {
      anchors.fill: parent
      source: backgroundsShape
    }
  }
}
