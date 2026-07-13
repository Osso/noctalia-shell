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
  assert.match(source, /readonly property Item audioPanelPlaceholder: audioPanelLoader\.item \? audioPanelLoader\.item\.panelRegion : audioPanelPlaceholderItem/, "audio panel background placeholder must not force panel loading");
  assert.match(source, /readonly property Item settingsPanelPlaceholder: settingsPanelLoader\.item \? settingsPanelLoader\.item\.panelRegion : settingsPanelPlaceholderItem/, "settings panel background placeholder must not force panel loading");
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
