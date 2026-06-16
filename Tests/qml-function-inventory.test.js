#!/usr/bin/env node

const assert = require("assert/strict");
const { readQml } = require("./qml-test-utils");

const requiredFunctionDeclarations = [
  ["Modules/Background/Background.qml", "calculateOptimalWallpaperSize"],
  ["Modules/Background/Background.qml", "recalculateImageSizes"],
  ["Modules/Background/Background.qml", "setWallpaperInitial"],
  ["Modules/Background/Background.qml", "setWallpaperImmediate"],
  ["Modules/Background/Background.qml", "setWallpaperWithTransition"],
  ["Modules/Background/Background.qml", "changeWallpaper"],
  ["Modules/Background/Background.qml", "performStartupTransition"],
  ["Modules/Background/Overview.qml", "setWallpaperInitial"],
  ["Modules/Dock/Dock.qml", "closeAllContextMenus"],
  ["Modules/Dock/Dock.qml", "normalizeAppId"],
  ["Modules/Dock/Dock.qml", "isAppIdPinned"],
  ["Modules/Dock/Dock.qml", "getAppNameFromDesktopEntry"],
  ["Modules/Dock/Dock.qml", "updateDockApps"],
  ["Modules/LockScreen/LockScreen.qml", "findBluetoothBatteryDevice"],
  ["Modules/MainScreen/AllScreens.qml", "screenHasBar"],
  ["Modules/Notification/Notification.qml", "triggerEntryAnimation"],
  ["Modules/Notification/Notification.qml", "animateOut"],
  ["Modules/OSD/OSD.qml", "getCurrentValue"],
  ["Modules/OSD/OSD.qml", "getMaxValue"],
  ["Modules/OSD/OSD.qml", "getDisplayPercentage"],
  ["Modules/OSD/OSD.qml", "getProgressColor"],
  ["Modules/OSD/OSD.qml", "getIconColor"],
  ["Modules/OSD/OSD.qml", "isTypeEnabled"],
  ["Modules/OSD/OSD.qml", "hideOSD"],
  ["Modules/OSD/OSD.qml", "calculateMargin"],
  ["Modules/Panels/Launcher/Launcher.qml", "normalizeAppId"],
  ["Modules/Panels/Launcher/Launcher.qml", "togglePin"],
  ["Modules/Panels/Settings/Bar/BarWidgetSettingsDialog.qml", "findFirstFocusable"],
  ["Modules/Panels/Wallpaper/WallhavenSettingsPopup.qml", "getCategoryValue"],
  ["Modules/Panels/Wallpaper/WallhavenSettingsPopup.qml", "updateCategories"],
  ["Modules/Panels/Wallpaper/WallpaperPanel.qml", "updateWallhavenResolution"],
  ["Modules/Panels/Wallpaper/WallpaperPanel.qml", "updateFiltered"],
  ["Modules/Panels/Wallpaper/WallpaperPanel.qml", "refreshWallpaperScreenData"],
  ["Modules/Panels/Wallpaper/WallpaperPanel.qml", "wallhavenDownloadAndApply"],
  ["Modules/Toast/ToastScreen.qml", "showToast"],
  ["Services/Hardware/BrightnessService.qml", "publishBrightnessUpdate"],
  ["Services/Hardware/BrightnessService.qml", "refreshBrightnessFromSystem"],
  ["Services/Hardware/BrightnessService.qml", "setBrightnessDebounced"],
  ["Services/Hardware/BrightnessService.qml", "setBrightness"],
  ["Services/Hardware/BrightnessService.qml", "initBrightness"],
  ["Widgets/NColorPickerDialog.qml", "updateColor"],
  ["Widgets/NSectionEditor.qml", "instantiateAndOpen"],
];

function assertFunctionDeclaration(relativePath, functionName) {
  const source = readQml(relativePath);
  const declaration = new RegExp(`\\bfunction\\s+${functionName}\\s*\\(`);

  assert.match(source, declaration, `${relativePath} must keep function ${functionName}`);
}

function testQmlFunctionInventoryHasCoverageAnchors() {
  for (const [relativePath, functionName] of requiredFunctionDeclarations) {
    assertFunctionDeclaration(relativePath, functionName);
  }
}

const tests = [
  testQmlFunctionInventoryHasCoverageAnchors,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
