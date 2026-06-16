#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/SetupWizard/SetupWizard.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    info: [],
    warnings: [],
    errors: [],
    i(...args) {
      this.info.push(args);
    },
    w(...args) {
      this.warnings.push(args);
    },
    e(...args) {
      this.errors.push(args);
    },
  };
}

function createSettings() {
  let saveCalls = 0;
  return {
    data: {
      wallpaper: {
        directory: "/old-walls",
      },
      general: {
        scaleRatio: 1,
      },
      bar: {
        position: "top",
      },
    },
    saveImmediate() {
      saveCalls += 1;
    },
    get saveCalls() {
      return saveCalls;
    },
  };
}

function createWallpaperService() {
  return {
    refreshCalls: 0,
    changes: [],
    refreshWallpapersList() {
      this.refreshCalls += 1;
    },
    changeWallpaper(wallpaper, screen) {
      this.changes.push([wallpaper, screen]);
    },
  };
}

function createSetupContext(overrides = {}) {
  const logger = createLogger();
  const settings = createSettings();
  const wallpaperService = createWallpaperService();
  const closeTimer = {
    starts: 0,
    start() {
      this.starts += 1;
    },
  };
  return {
    Logger: logger,
    Settings: settings,
    WallpaperService: wallpaperService,
    closeTimer,
    isCompleting: false,
    selectedWallpaperDirectory: "/new-walls",
    selectedWallpaper: "/new-walls/a.png",
    selectedScaleRatio: 1.25,
    selectedBarPosition: "bottom",
    ...overrides,
  };
}

function testSetupWizardCompleteSetupIgnoresDuplicateCompletion() {
  const completeSetup = qmlFunction("completeSetup");
  const ctx = createSetupContext({
    isCompleting: true,
  });

  completeSetup(ctx);

  assert.equal(ctx.Settings.saveCalls, 0);
  assert.equal(ctx.closeTimer.starts, 0);
  assert.deepEqual(ctx.WallpaperService.changes, []);
  assert.deepEqual(ctx.Logger.warnings, [
    ["SetupWizard", "completeSetup() called while already completing, ignoring"],
  ]);
}

function testSetupWizardCompleteSetupAppliesSelectionsAndStartsCloseTimer() {
  const completeSetup = qmlFunction("completeSetup");
  const ctx = createSetupContext();

  completeSetup(ctx);

  assert.equal(ctx.isCompleting, true);
  assert.equal(ctx.Settings.data.wallpaper.directory, "/new-walls");
  assert.equal(ctx.WallpaperService.refreshCalls, 1);
  assert.deepEqual(ctx.WallpaperService.changes, [["/new-walls/a.png", undefined]]);
  assert.equal(ctx.Settings.data.general.scaleRatio, 1.25);
  assert.equal(ctx.Settings.data.bar.position, "bottom");
  assert.equal(ctx.Settings.saveCalls, 1);
  assert.equal(ctx.closeTimer.starts, 1);
  assert.deepEqual(ctx.Logger.errors, []);
}

function testSetupWizardCompleteSetupSkipsWallpaperServiceWhenUnavailable() {
  const completeSetup = qmlFunction("completeSetup");
  const ctx = createSetupContext({
    WallpaperService: undefined,
    selectedWallpaper: "",
  });

  completeSetup(ctx);

  assert.equal(ctx.Settings.data.wallpaper.directory, "/old-walls");
  assert.equal(ctx.Settings.data.general.scaleRatio, 1.25);
  assert.equal(ctx.Settings.data.bar.position, "bottom");
  assert.equal(ctx.Settings.saveCalls, 1);
  assert.equal(ctx.closeTimer.starts, 1);
}

function testSetupWizardCompleteSetupResetsCompletionOnError() {
  const completeSetup = qmlFunction("completeSetup");
  const error = new Error("save failed");
  const ctx = createSetupContext();
  ctx.Settings.saveImmediate = () => {
    throw error;
  };

  completeSetup(ctx);

  assert.equal(ctx.isCompleting, false);
  assert.equal(ctx.closeTimer.starts, 0);
  assert.deepEqual(ctx.Logger.errors, [["SetupWizard", "Error completing setup:", error]]);
}

function testSetupWizardApplyWallpaperSettingsUpdatesChangedDirectoryAndWallpaper() {
  const applyWallpaperSettings = qmlFunction("applyWallpaperSettings");
  const ctx = createSetupContext();

  applyWallpaperSettings(ctx);

  assert.equal(ctx.Settings.data.wallpaper.directory, "/new-walls");
  assert.equal(ctx.WallpaperService.refreshCalls, 1);
  assert.deepEqual(ctx.WallpaperService.changes, [["/new-walls/a.png", undefined]]);
}

function testSetupWizardApplyWallpaperSettingsSkipsUnchangedOrEmptySelections() {
  const applyWallpaperSettings = qmlFunction("applyWallpaperSettings");
  const ctx = createSetupContext({
    selectedWallpaperDirectory: "/old-walls",
    selectedWallpaper: "",
  });

  applyWallpaperSettings(ctx);

  assert.equal(ctx.Settings.data.wallpaper.directory, "/old-walls");
  assert.equal(ctx.WallpaperService.refreshCalls, 0);
  assert.deepEqual(ctx.WallpaperService.changes, []);
}

function testSetupWizardApplyUISettingsPersistsScaleAndBarPosition() {
  const applyUISettings = qmlFunction("applyUISettings");
  const ctx = createSetupContext({
    selectedScaleRatio: 1.5,
    selectedBarPosition: "left",
  });

  applyUISettings(ctx);

  assert.equal(ctx.Settings.data.general.scaleRatio, 1.5);
  assert.equal(ctx.Settings.data.bar.position, "left");
}

const tests = [
  testSetupWizardCompleteSetupIgnoresDuplicateCompletion,
  testSetupWizardCompleteSetupAppliesSelectionsAndStartsCloseTimer,
  testSetupWizardCompleteSetupSkipsWallpaperServiceWhenUnavailable,
  testSetupWizardCompleteSetupResetsCompletionOnError,
  testSetupWizardApplyWallpaperSettingsUpdatesChangedDirectoryAndWallpaper,
  testSetupWizardApplyWallpaperSettingsSkipsUnchangedOrEmptySelections,
  testSetupWizardApplyUISettingsPersistsScaleAndBarPosition,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
