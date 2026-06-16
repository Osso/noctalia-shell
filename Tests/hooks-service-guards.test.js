#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Control/HooksService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext(hooks) {
  return {
    Settings: {
      data: {
        hooks,
      },
    },
    Quickshell: {
      commands: [],
      execDetached(command) {
        this.commands.push(command);
      },
    },
    Logger: {
      debug: [],
      errors: [],
      d(...args) {
        this.debug.push(args);
      },
      e(...args) {
        this.errors.push(args);
      },
    },
  };
}

function testWallpaperHookSkipsMissingDisabledAndBlankScripts() {
  const executeWallpaperHook = qmlFunction("executeWallpaperHook", "wallpaperPath", "screenName");

  for (const hooks of [null, { enabled: false, wallpaperChange: "echo $1" }, { enabled: true, wallpaperChange: "" }]) {
    const ctx = createContext(hooks);
    executeWallpaperHook(ctx, "/tmp/wallpaper.jpg", "HDMI-A-1");
    assert.deepEqual(ctx.Quickshell.commands, []);
  }
}

function testWallpaperHookSubstitutesPathAndScreen() {
  const executeWallpaperHook = qmlFunction("executeWallpaperHook", "wallpaperPath", "screenName");
  const ctx = createContext({
    enabled: true,
    wallpaperChange: "wallpaper --path '$1' --screen '$2' --again '$1'",
  });

  executeWallpaperHook(ctx, "/tmp/wallpaper.jpg", "HDMI-A-1");

  assert.deepEqual(ctx.Quickshell.commands, [[
    "sh",
    "-c",
    "wallpaper --path '/tmp/wallpaper.jpg' --screen 'HDMI-A-1' --again '/tmp/wallpaper.jpg'",
  ]]);
  assert.match(ctx.Logger.debug[0][1], /Executed wallpaper hook/);
}

function testWallpaperHookUsesEmptyScreenFallbackAndLogsErrors() {
  const executeWallpaperHook = qmlFunction("executeWallpaperHook", "wallpaperPath", "screenName");
  const ctx = createContext({
    enabled: true,
    wallpaperChange: "wallpaper '$1' '$2'",
  });
  ctx.Quickshell.execDetached = () => {
    throw new Error("spawn failed");
  };

  executeWallpaperHook(ctx, "/tmp/wallpaper.jpg", null);

  assert.match(ctx.Logger.errors[0][1], /Failed to execute wallpaper hook/);
  assert.match(ctx.Logger.errors[0][1], /spawn failed/);
}

function testDarkModeHookSkipsMissingDisabledAndBlankScripts() {
  const executeDarkModeHook = qmlFunction("executeDarkModeHook", "isDarkMode");

  for (const hooks of [null, { enabled: false, darkModeChange: "echo $1" }, { enabled: true, darkModeChange: "" }]) {
    const ctx = createContext(hooks);
    executeDarkModeHook(ctx, true);
    assert.deepEqual(ctx.Quickshell.commands, []);
  }
}

function testDarkModeHookSubstitutesBooleanState() {
  const executeDarkModeHook = qmlFunction("executeDarkModeHook", "isDarkMode");
  const ctx = createContext({
    enabled: true,
    darkModeChange: "dark-mode $1",
  });

  executeDarkModeHook(ctx, true);
  executeDarkModeHook(ctx, false);

  assert.deepEqual(ctx.Quickshell.commands, [
    ["sh", "-c", "dark-mode true"],
    ["sh", "-c", "dark-mode false"],
  ]);
}

const tests = [
  testWallpaperHookSkipsMissingDisabledAndBlankScripts,
  testWallpaperHookSubstitutesPathAndScreen,
  testWallpaperHookUsesEmptyScreenFallbackAndLogsErrors,
  testDarkModeHookSkipsMissingDisabledAndBlankScripts,
  testDarkModeHookSubstitutesBooleanState,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
