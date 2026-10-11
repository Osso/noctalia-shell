import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.Cards
import qs.Modules.Panels.Settings.Bar.WidgetSettings

ShellRoot {
  id: harness
  property var cases: []
  property var snapshots: []
  property int caseIndex: 0
  property var componentItem: null

  Component {
    id: calendar
    CalendarHeaderCard {}
  }
  Component {
    id: monitor
    SystemMonitorCard {}
  }
  Component {
    id: clock
    ClockSettings {
      widgetData: ({})
      widgetMetadata: ({
          usePrimaryColor: true,
          useCustomFont: false,
          customFont: "",
          formatHorizontal: "HH:mm ddd, MMM dd",
          formatVertical: "HH mm dd MM"
        })
    }
  }

  // The offscreen platform has no connection to the desktop.
  Window {
    id: window
    visible: true
    width: 1000
    height: 1200
    ColumnLayout {
      id: host
      width: window.width
      spacing: 0
    }
  }

  function fixSampleDates(item) {
    if (item.sampleDate !== undefined)
      item.sampleDate = Time.now;
    for (const child of item.children)
      fixSampleDates(child);
  }

  function startCase() {
    const scenario = cases[caseIndex];
    Settings.data = Object.assign({}, Settings.data, {
      general: Object.assign({}, Settings.data.general, {
        scaleRatio: scenario.scale
      })
    });
    window.width = scenario.width;
    const component = scenario.component === "calendar" ? calendar : scenario.component === "monitor" ? monitor : clock;
    const parentItem = scenario.component === "calendar" ? host : window.contentItem;
    componentItem = component.createObject(parentItem, {
      "width": scenario.width
    });
    if (!componentItem)
      throw new Error("Production component failed: " + scenario.component);
    if (scenario.component === "monitor")
      componentItem.height = 400;
    fixSampleDates(componentItem);
  }

  function measure(item) {
    const geometry = {
      x: item.x,
      y: item.y,
      width: item.width,
      height: item.height,
      visible: item.visible,
      enabled: item.enabled,
      children: []
    };
    for (const key of ["text", "value", "suffix", "contentScale", "color", "fillColor", "textColor", "contentHeight"])
      if (item[key] !== undefined)
        geometry[key] = key.toLowerCase().includes("color") ? String(item[key]) : item[key];
    for (const child of item.children)
      geometry.children.push(measure(child));
    return geometry;
  }

  Component.onCompleted: {
    if (Quickshell.env("QT_QPA_PLATFORM") !== "offscreen")
      throw new Error("Requires offscreen platform");
    Settings.data.ui.fontDefault = "DejaVu Sans";
    Settings.data.general.animationDisabled = true;
    Settings.data.location.weatherEnabled = true;
    Settings.data.location.name = "Dallas, Texas";
    Settings.data.location.analogClockInCalendar = false;
    for (const component of ["calendar", "monitor", "clock"])
      for (const width of [480, 1000])
        for (const scale of [1, 1.25])
          cases.push({
            component: component,
            width: width,
            scale: scale
          });
    startCase();
  }

  Timer {
    interval: 500
    running: true
    repeat: true
    onTriggered: {
      snapshots.push({
        scenario: cases[caseIndex],
        tree: measure(componentItem)
      });
      componentItem.destroy();
      caseIndex++;
      if (caseIndex === cases.length) {
        console.log("REMAINING_LAYOUT_GEOMETRY " + JSON.stringify(snapshots));
        Qt.quit();
      } else {
        Qt.callLater(startCase);
      }
    }
  }
}
