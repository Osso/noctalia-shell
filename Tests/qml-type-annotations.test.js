#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assertPropertyType(relativePath, propertyName, expectedType) {
  const source = readQml(relativePath);
  const declaration = new RegExp(`\\bproperty\\s+${expectedType}\\s+${propertyName}\\b`);

  assert.match(source, declaration, `${relativePath} must declare ${propertyName} as ${expectedType}`);
}

function assertNoPropertyType(relativePath, propertyName, unexpectedType) {
  const source = readQml(relativePath);
  const declaration = new RegExp(`\\bproperty\\s+${unexpectedType}\\s+${propertyName}\\b`);

  assert.doesNotMatch(source, declaration, `${relativePath} must not declare ${propertyName} as ${unexpectedType}`);
}

function testSliderCutoutColorsAreTyped() {
  const sliderFiles = [
    "Widgets/NSlider.qml",
    "Widgets/NColorSlider.qml",
    "Widgets/NValueSlider.qml",
  ];

  for (const sliderFile of sliderFiles) {
    assertPropertyType(sliderFile, "cutoutColor", "color");
  }
}

function testPopupAnchorItemsAreTyped() {
  const popupFiles = [
    "Widgets/NPopupContextMenu.qml",
    "Modules/Bar/Extras/TrayMenu.qml",
  ];

  for (const popupFile of popupFiles) {
    assertPropertyType(popupFile, "anchorItem", "Item");
  }
}

function testTooltipTargetItemIsTyped() {
  assertPropertyType("Modules/Tooltip/Tooltip.qml", "targetItem", "Item");
}

function testTooltipServiceCallsUseTargetItemFirst() {
  const callSiteFiles = [
    "Widgets/NColorSlider.qml",
    "Widgets/NColorPickerDialog.qml",
  ];

  for (const callSiteFile of callSiteFiles) {
    const source = readQml(callSiteFile);
    assert.doesNotMatch(source, /TooltipService\.show\(screen,/, `${callSiteFile} must pass the target item as the first TooltipService.show argument`);
  }
}

function testTooltipServiceTracksTypedTooltipInstances() {
  const tooltipServiceFile = "Services/UI/TooltipService.qml";

  assertPropertyType(tooltipServiceFile, "activeTooltip", "Tooltip");
  assertPropertyType(tooltipServiceFile, "pendingTooltip", "Tooltip");
}

function testSmartPanelButtonItemIsTyped() {
  assertPropertyType("Modules/MainScreen/SmartPanel.qml", "buttonItem", "Item");
}

function testSmartPanelPanelRegionIsTyped() {
  assertPropertyType("Modules/MainScreen/SmartPanel.qml", "panelRegion", "Item");
  assertNoPropertyType("Modules/MainScreen/SmartPanel.qml", "panelRegion", "var");
}

function testMainScreenPanelPlaceholdersAreTyped() {
  const placeholderNames = [
    "audioPanelPlaceholder",
    "batteryPanelPlaceholder",
    "bluetoothPanelPlaceholder",
    "brightnessPanelPlaceholder",
    "clockPanelPlaceholder",
    "changelogPanelPlaceholder",
    "controlCenterPanelPlaceholder",
    "launcherPanelPlaceholder",
    "notificationHistoryPanelPlaceholder",
    "sessionMenuPanelPlaceholder",
    "settingsPanelPlaceholder",
    "setupWizardPanelPlaceholder",
    "trayDrawerPanelPlaceholder",
    "wallpaperPanelPlaceholder",
    "wifiPanelPlaceholder",
    "vpnPanelPlaceholder",
    "processPanelPlaceholder",
  ];

  for (const placeholderName of placeholderNames) {
    assertPropertyType("Modules/MainScreen/MainScreen.qml", placeholderName, "Item");
    assertNoPropertyType("Modules/MainScreen/MainScreen.qml", placeholderName, "var");
  }
}

function testPanelContentItemsAreTyped() {
  const contentItemFiles = [
    "Modules/Panels/Wallpaper/WallpaperPanel.qml",
  ];

  for (const contentItemFile of contentItemFiles) {
    assertPropertyType(contentItemFile, "contentItem", "Item");
  }
}

function testPanelServiceLockScreenIsTyped() {
  assertPropertyType("Services/UI/PanelService.qml", "lockScreen", "Loader");
}

function testNotificationServerInstanceIsTyped() {
  assertPropertyType("Services/System/NotificationService.qml", "notificationServerLoader", "NotificationServer");
}

function testSettingsPanelActiveScrollViewIsTyped() {
  assertPropertyType("Modules/Panels/Settings/SettingsPanel.qml", "activeScrollView", "NScrollView");
}

function testComboBoxDelegateParentIsTyped() {
  assertPropertyType("Widgets/NComboBox.qml", "parentComboBox", "ComboBox");
}

function testPanelServiceOpenedPanelIsTyped() {
  assertPropertyType("Services/UI/PanelService.qml", "openedPanel", "SmartPanel");
}

function testContextMenuDelegatePopupIsTyped() {
  assertPropertyType("Widgets/NContextMenu.qml", "popup", "Popup");
}

function testGeometryReferencesAreTypedItems() {
  assertPropertyType("Modules/Bar/Bar.qml", "barItem", "Item");
  assertPropertyType("Modules/MainScreen/MainScreen.qml", "barItem", "Item");
  assertPropertyType("Modules/MainScreen/SmartPanel.qml", "panelItem", "Item");
  assertPropertyType("Modules/MainScreen/Backgrounds/PanelBackground.qml", "panelBg", "Item");
}

function testTimeNowPropertiesAreTypedDates() {
  const clockFiles = [
    "Modules/Bar/Widgets/Clock.qml",
    "Modules/Cards/CalendarHeaderCard.qml",
    "Modules/Cards/CalendarMonthCard.qml",
    "Modules/LockScreen/LockScreen.qml",
    "Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml",
    "Widgets/NClock.qml",
  ];

  for (const clockFile of clockFiles) {
    assertPropertyType(clockFile, "now", "date");
    assertNoPropertyType(clockFile, "now", "var");
  }
}

function testEffectSourcePropertiesAreTyped() {
  assertPropertyType("Modules/Cards/WeatherCard.qml", "source", "ShaderEffectSource");
  assertPropertyType("Widgets/NDropShadow.qml", "source", "Item");
}

function testBarWidgetLoaderScreenIsTyped() {
  const loaderFile = "Modules/Bar/Extras/BarWidgetLoader.qml";

  assertPropertyType(loaderFile, "widgetScreen", "ShellScreen");
  assertNoPropertyType(loaderFile, "widgetScreen", "var");
}

function testClockSettingsFocusedInputIsTyped() {
  const settingsFile = "Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml";

  assertPropertyType(settingsFile, "focusedInput", "NTextInput");
  assertNoPropertyType(settingsFile, "focusedInput", "var");
}

function testMangoPatternContainerIsTyped() {
  const mangoServiceFile = "Services/Compositor/MangoService.qml";

  assertPropertyType(mangoServiceFile, "patterns", "QtObject");
  assertNoPropertyType(mangoServiceFile, "patterns", "var");
}

function testPopupMenuWindowContentItemIsTyped() {
  const popupMenuWindowFile = "Modules/MainScreen/PopupMenuWindow.qml";

  assertPropertyType(popupMenuWindowFile, "contentItem", "QtObject");
  assertNoPropertyType(popupMenuWindowFile, "contentItem", "var");
}

function testLauncherActivePluginIsTyped() {
  const launcherFile = "Modules/Panels/Launcher/Launcher.qml";

  assertPropertyType(launcherFile, "activePlugin", "Item");
  assertNoPropertyType(launcherFile, "activePlugin", "var");
}

function testDockCurrentContextMenuIsTyped() {
  const dockFile = "Modules/Dock/Dock.qml";

  assertPropertyType(dockFile, "currentContextMenu", "DockMenu");
  assertNoPropertyType(dockFile, "currentContextMenu", "var");
}

function testLauncherPluginBackReferencesAreTyped() {
  const pluginFiles = [
    "Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml",
    "Modules/Panels/Launcher/Plugins/CalculatorPlugin.qml",
    "Modules/Panels/Launcher/Plugins/ClipboardPlugin.qml",
    "Modules/Panels/Launcher/Plugins/EmojiPlugin.qml",
  ];

  for (const pluginFile of pluginFiles) {
    assertPropertyType(pluginFile, "launcher", "Item");
    assertNoPropertyType(pluginFile, "launcher", "var");
  }
}

function testCompositorBackendIsTyped() {
  const compositorServiceFile = "Services/Compositor/CompositorService.qml";

  assertPropertyType(compositorServiceFile, "backend", "Item");
  assertNoPropertyType(compositorServiceFile, "backend", "var");
}

function testPowerProfilesReferenceIsTyped() {
  const powerProfileServiceFile = "Services/Power/PowerProfileService.qml";

  assertPropertyType(powerProfileServiceFile, "powerProfiles", "QtObject");
  assertNoPropertyType(powerProfileServiceFile, "powerProfiles", "var");
}

function testUPowerBatteryReferencesAreTyped() {
  const batteryFiles = [
    "Modules/Bar/Widgets/Battery.qml",
    "Modules/LockScreen/LockScreen.qml",
    "Modules/Panels/Battery/BatteryPanel.qml",
    "Modules/Panels/Settings/Tabs/BatteryTab.qml",
  ];

  for (const batteryFile of batteryFiles) {
    assertPropertyType(batteryFile, "battery", "UPowerDevice");
    assertNoPropertyType(batteryFile, "battery", "var");
  }
}

function testAudioNodeHandlesAreTyped() {
  const audioServiceFile = "Services/Media/AudioService.qml";

  assertPropertyType(audioServiceFile, "sinkAudio", "PwNodeAudio");
  assertPropertyType(audioServiceFile, "sourceAudio", "PwNodeAudio");
  assertNoPropertyType(audioServiceFile, "sinkAudio", "var");
  assertNoPropertyType(audioServiceFile, "sourceAudio", "var");
}

function testTrayMenuItemIsTyped() {
  const trayMenuFile = "Modules/Bar/Extras/TrayMenu.qml";

  assertPropertyType(trayMenuFile, "trayItem", "SystemTrayItem");
  assertNoPropertyType(trayMenuFile, "trayItem", "var");
}

function testTrayMenuSubMenuIsTyped() {
  const trayMenuFile = "Modules/Bar/Extras/TrayMenu.qml";

  assertPropertyType(trayMenuFile, "subMenu", "TrayMenu");
  assertNoPropertyType(trayMenuFile, "subMenu", "var");
}

function testSectionEditorRegistryIsTyped() {
  const sectionEditorFile = "Widgets/NSectionEditor.qml";

  assertPropertyType(sectionEditorFile, "widgetRegistry", "QtObject");
  assertNoPropertyType(sectionEditorFile, "widgetRegistry", "var");
}

const tests = [
  testSliderCutoutColorsAreTyped,
  testPopupAnchorItemsAreTyped,
  testTooltipTargetItemIsTyped,
  testTooltipServiceCallsUseTargetItemFirst,
  testTooltipServiceTracksTypedTooltipInstances,
  testSmartPanelButtonItemIsTyped,
  testSmartPanelPanelRegionIsTyped,
  testMainScreenPanelPlaceholdersAreTyped,
  testPanelContentItemsAreTyped,
  testPanelServiceLockScreenIsTyped,
  testNotificationServerInstanceIsTyped,
  testSettingsPanelActiveScrollViewIsTyped,
  testComboBoxDelegateParentIsTyped,
  testPanelServiceOpenedPanelIsTyped,
  testContextMenuDelegatePopupIsTyped,
  testGeometryReferencesAreTypedItems,
  testTimeNowPropertiesAreTypedDates,
  testEffectSourcePropertiesAreTyped,
  testBarWidgetLoaderScreenIsTyped,
  testClockSettingsFocusedInputIsTyped,
  testMangoPatternContainerIsTyped,
  testPopupMenuWindowContentItemIsTyped,
  testLauncherActivePluginIsTyped,
  testDockCurrentContextMenuIsTyped,
  testLauncherPluginBackReferencesAreTyped,
  testCompositorBackendIsTyped,
  testPowerProfilesReferenceIsTyped,
  testUPowerBatteryReferencesAreTyped,
  testAudioNodeHandlesAreTyped,
  testTrayMenuItemIsTyped,
  testTrayMenuSubMenuIsTyped,
  testSectionEditorRegistryIsTyped,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
