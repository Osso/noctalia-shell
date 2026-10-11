// Panel content and delegates capture this menu's owner IDs.
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Widgets
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.Compositor
import qs.Services.UI
import qs.Widgets

SmartPanel {
  id: root

  preferredWidth: Math.round(400 * Style.uiScaleRatio)
  preferredHeight: {
    var headerHeight = Settings.data.sessionMenu.showHeader ? Style.baseWidgetSize * 0.6 : 0;

    var dividerHeight = Settings.data.sessionMenu.showHeader ? Style.marginS : 0;
    var buttonHeight = Style.baseWidgetSize * 1.3 * Style.uiScaleRatio;
    var buttonSpacing = Style.marginS;
    var enabledCount = powerOptions.length;

    var headerSpacing = Settings.data.sessionMenu.showHeader ? (Style.marginL * 2) : 0;
    var baseHeight = (Style.marginL * 4) + headerHeight + dividerHeight + headerSpacing;
    var buttonsHeight = enabledCount > 0 ? (buttonHeight * enabledCount) + (buttonSpacing * (enabledCount - 1)) : 0;

    return Math.round(baseHeight + buttonsHeight);
  }

  // Positioning
  readonly property string panelPosition: Settings.data.sessionMenu.position

  panelAnchorHorizontalCenter: panelPosition === "center" || panelPosition.endsWith("_center")
  panelAnchorVerticalCenter: panelPosition === "center"
  panelAnchorLeft: panelPosition !== "center" && panelPosition.endsWith("_left")
  panelAnchorRight: panelPosition !== "center" && panelPosition.endsWith("_right")
  panelAnchorBottom: panelPosition.startsWith("bottom_")
  panelAnchorTop: panelPosition.startsWith("top_")

  // SessionMenu handle it's own closing logic
  property bool closeWithEscape: false

  // Timer properties
  readonly property int timerDuration: Settings.data.sessionMenu.countdownDuration
  property string pendingAction: ""
  property bool timerActive: false
  property int timeRemaining: 0

  // Navigation properties
  property int selectedIndex: 0

  // Action metadata mapping
  readonly property var actionMetadata: {
    "lock": {
      "icon": "lock",
      "title": I18n.tr("session-menu.lock"),
      "isShutdown": false
    },
    "suspend": {
      "icon": "suspend",
      "title": I18n.tr("session-menu.suspend"),
      "isShutdown": false
    },
    "hibernate": {
      "icon": "hibernate",
      "title": I18n.tr("session-menu.hibernate"),
      "isShutdown": false
    },
    "reboot": {
      "icon": "reboot",
      "title": I18n.tr("session-menu.reboot"),
      "isShutdown": false
    },
    "logout": {
      "icon": "logout",
      "title": I18n.tr("session-menu.logout"),
      "isShutdown": false
    },
    "shutdown": {
      "icon": "shutdown",
      "title": I18n.tr("session-menu.shutdown"),
      "isShutdown": true
    }
  }

  // Build powerOptions from settings, filtering enabled ones and adding metadata
  property var powerOptions: {
    var options = [];
    var settingsOptions = Settings.data.sessionMenu.powerOptions || [];

    for (var i = 0; i < settingsOptions.length; i++) {
      var settingOption = settingsOptions[i];
      if (settingOption.enabled && actionMetadata[settingOption.action]) {
        var metadata = actionMetadata[settingOption.action];
        options.push({
                       "action": settingOption.action,
                       "icon": metadata.icon,
                       "title": metadata.title,
                       "isShutdown": metadata.isShutdown,
                       "countdownEnabled": settingOption.countdownEnabled !== undefined ? settingOption.countdownEnabled : true
                     });
      }
    }

    return options;
  }

  // Update powerOptions when settings change
  Connections {
    target: Settings.data.sessionMenu
    function onPowerOptionsChanged() {
      var options = [];
      var settingsOptions = Settings.data.sessionMenu.powerOptions || [];

      for (var i = 0; i < settingsOptions.length; i++) {
        var settingOption = settingsOptions[i];
        if (settingOption.enabled && root.actionMetadata[settingOption.action]) {
          var metadata = root.actionMetadata[settingOption.action];
          options.push({
                         "action": settingOption.action,
                         "icon": metadata.icon,
                         "title": metadata.title,
                         "isShutdown": metadata.isShutdown,
                         "countdownEnabled": settingOption.countdownEnabled !== undefined ? settingOption.countdownEnabled : true
                       });
        }
      }

      root.powerOptions = options;
    }
  }

  // Lifecycle handlers
  onOpened: {
    selectedIndex = 0;
  }

  onClosed: {
    cancelTimer();
    selectedIndex = 0;
  }

  // Timer management
  function startTimer(action) {
    // Check if global countdown is disabled
    if (!Settings.data.sessionMenu.enableCountdown) {
      executeAction(action);
      return;
    }

    // Check per-item countdown setting
    var option = null;
    for (var i = 0; i < powerOptions.length; i++) {
      if (powerOptions[i].action === action) {
        option = powerOptions[i];
        break;
      }
    }

    // If this specific action has countdown disabled, execute immediately
    if (option && option.countdownEnabled === false) {
      executeAction(action);
      return;
    }

    if (timerActive && pendingAction === action) {
      // Second click - execute immediately
      executeAction(action);
      return;
    }

    pendingAction = action;
    timeRemaining = timerDuration;
    timerActive = true;
    countdownTimer.start();
  }

  function cancelTimer() {
    timerActive = false;
    pendingAction = "";
    timeRemaining = 0;
    countdownTimer.stop();
  }

  function executeAction(action) {
    // Stop timer but don't reset other properties yet
    countdownTimer.stop();

    switch (action) {
    case "lock":
      // Access lockScreen via PanelService
      if (PanelService.lockScreen && !PanelService.lockScreen.active) {
        PanelService.lockScreen.active = true;
      }
      break;
    case "suspend":
      // Check if we should lock before suspending
      if (Settings.data.general.lockOnSuspend) {
        CompositorService.lockAndSuspend();
      } else {
        CompositorService.suspend();
      }
      break;
    case "hibernate":
      CompositorService.hibernate();
      break;
    case "reboot":
      CompositorService.reboot();
      break;
    case "logout":
      CompositorService.logout();
      break;
    case "shutdown":
      CompositorService.shutdown();
      break;
    }

    // Reset timer state and close panel
    cancelTimer();
    root.close();
  }

  // Navigation functions
  function selectNextWrapped() {
    if (powerOptions.length > 0) {
      selectedIndex = (selectedIndex + 1) % powerOptions.length;
    }
  }

  function selectPreviousWrapped() {
    if (powerOptions.length > 0) {
      selectedIndex = (((selectedIndex - 1) % powerOptions.length) + powerOptions.length) % powerOptions.length;
    }
  }

  function selectFirst() {
    selectedIndex = 0;
  }

  function selectLast() {
    if (powerOptions.length > 0) {
      selectedIndex = powerOptions.length - 1;
    } else {
      selectedIndex = 0;
    }
  }

  function activate() {
    if (powerOptions.length > 0 && powerOptions[selectedIndex]) {
      const option = powerOptions[selectedIndex];
      startTimer(option.action);
    }
  }

  // Override keyboard handlers from SmartPanel
  function onEscapePressed() {
    if (timerActive) {
      cancelTimer();
    } else {
      root.close();
    }
  }

  function onTabPressed() {
    selectNextWrapped();
  }

  function onBackTabPressed() {
    selectPreviousWrapped();
  }

  function onUpPressed() {
    selectPreviousWrapped();
  }

  function onDownPressed() {
    selectNextWrapped();
  }

  function onReturnPressed() {
    activate();
  }

  function onHomePressed() {
    selectFirst();
  }

  function onEndPressed() {
    selectLast();
  }

  function onCtrlJPressed() {
    selectNextWrapped();
  }

  function onCtrlKPressed() {
    selectPreviousWrapped();
  }

  function tickCountdownTimer() {
    timeRemaining -= countdownTimer.interval;
    if (timeRemaining <= 0) {
      executeAction(pendingAction);
    }
  }

  // Countdown timer
  Timer {
    id: countdownTimer
    interval: 100
    repeat: true
    onTriggered: {
      root.tickCountdownTimer();
    }
  }

  panelContent: Rectangle {
    id: ui
    color: NColor.transparent

    // Navigation functions
    function selectFirst() {
      root.selectFirst();
    }

    function selectLast() {
      root.selectLast();
    }

    function selectNextWrapped() {
      root.selectNextWrapped();
    }

    function selectPreviousWrapped() {
      root.selectPreviousWrapped();
    }

    function activate() {
      root.activate();
    }

    NBox {
      anchors.fill: parent
      anchors.margins: Style.marginL

      ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.marginL
        spacing: Style.marginL

        // Header with title and close button
        RowLayout {
          visible: Settings.data.sessionMenu.showHeader
          Layout.fillWidth: true
          Layout.preferredHeight: Style.baseWidgetSize * 0.6

          NText {
            text: root.timerActive ? I18n.tr("session-menu.action-in-seconds", {
                                               "action": I18n.tr("session-menu." + root.pendingAction),
                                               "seconds": Math.ceil(root.timeRemaining / 1000)
                                             }) : I18n.tr("session-menu.title")
            font.weight: Style.fontWeightBold
            pointSize: Style.fontSizeL
            color: root.timerActive ? NColor.mPrimary : NColor.mOnSurface
            Layout.alignment: Qt.AlignVCenter
            verticalAlignment: Text.AlignVCenter
          }

          Item {
            Layout.fillWidth: true
          }

          NIconButton {
            icon: root.timerActive ? "stop" : "close"
            tooltipText: root.timerActive ? I18n.tr("tooltips.cancel-timer") : I18n.tr("tooltips.close")
            Layout.alignment: Qt.AlignVCenter
            baseSize: Style.baseWidgetSize * 0.7
            colorBg: root.timerActive ? Qt.alpha(NColor.mError, 0.08) : NColor.transparent
            colorFg: root.timerActive ? NColor.mError : NColor.mOnSurface
            onClicked: {
              if (root.timerActive) {
                root.cancelTimer();
              } else {
                root.cancelTimer();
                root.close();
              }
            }
          }
        }

        NDivider {
          visible: Settings.data.sessionMenu.showHeader
          Layout.fillWidth: true
        }

        // Power options
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.marginS

          Repeater {
            model: root.powerOptions
            delegate: PowerButton {
              id: powerOption

              required property int index
              required property var modelData
              readonly property string action: powerOption.modelData.action
              readonly property bool optionIsShutdown: powerOption.modelData.isShutdown

              Layout.fillWidth: true
              icon: powerOption.modelData.icon
              title: powerOption.modelData.title
              isShutdown: powerOption.optionIsShutdown
              isSelected: powerOption.index === root.selectedIndex
              onClicked: {
                root.selectedIndex = powerOption.index;
                root.startTimer(powerOption.action);
              }
              pending: root.timerActive && root.pendingAction === powerOption.action
              timeRemaining: root.timeRemaining
            }
          }
        }
      }
    }
  }

  // Custom power button component
  component PowerButton: Rectangle {
    id: buttonRoot

    property string icon: ""
    property string title: ""
    property bool pending: false
    property bool isShutdown: false
    property bool isSelected: false
    property int timeRemaining: 0

    signal clicked

    height: Style.baseWidgetSize * 1.3 * Style.uiScaleRatio
    radius: Style.radiusS
    color: {
      if (pending) {
        return Qt.alpha(NColor.mPrimary, 0.08);
      }
      if (isSelected || mouseArea.containsMouse) {
        return NColor.mHover;
      }
      return NColor.transparent;
    }

    border.width: pending ? Math.max(Style.borderM) : 0
    border.color: pending ? NColor.mPrimary : NColor.mOutline

    Behavior on color {
      ColorAnimation {
        duration: Style.animationFast
        easing.type: Easing.OutCirc
      }
    }

    Item {
      anchors.fill: parent
      anchors.margins: Style.marginM

      // Icon on the left
      NIcon {
        id: iconElement
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        icon: buttonRoot.icon
        color: {
          if (buttonRoot.pending)
            return NColor.mPrimary;
          if (buttonRoot.isShutdown && !buttonRoot.isSelected && !mouseArea.containsMouse)
            return NColor.mError;
          if (buttonRoot.isSelected || mouseArea.containsMouse)
            return NColor.mOnHover;
          return NColor.mOnSurface;
        }
        pointSize: Style.fontSizeXXL
        width: Style.baseWidgetSize * 0.5
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter

        Behavior on color {
          ColorAnimation {
            duration: Style.animationFast
            easing.type: Easing.OutCirc
          }
        }
      }

      // Text content in the middle
      ColumnLayout {
        anchors.left: iconElement.right
        anchors.right: pendingIndicator.visible ? pendingIndicator.left : parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.marginL
        anchors.rightMargin: pendingIndicator.visible ? Style.marginM : 0
        spacing: 0

        NText {
          text: buttonRoot.title
          font.weight: Style.fontWeightMedium
          pointSize: Style.fontSizeM
          color: {
            if (buttonRoot.pending)
              return NColor.mPrimary;
            if (buttonRoot.isShutdown && !buttonRoot.isSelected && !mouseArea.containsMouse)
              return NColor.mError;
            if (buttonRoot.isSelected || mouseArea.containsMouse)
              return NColor.mOnHover;
            return NColor.mOnSurface;
          }

          Behavior on color {
            ColorAnimation {
              duration: Style.animationFast
              easing.type: Easing.OutCirc
            }
          }
        }
      }

      // Pending indicator on the right
      Rectangle {
        id: pendingIndicator
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: 20
        height: 20
        radius: Math.min(Style.radiusL, width / 2)
        color: NColor.mPrimary
        visible: buttonRoot.pending

        NText {
          anchors.centerIn: parent
          text: Math.ceil(buttonRoot.timeRemaining / 1000)
          pointSize: Style.fontSizeS
          font.weight: Style.fontWeightBold
          color: NColor.mOnPrimary
        }
      }
    }

    MouseArea {
      id: mouseArea
      anchors.fill: parent
      hoverEnabled: true
      cursorShape: Qt.PointingHandCursor

      onClicked: buttonRoot.clicked()
    }
  }
}
