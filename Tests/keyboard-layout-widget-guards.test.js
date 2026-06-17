#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/KeyboardLayout.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createWidgetContext(overrides = {}) {
  const calls = [];
  const ctx = {
    currentLayout: "us",
    contextMenu: {
      implicitHeight: 30,
      implicitWidth: 70,
      name: "keyboard-menu",
      openAtItem(anchor, x, y) {
        calls.push(["menu-open", anchor.name, x, y]);
      },
    },
    pill: {
      name: "keyboard-pill",
    },
    root: {
      name: "keyboard-root",
    },
    screen: {
      name: "HDMI-A-1",
    },
    section: "left",
    sectionWidgetIndex: 1,
    widgetId: "KeyboardLayout",
    widgetSettings: {
      displayMode: "forceOpen",
    },
    BarService: {
      getContextMenuPosition(anchor, width, height) {
        calls.push(["menu-position", anchor.name, width, height]);
        return { x: 5, y: 8 };
      },
      openWidgetSettings(screen, section, index, widgetId, settings) {
        calls.push(["settings", screen.name, section, index, widgetId, settings.displayMode]);
      },
    },
    I18n: {
      tr(key, args) {
        if (args) {
          return `${key}:${args.layout}`;
        }
        return key;
      },
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
    },
  };

  Object.assign(ctx, overrides);
  ctx.root.displayMode = ctx.displayMode;
  ctx.closePopupMenuWindow = () => qmlFunction("closePopupMenuWindow")(ctx);
  ctx.displayText = () => qmlFunction("displayText")(ctx);
  return { calls, ctx };
}

function testKeyboardLayoutWidgetFormatsDisplayTextAndTooltip() {
  const displayText = qmlFunction("displayText");
  const tooltipText = qmlFunction("tooltipText");
  const { ctx } = createWidgetContext({ currentLayout: "fr" });

  assert.equal(displayText(ctx), "FR");
  assert.equal(tooltipText(ctx), "tooltips.keyboard-layout:FR");
}

function testKeyboardLayoutWidgetDisplayModeFlags() {
  const shouldForceOpen = qmlFunction("shouldForceOpen");
  const shouldForceClose = qmlFunction("shouldForceClose");
  const { ctx } = createWidgetContext();

  ctx.root.displayMode = "forceOpen";
  assert.equal(shouldForceOpen(ctx), true);
  assert.equal(shouldForceClose(ctx), false);

  ctx.root.displayMode = "alwaysHide";
  assert.equal(shouldForceOpen(ctx), false);
  assert.equal(shouldForceClose(ctx), true);

  ctx.root.displayMode = "onhover";
  assert.equal(shouldForceOpen(ctx), false);
  assert.equal(shouldForceClose(ctx), false);
}

function testKeyboardLayoutWidgetSettingsActionClosesPopupAndOpensWidgetSettings() {
  const handleContextMenuAction = qmlFunction("handleContextMenuAction", "action");
  const { calls, ctx } = createWidgetContext();

  handleContextMenuAction(ctx, "widget-settings");

  assert.deepEqual(calls, [
    ["popup", "HDMI-A-1"],
    ["popup-close"],
    ["settings", "HDMI-A-1", "left", 1, "KeyboardLayout", "forceOpen"],
  ]);
}

function testKeyboardLayoutWidgetRightClickShowsContextMenuAtPillPosition() {
  const openContextMenu = qmlFunction("openContextMenu");
  const { calls, ctx } = createWidgetContext();

  openContextMenu(ctx);

  assert.deepEqual(calls, [
    ["popup", "HDMI-A-1"],
    ["popup-show", "keyboard-menu"],
    ["menu-position", "keyboard-pill", 70, 30],
    ["menu-open", "keyboard-pill", 5, 8],
  ]);
}

const tests = [
  testKeyboardLayoutWidgetFormatsDisplayTextAndTooltip,
  testKeyboardLayoutWidgetDisplayModeFlags,
  testKeyboardLayoutWidgetSettingsActionClosesPopupAndOpensWidgetSettings,
  testKeyboardLayoutWidgetRightClickShowsContextMenuAtPillPosition,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
