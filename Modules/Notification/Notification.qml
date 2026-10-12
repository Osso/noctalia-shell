pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.Notifications
import Quickshell.Wayland
import Quickshell.Widgets
import qs.Commons
import qs.Services.System
import qs.Widgets

// Simple notification popup - displays multiple notifications
Variants {
  // If no notification display activated in settings, then show them all
  model: Quickshell.screens.filter(screen => (Settings.data.notifications.monitors.includes(screen.name) || (Settings.data.notifications.monitors.length === 0)))

  delegate: Loader {
    id: root

    required property ShellScreen modelData

    property ListModel notificationModel: NotificationService.activeList

    // Always create window (but with 0x0 dimensions when no notifications)
    active: notificationModel.count > 0 || delayTimer.running

    // Keep loader active briefly after last notification to allow animations to complete
    Timer {
      id: delayTimer
      interval: Style.animationSlow + 200
      repeat: false
    }

    Connections {
      target: notificationModel
      function onCountChanged() {
        if (notificationModel.count === 0 && root.active) {
          delayTimer.restart();
        }
      }
    }

    sourceComponent: PanelWindow {
      id: notifWindow
      screen: modelData

      readonly property string screenName: screen ? screen.name : "unknown"
      readonly property var notificationSettings: Settings.data.notifications || {}

      WlrLayershell.namespace: "noctalia-notifications-" + screenName
      WlrLayershell.layer: notificationSettings.overlayLayer ? WlrLayer.Overlay : WlrLayer.Top
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      WlrLayershell.exclusionMode: ExclusionMode.Ignore

      color: NColor.transparent

      // Parse location setting
      readonly property string location: notificationSettings.location || "top_right"
      readonly property bool isTop: location.startsWith("top")
      readonly property bool isBottom: location.startsWith("bottom")
      readonly property bool isLeft: location.endsWith("_left")
      readonly property bool isRight: location.endsWith("_right")
      readonly property bool isCentered: location === "top" || location === "bottom"

      readonly property string barPos: Settings.data.bar.position
      readonly property bool isFloating: Settings.data.bar.floating

      readonly property int notifWidth: Math.round(400 * Style.uiScaleRatio)

      // Calculate bar offsets for each edge separately
      readonly property int barOffsetTop: {
        if (barPos !== "top")
          return 0;
        const floatMarginV = isFloating ? Settings.data.bar.marginVertical * Style.marginXL : 0;
        return Style.barHeight + floatMarginV;
      }

      readonly property int barOffsetBottom: {
        if (barPos !== "bottom")
          return 0;
        const floatMarginV = isFloating ? Settings.data.bar.marginVertical * Style.marginXL : 0;
        return Style.barHeight + floatMarginV;
      }

      readonly property int barOffsetLeft: {
        if (barPos !== "left")
          return 0;
        const floatMarginH = isFloating ? Settings.data.bar.marginHorizontal * Style.marginXL : 0;
        return floatMarginH;
      }

      readonly property int barOffsetRight: {
        if (barPos !== "right")
          return 0;
        const floatMarginH = isFloating ? Settings.data.bar.marginHorizontal * Style.marginXL : 0;
        return floatMarginH;
      }

      // Anchoring
      anchors.top: isTop
      anchors.bottom: isBottom
      anchors.left: isLeft
      anchors.right: isRight

      // Margins for PanelWindow - only apply bar offset for the specific edge where the bar is
      margins.top: isTop ? barOffsetTop : 0
      margins.bottom: isBottom ? barOffsetBottom : 0
      margins.left: isLeft ? barOffsetLeft : 0
      margins.right: isRight ? barOffsetRight : 0

      implicitWidth: notifWidth
      implicitHeight: notificationStack.implicitHeight + Style.marginL

      mask: Region {
        x: 0
        y: 0
        width: notifWindow.width
        height: notifWindow.height
        intersection: Intersection.Xor
        regions: [notificationInputRegion]

        Region {
          id: notificationInputRegion
          x: notificationStack.x
          y: notificationStack.y
          width: notificationStack.width
          height: notificationStack.height
          intersection: Intersection.Subtract
        }
      }

      property var animateConnection: null

      Component.onCompleted: {
        animateConnection = function (notificationId) {
          var delegate = null;
          if (notificationRepeater) {
            for (var i = 0; i < notificationRepeater.count; i++) {
              var item = notificationRepeater.itemAt(i);
              if (item && item.notificationId === notificationId) {
                delegate = item;
                break;
              }
            }
          }

          if (delegate && delegate.animateOut) {
            delegate.animateOut();
          } else {
            NotificationService.dismissActiveNotification(notificationId);
          }
        };

        NotificationService.animateAndRemove.connect(animateConnection);
      }

      Component.onDestruction: {
        if (animateConnection) {
          NotificationService.animateAndRemove.disconnect(animateConnection);
          animateConnection = null;
        }
      }

      ColumnLayout {
        id: notificationStack

        anchors {
          top: notifWindow.isTop ? parent.top : undefined
          bottom: notifWindow.isBottom ? parent.bottom : undefined
          left: notifWindow.isLeft ? parent.left : undefined
          right: notifWindow.isRight ? parent.right : undefined
          horizontalCenter: notifWindow.isCentered ? parent.horizontalCenter : undefined
        }

        spacing: -Style.marginS
        width: notifWindow.notifWidth

        Behavior on implicitHeight {
          enabled: !Settings.data.general.animationDisabled
          SpringAnimation {
            spring: 2.0
            damping: 0.4
            epsilon: 0.01
            mass: 0.8
          }
        }

        Repeater {
          id: notificationRepeater
          model: root.notificationModel

          delegate: Item {
            id: card

            required property int index
            required property string id
            required property real progress
            required property int urgency
            required property string appName
            required property string summary
            required property string body
            required property string originalImage
            required property string actionsJson
            required property date timestamp

            property string notificationId: id
            property int hoverCount: 0
            property bool isRemoving: false

            readonly property int animationDelay: index * 100
            readonly property int slideDistance: 300

            Layout.preferredWidth: notifWindow.notifWidth
            Layout.preferredHeight: notificationContent.implicitHeight + Style.marginL * 2
            Layout.maximumHeight: Layout.preferredHeight

            // Animation properties
            property real scaleValue: 0.8
            property real opacityValue: 0.0
            property real slideOffset: 0

            scale: scaleValue
            opacity: opacityValue
            transform: Translate {
              y: card.slideOffset
            }

            readonly property real slideInOffset: notifWindow.isTop ? -slideDistance : slideDistance
            readonly property real slideOutOffset: slideInOffset

            // Background with border
            Rectangle {
              id: cardBackground
              anchors.fill: parent
              anchors.margins: Style.marginM
              radius: Style.radiusL
              border.color: Qt.alpha(NColor.mOutline, Settings.data.notifications.backgroundOpacity || 1.0)
              border.width: Style.borderS
              color: Qt.alpha(NColor.mSurface, Settings.data.notifications.backgroundOpacity || 1.0)

              // Progress bar
              Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 2
                color: NColor.transparent

                id: progressTrack
                readonly property real availableWidth: parent.width - (2 * parent.radius)

                Rectangle {
                  id: progressBar
                  height: parent.height
                  x: cardBackground.radius + (progressTrack.availableWidth * (1 - card.progress)) / 2
                  width: progressTrack.availableWidth * card.progress

                  color: {
                    var baseColor = card.urgency === 2 ? NColor.mError : card.urgency === 0 ? NColor.mOnSurface : NColor.mPrimary;
                    return Qt.alpha(baseColor, Settings.data.notifications.backgroundOpacity || 1.0);
                  }

                  antialiasing: true

                  Behavior on width {
                    enabled: !card.isRemoving
                    NumberAnimation {
                      duration: 100
                      easing.type: Easing.Linear
                    }
                  }

                  Behavior on x {
                    enabled: !card.isRemoving
                    NumberAnimation {
                      duration: 100
                      easing.type: Easing.Linear
                    }
                  }
                }
              }
            }

            NDropShadow {
              anchors.fill: cardBackground
              source: cardBackground
              autoPaddingEnabled: true
            }

            // Hover handling
            onHoverCountChanged: {
              if (hoverCount > 0) {
                resumeTimer.stop();
                NotificationService.pauseTimeout(notificationId);
              } else {
                resumeTimer.start();
              }
            }

            Timer {
              id: resumeTimer
              interval: 50
              repeat: false
              onTriggered: {
                if (card.hoverCount === 0) {
                  NotificationService.resumeTimeout(card.notificationId);
                }
              }
            }

            // Right-click to dismiss
            MouseArea {
              anchors.fill: parent
              acceptedButtons: Qt.RightButton
              hoverEnabled: true
              onEntered: parent.hoverCount++
              onExited: parent.hoverCount--
              onClicked: mouse => {
                if (mouse.button === Qt.RightButton) {
                  card.animateOut();
                }
              }
            }

            // Animation setup
            function triggerEntryAnimation() {
              animInDelayTimer.stop();
              removalTimer.stop();
              resumeTimer.stop();
              isRemoving = false;
              hoverCount = 0;
              if (Settings.data.general.animationDisabled) {
                slideOffset = 0;
                scaleValue = 1.0;
                opacityValue = 1.0;
                return;
              }

              slideOffset = slideInOffset;
              scaleValue = 0.8;
              opacityValue = 0.0;
              animInDelayTimer.interval = animationDelay;
              animInDelayTimer.start();
            }

            Component.onCompleted: triggerEntryAnimation()

            onNotificationIdChanged: triggerEntryAnimation()

            Timer {
              id: animInDelayTimer
              interval: 0
              repeat: false
              onTriggered: {
                if (card.isRemoving)
                  return;
                card.slideOffset = 0;
                card.scaleValue = 1.0;
                card.opacityValue = 1.0;
              }
            }

            function animateOut() {
              if (isRemoving)
                return;
              animInDelayTimer.stop();
              resumeTimer.stop();
              isRemoving = true;
              if (!Settings.data.general.animationDisabled) {
                slideOffset = slideOutOffset;
                scaleValue = 0.8;
                opacityValue = 0.0;
              }
            }

            Timer {
              id: removalTimer
              interval: Style.animationSlow
              repeat: false
              onTriggered: {
                NotificationService.dismissActiveNotification(card.notificationId);
              }
            }

            onIsRemovingChanged: {
              if (isRemoving) {
                removalTimer.start();
              }
            }

            Behavior on scale {
              enabled: !Settings.data.general.animationDisabled
              SpringAnimation {
                spring: 3
                damping: 0.4
                epsilon: 0.01
                mass: 0.8
              }
            }

            Behavior on opacity {
              enabled: !Settings.data.general.animationDisabled
              NumberAnimation {
                duration: Style.animationNormal
                easing.type: Easing.OutCubic
              }
            }

            Behavior on slideOffset {
              enabled: !Settings.data.general.animationDisabled
              SpringAnimation {
                spring: 2.5
                damping: 0.3
                epsilon: 0.01
                mass: 0.6
              }
            }

            // Content
            ColumnLayout {
              id: notificationContent
              anchors.fill: parent
              anchors.margins: Style.marginM
              spacing: Style.marginM

              RowLayout {
                Layout.fillWidth: true
                spacing: Style.marginL
                Layout.leftMargin: Style.marginM * 2
                Layout.rightMargin: Style.marginM * 2
                Layout.topMargin: Style.marginM
                Layout.bottomMargin: Style.marginM

                NImageRounded {
                  Layout.preferredWidth: Math.round(40 * Style.uiScaleRatio)
                  Layout.preferredHeight: Math.round(40 * Style.uiScaleRatio)
                  Layout.alignment: Qt.AlignVCenter
                  radius: Math.min(Style.radiusL, Layout.preferredWidth / 2)
                  imagePath: card.originalImage || ""
                  borderColor: NColor.transparent
                  borderWidth: 0
                  fallbackIcon: "bell"
                  fallbackIconSize: 24
                }

                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: Style.marginS

                  // Header with urgency indicator
                  RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.marginS

                    Rectangle {
                      Layout.preferredWidth: 6
                      Layout.preferredHeight: 6
                      Layout.alignment: Qt.AlignVCenter
                      radius: Style.radiusXS
                      color: card.urgency === 2 ? NColor.mError : card.urgency === 0 ? NColor.mOnSurface : NColor.mPrimary
                    }

                    NText {
                      text: card.appName || "Unknown App"
                      pointSize: Style.fontSizeXS
                      font.weight: Style.fontWeightBold
                      color: NColor.mSecondary
                    }

                    NText {
                      textFormat: Text.PlainText
                      text: " " + Time.formatRelativeTime(card.timestamp)
                      pointSize: Style.fontSizeXXS
                      color: NColor.mOnSurfaceVariant
                      Layout.alignment: Qt.AlignBottom
                    }

                    Item {
                      Layout.fillWidth: true
                    }
                  }

                  NText {
                    text: card.summary || I18n.tr("general.no-summary")
                    pointSize: Style.fontSizeM
                    font.weight: Style.fontWeightMedium
                    color: NColor.mOnSurface
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    maximumLineCount: 3
                    elide: Text.ElideRight
                    visible: text.length > 0
                    Layout.fillWidth: true
                    Layout.rightMargin: Style.marginM
                  }

                  NText {
                    text: card.body || ""
                    pointSize: Style.fontSizeM
                    color: NColor.mOnSurface
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere

                    maximumLineCount: 5
                    elide: Text.ElideRight
                    visible: text.length > 0
                    Layout.fillWidth: true
                    Layout.rightMargin: Style.marginXL
                  }

                  // Actions
                  Flow {
                    Layout.fillWidth: true
                    spacing: Style.marginS
                    Layout.topMargin: Style.marginM
                    flow: Flow.LeftToRight

                    property var parsedActions: {
                      try {
                        return card.actionsJson ? JSON.parse(card.actionsJson) : [];
                      } catch (e) {
                        return [];
                      }
                    }
                    visible: parsedActions.length > 0

                    Repeater {
                      model: parent.parsedActions

                      delegate: NButton {
                        id: actionButton
                        required property var modelData
                        property var actionData: actionButton.modelData

                        onEntered: card.hoverCount++
                        onExited: card.hoverCount--

                        text: {
                          var actionText = actionData.text || "Open";
                          if (actionText.includes(",")) {
                            return actionText.split(",")[1] || actionText;
                          }
                          return actionText;
                        }
                        fontSize: Style.fontSizeS
                        backgroundColor: NColor.mPrimary
                        textColor: hovered ? NColor.mOnHover : NColor.mOnPrimary
                        hoverColor: NColor.mHover
                        outlined: false
                        implicitHeight: 24
                        onClicked: {
                          NotificationService.invokeAction(card.notificationId, actionButton.actionData.identifier);
                        }
                      }
                    }
                  }
                }
              }
            }

            // Close button
            NIconButton {
              icon: "close"
              tooltipText: I18n.tr("tooltips.close")
              baseSize: Style.baseWidgetSize * 0.6
              anchors.top: parent.top
              anchors.topMargin: Style.marginXL
              anchors.right: parent.right
              anchors.rightMargin: Style.marginXL

              onClicked: {
                NotificationService.removeFromHistory(card.notificationId);
                card.animateOut();
              }
            }
          }
        }
      }
    }
  }
}
