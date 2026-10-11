import QtQuick
import QtQuick.Layouts
import Quickshell
import "../../Helpers/TimerDigits.js" as TimerDigits
import qs.Commons
import qs.Services.System
import qs.Widgets

// Timer card for the Calendar panel
NBox {
  id: root

  implicitHeight: content.implicitHeight + (Style.marginM * 2)
  Layout.fillWidth: true
  clip: true

  ColumnLayout {
    id: content
    anchors.fill: parent
    anchors.margins: Style.marginM
    spacing: Style.marginM
    clip: true

    // Header
    RowLayout {
      Layout.fillWidth: true
      spacing: Style.marginS

      NIcon {
        icon: root.isStopwatchMode ? "clock" : "hourglass"
        pointSize: Style.fontSizeL
        color: NColor.mPrimary
      }

      NText {
        text: I18n.tr("calendar.timer.title")
        pointSize: Style.fontSizeL
        font.weight: Style.fontWeightBold
        color: NColor.mOnSurface
        Layout.fillWidth: true
      }
    }

    // Timer display (editable when not running)
    Item {
      id: timerDisplayItem
      Layout.fillWidth: true
      Layout.preferredHeight: root.isRunning ? 160 * Style.uiScaleRatio : timerInput.implicitHeight
      Layout.alignment: Qt.AlignHCenter

      property string inputBuffer: ""
      property bool isEditing: false

      // Circular progress ring (only for countdown mode when running)
      Canvas {
        id: progressRing
        anchors.fill: parent
        anchors.margins: 12
        visible: !root.isStopwatchMode && root.isRunning && root.totalSeconds > 0
        z: -1

        property real progressRatio: {
          if (root.totalSeconds <= 0)
            return 0;
          // Inverted: show remaining time (starts at 1, goes to 0)
          const ratio = root.remainingSeconds / root.totalSeconds;
          return Math.max(0, Math.min(1, ratio));
        }

        onProgressRatioChanged: requestPaint()

        onPaint: {
          var ctx = getContext("2d");
          if (width <= 0 || height <= 0) {
            return;
          }

          var centerX = width / 2;
          var centerY = height / 2;
          var radius = Math.max(0, Math.min(width, height) / 2 - 6);

          ctx.reset();

          // Background circle (full track)
          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
          ctx.lineWidth = 4;
          ctx.strokeStyle = Qt.alpha(NColor.mOnSurface, 0.2);
          ctx.stroke();

          // Progress arc (elapsed portion)
          if (progressRatio > 0) {
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + progressRatio * 2 * Math.PI);
            ctx.lineWidth = 4;
            ctx.strokeStyle = NColor.mPrimary;
            ctx.lineCap = "round";
            ctx.stroke();
          }
        }
      }

      TextInput {
        id: timerInput
        anchors.centerIn: parent
        width: Math.max(implicitWidth, parent.width)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        selectByMouse: false
        cursorVisible: false
        cursorDelegate: Item {} // Empty cursor delegate to hide cursor
        readOnly: root.isStopwatchMode || root.isRunning
        enabled: !root.isRunning
        font.family: Settings.data.ui.fontFixed

        // Calculate if hours are being shown
        readonly property bool showingHours: {
          if (root.isStopwatchMode) {
            return root.elapsedSeconds >= 3600;
          }
          // In edit mode, always show hours (HH:MM:SS format)
          if (timerDisplayItem.isEditing) {
            return true;
          }
          // When not editing, only show hours if >= 1 hour
          return root.remainingSeconds >= 3600;
        }

        font.pointSize: {
          if (!root.isRunning) {
            return Style.fontSizeXXXL;
          }
          // When running, use smaller font if hours are shown
          return showingHours ? Style.fontSizeXXL : (Style.fontSizeXXL * 1.2);
        }

        font.weight: Style.fontWeightBold
        color: {
          if (root.isRunning) {
            return NColor.mPrimary;
          }
          if (timerDisplayItem.isEditing) {
            return NColor.mPrimary;
          }
          return NColor.mOnSurface;
        }

        // Display formatted time, but show input buffer when editing
        text: {
          if (root.isStopwatchMode) {
            return root.formatTime(root.elapsedSeconds, false); // Stopwatch: only show hours if >= 1 hour
          }
          if (!timerDisplayItem.isEditing) {
            // When not editing and not running, always show hours
            // When running, only show hours if >= 1 hour
            return root.formatTime(root.remainingSeconds, root.isRunning);
          }
          if (timerDisplayItem.inputBuffer !== "") {
            return root.formatTimeFromDigits(timerDisplayItem.inputBuffer);
          }
          return root.formatTime(0, false);
        }

        // Only accept digit keys
        Keys.onPressed: event => {
          if (root.isRunning || root.isStopwatchMode) {
            event.accepted = true;
            return;
          }

          // Handle backspace
          if (event.key === Qt.Key_Backspace) {
            if (timerDisplayItem.isEditing && timerDisplayItem.inputBuffer.length > 0) {
              timerDisplayItem.inputBuffer = timerDisplayItem.inputBuffer.slice(0, -1);
              if (timerDisplayItem.inputBuffer !== "") {
                root.parseDigitsToTime(timerDisplayItem.inputBuffer);
              } else {
                Time.timerRemainingSeconds = 0;
              }
            }
            event.accepted = true;
            return;
          }

          // Handle delete
          if (event.key === Qt.Key_Delete) {
            if (timerDisplayItem.isEditing) {
              timerDisplayItem.inputBuffer = "";
              Time.timerRemainingSeconds = 0;
            }
            event.accepted = true;
            return;
          }

          // Allow navigation keys (but don't let them modify text)
          if (event.key === Qt.Key_Left || event.key === Qt.Key_Right || event.key === Qt.Key_Home || event.key === Qt.Key_End || (event.modifiers & Qt.ControlModifier) || (event.modifiers & Qt.ShiftModifier)) {
            event.accepted = false; // Let default handling work for selection
            return;
          }

          // Handle enter/return
          if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            root.applyTimeFromBuffer();
            timerDisplayItem.isEditing = false;
            focus = false;
            event.accepted = true;
            return;
          }

          // Handle escape
          if (event.key === Qt.Key_Escape) {
            timerDisplayItem.inputBuffer = "";
            Time.timerRemainingSeconds = 0;
            timerDisplayItem.isEditing = false;
            focus = false;
            event.accepted = true;
            return;
          }

          // Only allow digits 0-9
          if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) {
            // Limit to 6 digits max
            if (timerDisplayItem.inputBuffer.length >= 6) {
              event.accepted = true; // Block if already at max
              return;
            }
            // Add the digit to the buffer
            timerDisplayItem.inputBuffer += String.fromCharCode(event.key);
            // Update the display and parse
            root.parseDigitsToTime(timerDisplayItem.inputBuffer);
            event.accepted = true; // We handled it
          } else {
            event.accepted = true; // Block all other keys
          }
        }

        Keys.onReturnPressed: {
          root.applyTimeFromBuffer();
          timerDisplayItem.isEditing = false;
          focus = false;
        }

        Keys.onEscapePressed: {
          timerDisplayItem.inputBuffer = "";
          Time.timerRemainingSeconds = 0;
          timerDisplayItem.isEditing = false;
          focus = false;
        }

        onActiveFocusChanged: {
          if (activeFocus) {
            timerDisplayItem.isEditing = true;
            timerDisplayItem.inputBuffer = "";
          } else {
            root.applyTimeFromBuffer();
            timerDisplayItem.isEditing = false;
            timerDisplayItem.inputBuffer = "";
          }
        }

        MouseArea {
          anchors.fill: parent
          enabled: !root.isRunning && !root.isStopwatchMode
          cursorShape: enabled ? Qt.IBeamCursor : Qt.ArrowCursor
          onClicked: {
            if (!root.isRunning && !root.isStopwatchMode) {
              timerInput.forceActiveFocus();
            }
          }
        }
      }
    }

    // Control buttons
    RowLayout {
      Layout.fillWidth: true
      spacing: Style.marginS

      Rectangle {
        Layout.fillWidth: true
        Layout.preferredWidth: 0
        implicitHeight: startButton.implicitHeight
        color: NColor.transparent

        NButton {
          id: startButton
          anchors.fill: parent
          text: root.isRunning ? I18n.tr("calendar.timer.pause") : I18n.tr("calendar.timer.start")
          icon: root.isRunning ? "player-pause" : "player-play"
          enabled: root.isStopwatchMode || root.remainingSeconds > 0
          onClicked: {
            if (root.isRunning) {
              root.pauseTimer();
            } else {
              root.startTimer();
            }
          }
        }
      }

      Rectangle {
        Layout.fillWidth: true
        Layout.preferredWidth: 0
        implicitHeight: resetButton.implicitHeight
        color: NColor.transparent

        NButton {
          id: resetButton
          anchors.fill: parent
          text: I18n.tr("calendar.timer.reset")
          icon: "refresh"
          enabled: (root.isStopwatchMode && (root.elapsedSeconds > 0 || root.isRunning)) || (!root.isStopwatchMode && (root.remainingSeconds > 0 || root.isRunning || root.soundPlaying))
          onClicked: {
            root.resetTimer();
          }
        }
      }
    }

    // Mode tabs (Android-style) - below buttons
    NTabBar {
      Layout.fillWidth: true
      Layout.alignment: Qt.AlignHCenter
      visible: !root.isRunning
      currentIndex: root.isStopwatchMode ? 1 : 0
      onCurrentIndexChanged: {
        const newMode = currentIndex === 1;
        if (newMode !== root.isStopwatchMode) {
          if (root.isRunning) {
            root.pauseTimer();
          }
          // Stop any repeating notification sound when switching modes
          SoundService.stopSound("alarm-beep.wav");
          Time.timerSoundPlaying = false;
          Time.timerStopwatchMode = newMode;
          if (newMode) {
            // Reset to 0 for stopwatch
            Time.timerElapsedSeconds = 0;
          } else {
            Time.timerRemainingSeconds = 0;
          }
        }
      }
      spacing: Style.marginXS

      NTabButton {
        text: I18n.tr("calendar.timer.countdown")
        tabIndex: 0
        checked: !root.isStopwatchMode
      }

      NTabButton {
        text: I18n.tr("calendar.timer.stopwatch")
        tabIndex: 1
        checked: root.isStopwatchMode
      }
    }
  }

  // Bind to Time for persistent timer state
  readonly property bool isRunning: Time.timerRunning
  property bool isStopwatchMode: Time.timerStopwatchMode
  readonly property int remainingSeconds: Time.timerRemainingSeconds
  readonly property int totalSeconds: Time.timerTotalSeconds
  readonly property int elapsedSeconds: Time.timerElapsedSeconds
  readonly property bool soundPlaying: Time.timerSoundPlaying

  function formatTime(seconds, hideHoursWhenZero) {
    return TimerDigits.formatDuration(seconds, hideHoursWhenZero);
  }

  function formatTimeFromDigits(digits) {
    return TimerDigits.formatFromDigits(digits);
  }

  function parseDigitsToTime(digits) {
    Time.timerRemainingSeconds = TimerDigits.totalSecondsFromDigits(digits);
  }

  function applyTimeFromBuffer() {
    if (timerDisplayItem.inputBuffer !== "") {
      parseDigitsToTime(timerDisplayItem.inputBuffer);
      timerDisplayItem.inputBuffer = "";
    }
  }

  function startTimer() {
    Time.timerStart();
  }

  function pauseTimer() {
    Time.timerPause();
  }

  function resetTimer() {
    Time.timerReset();
  }
}
