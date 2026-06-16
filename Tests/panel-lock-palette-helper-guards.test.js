#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const barWidgetDialogSource = readQml("Modules/Panels/Settings/Bar/BarWidgetSettingsDialog.qml");
const colorPaletteSource = readQml("Services/Theming/ColorPaletteGenerator.qml");
const controlCenterDialogSource = readQml("Modules/Panels/Settings/ControlCenter/ControlCenterWidgetSettingsDialog.qml");
const lockContextSource = readQml("Modules/LockScreen/LockContext.qml");
const lockScreenSource = readQml("Modules/LockScreen/LockScreen.qml");
const popupMenuWindowSource = readQml("Modules/MainScreen/PopupMenuWindow.qml");
const profileCardSource = readQml("Modules/Cards/ProfileCard.qml");
const taskbarGroupedSource = readQml("Modules/Bar/Widgets/TaskbarGrouped.qml");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBarWidgetSettingsDialogLoadsSectionWidgetData() {
  const loadWidgetSettings = qmlFunction(barWidgetDialogSource, "loadWidgetSettings");
  const calls = [];
  const widgetData = { id: "fallback" };
  const sectionWidgetData = { id: "section-widget" };
  const ctx = {
    widgetId: "Battery",
    widgetData,
    sectionId: "left",
    widgetIndex: 1,
    BarWidgetRegistry: {
      widgetSettingsMap: {
        Battery: "WidgetSettings/BatterySettings.qml",
      },
      widgetMetadata: {
        Battery: { name: "Battery" },
      },
    },
    Settings: {
      data: {
        bar: {
          widgets: {
            left: [{ id: "first" }, sectionWidgetData],
          },
        },
      },
    },
    settingsLoader: {
      setSource(source, props) {
        calls.push([source, props]);
      },
    },
  };

  loadWidgetSettings(ctx);

  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "WidgetSettings/BatterySettings.qml");
  assert.equal(calls[0][1].widgetData, sectionWidgetData);
  assert.deepEqual(calls[0][1].widgetMetadata, { name: "Battery" });
}

function testBarWidgetSettingsDialogSkipsUnknownWidgets() {
  const loadWidgetSettings = qmlFunction(barWidgetDialogSource, "loadWidgetSettings");
  const calls = [];

  loadWidgetSettings({
    widgetId: "Missing",
    widgetData: {},
    BarWidgetRegistry: {
      widgetSettingsMap: {},
      widgetMetadata: {},
    },
    settingsLoader: {
      setSource() {
        calls.push("called");
      },
    },
  });

  assert.deepEqual(calls, []);
}

function testControlCenterWidgetSettingsDialogLoadsCustomButtonSettings() {
  const loadWidgetSettings = qmlFunction(controlCenterDialogSource, "loadWidgetSettings");
  const calls = [];
  const widgetData = { command: "date" };

  loadWidgetSettings({
    widgetId: "CustomButton",
    widgetData,
    ControlCenterWidgetRegistry: {
      widgetMetadata: {
        CustomButton: { name: "Custom Button" },
      },
    },
    settingsLoader: {
      setSource(source, props) {
        calls.push([source, props]);
      },
    },
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "WidgetSettings/CustomButtonSettings.qml");
  assert.equal(calls[0][1].widgetData, widgetData);
  assert.deepEqual(calls[0][1].widgetMetadata, { name: "Custom Button" });
}

function testLockContextTryUnlockFailsClosedWhenPamUnavailable() {
  const tryUnlock = qmlFunction(lockContextSource, "tryUnlock");
  const ctx = {
    pamAvailable: false,
    errorMessage: "",
    showFailure: false,
    root: {
      unlockInProgress: false,
    },
  };

  tryUnlock(ctx);

  assert.equal(ctx.errorMessage, "PAM not available");
  assert.equal(ctx.showFailure, true);
  assert.equal(ctx.root.unlockInProgress, false);
}

function testLockContextTryUnlockStartsPamAuthentication() {
  const tryUnlock = qmlFunction(lockContextSource, "tryUnlock");
  let started = false;
  const logs = [];
  const ctx = {
    pamAvailable: true,
    errorMessage: "old",
    showFailure: true,
    root: {
      unlockInProgress: false,
    },
    Logger: {
      i(...args) {
        logs.push(args);
      },
    },
    pam: {
      user: "alessio",
      start() {
        started = true;
      },
    },
  };

  tryUnlock(ctx);

  assert.equal(ctx.root.unlockInProgress, true);
  assert.equal(ctx.errorMessage, "");
  assert.equal(ctx.showFailure, false);
  assert.equal(started, true);
  assert.equal(logs.length, 1);
}

function testLockScreenSchedulesUnloadTimer() {
  const scheduleUnloadAfterUnlock = qmlFunction(lockScreenSource, "scheduleUnloadAfterUnlock");
  let startCount = 0;

  scheduleUnloadAfterUnlock({
    unloadAfterUnlockTimer: {
      start() {
        startCount++;
      },
    },
  });

  assert.equal(startCount, 1);
}

function testPopupMenuWindowShowContextMenuGuardsMissingMenu() {
  const showContextMenu = qmlFunction(popupMenuWindowSource, "showContextMenu", "menu");
  const ctx = {
    contentItem: "old",
    openCount: 0,
    open() {
      this.openCount++;
    },
  };
  const menu = { id: "menu" };

  showContextMenu(ctx, null);
  assert.equal(ctx.contentItem, "old");
  assert.equal(ctx.openCount, 0);

  showContextMenu(ctx, menu);
  assert.equal(ctx.contentItem, menu);
  assert.equal(ctx.openCount, 1);
}

function testProfileCardUpdateSystemInfoStartsUptimeProcess() {
  const updateSystemInfo = qmlFunction(profileCardSource, "updateSystemInfo");
  const ctx = {
    uptimeProcess: {
      running: false,
    },
  };

  updateSystemInfo(ctx);

  assert.equal(ctx.uptimeProcess.running, true);
}

function testTaskbarGroupedOpenContextMenuBuildsWindowActionsAndPositionsMenu() {
  const openContextMenu = qmlFunction(taskbarGroupedSource, "openContextMenu", "globalX", "globalY", "itemWidth", "itemHeight");
  const contextMenu = {
    implicitWidth: 100,
    implicitHeight: 80,
    itemHeight: 24,
    model: [],
    openAtItem(item, x, y) {
      this.openCall = [item, x, y];
    },
  };
  const popupMenuWindow = {
    openCount: 0,
    contentItem: null,
    open() {
      this.openCount++;
    },
  };
  const root = {
    selectedWindow: { id: 10 },
    selectedAppName: "Terminal",
    barPosition: "bottom",
  };
  const ctx = {
    root,
    contextMenu,
    screen: { name: "HDMI-A-1" },
    I18n: {
      tr(key, args) {
        return args && args.app ? `${key}:${args.app}` : key;
      },
    },
    PanelService: {
      getPopupMenuWindow(screen) {
        assert.equal(screen.name, "HDMI-A-1");
        return popupMenuWindow;
      },
    },
    Style: {
      barHeight: 48,
      marginS: 6,
    },
  };

  openContextMenu(ctx, 200, 50, 80, 30);

  assert.deepEqual(contextMenu.model.map(item => item.action), ["activate", "close", "widget-settings"]);
  assert.deepEqual(contextMenu.model.map(item => item.label), [
    "context-menu.activate-app:Terminal",
    "context-menu.close-app:Terminal",
    "context-menu.widget-settings",
  ]);
  assert.equal(popupMenuWindow.openCount, 1);
  assert.equal(popupMenuWindow.contentItem, contextMenu);
  assert.deepEqual(contextMenu.openCall, [root, 190, -90]);
}

function testColorPaletteGeneratorUsesStrictSurfaceColorsAndGeneratedAccents() {
  const generatePalette = qmlFunction(colorPaletteSource, "generatePalette", "colors", "isDarkMode", "isStrict");
  const calls = [];
  const ctx = {
    ColorsConvert: {
      generateContainerColor(color, isDarkMode) {
        calls.push(["container", color, isDarkMode]);
        return `${color}-container`;
      },
      generateOnColor(color, isDarkMode) {
        calls.push(["on", color, isDarkMode]);
        return `on-${color}`;
      },
      adjustLightness(color, amount) {
        calls.push(["lightness", color, amount]);
        return `${color}-light-${amount}`;
      },
      adjustLightnessAndSaturation(color, lightness, saturation) {
        calls.push(["outline", color, lightness, saturation]);
        return `${color}-outline`;
      },
      generateSurfaceVariant(surface, level, isDarkMode) {
        calls.push(["surface", surface, level, isDarkMode]);
        return `${surface}-surface-${level}`;
      },
    },
  };
  const colors = {
    mPrimary: "#111111",
    mSecondary: "#222222",
    mTertiary: "#333333",
    mError: "#ff0000",
    mSurface: "#101010",
    mOnSurface: "#eeeeee",
    mSurfaceVariant: "#202020",
    mOnSurfaceVariant: "#dddddd",
    mOutline: "#444444",
  };

  const palette = generatePalette(ctx, colors, true, true);

  assert.equal(palette.primary.default.hex, "#111111");
  assert.equal(palette.primary.default.hex_stripped, "111111");
  assert.equal(palette.primary_container.default.hex, "#111111-container");
  assert.equal(palette.on_primary.default.hex, "on-#111111");
  assert.equal(palette.surface_variant.default.hex, "#202020");
  assert.equal(palette.on_surface_variant.default.hex, "#dddddd");
  assert.equal(palette.outline.default.hex, "#444444");
  assert.equal(palette.shadow.default.hex, "#000000");
  assert.ok(calls.some(call => call[0] === "surface" && call[2] === 4));
}

const tests = [
  testBarWidgetSettingsDialogLoadsSectionWidgetData,
  testBarWidgetSettingsDialogSkipsUnknownWidgets,
  testControlCenterWidgetSettingsDialogLoadsCustomButtonSettings,
  testLockContextTryUnlockFailsClosedWhenPamUnavailable,
  testLockContextTryUnlockStartsPamAuthentication,
  testLockScreenSchedulesUnloadTimer,
  testPopupMenuWindowShowContextMenuGuardsMissingMenu,
  testProfileCardUpdateSystemInfoStartsUptimeProcess,
  testTaskbarGroupedOpenContextMenuBuildsWindowActionsAndPositionsMenu,
  testColorPaletteGeneratorUsesStrictSurfaceColorsAndGeneratedAccents,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
