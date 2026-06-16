#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Theming/AppThemeService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  const callArgs = argNames.length > 0 ? `, ${argNames.join(", ")}` : "";
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx${callArgs}); }`);
}

function createContext() {
  const events = [];
  return {
    events,
    Settings: {
      data: {
        colorSchemes: {
          useWallpaperColors: false,
          predefinedScheme: "ayu-dark",
          darkMode: false,
        },
      },
    },
    Screen: {
      name: "HDMI-A-1",
    },
    ColorSchemeService: {
      applyScheme(schemeName) {
        events.push(["applyScheme", schemeName]);
      },
    },
    WallpaperService: {
      getWallpaper(screenName) {
        events.push(["getWallpaper", screenName]);
        return "";
      },
    },
    TemplateProcessor: {
      processWallpaperColors(path, mode) {
        events.push(["processWallpaperColors", path, mode]);
      },
      processPredefinedScheme(schemeData, mode) {
        events.push(["processPredefinedScheme", schemeData, mode]);
      },
    },
    Logger: {
      errors: [],
      infos: [],
      e(...args) {
        this.errors.push(args);
      },
      i(...args) {
        this.infos.push(args);
      },
    },
  };
}

function testAppThemeGenerateChoosesWallpaperOrPredefinedSchemeFlow() {
  const generate = qmlFunction("generate");
  const ctx = createContext();
  ctx.generateFromWallpaper = () => ctx.events.push(["generateFromWallpaper"]);

  generate(ctx);

  assert.deepEqual(ctx.events, [["applyScheme", "ayu-dark"]]);

  ctx.events.length = 0;
  ctx.Settings.data.colorSchemes.useWallpaperColors = true;
  generate(ctx);

  assert.deepEqual(ctx.events, [["generateFromWallpaper"]]);
}

function testAppThemeGenerateFromWallpaperRequiresWallpaperAndUsesMode() {
  const generateFromWallpaper = qmlFunction("generateFromWallpaper");
  const ctx = createContext();

  generateFromWallpaper(ctx);

  assert.deepEqual(ctx.events, [["getWallpaper", "HDMI-A-1"]]);
  assert.deepEqual(ctx.Logger.errors, [["AppThemeService", "No wallpaper found"]]);

  ctx.events.length = 0;
  ctx.Logger.errors = [];
  ctx.Settings.data.colorSchemes.darkMode = true;
  ctx.WallpaperService.getWallpaper = screenName => {
    ctx.events.push(["getWallpaper", screenName]);
    return "/walls/current.jpg";
  };

  generateFromWallpaper(ctx);

  assert.deepEqual(ctx.events, [
    ["getWallpaper", "HDMI-A-1"],
    ["processWallpaperColors", "/walls/current.jpg", "dark"],
  ]);
  assert.deepEqual(ctx.Logger.errors, []);
}

function testAppThemeGenerateFromPredefinedSchemeUsesCurrentMode() {
  const generateFromPredefinedScheme = qmlFunction("generateFromPredefinedScheme", "schemeData");
  const ctx = createContext();
  const schemeData = {
    name: "Ayu",
    colors: {
      primary: "#ffcc66",
    },
  };

  generateFromPredefinedScheme(ctx, schemeData);

  assert.deepEqual(ctx.Logger.infos, [["AppThemeService", "Generating templates from predefined color scheme"]]);
  assert.deepEqual(ctx.events, [["processPredefinedScheme", schemeData, "light"]]);

  ctx.events.length = 0;
  ctx.Settings.data.colorSchemes.darkMode = true;
  generateFromPredefinedScheme(ctx, schemeData);

  assert.deepEqual(ctx.events, [["processPredefinedScheme", schemeData, "dark"]]);
}

const tests = [
  testAppThemeGenerateChoosesWallpaperOrPredefinedSchemeFlow,
  testAppThemeGenerateFromWallpaperRequiresWallpaperAndUsesMode,
  testAppThemeGenerateFromPredefinedSchemeUsesCurrentMode,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
