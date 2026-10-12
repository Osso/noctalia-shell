pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Cards
import qs.Services.System

ShellRoot {
  id: harness

  TestCase {
    id: input
    when: false
  }

  Window {
    width: 440
    height: 400
    visible: true // Offscreen only; runner removes desktop connections.

    TimerCard {
      id: card
      width: 400
      height: implicitHeight
    }
  }

  function require(condition, message) {
    if (!condition) {
      console.error("TIMER_CARD_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function findItem(item, predicate) {
    if (predicate(item))
      return item;
    for (const child of item.children || []) {
      const found = harness.findItem(child, predicate);
      if (found)
        return found;
    }
    return null;
  }

  function display() {
    return harness.findItem(card, item => item.cursorVisible !== undefined);
  }

  function button(action) {
    return harness.findItem(card, item => item.text === "calendar.timer." + action && item.clicked !== undefined);
  }

  function tabs() {
    return harness.findItem(card, item => item.currentIndex !== undefined);
  }

  function ring() {
    return harness.findItem(card, item => item.progressRatio !== undefined);
  }

  function click(item) {
    input.mouseClick(item, item.width / 2, item.height / 2, Qt.LeftButton);
  }

  function enterDigits(keys) {
    harness.click(harness.display());
    for (const key of keys)
      input.keyClick(key);
  }

  Timer {
    id: steps
    interval: 150
    running: true
    repeat: true
    property int step: 0
    property int pausedValue: 0
    property int waits: 0

    onTriggered: {
      switch (steps.step) {
      case 0:
        harness.require(card.formatTime(3661, false) === "01:01:01", "hours formatting");
        harness.require(card.formatTime(61, true) === "01:01", "hidden zero hours");
        harness.require(card.formatTime(-1, false) === "00:00:00", "negative duration clamped");
        harness.require(card.formatTimeFromDigits("1") === "00:00:01", "single digit");
        harness.require(card.formatTimeFromDigits("123456") === "12:34:56", "six digits");
        harness.require(card.formatTimeFromDigits("999999") === "99:59:59", "digit limits");
        harness.require(!harness.button("start").enabled, "zero countdown cannot start");
        harness.enterDigits([Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6]);
        harness.require(harness.display().text === "12:34:56", "editing displays digits");
        harness.require(Time.timerRemainingSeconds === 45296, "digits parsed into shared Time state");
        input.keyClick(Qt.Key_7);
        harness.require(harness.display().text === "12:34:56", "seventh digit blocked");
        input.keyClick(Qt.Key_Backspace);
        harness.require(harness.display().text === "01:23:45", "backspace reparses digits");
        input.keyClick(Qt.Key_Delete);
        harness.require(Time.timerRemainingSeconds === 0, "delete clears time");
        input.keyClick(Qt.Key_1);
        input.keyClick(Qt.Key_Escape);
        harness.require(Time.timerRemainingSeconds === 0 && !harness.display().activeFocus, "escape clears and unfocuses");
        harness.enterDigits([Qt.Key_1, Qt.Key_0]);
        input.keyClick(Qt.Key_Return);
        harness.require(harness.display().text === "00:00:10", "return commits digits");
        harness.click(harness.button("start"));
        harness.require(card.isRunning && Time.timerTotalSeconds === 10, "button starts countdown");
        harness.require(harness.display().text === "00:10" && harness.display().readOnly, "running countdown display");
        harness.require(harness.ring().visible && !harness.tabs().visible, "countdown ring and hidden mode tabs");
        // Time.timestamp currently caches Date.now() without a notify dependency.
        // Inject elapsed start time; keep its real scheduled update path intact.
        Time.timerStartTimestamp = Time.timestamp - 1;
        break;
      case 1:
        // Wait for the real Time singleton's scheduled update to observe elapsed time.
        if (card.remainingSeconds === 10 && steps.waits++ < 15)
          return;
        harness.require(card.remainingSeconds < 10 && card.remainingSeconds > 0, "real countdown tick");
        harness.require(harness.ring().progressRatio < 1 && harness.ring().progressRatio > 0, "ring follows remaining time");
        harness.click(harness.button("pause"));
        steps.pausedValue = card.remainingSeconds;
        harness.require(!card.isRunning && Time.timerStartTimestamp === 0, "pause stops timer");
        steps.waits = 0;
        break;
      case 2:
        if (steps.waits++ < 8)
          return;
        harness.require(card.remainingSeconds === steps.pausedValue, "paused time remains stable across ticks");
        harness.click(harness.button("start"));
        harness.require(Time.timerTotalSeconds === steps.pausedValue, "resume starts from paused remaining time");
        harness.click(harness.button("reset"));
        harness.require(!card.isRunning && card.remainingSeconds === 0 && card.totalSeconds === 0, "reset clears countdown");
        harness.enterDigits([Qt.Key_1]);
        input.keyClick(Qt.Key_Return);
        harness.click(harness.button("start"));
        Time.timerStartTimestamp = Time.timestamp - 1;
        steps.waits = 0;
        break;
      case 3:
        if (card.isRunning && steps.waits++ < 15)
          return;
        harness.require(!card.isRunning && card.remainingSeconds === 0 && card.soundPlaying, "countdown finishes at zero");
        harness.require(SoundService.plays === 1 && SoundService.lastOptions.repeat, "completion requests repeating alarm");
        harness.require(harness.button("reset").enabled, "alarm can be reset at zero");
        harness.click(harness.button("reset"));
        harness.require(!card.soundPlaying && SoundService.stops > 0, "reset stops alarm");
        harness.click(harness.button("stopwatch"));
        harness.require(card.isStopwatchMode && harness.tabs().currentIndex === 1, "tab switches to stopwatch");
        harness.require(harness.display().text === "00:00:00" && harness.display().readOnly, "idle stopwatch display");
        harness.click(harness.button("start"));
        harness.require(card.isRunning && !harness.ring().visible, "stopwatch starts without countdown ring");
        Time.timerStartTimestamp = Time.timestamp - 1;
        steps.waits = 0;
        break;
      case 4:
        if (card.elapsedSeconds === 0 && steps.waits++ < 15)
          return;
        harness.require(card.elapsedSeconds > 0, "real stopwatch tick");
        harness.click(harness.button("pause"));
        steps.pausedValue = card.elapsedSeconds;
        harness.require(Time.timerPausedAt === steps.pausedValue, "stopwatch pause preserves elapsed time");
        steps.waits = 0;
        break;
      case 5:
        if (steps.waits++ < 8)
          return;
        harness.require(card.elapsedSeconds === steps.pausedValue, "paused stopwatch stable");
        harness.click(harness.button("start"));
        harness.require(Time.timerPausedAt === steps.pausedValue, "stopwatch resumes elapsed time");
        harness.click(harness.button("pause"));
        Time.timerElapsedSeconds = 3661;
        harness.require(harness.display().text === "01:01:01" && harness.display().showingHours, "stopwatch hour transition");
        harness.click(harness.button("reset"));
        harness.require(card.elapsedSeconds === 0 && !card.isRunning, "stopwatch reset");
        harness.click(harness.button("countdown"));
        harness.require(!card.isStopwatchMode && harness.tabs().currentIndex === 0, "switch back to countdown");
        card.parseDigitsToTime("10000");
        harness.require(harness.display().text === "01:00:00", "countdown hour transition");
        harness.click(harness.button("start"));
        harness.require(harness.display().showingHours, "running hour countdown");
        harness.click(harness.button("reset"));
        console.log("TIMER_CARD_BEHAVIOR_PASS");
        Qt.quit();
        break;
      }
      steps.step++;
    }
  }
}
