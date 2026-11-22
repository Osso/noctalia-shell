pragma Singleton
import QtQuick

import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.System

Singleton {
  id: root

  // Current date (shifted to locationTimezone when resolved)
  property date now: new Date()
  property string locationTimezone: ""
  property var locationUtcOffsetSeconds: null
  property int _lastOffsetRefreshHour: -1

  // Returns a Unix Timestamp (in seconds)
  readonly property int timestamp: Math.floor(Date.now() / 1000)

  // Timer state (for countdown/stopwatch)
  property bool timerRunning: false
  property bool timerStopwatchMode: false
  property int timerRemainingSeconds: 0
  property int timerTotalSeconds: 0
  property int timerElapsedSeconds: 0
  property bool timerSoundPlaying: false
  property int timerStartTimestamp: 0 // Unix timestamp when timer was started
  property int timerPausedAt: 0 // Value when paused (for resuming)

  // Ref-counted second-level updates for visible clocks/timers that need them.
  property int secondUpdateRefs: 0
  readonly property bool secondUpdatesRequired: root.timerRunning || root.secondUpdateRefs > 0

  onSecondUpdatesRequiredChanged: scheduleNextUpdate(new Date())

  Timer {
    id: updateTimer
    interval: 1000
    repeat: false
    running: false
    triggeredOnStart: false
    onTriggered: root.updateTime(new Date())
  }

  Process {
    id: timezoneProcess
    command: ["env", "TZ=" + root.locationTimezone, "date", "+%z"]
    stdout: StdioCollector {
      id: timezoneStdout
      onStreamFinished: root.applyTimezoneOffsetString(timezoneStdout.text)
    }
  }

  Component.onCompleted: updateTime(new Date())

  function parseUtcOffsetSeconds(offsetText) {
    const match = /^([+-])(\d{2})(\d{2})$/.exec((offsetText || "").trim());
    if (!match) {
      return null;
    }
    const sign = match[1] === "-" ? -1 : 1;
    const hours = parseInt(match[2], 10);
    const minutes = parseInt(match[3], 10);
    return sign * (hours * 3600 + minutes * 60);
  }

  function dateInLocationTimezone(currentTime, utcOffsetSeconds) {
    if (utcOffsetSeconds === null || utcOffsetSeconds === undefined) {
      return currentTime;
    }
    const localOffsetSeconds = -currentTime.getTimezoneOffset() * 60;
    const deltaMs = (utcOffsetSeconds - localOffsetSeconds) * 1000;
    return new Date(currentTime.getTime() + deltaMs);
  }

  function applyTimezoneOffsetString(offsetText) {
    const parsed = root.parseUtcOffsetSeconds(offsetText);
    if (parsed !== null) {
      root.locationUtcOffsetSeconds = parsed;
      root.updateTime(new Date());
    }
  }

  function setLocationTimezone(tz) {
    const normalized = (tz || "").trim();
    if (normalized === root.locationTimezone && (normalized === "" || root.locationUtcOffsetSeconds !== null)) {
      return;
    }
    root.locationTimezone = normalized;
    if (normalized === "") {
      root.locationUtcOffsetSeconds = null;
      root._lastOffsetRefreshHour = -1;
      root.updateTime(new Date());
      return;
    }
    if (!/^[A-Za-z0-9_+-]+(\/[A-Za-z0-9_+-]+)*$/.test(normalized)) {
      return;
    }
    timezoneProcess.running = false;
    timezoneProcess.command = ["env", "TZ=" + normalized, "date", "+%z"];
    timezoneProcess.running = true;
  }

  function updateTime(currentTime) {
    root.now = root.dateInLocationTimezone(currentTime, root.locationUtcOffsetSeconds);
    if (root.locationTimezone !== "" && currentTime.getMinutes() === 0 && currentTime.getHours() !== root._lastOffsetRefreshHour) {
      root._lastOffsetRefreshHour = currentTime.getHours();
      timezoneProcess.running = false;
      timezoneProcess.command = ["env", "TZ=" + root.locationTimezone, "date", "+%z"];
      timezoneProcess.running = true;
    }
    updateTimerState();
    scheduleNextUpdate(currentTime);
  }

  function updateTimerState() {
    if (!root.timerRunning || root.timerStartTimestamp <= 0) {
      return;
    }

    const elapsedSinceStart = root.timestamp - root.timerStartTimestamp;

    if (root.timerStopwatchMode) {
      root.timerElapsedSeconds = root.timerPausedAt + elapsedSinceStart;
      return;
    }

    root.timerRemainingSeconds = root.timerTotalSeconds - elapsedSinceStart;
    if (root.timerRemainingSeconds <= 0) {
      root.timerOnFinished();
    }
  }

  function scheduleNextUpdate(currentTime) {
    updateTimer.interval = nextUpdateInterval(currentTime);
    updateTimer.restart();
  }

  function nextUpdateInterval(date) {
    const bufferMs = 10;
    const minimumIntervalMs = 100;
    if (root.secondUpdatesRequired) {
      return Math.max(minimumIntervalMs, 1000 - date.getMilliseconds() + bufferMs);
    }

    const untilNextMinute = 60000 - date.getSeconds() * 1000 - date.getMilliseconds();
    return Math.max(minimumIntervalMs, untilNextMinute + bufferMs);
  }

  function beginSecondUpdates() {
    secondUpdateRefs++;
  }

  function endSecondUpdates() {
    secondUpdateRefs = Math.max(0, secondUpdateRefs - 1);
  }

  function formatRequiresSeconds(format) {
    if (!format) {
      return false;
    }
    return /(^|[^A-Za-z])s{1,2}([^A-Za-z]|$)/.test(format);
  }

  // Formats a Date object into a YYYYMMDD-HHMMSS string.
  function getFormattedTimestamp(date) {
    if (!date) {
      date = new Date();
    }
    const year = date.getFullYear();

    // getMonth() is zero-based, so we add 1
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}${month}${day}-${hours}${minutes}${seconds}`;
  }

  // Format an easy to read approximate duration ex: 4h 32m
  // Used to display the time remaining on the Battery widget, computer uptime, etc..
  function formatVagueHumanReadableDuration(totalSeconds) {
    if (typeof totalSeconds !== 'number' || totalSeconds < 0) {
      return '0s';
    }

    // Floor the input to handle decimal seconds
    totalSeconds = Math.floor(totalSeconds);

    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const parts = [];
    if (days)
      parts.push(`${days}d`);
    if (hours)
      parts.push(`${hours}h`);
    if (minutes)
      parts.push(`${minutes}m`);

    // Only show seconds if no hours and no minutes
    if (!hours && !minutes) {
      parts.push(`${seconds}s`);
    }

    return parts.join(' ');
  }

  // Format a date into
  function formatRelativeTime(date) {
    if (!date)
      return "";
    const diff = Date.now() - date.getTime();
    if (diff < 60000)
      return I18n.tr("notifications.time.now");
    if (diff < 120000)
      return I18n.tr("notifications.time.diffM");
    if (diff < 3600000)
      return I18n.tr("notifications.time.diffMM", {
                       "diff": Math.floor(diff / 60000)
                     });
    if (diff < 7200000)
      return I18n.tr("notifications.time.diffH");
    if (diff < 86400000)
      return I18n.tr("notifications.time.diffHH", {
                       "diff": Math.floor(diff / 3600000)
                     });
    if (diff < 172800000)
      return I18n.tr("notifications.time.diffD");
    return I18n.tr("notifications.time.diffDD", {
                     "diff": Math.floor(diff / 86400000)
                   });
  }

  // Timer functions
  function timerStart() {
    const currentTime = new Date();
    root.now = root.dateInLocationTimezone(currentTime, root.locationUtcOffsetSeconds);
    if (root.timerStopwatchMode) {
      root.timerRunning = true;
      root.timerStartTimestamp = root.timestamp;
      root.timerPausedAt = root.timerElapsedSeconds;
    } else {
      if (root.timerRemainingSeconds <= 0) {
        return;
      }
      root.timerRunning = true;
      root.timerTotalSeconds = root.timerRemainingSeconds;
      root.timerStartTimestamp = root.timestamp;
      root.timerPausedAt = 0;
    }
    scheduleNextUpdate(root.now);
  }

  function timerPause() {
    updateTimerState();
    if (root.timerRunning) {
      // Save current state
      if (root.timerStopwatchMode) {
        root.timerPausedAt = root.timerElapsedSeconds;
      } else {
        root.timerPausedAt = root.timerRemainingSeconds;
      }
    }
    root.timerRunning = false;
    root.timerStartTimestamp = 0;
    // Stop any repeating notification sound when pausing
    SoundService.stopSound("alarm-beep.wav");
    root.timerSoundPlaying = false;
  }

  function timerReset() {
    root.timerRunning = false;
    root.timerStartTimestamp = 0;
    if (root.timerStopwatchMode) {
      root.timerElapsedSeconds = 0;
      root.timerPausedAt = 0;
    } else {
      root.timerRemainingSeconds = 0;
      root.timerTotalSeconds = 0;
      root.timerPausedAt = 0;
    }
    // Stop any repeating notification sound
    SoundService.stopSound("alarm-beep.wav");
    root.timerSoundPlaying = false;
  }

  function timerOnFinished() {
    root.timerRunning = false;
    root.timerRemainingSeconds = 0;
    // Play notification sound with repeat at lower volume
    root.timerSoundPlaying = true;
    SoundService.playSound("alarm-beep.wav", {
                             repeat: true,
                             volume: 0.3
                           });
  }
}
