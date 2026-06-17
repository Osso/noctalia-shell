#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const aboutTabSource = readQml("Modules/Panels/Settings/Tabs/AboutTab.qml");
const batterySettingsSource = readQml("Modules/Panels/Settings/Bar/WidgetSettings/BatterySettings.qml");
const changelogSource = readQml("Modules/Panels/Changelog/ChangelogPanel.qml");
const clockSettingsSource = readQml("Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml");
const scrollViewSource = readQml("Widgets/NScrollView.qml");
const wallhavenPopupSource = readQml("Modules/Panels/Wallpaper/WallhavenSettingsPopup.qml");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testAboutTabFetchGitCommitSkipsMissingShellDir() {
  const fetchGitCommit = qmlFunction(aboutTabSource, "fetchGitCommit");
  const messages = [];
  const ctx = {
    Quickshell: { shellDir: "" },
    Logger: {
      d(...args) {
        messages.push(args);
      },
    },
    gitProcess: {
      workingDirectory: "unchanged",
      running: false,
    },
  };

  fetchGitCommit(ctx);

  assert.equal(ctx.gitProcess.workingDirectory, "unchanged");
  assert.equal(ctx.gitProcess.running, false);
  assert.equal(messages.length, 2);
}

function testAboutTabFetchGitCommitStartsProcessInShellDir() {
  const fetchGitCommit = qmlFunction(aboutTabSource, "fetchGitCommit");
  const ctx = {
    Quickshell: { shellDir: "/tmp/noctalia-shell" },
    Logger: {
      d() {},
    },
    gitProcess: {
      workingDirectory: "",
      running: false,
    },
  };

  fetchGitCommit(ctx);

  assert.equal(ctx.gitProcess.workingDirectory, "/tmp/noctalia-shell");
  assert.equal(ctx.gitProcess.running, true);
}

function testBatterySettingsBuildDeviceModelFiltersLinePowerDevices() {
  const buildDeviceModel = qmlFunction(batterySettingsSource, "buildDeviceModel");
  const ctx = {
    I18n: {
      tr(key) {
        return key;
      },
    },
    UPowerDeviceType: {
      LinePower: "line-power",
    },
    UPower: {
      devices: {
        values: [
          { type: "battery", model: "Laptop Battery", nativePath: "/bat0" },
          { type: "line-power", model: "AC Adapter", nativePath: "/ac" },
          { type: "mouse", nativePath: "/mouse" },
          null,
        ],
      },
    },
  };

  assert.deepEqual(buildDeviceModel(ctx), [
    { key: "", name: "bar.widget-settings.battery.device.default" },
    { key: "/bat0", name: "Laptop Battery" },
    { key: "/mouse", name: "/mouse" },
  ]);
  assert.deepEqual(buildDeviceModel({ ...ctx, UPower: { devices: null } }), [
    { key: "", name: "bar.widget-settings.battery.device.default" },
  ]);
}

function testChangelogFormatReleaseDateHandlesEmptyInvalidAndValidDates() {
  const formatReleaseDate = qmlFunction(changelogSource, "formatReleaseDate", "dateString");
  const ctx = {
    Qt: {
      DefaultLocaleLongDate: "long-date",
      formatDate(date, format) {
        assert.equal(format, "long-date");
        return `formatted:${date.toISOString().slice(0, 10)}`;
      },
    },
  };

  assert.equal(formatReleaseDate(ctx, ""), "");
  assert.equal(formatReleaseDate(ctx, "not-a-date"), "not-a-date");
  assert.equal(formatReleaseDate(ctx, "2026-06-16T12:00:00Z"), "formatted:2026-06-16");
}

function testClockSettingsInsertTokenDefaultsToHorizontalInput() {
  assert.match(clockSettingsSource, /function insertToken\(token: string\)/, "ClockSettings insertToken must type token input");
  const insertToken = qmlFunction(clockSettingsSource, "insertToken", "token");
  const inputItem = {
    cursorPosition: 5,
    text: "time ",
    focus: false,
  };
  const ctx = {
    focusedInput: null,
    inputHoriz: {
      inputItem,
    },
  };

  insertToken(ctx, "{date}");

  assert.equal(ctx.focusedInput, ctx.inputHoriz);
  assert.equal(inputItem.text, "time {date} ");
  assert.equal(inputItem.cursorPosition, 12);
  assert.equal(inputItem.focus, true);
}

function testWallhavenSettingsUpdateResolutionSetsModeAndOptionalSearch() {
  const updateResolution = qmlFunction(wallhavenPopupSource, "updateResolution", "triggerSearch");
  const searchCalls = [];
  const ctx = {
    Settings: {
      data: {
        wallpaper: {
          wallhavenResolutionWidth: "1920",
          wallhavenResolutionHeight: "1080",
          wallhavenResolutionMode: "exact",
          useWallhaven: true,
          wallhavenQuery: "forest",
        },
      },
    },
    WallhavenService: {
      minResolution: "old-min",
      resolutions: "old-resolution",
      search(query, page) {
        searchCalls.push([query, page]);
      },
    },
  };

  updateResolution(ctx, true);

  assert.equal(ctx.WallhavenService.minResolution, "");
  assert.equal(ctx.WallhavenService.resolutions, "1920x1080");
  assert.deepEqual(searchCalls, [["forest", 1]]);

  ctx.Settings.data.wallpaper.wallhavenResolutionWidth = "";
  updateResolution(ctx, false);
  assert.equal(ctx.WallhavenService.minResolution, "");
  assert.equal(ctx.WallhavenService.resolutions, "");
  assert.deepEqual(searchCalls, [["forest", 1]]);
}

function testScrollViewConfigureFlickableUpdatesOnlyFlickableChildren() {
  const configureFlickable = qmlFunction(scrollViewSource, "configureFlickable");
  const flickable = {
    width: 640,
    boundsBehavior: "old",
    flickableDirection: "old-direction",
    contentWidth: null,
    toString() {
      return "QQuickFlickable";
    },
  };
  const ctx = {
    children: [
      {
        toString() {
          return "Rectangle";
        },
      },
      flickable,
    ],
    root: {
      boundsBehavior: "stop-at-bounds",
      preventHorizontalScroll: true,
      flickableDirection: "auto",
    },
    Flickable: {
      VerticalFlick: "vertical",
    },
    Qt: {
      binding(callback) {
        return callback();
      },
    },
  };

  configureFlickable(ctx);

  assert.equal(flickable.boundsBehavior, "stop-at-bounds");
  assert.equal(flickable.flickableDirection, "vertical");
  assert.equal(flickable.contentWidth, 640);
}

const tests = [
  testAboutTabFetchGitCommitSkipsMissingShellDir,
  testAboutTabFetchGitCommitStartsProcessInShellDir,
  testBatterySettingsBuildDeviceModelFiltersLinePowerDevices,
  testChangelogFormatReleaseDateHandlesEmptyInvalidAndValidDates,
  testClockSettingsInsertTokenDefaultsToHorizontalInput,
  testWallhavenSettingsUpdateResolutionSetsModeAndOptionalSearch,
  testScrollViewConfigureFlickableUpdatesOnlyFlickableChildren,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
