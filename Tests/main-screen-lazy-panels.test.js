#!/usr/bin/env node

const assert = require("assert/strict");
const { readQml } = require("./qml-test-utils");

function testMainScreenRegistersLazyPanelLoaders() {
  const source = readQml("Modules/MainScreen/MainScreen.qml");

  assert.match(source, /function registerLazyPanel\(panelName, loader\)/, "MainScreen must centralize lazy panel registration");
  assert.match(source, /PanelService\.registerPanelLoader\(panelObjectName\(panelName\), loader\)/, "MainScreen must register panel loaders with PanelService");
  assert.match(source, /readonly property Item audioPanelPlaceholder: audioPanelLoader\.item \? audioPanelLoader\.item\.panelRegion : audioPanelPlaceholderItem/, "audio panel background placeholder must not force panel loading");
  assert.match(source, /readonly property Item settingsPanelPlaceholder: settingsPanelLoader\.item \? settingsPanelLoader\.item\.panelRegion : settingsPanelPlaceholderItem/, "settings panel background placeholder must not force panel loading");
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
  testMainScreenPanelsAreLazyLoaders,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
