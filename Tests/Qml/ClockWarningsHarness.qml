import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets

ShellRoot {
  id: harness
  property var clock

  Window {
    id: window
    width: 480
    height: 320
    visible: true // Offscreen only; no desktop connection.
  }

  Component {
    id: factory
    Clock {
      widgetId: "Clock"
      section: "left"
      sectionWidgetIndex: 0
    }
  }

  function require(condition, message) {
    if (!condition) {
      console.error("CLOCK_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function items(item, predicate) {
    let found = predicate(item) ? [item] : [];
    for (const child of item.children || [])
      found = found.concat(harness.items(child, predicate));
    return found;
  }

  function texts() {
    return harness.items(harness.clock, item => item.visible && item.text !== undefined && item.icon === undefined);
  }

  function expectTexts(expected) {
    const actual = harness.texts().map(item => item.text);
    harness.require(JSON.stringify(actual) === JSON.stringify(expected), "expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual));
  }

  function configure(horizontal, vertical) {
    const settings = JSON.parse(JSON.stringify(Settings.data));
    settings.bar.widgets.left = [
      {
        formatHorizontal: horizontal,
        formatVertical: vertical,
        usePrimaryColor: true,
        useCustomFont: true,
        customFont: "DejaVu Sans Mono"
      }
    ];
    Settings.data = settings;
  }

  function setPosition(position) {
    const settings = JSON.parse(JSON.stringify(Settings.data));
    settings.bar.position = position;
    Settings.data = settings;
  }

  Timer {
    id: steps
    interval: 100
    running: true
    repeat: true
    property int step: 0

    onTriggered: {
      switch (steps.step) {
      case 0:
        harness.setPosition("top");
        harness.configure("HH:mm", "HH mm");
        harness.clock = factory.createObject(window.contentItem);
        break;
      case 1:
        harness.expectTexts(["14:30"]);
        harness.require(Time.secondUpdateRefs === 0, "minute format must not register seconds");
        harness.require(harness.texts()[0].pointSize === 12, "single horizontal line point size");
        harness.require(harness.texts()[0].family === "DejaVu Sans Mono" && harness.texts()[0].color.toString() === "#abcdef", "font and primary color settings");
        harness.configure("h:mm AP", "h mm AP");
        break;
      case 2:
        harness.expectTexts(["2:30 PM"]);
        harness.configure("HH:mm:ss\\nyyyy-MM-dd", "HH mm ss");
        break;
      case 3:
        harness.expectTexts(["14:30:45", "2026-10-11"]);
        harness.require(Time.secondUpdateRefs === 1, "seconds format registers once");
        harness.require(harness.texts()[0].pointSize === 10 && harness.texts()[1].pointSize === 9, "multiline delegate index point sizes");
        Time.now = new Date(2026, 9, 11, 14, 30, 46);
        break;
      case 4:
        harness.expectTexts(["14:30:46", "2026-10-11"]);
        Time.now = new Date(2026, 9, 11, 23, 59, 59);
        break;
      case 5:
        harness.expectTexts(["23:59:59", "2026-10-11"]);
        Time.now = new Date(2026, 9, 12, 0, 0, 0);
        break;
      case 6:
        harness.expectTexts(["00:00:00", "2026-10-12"]);
        harness.setPosition("left");
        break;
      case 7:
        harness.expectTexts(["00", "00", "00"]);
        harness.require(Time.secondUpdateRefs === 1, "orientation does not double-register");
        harness.configure("HH:mm:ss", "h mm AP");
        break;
      case 8:
        harness.expectTexts(["12", "00", "AM"]);
        harness.require(Time.secondUpdateRefs === 0, "active minute vertical format deregisters despite inactive seconds format");
        harness.configure("HH:mm", "HH mm ss");
        break;
      case 9:
        harness.require(Time.secondUpdateRefs === 1, "vertical seconds registers");
        harness.clock.visible = false;
        break;
      case 10:
        harness.require(Time.secondUpdateRefs === 0, "hidden clock deregisters");
        harness.clock.visible = true;
        break;
      case 11:
        harness.require(Time.secondUpdateRefs === 1, "shown clock registers once");
        harness.clock.destroy();
        break;
      case 12:
        harness.require(Time.secondUpdateRefs === 0, "destruction releases second updates");
        harness.setPosition("top");
        harness.configure("HH:mm", "HH mm");
        harness.clock = factory.createObject(window.contentItem);
        break;
      case 13:
        harness.expectTexts(["00:00"]);
        harness.require(Time.secondUpdateRefs === 0, "recreated minute clock remains unregistered");
        harness.clock.destroy();
        break;
      case 14:
        harness.require(Time.secondUpdateRefs === 0, "all consumers released");
        console.log("CLOCK_BEHAVIOR_PASS", "15 transition rows");
        Qt.quit();
        break;
      }
      steps.step++;
    }
  }
}
