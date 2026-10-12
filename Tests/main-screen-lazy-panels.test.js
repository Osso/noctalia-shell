#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const mainScreenSource = readQml("Modules/MainScreen/MainScreen.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(mainScreenSource, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testMainScreenRegistersLazyPanelLoaders() {
  const source = readQml("Modules/MainScreen/MainScreen.qml");

  assert.match(source, /function registerLazyPanel\(panelName, loader\)/, "MainScreen must centralize lazy panel registration");
  assert.match(source, /const panelKey = panelObjectName\(panelName\)[\s\S]*PanelService\.registerPanelLoader\(panelKey, loader\)/, "MainScreen must register panel loaders with PanelService");
  assert.match(source, /Component\.onDestruction: root\.unregisterLazyPanels\(\)/, "MainScreen must unregister its lazy loaders during destruction");
  for (const panelName of ["audio", "settings"]) {
    const declaration = source.split("\n").find(line => line.includes(` ${panelName}PanelPlaceholder:`));
    assert.ok(declaration, `${panelName} placeholder binding must exist`);
    const binding = declaration.slice(declaration.indexOf(":") + 1);
    const evaluate = new Function("ctx", `with (ctx) { return (${binding}); }`);
    const placeholder = { name: `${panelName}-placeholder` };
    const loader = { active: false, item: null };
    const ctx = {
      [`${panelName}PanelLoader`]: loader,
      [`${panelName}PanelPlaceholderItem`]: placeholder,
    };
    assert.equal(evaluate(ctx), placeholder, "unloaded panels expose their placeholder");
    assert.equal(loader.active, false, "reading placeholder must not activate loader");
    const region = { name: `${panelName}-loaded-region` };
    loader.item = { panelRegion: region };
    assert.equal(evaluate(ctx), region, "loaded panels expose their own region");
    loader.item = null;
    assert.equal(evaluate(ctx), placeholder, "unloaded panels return to their placeholder");
    assert.equal(loader.active, false);
  }
}

function testMainScreenRegistersAndUnregistersLazyLoaders() {
  const registerLazyPanel = qmlFunction("registerLazyPanel", "panelName", "loader");
  const unregisterLazyPanels = qmlFunction("unregisterLazyPanels");
  const registrations = [];
  const removals = [];
  const ctx = {
    registeredLazyPanels: [],
    panelObjectName(name) {
      return `${name}-eDP-1`;
    },
    PanelService: {
      registerPanelLoader(key, loader) {
        registrations.push({ key, loader });
      },
      unregisterPanelLoader(key, loader) {
        removals.push({ key, loader });
      },
    },
  };
  const audioLoader = { id: "audio" };
  const clockLoader = { id: "clock" };

  registerLazyPanel(ctx, "audioPanel", audioLoader);
  registerLazyPanel(ctx, "clockPanel", clockLoader);
  unregisterLazyPanels(ctx);
  unregisterLazyPanels(ctx);

  assert.deepEqual(registrations, [
    { key: "audioPanel-eDP-1", loader: audioLoader },
    { key: "clockPanel-eDP-1", loader: clockLoader },
  ]);
  assert.deepEqual(removals, registrations);
  assert.deepEqual(ctx.registeredLazyPanels, []);
}

function testMainScreenLazyPanelLoadersFillContainer() {
  const source = readQml("Modules/MainScreen/MainScreen.qml");
  const loaderIds = [
    "audioPanelLoader",
    "batteryPanelLoader",
    "bluetoothPanelLoader",
    "brightnessPanelLoader",
    "controlCenterPanelLoader",
    "changelogPanelLoader",
    "clockPanelLoader",
    "launcherPanelLoader",
    "notificationHistoryPanelLoader",
    "sessionMenuPanelLoader",
    "settingsPanelLoader",
    "setupWizardPanelLoader",
    "trayDrawerPanelLoader",
    "wallpaperPanelLoader",
    "wifiPanelLoader",
    "vpnPanelLoader",
    "processPanelLoader",
  ];

  for (const loaderId of loaderIds) {
    assert.match(source, new RegExp(`Loader\\s*\\{[\\s\\S]*id: ${loaderId}[\\s\\S]*anchors\\.fill: parent[\\s\\S]*sourceComponent:`), `${loaderId} must fill the panel container so loaded SmartPanel children have non-zero parent dimensions`);
  }
}

function testMainScreenPanelsAreLazyLoaders() {
  const source = readQml("Modules/MainScreen/MainScreen.qml");
  const panelNames = [
    "AudioPanel",
    "BatteryPanel",
    "BluetoothPanel",
    "BrightnessPanel",
    "ControlCenterPanel",
    "ChangelogPanel",
    "ClockPanel",
    "Launcher",
    "NotificationHistoryPanel",
    "SessionMenu",
    "SettingsPanel",
    "SetupWizard",
    "TrayDrawerPanel",
    "WallpaperPanel",
    "WiFiPanel",
    "VPNPanel",
    "ProcessPanel",
  ];

  for (const panelName of panelNames) {
    assert.doesNotMatch(source, new RegExp(`\\n\\s*${panelName}\\s*\\{\\s*\\n\\s*id:`), `${panelName} must not be directly instantiated at MainScreen startup`);
  }

  assert.match(source, /Loader\s*\{[\s\S]*id: audioPanelLoader[\s\S]*active: false[\s\S]*sourceComponent: AudioPanel/, "AudioPanel must be behind an inactive Loader");
  assert.match(source, /Loader\s*\{[\s\S]*id: settingsPanelLoader[\s\S]*active: false[\s\S]*sourceComponent: SettingsPanel/, "SettingsPanel must be behind an inactive Loader");
  assert.match(source, /Loader\s*\{[\s\S]*id: processPanelLoader[\s\S]*active: false[\s\S]*sourceComponent: ProcessPanel/, "ProcessPanel must be behind an inactive Loader");
}

const tests = [
  testMainScreenRegistersLazyPanelLoaders,
  testMainScreenRegistersAndUnregistersLazyLoaders,
  testMainScreenLazyPanelLoadersFillContainer,
  testMainScreenPanelsAreLazyLoaders,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
