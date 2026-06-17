#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/UI/WallpaperService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testWallpaperServiceInitializationAndModels() {
  const initBody = extractFunctionBody(source, "init");
  const translateBody = extractFunctionBody(source, "translateModels");
  const fillModeBody = extractFunctionBody(source, "getFillModeUniform");

  assert.match(initBody, /Logger\.i\("Wallpaper", "Service started"\)/, "init must log service startup");
  assert.match(initBody, /translateModels\(\)/, "init must translate UI models");
  assert.match(initBody, /Qt\.callLater\(\(\) =>[\s\S]*wallpaperCacheFile = Settings\.cacheDir \+ "wallpapers\.json"[\s\S]*wallpaperCacheView\.path = wallpaperCacheFile/, "init must defer cache path setup until Settings is available");
  assert.match(initBody, /Qt\.callLater\(refreshWallpapersList\)/, "init must schedule an initial wallpaper scan");
  assert.match(translateBody, /if \(!I18n\.isLoaded\)[\s\S]*Qt\.callLater\(translateModels\)[\s\S]*return;/, "translateModels must retry until translations are ready");
  assert.match(translateBody, /"key": "center"[\s\S]*"uniform": 0\.0/, "translateModels must include center fill mode");
  assert.match(translateBody, /"key": "crop"[\s\S]*"uniform": 1\.0/, "translateModels must include crop fill mode");
  assert.match(translateBody, /"key": "fit"[\s\S]*"uniform": 2\.0/, "translateModels must include fit fill mode");
  assert.match(translateBody, /"key": "stretch"[\s\S]*"uniform": 3\.0/, "translateModels must include stretch fill mode");
  assert.match(translateBody, /"key": "none"[\s\S]*"key": "random"[\s\S]*"key": "fade"[\s\S]*"key": "disc"[\s\S]*"key": "stripes"[\s\S]*"key": "wipe"/, "translateModels must include all transition modes");
  assert.match(fillModeBody, /for \(var i = 0; i < fillModeModel\.count; i\+\+\)/, "getFillModeUniform must scan the fill mode model");
  assert.match(fillModeBody, /if \(mode\.key === Settings\.data\.wallpaper\.fillMode\)[\s\S]*return mode\.uniform/, "getFillModeUniform must return the configured uniform value");
  assert.match(fillModeBody, /return 1\.0/, "getFillModeUniform must fall back to crop");
}

function testWallpaperServiceMonitorAndWallpaperSelection() {
  const configBody = extractFunctionBody(source, "getMonitorConfig");
  const changeBody = extractFunctionBody(source, "changeWallpaper");
  const setBody = extractFunctionBody(source, "_setWallpaper");

  assert.match(configBody, /var monitors = Settings\.data\.wallpaper\.monitorDirectories/, "getMonitorConfig must read monitor directory settings");
  assert.match(configBody, /if \(monitors !== undefined\)[\s\S]*for \(var i = 0; i < monitors\.length; i\+\+\)/, "getMonitorConfig must tolerate missing monitor config");
  assert.match(configBody, /if \(monitors\[i\]\.name !== undefined && monitors\[i\]\.name === screenName\)[\s\S]*return monitors\[i\]/, "getMonitorConfig must return the named monitor config");
  assert.match(changeBody, /if \(screenName !== undefined\)[\s\S]*_setWallpaper\(screenName, path\)/, "changeWallpaper must update a single named screen");
  assert.match(changeBody, /for \(var i = 0; i < Quickshell\.screens\.length; i\+\+\)[\s\S]*_setWallpaper\(Quickshell\.screens\[i\]\.name, path\)/, "changeWallpaper must update all screens when no screen is specified");
  assert.match(setBody, /if \(path === "" \|\| path === undefined\)[\s\S]*return;/, "_setWallpaper must reject empty paths");
  assert.match(setBody, /if \(screenName === undefined\)[\s\S]*Logger\.w\("Wallpaper", "setWallpaper", "no screen specified"\)[\s\S]*return;/, "_setWallpaper must reject missing screen names");
  assert.match(setBody, /var oldPath = currentWallpapers\[screenName\] \|\| ""[\s\S]*var wallpaperChanged = \(oldPath !== path\)/, "_setWallpaper must detect real wallpaper changes");
  assert.match(setBody, /if \(!wallpaperChanged\)[\s\S]*return;/, "_setWallpaper must avoid redundant updates");
  assert.match(setBody, /currentWallpapers\[screenName\] = path[\s\S]*saveTimer\.restart\(\)/, "_setWallpaper must update and persist cache state");
  assert.match(setBody, /root\.wallpaperChanged\(screenName, path\)/, "_setWallpaper must emit wallpaper change signals");
  assert.match(setBody, /if \(randomWallpaperTimer\.running\)[\s\S]*randomWallpaperTimer\.restart\(\)/, "_setWallpaper must restart active random timers");
}

function testWallpaperServiceRandomWallpaperFlow() {
  const randomBody = extractFunctionBody(source, "setRandomWallpaper");
  const toggleBody = extractFunctionBody(source, "toggleRandomWallpaper");
  const restartBody = extractFunctionBody(source, "restartRandomWallpaperTimer");
  const listBody = extractFunctionBody(source, "getWallpapersList");

  assert.match(randomBody, /if \(Settings\.data\.wallpaper\.enableMultiMonitorDirectories\)/, "setRandomWallpaper must branch for multi-monitor directories");
  assert.match(randomBody, /for \(var i = 0; i < Quickshell\.screens\.length; i\+\+\)[\s\S]*var screenName = Quickshell\.screens\[i\]\.name[\s\S]*var wallpaperList = getWallpapersList\(screenName\)/, "setRandomWallpaper must select per-screen lists");
  assert.match(randomBody, /Math\.floor\(Math\.random\(\) \* wallpaperList\.length\)[\s\S]*changeWallpaper\(randomPath, screenName\)/, "setRandomWallpaper must choose a random per-screen wallpaper");
  assert.match(randomBody, /var wallpaperList = getWallpapersList\(Screen\.name\)[\s\S]*changeWallpaper\(randomPath, undefined\)/, "setRandomWallpaper must choose one wallpaper for all screens in single-directory mode");
  assert.match(toggleBody, /if \(Settings\.data\.wallpaper\.randomEnabled\)[\s\S]*restartRandomWallpaperTimer\(\)[\s\S]*setRandomWallpaper\(\)/, "toggleRandomWallpaper must restart and immediately randomize when enabled");
  assert.match(restartBody, /if \(Settings\.data\.wallpaper\.randomEnabled\)[\s\S]*randomWallpaperTimer\.restart\(\)/, "restartRandomWallpaperTimer must only run when random mode is enabled");
  assert.match(listBody, /if \(screenName != undefined && wallpaperLists\[screenName\] != undefined\)[\s\S]*return wallpaperLists\[screenName\]/, "getWallpapersList must return cached lists for known screens");
  assert.match(listBody, /return \[\]/, "getWallpapersList must fail closed for unknown screens");
}

function testWallpaperServiceRefreshAndRecursiveScan() {
  const refreshBody = extractFunctionBody(source, "refreshWallpapersList");
  const scanBody = extractFunctionBody(source, "scanDirectoryRecursive");

  assert.match(refreshBody, /scanningCount = 0/, "refreshWallpapersList must reset scan count");
  assert.match(refreshBody, /if \(Settings\.data\.wallpaper\.recursiveSearch\)[\s\S]*for \(var i = 0; i < Quickshell\.screens\.length; i\+\+\)[\s\S]*scanDirectoryRecursive\(screenName, directory\)/, "refreshWallpapersList must start recursive scans per screen");
  assert.match(refreshBody, /for \(var i = 0; i < wallpaperScanners\.count; i\+\+\)[\s\S]*var scanner = wallpaperScanners\.objectAt\(i\)/, "refreshWallpapersList must refresh FolderListModel scanners in non-recursive mode");
  assert.match(refreshBody, /s\.currentDirectory = "\/tmp"[\s\S]*Qt\.callLater\(function \(\)[\s\S]*s\.currentDirectory = directory/, "refreshWallpapersList must force FolderListModel rescans");
  assert.match(scanBody, /if \(!directory \|\| directory === ""\)[\s\S]*wallpaperLists\[screenName\] = \[\][\s\S]*wallpaperListChanged\(screenName, 0\)[\s\S]*return;/, "scanDirectoryRecursive must fail closed for empty directories");
  assert.match(scanBody, /if \(recursiveProcesses\[screenName\]\)[\s\S]*recursiveProcesses\[screenName\]\.running = false[\s\S]*recursiveProcesses\[screenName\]\.destroy\(\)[\s\S]*delete recursiveProcesses\[screenName\][\s\S]*scanningCount--/, "scanDirectoryRecursive must cancel existing scans for the screen");
  assert.match(scanBody, /scanningCount\+\+/, "scanDirectoryRecursive must increment active scan count");
  assert.match(scanBody, /command: \["find", "-L", "` \+ directory \+ `", "-type", "f"/, "scanDirectoryRecursive must use find for recursive image discovery");
  assert.match(scanBody, /"-iname", "\*\.jpg"[\s\S]*"-iname", "\*\.jpeg"[\s\S]*"-iname", "\*\.png"[\s\S]*"-iname", "\*\.gif"[\s\S]*"-iname", "\*\.pnm"[\s\S]*"-iname", "\*\.bmp"/, "scanDirectoryRecursive must include supported image extensions");
  assert.match(scanBody, /recursiveProcesses\[screenName\] = processObject/, "scanDirectoryRecursive must keep process references alive");
  assert.match(scanBody, /if \(exitCode === 0\)[\s\S]*var lines = processObject\.stdout\.text\.split\('\\n'\)[\s\S]*files\.sort\(\)[\s\S]*wallpaperLists\[screenName\] = files[\s\S]*wallpaperListChanged\(screenName, files\.length\)/, "scanDirectoryRecursive must parse, sort, cache, and signal successful scans");
  assert.match(scanBody, /else[\s\S]*wallpaperLists\[screenName\] = \[\][\s\S]*wallpaperListChanged\(screenName, 0\)/, "scanDirectoryRecursive must clear lists after failed scans");
  assert.match(scanBody, /delete recursiveProcesses\[screenName\][\s\S]*processObject\.destroy\(\)/, "scanDirectoryRecursive must clean up process references");
  assert.match(scanBody, /processObject\.exited\.connect\(handler\)[\s\S]*processObject\.running = true/, "scanDirectoryRecursive must connect and start the process");
}

function testWallpaperServiceLookupHelpersExecute() {
  const getFillModeUniform = qmlFunction("getFillModeUniform");
  const getMonitorConfig = qmlFunction("getMonitorConfig", "screenName");
  const getWallpapersList = qmlFunction("getWallpapersList", "screenName");
  const fillModes = [
    { key: "center", uniform: 0 },
    { key: "crop", uniform: 1 },
    { key: "fit", uniform: 2 },
  ];
  const ctx = {
    fillModeModel: {
      count: fillModes.length,
      get(index) {
        return fillModes[index];
      },
    },
    Settings: {
      data: {
        wallpaper: {
          fillMode: "fit",
          monitorDirectories: [
            { name: "eDP-1", path: "/wallpapers/laptop" },
            { name: "HDMI-A-1", path: "/wallpapers/external" },
          ],
        },
      },
    },
    wallpaperLists: {
      "HDMI-A-1": ["/a.jpg", "/b.jpg"],
    },
  };

  assert.equal(getFillModeUniform(ctx), 2, "getFillModeUniform must return the configured mode uniform");
  ctx.Settings.data.wallpaper.fillMode = "missing";
  assert.equal(getFillModeUniform(ctx), 1, "getFillModeUniform must fall back to crop uniform");
  assert.deepEqual(getMonitorConfig(ctx, "HDMI-A-1"), { name: "HDMI-A-1", path: "/wallpapers/external" }, "getMonitorConfig must return named monitor config");
  assert.equal(getMonitorConfig(ctx, "DP-1"), undefined, "getMonitorConfig must return undefined for unknown screens");
  assert.deepEqual(getWallpapersList(ctx, "HDMI-A-1"), ["/a.jpg", "/b.jpg"], "getWallpapersList must return cached screen lists");
  assert.deepEqual(getWallpapersList(ctx, "DP-1"), [], "getWallpapersList must fail closed for unknown screens");
}

function testWallpaperServiceMonitorConfigUsesTypedScreenName() {
  assert.match(source, /function getMonitorConfig\(screenName: string\)/, "getMonitorConfig must type the screen name input");
  assert.match(source, /function setMonitorDirectory\(screenName: string, directory: string\)/, "setMonitorDirectory must type screen and directory inputs");
  assert.match(source, /function changeWallpaper\(path: string, screenName\)/, "changeWallpaper must type the required path input while keeping screen optional");
  assert.match(source, /function _setWallpaper\(screenName: string, path: string\)/, "_setWallpaper must type screen and path inputs");
  assert.match(source, /function scanDirectoryRecursive\(screenName: string, directory: string\)/, "scanDirectoryRecursive must type screen and directory inputs");
}

function testWallpaperServiceRandomWallpaperExecutesScreenSelection() {
  const setRandomWallpaper = qmlFunction("setRandomWallpaper");
  const changes = [];
  const ctx = {
    Logger: { d() {} },
    Math: Object.assign(Object.create(Math), {
      random() {
        return 0.75;
      },
    }),
    Settings: {
      data: {
        wallpaper: {
          enableMultiMonitorDirectories: true,
        },
      },
    },
    Quickshell: {
      screens: [{ name: "eDP-1" }, { name: "HDMI-A-1" }],
    },
    getWallpapersList(screenName) {
      return screenName === "eDP-1" ? ["/laptop-a.jpg", "/laptop-b.jpg"] : [];
    },
    changeWallpaper(path, screenName) {
      changes.push({ path, screenName });
    },
  };

  setRandomWallpaper(ctx);
  assert.deepEqual(changes, [{ path: "/laptop-b.jpg", screenName: "eDP-1" }], "setRandomWallpaper must randomize screens that have cached wallpapers");

  ctx.Settings.data.wallpaper.enableMultiMonitorDirectories = false;
  ctx.Screen = { name: "primary" };
  ctx.getWallpapersList = screenName => screenName === "primary" ? ["/shared-a.jpg", "/shared-b.jpg"] : [];
  setRandomWallpaper(ctx);
  assert.deepEqual(changes[1], { path: "/shared-b.jpg", screenName: undefined }, "single-directory random mode must update all screens through undefined screenName");
}

const tests = [
  testWallpaperServiceInitializationAndModels,
  testWallpaperServiceMonitorAndWallpaperSelection,
  testWallpaperServiceRandomWallpaperFlow,
  testWallpaperServiceRefreshAndRecursiveScan,
  testWallpaperServiceLookupHelpersExecute,
  testWallpaperServiceMonitorConfigUsesTypedScreenName,
  testWallpaperServiceRandomWallpaperExecutesScreenSelection,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
