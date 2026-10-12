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
  const getFillModeUniform = qmlFunction("getFillModeUniform");

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
  const modes = [
    { key: "center", uniform: 0 },
    { key: "crop", uniform: 1 },
    { key: "fit", uniform: 2 },
  ];
  const ctx = {
    fillModeModel: { count: modes.length, get: index => modes[index] },
    Settings: { data: { wallpaper: { fillMode: "fit" } } },
  };
  assert.equal(getFillModeUniform(ctx), 2, "lookup must reach later fill modes");
  ctx.Settings.data.wallpaper.fillMode = "missing";
  assert.equal(getFillModeUniform(ctx), 1, "unknown fill modes use crop");
  ctx.fillModeModel.count = 0;
  assert.equal(getFillModeUniform(ctx), 1, "empty models use crop");
}

function testWallpaperServiceMonitorAndWallpaperSelection() {
  const getMonitorConfig = qmlFunction("getMonitorConfig", "screenName");
  const changeWallpaper = qmlFunction("changeWallpaper", "path", "screenName");
  const setBody = extractFunctionBody(source, "_setWallpaper");

  const monitors = [{ directory: "/unnamed" }, { name: "HDMI-A-1", directory: "/external" }];
  const changes = [];
  const ctx = {
    Settings: { data: { wallpaper: { monitorDirectories: monitors } } },
    Quickshell: { screens: [{ name: "eDP-1" }, { name: "HDMI-A-1" }] },
    _setWallpaper: (screenName, path) => changes.push({ screenName, path }),
  };
  assert.equal(getMonitorConfig(ctx, "HDMI-A-1"), monitors[1]);
  assert.equal(getMonitorConfig(ctx, "unknown"), undefined);
  ctx.Settings.data.wallpaper.monitorDirectories = undefined;
  assert.equal(getMonitorConfig(ctx, "HDMI-A-1"), undefined);
  changeWallpaper(ctx, "/single.jpg", "HDMI-A-1");
  changeWallpaper(ctx, "/shared.jpg", undefined);
  assert.deepEqual(changes, [
    { screenName: "HDMI-A-1", path: "/single.jpg" },
    { screenName: "eDP-1", path: "/shared.jpg" },
    { screenName: "HDMI-A-1", path: "/shared.jpg" },
  ]);
  assert.match(setBody, /if \(path === "" \|\| path === undefined\)[\s\S]*return;/, "_setWallpaper must reject empty paths");
  assert.match(setBody, /if \(screenName === undefined\)[\s\S]*Logger\.w\("Wallpaper", "setWallpaper", "no screen specified"\)[\s\S]*return;/, "_setWallpaper must reject missing screen names");
  assert.match(setBody, /var oldPath = currentWallpapers\[screenName\] \|\| ""[\s\S]*var wallpaperChanged = \(oldPath !== path\)/, "_setWallpaper must detect real wallpaper changes");
  assert.match(setBody, /if \(!wallpaperChanged\)[\s\S]*return;/, "_setWallpaper must avoid redundant updates");
  assert.match(setBody, /currentWallpapers\[screenName\] = path[\s\S]*saveTimer\.restart\(\)/, "_setWallpaper must update and persist cache state");
  assert.match(setBody, /root\.wallpaperChanged\(screenName, path\)/, "_setWallpaper must emit wallpaper change signals");
  assert.match(setBody, /if \(randomWallpaperTimer\.running\)[\s\S]*randomWallpaperTimer\.restart\(\)/, "_setWallpaper must restart active random timers");
}

function testWallpaperServiceRandomWallpaperFlow() {
  const setRandomWallpaper = qmlFunction("setRandomWallpaper");
  const toggleBody = extractFunctionBody(source, "toggleRandomWallpaper");
  const restartBody = extractFunctionBody(source, "restartRandomWallpaperTimer");
  const listBody = extractFunctionBody(source, "getWallpapersList");

  const changes = [];
  const ctx = {
    Settings: { data: { wallpaper: { enableMultiMonitorDirectories: true } } },
    Quickshell: { screens: [{ name: "first" }, { name: "second" }] },
    Logger: { d() {} },
    Math: Object.assign(Object.create(Math), { random: () => 0.75 }),
    getWallpapersList: name => [`/${name}-a.jpg`, `/${name}-b.jpg`],
    changeWallpaper: (path, screenName) => changes.push({ path, screenName }),
  };
  setRandomWallpaper(ctx);
  assert.deepEqual(changes, [
    { path: "/first-b.jpg", screenName: "first" },
    { path: "/second-b.jpg", screenName: "second" },
  ], "random selection must process every screen's own list");
  ctx.Settings.data.wallpaper.enableMultiMonitorDirectories = false;
  ctx.Screen = { name: "primary" };
  setRandomWallpaper(ctx);
  assert.deepEqual(changes[2], { path: "/primary-b.jpg", screenName: undefined });
  assert.match(toggleBody, /if \(Settings\.data\.wallpaper\.randomEnabled\)[\s\S]*restartRandomWallpaperTimer\(\)[\s\S]*setRandomWallpaper\(\)/, "toggleRandomWallpaper must restart and immediately randomize when enabled");
  assert.match(restartBody, /if \(Settings\.data\.wallpaper\.randomEnabled\)[\s\S]*randomWallpaperTimer\.restart\(\)/, "restartRandomWallpaperTimer must only run when random mode is enabled");
  assert.match(listBody, /if \(screenName != undefined && wallpaperLists\[screenName\] != undefined\)[\s\S]*return wallpaperLists\[screenName\]/, "getWallpapersList must return cached lists for known screens");
  assert.match(listBody, /return \[\]/, "getWallpapersList must fail closed for unknown screens");
}

function testWallpaperServiceRefreshAndRecursiveScan() {
  const refreshWallpapersList = qmlFunction("refreshWallpapersList");
  const scanBody = extractFunctionBody(source, "scanDirectoryRecursive");

  const scans = [];
  const deferred = [];
  const scanners = [
    { screenName: "first", currentDirectory: "/old-first" },
    null,
    { screenName: "second", currentDirectory: "/old-second" },
  ];
  const ctx = {
    scanningCount: 9,
    Settings: { data: { wallpaper: { recursiveSearch: true } } },
    Quickshell: { screens: [{ name: "first" }, { name: "second" }] },
    Logger: { d() {} },
    getMonitorDirectory: name => `/wallpapers/${name}`,
    scanDirectoryRecursive: (name, directory) => scans.push([name, directory]),
    wallpaperScanners: { count: scanners.length, objectAt: index => scanners[index] },
    Qt: { callLater: callback => deferred.push(callback) },
  };
  ctx.root = ctx;
  refreshWallpapersList(ctx);
  assert.equal(ctx.scanningCount, 0);
  assert.deepEqual(scans, [["first", "/wallpapers/first"], ["second", "/wallpapers/second"]]);
  assert.equal(deferred.length, 0);
  ctx.Settings.data.wallpaper.recursiveSearch = false;
  ctx.scanningCount = 7;
  refreshWallpapersList(ctx);
  assert.equal(ctx.scanningCount, 0);
  assert.equal(scans.length, 2, "non-recursive refresh must not spawn recursive scans");
  assert.deepEqual(scanners.filter(Boolean).map(scanner => scanner.currentDirectory), ["/tmp", "/tmp"]);
  assert.equal(deferred.length, 2);
  deferred[1]();
  assert.equal(scanners[2].currentDirectory, "/wallpapers/second");
  assert.equal(scanners[0].currentDirectory, "/tmp", "deferred scanner state must stay isolated");
  deferred[0]();
  assert.equal(scanners[0].currentDirectory, "/wallpapers/first");
  assert.match(scanBody, /if \(!directory \|\| directory === ""\)[\s\S]*wallpaperLists\[screenName\] = \[\][\s\S]*wallpaperListChanged\(screenName, 0\)[\s\S]*return;/, "scanDirectoryRecursive must fail closed for empty directories");
  assert.match(scanBody, /if \(recursiveProcesses\[screenName\]\)[\s\S]*recursiveProcesses\[screenName\]\.running = false[\s\S]*recursiveProcesses\[screenName\]\.destroy\(\)[\s\S]*delete recursiveProcesses\[screenName\][\s\S]*scanningCount--/, "scanDirectoryRecursive must cancel existing scans for the screen");
  assert.match(scanBody, /scanningCount\+\+/, "scanDirectoryRecursive must increment active scan count");
  assert.match(scanBody, /command: \["find", "-L", "` \+ directory \+ `", "-type", "f"/, "scanDirectoryRecursive must use find for recursive image discovery");
  assert.match(scanBody, /"-iname", "\*\.jpg"[\s\S]*"-iname", "\*\.jpeg"[\s\S]*"-iname", "\*\.png"[\s\S]*"-iname", "\*\.gif"[\s\S]*"-iname", "\*\.pnm"[\s\S]*"-iname", "\*\.bmp"/, "scanDirectoryRecursive must include supported image extensions");
  assert.match(scanBody, /recursiveProcesses\[screenName\] = processObject/, "scanDirectoryRecursive must keep process references alive");
  const scanDirectoryRecursive = qmlFunction("scanDirectoryRecursive", "screenName", "directory");
  const signals = [];
  const processes = [];
  const scanCtx = {
    scanningCount: 0,
    recursiveProcesses: {},
    wallpaperLists: {},
    wallpaperListChanged: (name, count) => signals.push([name, count]),
    Logger: { d() {}, i() {}, w() {} },
    Qt: {
      createComponent() { return {}; },
      createQmlObject(qml, owner, name) {
        assert.equal(owner, scanCtx);
        assert.ok(name.startsWith("RecursiveScan_"));
        const process = {
          running: false,
          destroyed: false,
          stdout: { text: " /z.png\n\n/a.jpg \n" },
          exited: { connect(handler) { process.finish = handler; } },
          destroy() { this.destroyed = true; },
        };
        processes.push(process);
        return process;
      },
    },
  };
  scanCtx.root = scanCtx;
  scanDirectoryRecursive(scanCtx, "first", "/wallpapers/first");
  assert.equal(scanCtx.scanningCount, 1);
  assert.equal(processes[0].running, true);
  assert.equal(scanCtx.recursiveProcesses.first, processes[0]);
  processes[0].finish(0);
  assert.deepEqual(scanCtx.wallpaperLists.first, ["/a.jpg", "/z.png"]);
  assert.deepEqual(signals, [["first", 2]]);
  assert.equal(scanCtx.scanningCount, 0);
  assert.deepEqual(scanCtx.recursiveProcesses, {});
  assert.equal(processes[0].destroyed, true);

  scanDirectoryRecursive(scanCtx, "first", "/wallpapers/first");
  processes[1].finish(1);
  assert.deepEqual(scanCtx.wallpaperLists.first, []);
  assert.deepEqual(signals.at(-1), ["first", 0]);
  assert.equal(scanCtx.scanningCount, 0);
  assert.deepEqual(scanCtx.recursiveProcesses, {});
  assert.equal(processes[1].destroyed, true);
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
  assert.match(source, /function getMonitorConfig\(screenName\)/, "getMonitorConfig must type the screen name input");
  assert.match(source, /function getMonitorDirectory\(screenName\)/, "getMonitorDirectory must type the screen name input");
  assert.match(source, /function setMonitorDirectory\(screenName, directory\)/, "setMonitorDirectory must type screen and directory inputs");
  assert.match(source, /function getWallpaper\(screenName\)/, "getWallpaper must type the screen name input");
  assert.match(source, /function changeWallpaper\(path, screenName\)/, "changeWallpaper must type the required path input while keeping screen optional");
  assert.match(source, /function _setWallpaper\(screenName, path\)/, "_setWallpaper must type screen and path inputs");
  assert.match(source, /function getWallpapersList\(screenName\)/, "getWallpapersList must type the screen name input");
  assert.match(source, /function scanDirectoryRecursive\(screenName, directory\)/, "scanDirectoryRecursive must type screen and directory inputs");
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
