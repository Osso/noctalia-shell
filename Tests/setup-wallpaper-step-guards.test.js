#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/SetupWizard/SetupWallpaperStep.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testSetupWallpaperStepCopiesWallpaperListToFilteredList() {
  const updateFilteredWallpapers = qmlFunction("updateFilteredWallpapers");
  const wallpapers = ["/walls/a.png", "/walls/b.jpg"];
  const ctx = {
    wallpapersList: wallpapers,
    filteredWallpapers: [],
  };

  updateFilteredWallpapers(ctx);

  assert.equal(ctx.filteredWallpapers, wallpapers);
}

function testSetupWallpaperStepRefreshClearsEmptyDirectory() {
  const refreshWallpapers = qmlFunction("refreshWallpapers");
  const ctx = {
    selectedDirectory: "",
    wallpapersList: ["old"],
    filteredWallpapers: ["old"],
  };

  refreshWallpapers(ctx);

  assert.deepEqual(ctx.wallpapersList, []);
  assert.deepEqual(ctx.filteredWallpapers, []);
}

function testSetupWallpaperStepRefreshUsesWallpaperServiceAndSelectsFirstWallpaper() {
  const refreshWallpapers = qmlFunction("refreshWallpapers");
  let updateCalls = 0;
  const ctx = {
    selectedDirectory: "/walls",
    selectedWallpaper: "",
    wallpapersList: [],
    filteredWallpapers: [],
    Screen: {
      name: "HDMI-A-1",
    },
    WallpaperService: {
      getWallpapersList(screenName) {
        assert.equal(screenName, "HDMI-A-1");
        return ["/walls/a.png", "/walls/b.jpg"];
      },
    },
    updateFilteredWallpapers() {
      updateCalls += 1;
      this.filteredWallpapers = this.wallpapersList;
    },
  };

  refreshWallpapers(ctx);

  assert.deepEqual(ctx.wallpapersList, ["/walls/a.png", "/walls/b.jpg"]);
  assert.equal(ctx.filteredWallpapers, ctx.wallpapersList);
  assert.equal(ctx.selectedWallpaper, "/walls/a.png");
  assert.equal(updateCalls, 1);
}

function testSetupWallpaperStepRefreshFallsBackToDirectoryScanner() {
  const refreshWallpapers = qmlFunction("refreshWallpapers");
  const readCalls = [];
  const ctx = {
    selectedDirectory: "/manual-walls",
    selectedWallpaper: "",
    wallpapersList: [],
    filteredWallpapers: [],
    WallpaperService: {},
    readDirectoryImages(directoryPath) {
      readCalls.push(directoryPath);
      return [];
    },
  };

  refreshWallpapers(ctx);

  assert.deepEqual(readCalls, ["/manual-walls"]);
}

function testSetupWallpaperStepReadDirectoryImagesStartsScannerCommand() {
  const readDirectoryImages = qmlFunction("readDirectoryImages", "directoryPath");
  const ctx = {
    directoryScanner: {
      command: [],
      running: false,
    },
  };

  assert.deepEqual(readDirectoryImages(ctx, "/walls"), []);
  assert.deepEqual(ctx.directoryScanner.command, [
    "find",
    "/walls",
    "-type",
    "f",
    "\\(-iname",
    "*.jpg",
    "-o",
    "-iname",
    "*.jpeg",
    "-o",
    "-iname",
    "*.png",
    "-o",
    "-iname",
    "*.bmp",
    "-o",
    "-iname",
    "*.webp",
    "-o",
    "-iname",
    "*.svg",
    "\\)",
  ]);
  assert.equal(ctx.directoryScanner.running, true);
}

function testSetupWallpaperStepReadDirectoryImagesUsesTypedDirectoryPath() {
  assert.match(source, /function readDirectoryImages\(directoryPath: string\)/, "readDirectoryImages must type the directory path input");
}

const tests = [
  testSetupWallpaperStepCopiesWallpaperListToFilteredList,
  testSetupWallpaperStepRefreshClearsEmptyDirectory,
  testSetupWallpaperStepRefreshUsesWallpaperServiceAndSelectsFirstWallpaper,
  testSetupWallpaperStepRefreshFallsBackToDirectoryScanner,
  testSetupWallpaperStepReadDirectoryImagesStartsScannerCommand,
  testSetupWallpaperStepReadDirectoryImagesUsesTypedDirectoryPath,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
