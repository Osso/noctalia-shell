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

const tests = [
  testActiveWindowCalculatedVerticalDimensionUsesScaledWidgetSize,
  testActiveWindowContentWidthIncludesVisibleIconTextAndMargins,
  testActiveWindowAppIconPrefersFocusedWindowAppId,
  testActiveWindowAppIconFallsBackToHyprlandToplevel,
  testActiveWindowAppIconFallsBackWhenLookupsFail,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
