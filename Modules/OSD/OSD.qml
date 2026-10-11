pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Services.Hardware
import qs.Services.Keyboard
import qs.Services.Media
import qs.Widgets
import "../../Helpers/BrightnessParsing.js" as BrightnessParsing

// Unified OSD component that displays volume, input volume, and brightness changes
Variants {
  id: osd

  // Do not change the order or it will break settings.
  enum Type {
    Volume,
    InputVolume,
    Brightness,
    LockKey
  }

  model: Quickshell.screens.filter(screen => (Settings.data.osd.monitors.includes(screen.name) || Settings.data.osd.monitors.length === 0) && Settings.data.osd.enabled)

  delegate: Component {
    Item {
      id: root

      required property ShellScreen modelData
      property alias active: panelLoader.active
      readonly property alias item: panelLoader.item
      signal showRequested
      signal hideRequested

      // OSD State
      property int currentOSDType: -1 // OSD.Type enum value, -1 means none
      property bool startupComplete: false
      property real currentBrightness: 0

      // Lock Key States
      property string lastLockKeyChanged: ""  // "caps", "num", "scroll", or ""

      // Current values (computed properties)
      readonly property real currentVolume: AudioService.volume
      readonly property bool isMuted: AudioService.muted
      readonly property real currentInputVolume: AudioService.inputVolume
      readonly property bool isInputMuted: AudioService.inputMuted
      readonly property real epsilon: 0.005

      // Helper Functions
      function getIcon() {
        switch (currentOSDType) {
        case OSD.Type.Volume:
          if (isMuted)
            return "volume-mute";
          // Show volume-x icon when volume is effectively 0% (within rounding threshold)
          if (currentVolume < root.epsilon)
            return "volume-x";
          return currentVolume <= 0.5 ? "volume-low" : "volume-high";
        case OSD.Type.InputVolume:
          return isInputMuted ? "microphone-off" : "microphone";
        case OSD.Type.Brightness:
          // Show sun-off icon when brightness is effectively 0% (within rounding threshold)
          if (currentBrightness < root.epsilon)
            return "sun-off";
          return currentBrightness <= 0.5 ? "brightness-low" : "brightness-high";
        case OSD.Type.LockKey:
          return "keyboard";
        default:
          return "";
        }
      }

      function getCurrentValue() {
        switch (currentOSDType) {
        case OSD.Type.Volume:
          return isMuted ? 0 : currentVolume;
        case OSD.Type.InputVolume:
          return isInputMuted ? 0 : currentInputVolume;
        case OSD.Type.Brightness:
          return currentBrightness;
        case OSD.Type.LockKey:
          return 1.0; // Always show 100% when showing lock key status
        default:
          return 0;
        }
      }

      function getMaxValue() {
        if (currentOSDType === OSD.Type.Volume || currentOSDType === OSD.Type.InputVolume) {
          return Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
        }
        return 1.0;
      }

      function getDisplayPercentage() {
        if (currentOSDType === OSD.Type.LockKey) {
          // For lock keys, return the pre-determined status text
          return lastLockKeyChanged;
        }

        const value = getCurrentValue();
        const max = getMaxValue();
        if ((currentOSDType === OSD.Type.Volume || currentOSDType === OSD.Type.InputVolume) && Settings.data.audio.volumeOverdrive) {
          const pct = Math.round(value * 100);
          return pct + "%";
        }
        const pct = Math.round(Math.min(max, value) * 100);
        return pct + "%";
      }

      function getProgressColor() {
        const isMutedState = (currentOSDType === OSD.Type.Volume && isMuted) || (currentOSDType === OSD.Type.InputVolume && isInputMuted);
        if (isMutedState) {
          return NColor.mError;
        }
        // When volumeOverdrive is enabled, show error color if volume is above 100%
        if ((currentOSDType === OSD.Type.Volume || currentOSDType === OSD.Type.InputVolume) && Settings.data.audio.volumeOverdrive) {
          const value = getCurrentValue();
          if (value > 1.0) {
            return NColor.mError;
          }
        }
        // For lock keys, use a different color to indicate the lock state
        if (currentOSDType === OSD.Type.LockKey) {
          // Check the specific lock key that was changed
          if (lastLockKeyChanged.startsWith("CAPS")) {
            return LockKeysService.capsLockOn ? NColor.mPrimary : NColor.mOnSurfaceVariant;
          } else if (lastLockKeyChanged.startsWith("NUM")) {
            return LockKeysService.numLockOn ? NColor.mPrimary : NColor.mOnSurfaceVariant;
          } else if (lastLockKeyChanged.startsWith("SCROLL")) {
            return LockKeysService.scrollLockOn ? NColor.mPrimary : NColor.mOnSurfaceVariant;
          }
        }
        return NColor.mPrimary;
      }

      function getIconColor() {
        const isMutedState = (currentOSDType === OSD.Type.Volume && isMuted) || (currentOSDType === OSD.Type.InputVolume && isInputMuted);
        if (isMutedState)
          return NColor.mError;

        if (currentOSDType === OSD.Type.LockKey) {
          // Check the specific lock key that was changed
          if (lastLockKeyChanged.startsWith("CAPS")) {
            return LockKeysService.capsLockOn ? NColor.mPrimary : NColor.mOnSurfaceVariant;
          } else if (lastLockKeyChanged.startsWith("NUM")) {
            return LockKeysService.numLockOn ? NColor.mPrimary : NColor.mOnSurfaceVariant;
          } else if (lastLockKeyChanged.startsWith("SCROLL")) {
            return LockKeysService.scrollLockOn ? NColor.mPrimary : NColor.mOnSurfaceVariant;
          }
        }

        return NColor.mOnSurface;
      }

      // Brightness Handling
      function connectBrightnessMonitors() {
        for (var i = 0; i < BrightnessService.monitors.length; i++) {
          const monitor = BrightnessService.monitors[i];
          monitor.brightnessUpdated.disconnect(onBrightnessChanged);
          monitor.brightnessUpdated.connect(onBrightnessChanged);
        }
      }

      function disconnectBrightnessMonitors() {
        for (var i = 0; i < BrightnessService.monitors.length; i++) {
          const monitor = BrightnessService.monitors[i];
          monitor.brightnessUpdated.disconnect(onBrightnessChanged);
        }
      }

      function onBrightnessChanged(newBrightness) {
        if (newBrightness === null || newBrightness === undefined) {
          return;
        }

        const normalizedBrightness = Number(newBrightness);
        if (!BrightnessParsing.isValidBrightnessRatio(normalizedBrightness)) {
          return;
        }

        root.currentBrightness = normalizedBrightness;
        showOSD(OSD.Type.Brightness);
      }

      // Check if a specific OSD type is enabled
      function isTypeEnabled(type) {
        const enabledTypes = Settings.data.osd.enabledTypes || [];
        // If enabledTypes is empty, all types are enabled (backwards compatibility)
        if (enabledTypes.length === 0)
          return true;
        return enabledTypes.includes(type);
      }

      // OSD Display Control
      function showOSD(type) {
        // Ignore all OSD requests during startup period
        if (!startupComplete)
          return;

        // Check if this OSD type is enabled
        if (!isTypeEnabled(type))
          return;

        if (!modelData)
          return;

        currentOSDType = type;

        if (!root.active) {
          root.active = true;
        }

        if (root.item) {
          root.showRequested();
        } else {
          Qt.callLater(() => {
            if (root.item)
              root.showRequested();
          });
        }
      }

      function hideOSD() {
        if (root.item) {
          root.hideRequested();
        } else if (root.active) {
          root.active = false;
        }
      }

      // Signal Connections

      // AudioService monitoring
      Connections {
        target: AudioService

        function onVolumeChanged() {
          root.showOSD(OSD.Type.Volume);
        }

        function onMutedChanged() {
          if (AudioService.consumeOutputOSDSuppression())
            return;
          root.showOSD(OSD.Type.Volume);
        }

        function onInputVolumeChanged() {
          if (AudioService.hasInput)
            root.showOSD(OSD.Type.InputVolume);
        }

        function onInputMutedChanged() {
          if (!AudioService.hasInput)
            return;
          if (AudioService.consumeInputOSDSuppression())
            return;
          root.showOSD(OSD.Type.InputVolume);
        }

        // Refresh OSD when device changes to ensure correct volume is displayed
        function onSinkChanged() {
          // If volume OSD is currently showing, refresh it to show new device's volume
          if (root.currentOSDType === OSD.Type.Volume) {
            Qt.callLater(() => {
              root.showOSD(OSD.Type.Volume);
            });
          }
        }

        function onSourceChanged() {
          // If input volume OSD is currently showing, refresh it to show new device's volume
          if (root.currentOSDType === OSD.Type.InputVolume) {
            Qt.callLater(() => {
              root.showOSD(OSD.Type.InputVolume);
            });
          }
        }
      }

      // Brightness monitoring
      Connections {
        target: BrightnessService
        function onMonitorsChanged() {
          root.connectBrightnessMonitors();
        }
      }

      // LockKeys monitoring with a cleaner approach
      Connections {
        target: LockKeysService

        function onCapsLockChanged(active) {
          root.lastLockKeyChanged = active ? "CAPS ON" : "CAPS OFF";
          root.showOSD(OSD.Type.LockKey);
        }

        function onNumLockChanged(active) {
          root.lastLockKeyChanged = active ? "NUM ON" : "NUM OFF";
          root.showOSD(OSD.Type.LockKey);
        }

        function onScrollLockChanged(active) {
          root.lastLockKeyChanged = active ? "SCROLL ON" : "SCROLL OFF";
          root.showOSD(OSD.Type.LockKey);
        }
      }

      // Startup timer - connect brightness monitors and enable OSD after 2 seconds
      Timer {
        id: startupTimer
        interval: 2000
        running: true
        onTriggered: {
          root.connectBrightnessMonitors();
          root.startupComplete = true;
        }
      }

      Component.onDestruction: disconnectBrightnessMonitors()

      // Visual Component
      Loader {
        id: panelLoader
        active: false
        sourceComponent: Component {
          PanelWindow {
            id: panel

            readonly property alias owner: root
            readonly property ShellScreen sourceScreen: root.modelData

            Connections {
              target: root
              function onShowRequested() {
                panel.showOSD();
              }
              function onHideRequested() {
                panel.hideOSD();
              }
            }
            screen: panel.sourceScreen

            readonly property string screenName: panel.sourceScreen.name
            readonly property var osdSettings: Settings.data.osd || {}

            // Position configuration
            readonly property string location: osdSettings.location || "top_right"
            readonly property bool isTop: location === "top" || location.startsWith("top")
            readonly property bool isBottom: location === "bottom" || location.startsWith("bottom")
            readonly property bool isLeft: location.includes("_left") || location === "left"
            readonly property bool isRight: location.includes("_right") || location === "right"
            readonly property bool verticalMode: location === "left" || location === "right"

            // Dimensions
            readonly property bool isShortMode: panel.owner.currentOSDType === OSD.Type.LockKey
            readonly property int longHWidth: Math.round(320 * Style.uiScaleRatio)
            readonly property int longHHeight: Math.round(72 * Style.uiScaleRatio)
            readonly property int shortHWidth: Math.round(180 * Style.uiScaleRatio)
            readonly property int longVWidth: Math.round(80 * Style.uiScaleRatio)
            readonly property int longVHeight: Math.round(280 * Style.uiScaleRatio)
            readonly property int shortVHeight: Math.round(180 * Style.uiScaleRatio)

            readonly property int barThickness: {
              const base = Math.max(8, Math.round(8 * Style.uiScaleRatio));
              return base % 2 === 0 ? base : base + 1;
            }

            anchors.top: isTop
            anchors.bottom: isBottom
            anchors.left: isLeft
            anchors.right: isRight

            function calculateMargin(isAnchored, position) {
              if (!isAnchored)
                return 0;

              let base = Style.marginM;
              if (Settings.data.bar.position === position) {
                const isVertical = position === "top" || position === "bottom";
                const floatExtra = Settings.data.bar.floating ? (isVertical ? Settings.data.bar.marginVertical : Settings.data.bar.marginHorizontal) * Style.marginXL : 0;
                return Style.barHeight + base + floatExtra;
              }
              return base;
            }

            margins.top: calculateMargin(anchors.top, "top")
            margins.bottom: calculateMargin(anchors.bottom, "bottom")
            margins.left: calculateMargin(anchors.left, "left")
            margins.right: calculateMargin(anchors.right, "right")

            implicitWidth: verticalMode ? longVWidth : (isShortMode ? shortHWidth : longHWidth)
            implicitHeight: verticalMode ? (isShortMode ? shortVHeight : longVHeight) : longHHeight
            color: NColor.transparent

            WlrLayershell.namespace: "noctalia-osd-" + screenName
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            WlrLayershell.layer: osdSettings.overlayLayer ? WlrLayer.Overlay : WlrLayer.Top
            WlrLayershell.exclusionMode: ExclusionMode.Ignore

            Item {
              id: osdItem
              anchors.fill: parent
              visible: false
              opacity: 0
              scale: 0.85

              Behavior on opacity {
                NumberAnimation {
                  duration: Style.animationNormal
                  easing.type: Easing.InOutQuad
                }
              }

              Behavior on scale {
                NumberAnimation {
                  duration: Style.animationNormal
                  easing.type: Easing.InOutQuad
                }
              }

              Timer {
                id: hideTimer
                interval: Settings.data.osd.autoHideMs
                onTriggered: osdItem.hide()
              }

              Timer {
                id: visibilityTimer
                interval: Style.animationNormal + 50
                onTriggered: {
                  osdItem.visible = false;
                  panel.owner.currentOSDType = -1;
                  panel.owner.lastLockKeyChanged = ""; // Reset the lock key change indicator
                  panel.owner.active = false;
                }
              }

              Rectangle {
                id: background
                anchors.fill: parent
                anchors.margins: Style.marginM * 1.5
                radius: Style.radiusL
                color: Qt.alpha(NColor.mSurface, Settings.data.osd.backgroundOpacity || 1.0)
                border.color: Qt.alpha(NColor.mOutline, Settings.data.osd.backgroundOpacity || 1.0)
                border.width: {
                  const bw = Math.max(2, Style.borderM);
                  return bw % 2 === 0 ? bw : bw + 1;
                }
              }

              NDropShadow {
                anchors.fill: background
                source: background
                autoPaddingEnabled: true
              }

              Loader {
                id: contentLoader
                anchors.fill: background
                anchors.margins: Style.marginM
                active: true
                sourceComponent: panel.verticalMode ? verticalContent : horizontalContent
              }

              Component {
                id: horizontalContent
                RowLayout {
                  id: horizontalLayout
                  readonly property alias owner: root
                  property int barThickness: panel.barThickness
                  anchors.fill: parent
                  anchors.leftMargin: Style.marginL
                  anchors.rightMargin: Style.marginL
                  spacing: Style.marginM
                  clip: true

                  // TextMetrics to measure the maximum possible percentage width
                  TextMetrics {
                    id: percentageMetrics
                    font.family: Settings.data.ui.fontFixed
                    font.weight: Style.fontWeightMedium
                    font.pointSize: Style.fontSizeS * (Settings.data.ui.fontFixedScale * Style.uiScaleRatio)
                    text: "150%" // Maximum possible value with volumeOverdrive
                  }

                  // Common Icon for all types
                  NIcon {
                    icon: horizontalLayout.owner.getIcon()
                    color: horizontalLayout.owner.getIconColor()
                    pointSize: Style.fontSizeXL
                    Layout.alignment: Qt.AlignVCenter

                    Behavior on color {
                      ColorAnimation {
                        duration: Style.animationNormal
                        easing.type: Easing.InOutQuad
                      }
                    }
                  }

                  // Lock Key Status Text (replaces progress bar)
                  NText {
                    visible: horizontalLayout.owner.currentOSDType === OSD.Type.LockKey
                    text: horizontalLayout.owner.getDisplayPercentage()
                    color: horizontalLayout.owner.getProgressColor()
                    pointSize: Style.fontSizeM
                    family: Settings.data.ui.fontFixed
                    font.weight: Style.fontWeightMedium
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignVCenter
                  }

                  // Progress Bar for Volume/Brightness
                  Rectangle {
                    visible: horizontalLayout.owner.currentOSDType !== OSD.Type.LockKey
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    height: horizontalLayout.barThickness
                    radius: Math.round(horizontalLayout.barThickness / 2)
                    color: NColor.mSurfaceVariant

                    Rectangle {
                      anchors.left: parent.left
                      anchors.top: parent.top
                      anchors.bottom: parent.bottom
                      width: parent.width * Math.min(1.0, horizontalLayout.owner.getCurrentValue() / horizontalLayout.owner.getMaxValue())
                      radius: parent.radius
                      color: horizontalLayout.owner.getProgressColor()

                      Behavior on width {
                        NumberAnimation {
                          duration: Style.animationNormal
                          easing.type: Easing.InOutQuad
                        }
                      }
                      Behavior on color {
                        ColorAnimation {
                          duration: Style.animationNormal
                          easing.type: Easing.InOutQuad
                        }
                      }
                    }
                  }

                  // Percentage Text for Volume/Brightness
                  NText {
                    visible: horizontalLayout.owner.currentOSDType !== OSD.Type.LockKey
                    text: horizontalLayout.owner.getDisplayPercentage()
                    color: NColor.mOnSurface
                    pointSize: Style.fontSizeS
                    family: Settings.data.ui.fontFixed
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                    Layout.fillWidth: false
                    Layout.preferredWidth: Math.ceil(percentageMetrics.width) + Math.round(8 * Style.uiScaleRatio)
                    Layout.maximumWidth: Math.ceil(percentageMetrics.width) + Math.round(8 * Style.uiScaleRatio)
                    Layout.minimumWidth: Math.ceil(percentageMetrics.width)
                  }
                }
              }

              Component {
                id: verticalContent
                ColumnLayout {
                  id: verticalLayout
                  readonly property alias owner: root
                  property int barThickness: panel.barThickness
                  anchors.fill: parent
                  anchors.topMargin: Style.marginL
                  anchors.bottomMargin: Style.marginL
                  spacing: verticalLayout.owner.currentOSDType === OSD.Type.LockKey ? Style.marginM : Style.marginS
                  clip: true

                  // Unified Text display for Percentage or Lock Status
                  NText {
                    text: verticalLayout.owner.getDisplayPercentage()
                    color: verticalLayout.owner.currentOSDType === OSD.Type.LockKey ? verticalLayout.owner.getProgressColor() : NColor.mOnSurface
                    pointSize: verticalLayout.owner.currentOSDType === OSD.Type.LockKey ? Style.fontSizeM : Style.fontSizeS
                    family: Settings.data.ui.fontFixed
                    font.weight: verticalLayout.owner.currentOSDType === OSD.Type.LockKey ? Style.fontWeightMedium : Style.fontWeightRegular
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    // Only set preferredHeight for the standard case to maintain layout
                    Layout.preferredHeight: verticalLayout.owner.currentOSDType === OSD.Type.LockKey ? -1 : Math.round(20 * Style.uiScaleRatio)
                  }

                  // Progress Bar for Volume/Brightness
                  Item {
                    visible: verticalLayout.owner.currentOSDType !== OSD.Type.LockKey
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Rectangle {
                      anchors.horizontalCenter: parent.horizontalCenter
                      anchors.top: parent.top
                      anchors.bottom: parent.bottom
                      width: verticalLayout.barThickness
                      radius: Math.round(verticalLayout.barThickness / 2)
                      color: NColor.mSurfaceVariant

                      Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: parent.height * Math.min(1.0, verticalLayout.owner.getCurrentValue() / verticalLayout.owner.getMaxValue())
                        radius: parent.radius
                        color: verticalLayout.owner.getProgressColor()

                        Behavior on height {
                          NumberAnimation {
                            duration: Style.animationNormal
                            easing.type: Easing.InOutQuad
                          }
                        }
                        Behavior on color {
                          ColorAnimation {
                            duration: Style.animationNormal
                            easing.type: Easing.InOutQuad
                          }
                        }
                      }
                    }
                  }

                  // Unified Icon display
                  NIcon {
                    icon: verticalLayout.owner.getIcon()
                    color: verticalLayout.owner.getIconColor()
                    pointSize: verticalLayout.owner.currentOSDType === OSD.Type.LockKey ? Style.fontSizeXL : Style.fontSizeL
                    Layout.alignment: verticalLayout.owner.currentOSDType === OSD.Type.LockKey ? Qt.AlignHCenter : (Qt.AlignHCenter | Qt.AlignBottom)

                    Behavior on color {
                      ColorAnimation {
                        duration: Style.animationNormal
                        easing.type: Easing.InOutQuad
                      }
                    }
                  }
                }
              }

              function show() {
                hideTimer.stop();
                visibilityTimer.stop();
                osdItem.visible = true;

                Qt.callLater(() => {
                  osdItem.opacity = 1;
                  osdItem.scale = 1.0;
                });

                hideTimer.start();
              }

              function hide() {
                hideTimer.stop();
                visibilityTimer.stop();
                osdItem.opacity = 0;
                osdItem.scale = 0.85;
                visibilityTimer.start();
              }

              function hideImmediately() {
                hideTimer.stop();
                visibilityTimer.stop();
                osdItem.opacity = 0;
                osdItem.scale = 0.85;
                osdItem.visible = false;
                panel.owner.currentOSDType = -1;
                panel.owner.active = false;
              }
            }

            function showOSD() {
              osdItem.show();
            }

            function hideOSD() {
              osdItem.hideImmediately();
            }
          }
        }
      }
    }
  }
}
