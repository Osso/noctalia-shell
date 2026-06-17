#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/Clock.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createClockContext() {
  const calls = [];
  const ctx = {
    root: {
      name: "clock-root",
    },
    screen: {
      name: "HDMI-A-1",
    },
    section: "right",
    sectionWidgetIndex: 2,
    widgetId: "Clock",
    widgetSettings: {
      formatHorizontal: "hh:mm",
    },
    PanelService: {
      getPopupMenuWindow(screen) {
        calls.push(["popup", screen.name]);
        return {
          close() {
            calls.push(["popup-close"]);
          },
          showContextMenu(menu) {
            calls.push(["popup-show", menu.name]);
          },
        };
      },
      getPanel(name, screen) {
        calls.push(["panel", name, screen.name]);
        return {
          toggle(anchor) {
            calls.push(["panel-toggle", anchor.name]);
          },
        };
      },
    },
    BarService: {
      getContextMenuPosition(anchor, width, height) {
        calls.push(["menu-position", anchor.name, width, height]);
        return { x: 11, y: 22 };
      },
      openWidgetSettings(screen, section, index, widgetId, settings) {
        calls.push(["settings", screen.name, section, index, widgetId, settings.formatHorizontal]);
      },
    },
    contextMenu: {
      implicitHeight: 40,
      implicitWidth: 80,
      name: "clock-menu",
      openAtItem(anchor, x, y) {
        calls.push(["menu-open", anchor.name, x, y]);
      },
    },
  };
  ctx.closePopupMenuWindow = () => qmlFunction("closePopupMenuWindow")(ctx);
  ctx.toggleCalendarPanel = anchor => qmlFunction("toggleCalendarPanel", "anchor")(ctx, anchor);

  return { calls, ctx };
}

function testClockWidgetOpenCalendarActionClosesPopupAndTogglesClockPanel() {
  const handleContextMenuAction = qmlFunction("handleContextMenuAction", "action");
  const { calls, ctx } = createClockContext();

  handleContextMenuAction(ctx, "open-calendar");

  assert.deepEqual(calls, [
    ["popup", "HDMI-A-1"],
    ["popup-close"],
    ["panel", "clockPanel", "HDMI-A-1"],
    ["panel-toggle", "clock-root"],
  ]);
}

function testClockWidgetSettingsActionClosesPopupAndOpensWidgetSettings() {
  const handleContextMenuAction = qmlFunction("handleContextMenuAction", "action");
  const { calls, ctx } = createClockContext();

  handleContextMenuAction(ctx, "widget-settings");

  assert.deepEqual(calls, [
    ["popup", "HDMI-A-1"],
    ["popup-close"],
    ["settings", "HDMI-A-1", "right", 2, "Clock", "hh:mm"],
  ]);
}

function testClockWidgetPrimaryClickTogglesClockPanelFromMouseArea() {
  const toggleCalendarPanel = qmlFunction("toggleCalendarPanel", "anchor");
  const { calls, ctx } = createClockContext();

  toggleCalendarPanel(ctx, { name: "clock-mouse-area" });

  assert.deepEqual(calls, [
    ["panel", "clockPanel", "HDMI-A-1"],
    ["panel-toggle", "clock-mouse-area"],
  ]);
}

function testClockWidgetRightClickShowsContextMenuAtWidgetPosition() {
  const openContextMenu = qmlFunction("openContextMenu");
  const { calls, ctx } = createClockContext();

  openContextMenu(ctx);

  assert.deepEqual(calls, [
    ["popup", "HDMI-A-1"],
    ["popup-show", "clock-menu"],
    ["menu-position", "clock-root", 80, 40],
    ["menu-open", "clock-root", 11, 22],
  ]);
}

const tests = [
  testClockWidgetOpenCalendarActionClosesPopupAndTogglesClockPanel,
  testClockWidgetSettingsActionClosesPopupAndOpensWidgetSettings,
  testClockWidgetPrimaryClickTogglesClockPanelFromMouseArea,
  testClockWidgetRightClickShowsContextMenuAtWidgetPosition,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
