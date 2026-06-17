#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/ActiveWindow.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testActiveWindowCalculatedVerticalDimensionUsesScaledWidgetSize() {
  const calculatedVerticalDimension = qmlFunction("calculatedVerticalDimension");

  assert.equal(calculatedVerticalDimension({
    Style: {
      baseWidgetSize: 40,
    },
    scaling: 1,
  }), 35);

  assert.equal(calculatedVerticalDimension({
    Style: {
      baseWidgetSize: 40,
    },
    scaling: 1.5,
  }), 53);
}

function testActiveWindowContentWidthIncludesVisibleIconTextAndMargins() {
  const calculateContentWidth = qmlFunction("calculateContentWidth");
  const baseContext = {
    Style: {
      marginS: 6,
      marginXXS: 2,
    },
    scaling: 1.25,
    fullTitleMetrics: {
      contentWidth: 101.2,
    },
  };

  assert.equal(calculateContentWidth({
    ...baseContext,
    showIcon: true,
  }), 151);

  assert.equal(calculateContentWidth({
    ...baseContext,
    showIcon: false,
  }), 121);
}

function createIconContext({ focusedWindow = null, isHyprland = false, activeToplevel = null, iconResults = {} } = {}) {
  const iconCalls = [];
  const warnings = [];
  return {
    iconCalls,
    warnings,
    fallbackIcon: "user-desktop",
    CompositorService: {
      isHyprland,
      getFocusedWindow() {
        return focusedWindow;
      },
    },
    ToplevelManager: {
      activeToplevel,
    },
    ThemeIcons: {
      iconForAppId(appId) {
        iconCalls.push(["app", appId]);
        return iconResults[appId] || "";
      },
      iconFromName(iconName) {
        iconCalls.push(["fallback", iconName]);
        return `fallback:${iconName}`;
      },
    },
    Logger: {
      w(...args) {
        warnings.push(args);
      },
    },
  };
}

function testActiveWindowAppIconPrefersFocusedWindowAppId() {
  const getAppIcon = qmlFunction("getAppIcon");
  const ctx = createIconContext({
    focusedWindow: {
      appId: "Firefox.Desktop",
    },
    isHyprland: true,
    activeToplevel: {
      appId: "terminal.desktop",
    },
    iconResults: {
      "firefox.desktop": "/icons/firefox.svg",
      "terminal.desktop": "/icons/terminal.svg",
    },
  });

  assert.equal(getAppIcon(ctx), "/icons/firefox.svg");
  assert.deepEqual(ctx.iconCalls, [["app", "firefox.desktop"]]);
  assert.deepEqual(ctx.warnings, []);
}

function testActiveWindowAppIconFallsBackToHyprlandToplevel() {
  const getAppIcon = qmlFunction("getAppIcon");
  const ctx = createIconContext({
    focusedWindow: {
      appId: "",
    },
    isHyprland: true,
    activeToplevel: {
      appId: 1234,
    },
    iconResults: {
      "1234": "/icons/numeric-app.svg",
    },
  });

  assert.equal(getAppIcon(ctx), "/icons/numeric-app.svg");
  assert.deepEqual(ctx.iconCalls, [["app", "1234"]]);
}

function testActiveWindowAppIconFallsBackWhenLookupsFail() {
  const getAppIcon = qmlFunction("getAppIcon");
  const ctx = createIconContext({
    focusedWindow: {
      appId: "broken.desktop",
    },
    isHyprland: false,
  });
  ctx.ThemeIcons.iconForAppId = appId => {
    ctx.iconCalls.push(["app", appId]);
    throw new Error("icon lookup failed");
  };

  assert.equal(getAppIcon(ctx), "fallback:user-desktop");
  assert.deepEqual(ctx.iconCalls, [["app", "broken.desktop"], ["fallback", "user-desktop"]]);
  assert.equal(ctx.warnings.length, 1);
  assert.equal(ctx.warnings[0][0], "ActiveWindow");
}

function testActiveWindowTitleFallsBackWhenCompositorHasNoTitle() {
  const getWindowTitle = qmlFunction("getWindowTitle");

  assert.equal(getWindowTitle({
    CompositorService: {
      getFocusedWindowTitle() {
        return "Terminal";
      },
    },
  }), "Terminal");
  assert.equal(getWindowTitle({
    CompositorService: {
      getFocusedWindowTitle() {
        return "";
      },
    },
  }), "No active window");
}

function testActiveWindowHideModeVisibilityAndOpacity() {
  const shouldShowWidget = qmlFunction("shouldShowWidget", "currentOpacity");
  const widgetOpacity = qmlFunction("widgetOpacity");

  assert.equal(shouldShowWidget({ hideMode: "hidden", hasFocusedWindow: false }, 0), false);
  assert.equal(shouldShowWidget({ hideMode: "hidden", hasFocusedWindow: false }, 0.2), true);
  assert.equal(shouldShowWidget({ hideMode: "hidden", hasFocusedWindow: true }, 0), true);
  assert.equal(shouldShowWidget({ hideMode: "transparent", hasFocusedWindow: false }, 0), true);

  assert.equal(widgetOpacity({ hideMode: "transparent", hasFocusedWindow: false }), 0);
  assert.equal(widgetOpacity({ hideMode: "hidden", hasFocusedWindow: false }), 0);
  assert.equal(widgetOpacity({ hideMode: "visible", hasFocusedWindow: false }), 1);
  assert.equal(widgetOpacity({ hideMode: "transparent", hasFocusedWindow: true }), 1);
}

function createContextMenuContext() {
  const calls = [];
  const ctx = {
    contextMenu: {
      implicitHeight: 20,
      implicitWidth: 80,
      name: "active-window-menu",
      openAtItem(anchor, x, y) {
        calls.push(["menu-open", anchor.name, x, y]);
      },
    },
    root: {
      name: "active-window-root",
    },
    screen: {
      name: "HDMI-A-1",
    },
    section: "center",
    sectionWidgetIndex: 3,
    widgetId: "ActiveWindow",
    widgetSettings: {
      hideMode: "visible",
    },
    BarService: {
      getContextMenuPosition(anchor, width, height) {
        calls.push(["menu-position", anchor.name, width, height]);
        return { x: 7, y: 9 };
      },
      openWidgetSettings(screen, section, index, widgetId, settings) {
        calls.push(["settings", screen.name, section, index, widgetId, settings.hideMode]);
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
  ctx.closePopupMenuWindow = () => qmlFunction("closePopupMenuWindow")(ctx);
  return { calls, ctx };
}

function testActiveWindowContextMenuActionClosesPopupAndOpensSettings() {
  const handleContextMenuAction = qmlFunction("handleContextMenuAction", "action");
  const { calls, ctx } = createContextMenuContext();

  handleContextMenuAction(ctx, "widget-settings");

  assert.deepEqual(calls, [
    ["popup", "HDMI-A-1"],
    ["popup-close"],
    ["settings", "HDMI-A-1", "center", 3, "ActiveWindow", "visible"],
  ]);
}

function testActiveWindowRightClickOpensContextMenuAtWidgetPosition() {
  const openContextMenu = qmlFunction("openContextMenu");
  const { calls, ctx } = createContextMenuContext();

  openContextMenu(ctx);

  assert.deepEqual(calls, [
    ["popup", "HDMI-A-1"],
    ["popup-show", "active-window-menu"],
    ["menu-position", "active-window-root", 80, 20],
    ["menu-open", "active-window-root", 7, 9],
  ]);
}

const tests = [
  testActiveWindowCalculatedVerticalDimensionUsesScaledWidgetSize,
  testActiveWindowContentWidthIncludesVisibleIconTextAndMargins,
  testActiveWindowAppIconPrefersFocusedWindowAppId,
  testActiveWindowAppIconFallsBackToHyprlandToplevel,
  testActiveWindowAppIconFallsBackWhenLookupsFail,
  testActiveWindowTitleFallsBackWhenCompositorHasNoTitle,
  testActiveWindowHideModeVisibilityAndOpacity,
  testActiveWindowContextMenuActionClosesPopupAndOpensSettings,
  testActiveWindowRightClickOpensContextMenuAtWidgetPosition,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
