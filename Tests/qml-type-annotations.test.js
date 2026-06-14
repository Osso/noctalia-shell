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

const tests = [
  testSliderCutoutColorsAreTyped,
  testPopupAnchorItemsAreTyped,
  testTooltipTargetItemIsTyped,
  testTooltipServiceCallsUseTargetItemFirst,
  testTooltipServiceTracksTypedTooltipInstances,
  testSmartPanelButtonItemIsTyped,
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
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
