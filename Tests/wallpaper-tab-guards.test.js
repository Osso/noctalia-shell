#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Tabs/WallpaperTab.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext(randomIntervalSec = 300) {
  return {
    customForcedVisible: true,
    Settings: {
      data: {
        wallpaper: {
          randomIntervalSec,
        },
      },
    },
    WallpaperService: {
      restartCount: 0,
      restartRandomWallpaperTimer() {
        this.restartCount += 1;
      },
    },
  };
}

function testSetIntervalSecondsPersistsPresetRestartsTimerAndHidesCustom() {
  const setIntervalSeconds = qmlFunction("setIntervalSeconds", "sec");
  const ctx = createContext(300);

  setIntervalSeconds(ctx, 900);

  assert.equal(ctx.Settings.data.wallpaper.randomIntervalSec, 900);
  assert.equal(ctx.WallpaperService.restartCount, 1);
  assert.equal(ctx.customForcedVisible, false);
}

function testIsSelectedMatchesCurrentIntervalOnly() {
  const isSelected = qmlFunction("isSelected", "sec");
  const ctx = createContext(1800);

  assert.equal(isSelected(ctx, 1800), true);
  assert.equal(isSelected(ctx, 900), false);
}

const tests = [
  testSetIntervalSecondsPersistsPresetRestartsTimerAndHidesCustom,
  testIsSelectedMatchesCurrentIntervalOnly,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
