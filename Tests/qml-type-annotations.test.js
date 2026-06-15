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

function testSettingsPanelTabsDelegatesAreTyped() {
  const source = readQml("Modules/Panels/Settings/SettingsPanel.qml");
  const sidebarDelegate = /NListView\s*\{[\s\S]*?model:\s*root\.tabsModel[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+icon[\s\S]*?required\s+property\s+string\s+label[\s\S]*?icon:\s*tabItem\.icon[\s\S]*?text:\s*I18n\.tr\(tabItem\.label\)/;
  const contentDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.tabsModel[\s\S]*?delegate:\s*Loader\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?active:\s*index\s*===\s*root\.currentTabIndex/;

  assert.match(source, sidebarDelegate, "SettingsPanel sidebar tab delegate must type scalar roles");
  assert.match(source, contentDelegate, "SettingsPanel content loader delegate must declare index role");
  assert.doesNotMatch(source, /modelData\.(?:icon|label)/, "SettingsPanel tab delegates must use typed roles instead of modelData.*");
  assert.doesNotMatch(source, /delegate:\s*Loader\s*\{[\s\S]*?required\s+property\s+var\s+modelData/, "SettingsPanel content loader must not keep unused modelData");
}

function testComboBoxDelegateParentIsTyped() {
  assertPropertyType("Widgets/NComboBox.qml", "parentComboBox", "ComboBox");
}

function testComboBoxDelegateIndexIsTyped() {
  const source = readQml("Widgets/NComboBox.qml");
  const delegateIndex = /delegate:\s*ItemDelegate\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?property\s+int\s+itemIndex:\s*index/;

  assert.match(source, delegateIndex, "NComboBox delegate must declare index role before using it");
}

function testWeatherCardForecastDelegateIndexIsTyped() {
  const source = readQml("Modules/Cards/WeatherCard.qml");
  const forecastDelegate = /Repeater\s*\{[\s\S]*?model:\s*weatherReady\s*\?[\s\S]*?delegate:\s*ColumnLayout\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?daily\.time\[index\]/;

  assert.match(source, forecastDelegate, "WeatherCard forecast delegate must declare index role before reading forecast arrays");
}

function testLockScreenForecastDelegateIndexIsTyped() {
  const source = readQml("Modules/LockScreen/LockScreen.qml");
  const forecastDelegate = /Repeater\s*\{[\s\S]*?model:\s*MediaService\.currentPlayer\s*&&\s*MediaService\.canPlay\s*\?\s*3\s*:\s*4[\s\S]*?delegate:\s*ColumnLayout\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?daily\.time\[index\]/;

  assert.match(source, forecastDelegate, "LockScreen forecast delegate must declare index role before reading forecast arrays");
}

function testChangelogPanelHighlightDelegatesAreTyped() {
  const source = readQml("Modules/Panels/Changelog/ChangelogPanel.qml");
  const highlightDelegate = /Repeater\s*\{[\s\S]*?model:\s*releaseHighlights[\s\S]*?delegate:\s*ColumnLayout\s*\{[\s\S]*?required\s+property\s+var\s+entries[\s\S]*?model:\s*entries/;
  const entryDelegate = /Repeater\s*\{[\s\S]*?model:\s*entries[\s\S]*?delegate:\s*NText\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?headingLevel\(modelData\)/;

  assert.match(source, highlightDelegate, "ChangelogPanel highlight delegate must type entries role");
  assert.match(source, entryDelegate, "ChangelogPanel entry delegate must type string modelData");
  assert.doesNotMatch(source, /modelData\.entries/, "ChangelogPanel highlight delegate must use typed entries role instead of modelData.entries");
}

function testNotificationDelegateIndexIsTyped() {
  const source = readQml("Modules/Notification/Notification.qml");
  const notificationDelegate = /Repeater\s*\{[\s\S]*?model:\s*notificationModel[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?animationDelay:\s*index\s*\*\s*100/;

  assert.match(source, notificationDelegate, "Notification card delegate must declare index role before using it for animation delay");
}

function testWallpaperTabIntervalPresetModelDataIsTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/WallpaperTab.qml");
  const intervalPresetDelegate = /Repeater\s*\{[\s\S]*?model:\s*presetRow\.intervalPresets[\s\S]*?delegate:\s*IntervalPresetChip\s*\{[\s\S]*?required\s+property\s+int\s+modelData[\s\S]*?seconds:\s*modelData/;

  assert.match(source, intervalPresetDelegate, "WallpaperTab interval preset delegate must type numeric modelData");
}

function testLauncherResultDelegatesAreTyped() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const listDelegate = /NListView\s*\{[\s\S]*?model:\s*results[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*entry[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?index\s*===\s*selectedIndex/;
  const gridDelegate = /GridView\s*\{[\s\S]*?model:\s*results[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*gridEntry[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?index\s*===\s*selectedIndex/;

  assert.match(source, listDelegate, "Launcher list result delegate must declare modelData and index roles");
  assert.match(source, gridDelegate, "Launcher grid result delegate must declare modelData and index roles");
}

function testDateTimeTokenDelegateRolesAreTyped() {
  const source = readQml("Widgets/NDateTimeTokens.qml");
  const tokenDelegate = /delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*tokenDelegate[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+category[\s\S]*?required\s+property\s+string\s+token[\s\S]*?required\s+property\s+string\s+description[\s\S]*?root\.tokenClicked\(token\)[\s\S]*?getCategoryColor\(category\)[\s\S]*?text:\s*description[\s\S]*?toString\(root\.sampleDate,\s*token\)/;

  assert.match(source, tokenDelegate, "NDateTimeTokens delegate must type scalar token roles");
  assert.doesNotMatch(source, /required\s+property\s+var\s+modelData/, "NDateTimeTokens delegate must not keep unused modelData");
  assert.doesNotMatch(source, /modelData\.(?:category|token|description)/, "NDateTimeTokens delegate must use typed roles instead of modelData.*");
}

function testSetupCustomizeOptionDelegatesAreTyped() {
  const source = readQml("Modules/Panels/SetupWizard/SetupCustomizeStep.qml");
  const barPositionDelegate = /model:\s*\[[\s\S]*?"key":\s*"left"[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+string\s+key[\s\S]*?required\s+property\s+string\s+name[\s\S]*?selectedBarPosition\s*===\s*key[\s\S]*?text:\s*name[\s\S]*?barPositionChanged\(key\)/;
  const densityDelegate = /model:\s*\[[\s\S]*?"key":\s*"comfortable"[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+string\s+key[\s\S]*?required\s+property\s+string\s+name[\s\S]*?Settings\.data\.bar\.density\s*===\s*key[\s\S]*?text:\s*name[\s\S]*?Settings\.data\.bar\.density\s*=\s*key/;

  assert.match(source, barPositionDelegate, "SetupCustomizeStep bar position delegate must type key/name roles");
  assert.match(source, densityDelegate, "SetupCustomizeStep density delegate must type key/name roles");
  assert.doesNotMatch(source, /modelData\.(?:key|name)/, "SetupCustomizeStep option delegates must use typed roles instead of modelData.*");
}

function testColorPickerSwatchDelegatesAreTyped() {
  const source = readQml("Widgets/NColorPickerDialog.qml");
  const themeSwatchDelegate = /model:\s*\[[\s\S]*?name:\s*"mPrimary"[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+swatchName:\s*modelData\.name[\s\S]*?readonly\s+property\s+color\s+swatchColor:\s*modelData\.color[\s\S]*?color:\s*swatchColor/;
  const paletteSwatchDelegate = /Repeater\s*\{[\s\S]*?model:\s*ColorList\.colors[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+swatchName:\s*modelData\.name[\s\S]*?readonly\s+property\s+color\s+swatchColor:\s*modelData\.color[\s\S]*?color:\s*swatchColor/;

  assert.match(source, themeSwatchDelegate, "NColorPickerDialog theme swatch delegate must declare typed swatch aliases");
  assert.match(source, paletteSwatchDelegate, "NColorPickerDialog palette swatch delegate must declare typed swatch aliases");

  const dynamicSwatchFieldReads = source
    .match(/modelData\.(?:name|color)/g)
    ?? [];
  assert.deepEqual(dynamicSwatchFieldReads, [
    "modelData.name",
    "modelData.color",
    "modelData.name",
    "modelData.color",
  ], "NColorPickerDialog swatch bindings must use typed local aliases after declaration");
}

function testSetupAppearanceSchemeLoaderModelDataIsTyped() {
  const source = readQml("Modules/Panels/SetupWizard/SetupAppearanceStep.qml");
  const schemeLoaderDelegate = /Repeater\s*\{[\s\S]*?model:\s*ColorSchemeService\.schemes[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?path:\s*modelData/;
  const materialSchemeDelegate = /model:\s*\[[\s\S]*?"key":\s*"scheme-tonal-spot"[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+string\s+key[\s\S]*?required\s+property\s+string\s+name[\s\S]*?matugenSchemeType\s*===\s*key[\s\S]*?text:\s*name[\s\S]*?matugenSchemeType\s*=\s*key/;

  assert.match(source, schemeLoaderDelegate, "SetupAppearanceStep scheme loader delegate must type string modelData");
  assert.match(source, materialSchemeDelegate, "SetupAppearanceStep material scheme delegate must type key/name roles");
  assert.doesNotMatch(source, /modelData\.(?:key|name)/, "SetupAppearanceStep material scheme delegate must use typed roles instead of modelData.*");
}

function testFilePickerDelegatesUseTypedFileRoles() {
  const source = readQml("Widgets/NFilePicker.qml");
  const gridDelegate = /GridView\s*\{[\s\S]*?model:\s*filteredModel[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*gridItem[\s\S]*?required\s+property\s+string\s+fileName[\s\S]*?required\s+property\s+string\s+filePath[\s\S]*?required\s+property\s+bool\s+fileIsDir[\s\S]*?required\s+property\s+int\s+fileSize[\s\S]*?currentSelection\.includes\(filePath\)/;
  const listDelegate = /NListView\s*\{[\s\S]*?model:\s*filteredModel[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*listItem[\s\S]*?required\s+property\s+string\s+fileName[\s\S]*?required\s+property\s+string\s+filePath[\s\S]*?required\s+property\s+bool\s+fileIsDir[\s\S]*?required\s+property\s+int\s+fileSize[\s\S]*?currentSelection\.includes\(filePath\)/;

  assert.match(source, gridDelegate, "NFilePicker grid delegate must declare file roles");
  assert.match(source, listDelegate, "NFilePicker list delegate must declare file roles");
  assert.doesNotMatch(source, /model\.file(?:Name|Path|IsDir|Size)/, "NFilePicker delegates must use typed file role properties instead of model.*");
}

function testTaskbarWindowDelegateRolesAreTyped() {
  const source = readQml("Modules/Bar/Widgets/Taskbar.qml");
  const taskbarDelegate = /Repeater\s*\{[\s\S]*?model:\s*CompositorService\.windows[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+appId[\s\S]*?required\s+property\s+string\s+title[\s\S]*?required\s+property\s+string\s+output[\s\S]*?required\s+property\s+int\s+workspaceId[\s\S]*?required\s+property\s+bool\s+isFocused/;

  assert.match(source, taskbarDelegate, "Taskbar window delegate must type scalar window roles");
  assert.doesNotMatch(source, /modelData\.(?:appId|title|output|workspaceId|isFocused)/, "Taskbar window delegate must use typed scalar roles instead of modelData.* field reads");
}

function testShortcutsCardShortcutIdsAreTyped() {
  const source = readQml("Modules/Cards/ShortcutsCard.qml");
  const leftDelegate = /model:\s*Settings\.data\.controlCenter\.shortcuts\.left[\s\S]*?delegate:\s*ControlCenterWidgetLoader\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+id[\s\S]*?widgetId:\s*id[\s\S]*?"widgetId":\s*id/;
  const rightDelegate = /model:\s*Settings\.data\.controlCenter\.shortcuts\.right[\s\S]*?delegate:\s*ControlCenterWidgetLoader\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+id[\s\S]*?widgetId:\s*id[\s\S]*?"widgetId":\s*id/;

  assert.match(source, leftDelegate, "ShortcutsCard left shortcut delegate must type id role");
  assert.match(source, rightDelegate, "ShortcutsCard right shortcut delegate must type id role");
  assert.doesNotMatch(source, /modelData\.id/, "ShortcutsCard shortcut delegates must use typed id role instead of modelData.id");
}

function testSectionEditorWidgetIdsAreTyped() {
  const source = readQml("Widgets/NSectionEditor.qml");
  const widgetDelegate = /Repeater\s*\{[\s\S]*?model:\s*widgetModel[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*widgetItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+id[\s\S]*?widgetHasUserSettings\(id\)[\s\S]*?text:\s*id[\s\S]*?"widgetId":\s*id/;

  assert.match(source, widgetDelegate, "NSectionEditor widget delegate must type id role");
  assert.doesNotMatch(source, /modelData\.id/, "NSectionEditor widget delegate must use typed id role instead of modelData.id");
}

function testSessionMenuPowerOptionRolesAreTyped() {
  const source = readQml("Modules/Panels/SessionMenu/SessionMenu.qml");
  const powerOptionDelegate = /Repeater\s*\{[\s\S]*?model:\s*powerOptions[\s\S]*?delegate:\s*PowerButton\s*\{[\s\S]*?required\s+property\s+string\s+icon[\s\S]*?required\s+property\s+string\s+title[\s\S]*?required\s+property\s+string\s+action[\s\S]*?required\s+property\s+bool\s+isShutdown[\s\S]*?startTimer\(action\)[\s\S]*?pending:\s*timerActive\s*&&\s*pendingAction\s*===\s*action/;

  assert.match(source, powerOptionDelegate, "SessionMenu power option delegate must type scalar roles");
  assert.doesNotMatch(source, /modelData\.(?:icon|title|action|isShutdown)/, "SessionMenu power option delegate must use typed roles instead of modelData.*");
}

function testCalendarMonthDayDelegateRolesAreTyped() {
  const source = readQml("Modules/Cards/CalendarMonthCard.qml");
  const dayDelegate = /Repeater\s*\{[\s\S]*?model:\s*grid\.daysModel[\s\S]*?Item\s*\{[\s\S]*?id:\s*dayCell[\s\S]*?required\s+property\s+int\s+day[\s\S]*?required\s+property\s+int\s+month[\s\S]*?required\s+property\s+int\s+year[\s\S]*?required\s+property\s+bool\s+today[\s\S]*?required\s+property\s+bool\s+currentMonth[\s\S]*?text:\s*dayCell\.day[\s\S]*?hasEventsOnDate\(dayCell\.year,\s*dayCell\.month,\s*dayCell\.day\)/;

  assert.match(source, dayDelegate, "CalendarMonthCard day delegate must type scalar date roles");
  assert.doesNotMatch(source, /modelData\.(?:day|month|year|today|currentMonth)/, "CalendarMonthCard day delegate must use typed roles instead of modelData scalar date reads");
}

function testAboutTabContributorDelegateIndexesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/AboutTab.qml");
  const topContributorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Math\.min\(root\.contributors\.length,\s*root\.topContributorsCount\)[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?root\.contributors\[index\]\.login/;
  const remainingContributorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Math\.max\(0,\s*root\.contributors\.length\s*-\s*root\.topContributorsCount\)[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?root\.contributors\[index\s*\+\s*root\.topContributorsCount\]\.login/;

  assert.match(source, topContributorDelegate, "AboutTab top contributor delegate must declare index role");
  assert.match(source, remainingContributorDelegate, "AboutTab remaining contributor delegate must declare index role");
}

function testCustomButtonStateCheckDelegateRolesAreTyped() {
  const source = readQml("Modules/Panels/Settings/ControlCenter/WidgetSettings/CustomButtonSettings.qml");
  const stateCheckDelegate = /Repeater\s*\{[\s\S]*?model:\s*_settings\._stateChecksListModel[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+string\s+command[\s\S]*?required\s+property\s+string\s+icon[\s\S]*?required\s+property\s+int\s+index[\s\S]*?property\s+int\s+currentIndex:\s*index/;

  assert.match(source, stateCheckDelegate, "CustomButtonSettings state-check delegate must type command, icon, and index roles");
  assert.doesNotMatch(source, /model\.(?:command|icon)/, "CustomButtonSettings state-check delegate must use typed role properties instead of model.*");
}

function testTraySettingsBlacklistDelegateRolesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Bar/WidgetSettings/TraySettings.qml");
  const blacklistDelegate = /ListView\s*\{[\s\S]*?model:\s*blacklistModel[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+string\s+rule[\s\S]*?required\s+property\s+int\s+index[\s\S]*?visible:\s*rule\s*!==\s*""[\s\S]*?text:\s*rule/;

  assert.match(source, blacklistDelegate, "TraySettings blacklist delegate must type rule and index roles");
  assert.doesNotMatch(source, /model\.rule/, "TraySettings blacklist delegate must use typed rule role instead of model.rule");
}

function testReorderCheckboxDelegateRolesAreTyped() {
  const source = readQml("Widgets/NReorderCheckboxes.qml");
  const checkboxDelegate = /ListView\s*\{[\s\S]*?model:\s*root\.model[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?id:\s*delegateItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+id[\s\S]*?required\s+property\s+string\s+text[\s\S]*?property\s+bool\s+itemEnabled:\s*modelData\.enabled\s*\|\|\s*false[\s\S]*?root\.disabledIds\s*\|\|\s*\[\]\)\.indexOf\(id\)[\s\S]*?color:\s*delegateItem\.itemEnabled\s*\?[\s\S]*?visible:\s*delegateItem\.itemEnabled/;

  assert.match(source, checkboxDelegate, "NReorderCheckboxes delegate must type item roles");
  assert.doesNotMatch(source, /required\s+property\s+bool\s+enabled/, "NReorderCheckboxes must not bind the enabled role to Item.enabled");
  assert.doesNotMatch(source, /modelData\.(?:id|text)/, "NReorderCheckboxes delegate must use typed roles instead of modelData.*");
}

function testSessionMenuTabEntryDelegateRolesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/SessionMenuTab.qml");
  const entryDelegate = /ListView\s*\{[\s\S]*?model:\s*entriesModel[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?id:\s*delegateItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+id[\s\S]*?required\s+property\s+string\s+text[\s\S]*?required\s+property\s+bool\s+countdownEnabled[\s\S]*?property\s+bool\s+entryEnabled:\s*modelData\.enabled\s*\|\|\s*false[\s\S]*?color:\s*delegateItem\.entryEnabled\s*\?\s*Color\.mPrimary[\s\S]*?text:\s*delegateItem\.text[\s\S]*?checked:\s*delegateItem\.countdownEnabled/;

  assert.match(source, entryDelegate, "SessionMenuTab entry delegate must type scalar roles");
  assert.doesNotMatch(source, /required\s+property\s+bool\s+enabled/, "SessionMenuTab must not bind the enabled role to Item.enabled");
  assert.doesNotMatch(source, /modelData\.(?:id|text|countdownEnabled)/, "SessionMenuTab entry delegate must use typed roles instead of modelData.*");
}

function testColorSchemeTabSchemeModelDataIsTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/ColorSchemeTab.qml");
  const fileLoaderDelegate = /Repeater\s*\{[\s\S]*?model:\s*ColorSchemeService\.schemes[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?path:\s*modelData/;
  const schemeGridDelegate = /Repeater\s*\{[\s\S]*?model:\s*ColorSchemeService\.schemes[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?property\s+string\s+schemePath:\s*modelData[\s\S]*?property\s+string\s+schemeName:\s*root\.extractSchemeName\(modelData\)/;

  assert.match(source, fileLoaderDelegate, "ColorSchemeTab file loader delegate must type string modelData");
  assert.match(source, schemeGridDelegate, "ColorSchemeTab scheme grid delegate must type string modelData");
}

function testSchemeDownloaderDelegatesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml");
  const schemeDelegate = /Repeater\s*\{[\s\S]*?model:\s*availableSchemes[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+name[\s\S]*?property\s+string\s+schemeName:\s*name[\s\S]*?root\.fetchSchemeColors\(modelData\)[\s\S]*?property\s+string\s+schemeName:\s*schemeItem\.schemeName/;
  const swatchDelegate = /Repeater\s*\{[\s\S]*?model:\s*schemeRow\.colorKeys[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?color:\s*root\.getSchemeColor\(schemeRow\.schemeName,\s*modelData\)/;

  assert.match(source, schemeDelegate, "SchemeDownloader scheme delegate must declare modelData");
  assert.match(source, swatchDelegate, "SchemeDownloader swatch delegate must type string modelData");
  assert.doesNotMatch(source, /modelData\.name/, "SchemeDownloader scheme delegate must use typed name role instead of modelData.name");
}

function testControlCenterPanelCardDelegateIsTyped() {
  const source = readQml("Modules/Panels/ControlCenter/ControlCenterPanel.qml");
  const cardDelegate = /Repeater\s*\{[\s\S]*?model:\s*Settings\.data\.controlCenter\.cards[\s\S]*?Loader\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?active:\s*modelData\.enabled[\s\S]*?switch\s*\(modelData\.id\)/;

  assert.match(source, cardDelegate, "ControlCenterPanel card delegate must declare modelData");
}

function testPanelServiceOpenedPanelIsTyped() {
  assertPropertyType("Services/UI/PanelService.qml", "openedPanel", "SmartPanel");
}

function testContextMenuDelegatePopupIsTyped() {
  assertPropertyType("Widgets/NContextMenu.qml", "popup", "Popup");
}

function testContextMenuDelegateRolesAreTyped() {
  const source = readQml("Widgets/NContextMenu.qml");
  const delegateRoles = /delegate:\s*ItemDelegate\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?height:\s*modelData\.visible[\s\S]*?popup\.triggered\(modelData\.action\s*\|\|\s*modelData\.key\s*\|\|\s*index\.toString\(\)\)/;

  assert.match(source, delegateRoles, "NContextMenu delegate must declare modelData and index roles");
}

function testGeometryReferencesAreTypedItems() {
  assertPropertyType("Modules/Bar/Bar.qml", "barItem", "Item");
  assertPropertyType("Modules/MainScreen/MainScreen.qml", "barItem", "Item");
  assertPropertyType("Modules/MainScreen/SmartPanel.qml", "panelItem", "Item");
  assertPropertyType("Modules/MainScreen/Backgrounds/PanelBackground.qml", "panelBg", "Item");
}

function testTimeNowPropertiesAreTypedDates() {
  const clockFiles = [
    "Commons/Time.qml",
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

function testControlCenterWidgetLoaderScreenIsTyped() {
  const loaderFile = "Modules/Panels/ControlCenter/ControlCenterWidgetLoader.qml";

  assertPropertyType(loaderFile, "widgetScreen", "ShellScreen");
  assertNoPropertyType(loaderFile, "widgetScreen", "var");
}

function testClockSettingsFocusedInputIsTyped() {
  const settingsFile = "Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml";

  assertPropertyType(settingsFile, "focusedInput", "NTextInput");
  assertNoPropertyType(settingsFile, "focusedInput", "var");
}

function testClockSettingsPreviewModelsAreTyped() {
  const source = readQml("Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml");
  const horizontalPreview = /model:\s*I18n\.locale\.toString\(now,\s*valueFormatHorizontal\.trim\(\)\)\.split\("\\\\n"\)[\s\S]*?delegate:\s*NText\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?text:\s*modelData/;
  const verticalPreview = /model:\s*I18n\.locale\.toString\(now,\s*valueFormatVertical\.trim\(\)\)\.split\(" "\)[\s\S]*?delegate:\s*NText\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?text:\s*modelData/;

  assert.match(source, horizontalPreview, "ClockSettings horizontal preview delegate must type string modelData");
  assert.match(source, verticalPreview, "ClockSettings vertical preview delegate must type string modelData");
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

function testDockMenuItemDelegateInputsAreTyped() {
  const source = readQml("Modules/Dock/DockMenu.qml");
  const itemDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.items[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?icon:\s*modelData\.icon[\s\S]*?text:\s*modelData\.text/;

  assert.match(source, itemDelegate, "DockMenu item delegate must declare modelData and index inputs");
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

function testBluetoothDeviceDelegateInputsAreTyped() {
  const source = readQml("Modules/Panels/Bluetooth/BluetoothDevicesList.qml");
  const deviceDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.model[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+BluetoothDevice\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?BluetoothService\.canConnect\(modelData\)/;

  assert.match(source, deviceDelegate, "BluetoothDevicesList device delegate must type modelData as BluetoothDevice and declare index");
}

function testAudioNodeHandlesAreTyped() {
  const audioServiceFile = "Services/Media/AudioService.qml";

  assertPropertyType(audioServiceFile, "sinkAudio", "PwNodeAudio");
  assertPropertyType(audioServiceFile, "sourceAudio", "PwNodeAudio");
  assertNoPropertyType(audioServiceFile, "sinkAudio", "var");
  assertNoPropertyType(audioServiceFile, "sourceAudio", "var");
}

function testAudioPanelDeviceDelegatesAreTyped() {
  const source = readQml("Modules/Panels/Audio/AudioPanel.qml");
  const sinkDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sinks[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?text:\s*modelData\.description/;
  const sourceDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sources[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?text:\s*modelData\.description/;

  assert.match(source, sinkDelegate, "AudioPanel sink delegate must type modelData and index");
  assert.match(source, sourceDelegate, "AudioPanel source delegate must type modelData and index");
}

function testProcessPanelProcessDelegateInputsAreTyped() {
  const source = readQml("Modules/Panels/Process/ProcessPanel.qml");
  const processDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.processList[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?ProcessService\.getProcessIcon\(modelData\.command\)/;

  assert.match(source, processDelegate, "ProcessPanel process delegate must declare modelData and index");
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

function testTrayMenuLoaderReferencesAreTyped() {
  const trayMenuLoaderFiles = [
    "Modules/Bar/Widgets/Tray.qml",
    "Modules/Panels/Tray/TrayDrawerPanel.qml",
  ];

  for (const trayMenuLoaderFile of trayMenuLoaderFiles) {
    assertPropertyType(trayMenuLoaderFile, "trayMenu", "Loader");
    assertNoPropertyType(trayMenuLoaderFile, "trayMenu", "var");
  }
}

function testSectionEditorRegistryIsTyped() {
  const sectionEditorFile = "Widgets/NSectionEditor.qml";

  assertPropertyType(sectionEditorFile, "widgetRegistry", "QtObject");
  assertNoPropertyType(sectionEditorFile, "widgetRegistry", "var");
}

function testDisplayTabBrightnessMonitorIsTyped() {
  const displayTabFile = "Modules/Panels/Settings/Tabs/DisplayTab.qml";

  assertPropertyType(displayTabFile, "brightnessMonitor", "QtObject");
  assertNoPropertyType(displayTabFile, "brightnessMonitor", "var");
}

function testBrightnessPanelBrightnessMonitorIsTyped() {
  const brightnessPanelFile = "Modules/Panels/Brightness/BrightnessPanel.qml";

  assertPropertyType(brightnessPanelFile, "brightnessMonitor", "QtObject");
  assertNoPropertyType(brightnessPanelFile, "brightnessMonitor", "var");
}

function testBrightnessServiceMonitorScreenModelAliasIsTyped() {
  const brightnessServiceFile = "Services/Hardware/BrightnessService.qml";
  const source = readQml(brightnessServiceFile);
  const monitorComponent = /component\s+Monitor:\s+QtObject\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+screenModel:\s+modelData\.model/;

  assert.match(source, monitorComponent, "BrightnessService Monitor must expose typed screenModel alias from ShellScreen modelData");
  assert.match(source, /root\.ddcMonitors\.some\(m\s*=>\s*m\.model\s*===\s*screenModel\)/, "BrightnessService DDC detection must use screenModel");
  assert.match(source, /root\.ddcMonitors\.find\(m\s*=>\s*m\.model\s*===\s*screenModel\)/, "BrightnessService DDC bus lookup must use screenModel");
  assert.match(source, /root\.appleDisplayPresent\s*&&\s*screenModel\.startsWith\("StudioDisplay"\)/, "BrightnessService Apple display detection must use screenModel");

  const modelReads = source.match(/modelData\.model/g) ?? [];
  assert.deepEqual(modelReads, ["modelData.model"], "BrightnessService Monitor must use screenModel after declaration");
}

function testBackgroundShapeContainersAreTyped() {
  const backgroundFiles = [
    "Modules/MainScreen/Backgrounds/BarBackground.qml",
    "Modules/MainScreen/Backgrounds/PanelBackground.qml",
  ];

  for (const backgroundFile of backgroundFiles) {
    assertPropertyType(backgroundFile, "shapeContainer", "Shape");
    assertNoPropertyType(backgroundFile, "shapeContainer", "var");
  }
}

function testWallpaperPanelScreenReferencesAreTyped() {
  const wallpaperPanelFile = "Modules/Panels/Wallpaper/WallpaperPanel.qml";

  assertPropertyType(wallpaperPanelFile, "currentScreen", "ShellScreen");
  assertPropertyType(wallpaperPanelFile, "targetScreen", "ShellScreen");
  assertNoPropertyType(wallpaperPanelFile, "currentScreen", "var");
  assertNoPropertyType(wallpaperPanelFile, "targetScreen", "var");
}

function testWallpaperPanelMonitorTabModelIsTyped() {
  const source = readQml("Modules/Panels/Wallpaper/WallpaperPanel.qml");
  const monitorTabModel = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?required\s+property\s+ShellScreen\s+modelData/;

  assert.match(source, monitorTabModel, "WallpaperPanel monitor tabs must type screen modelData as ShellScreen");
}

function testWallpaperPanelScreenViewModelIsTyped() {
  const source = readQml("Modules/Panels/Wallpaper/WallpaperPanel.qml");
  const screenViewModel = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?delegate:\s*WallpaperScreenView\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?targetScreen:\s*modelData/;

  assert.match(source, screenViewModel, "WallpaperPanel screen views must type screen modelData as ShellScreen");
}

function testSettingsMonitorModelsAreTyped() {
  const monitorSettingFiles = [
    "Modules/Panels/Settings/Tabs/BarTab.qml",
    "Modules/Panels/Settings/Tabs/DisplayTab.qml",
    "Modules/Panels/Settings/Tabs/DockTab.qml",
    "Modules/Panels/Settings/Tabs/NotificationsTab.qml",
    "Modules/Panels/Settings/Tabs/OsdTab.qml",
    "Modules/Panels/Settings/Tabs/WallpaperTab.qml",
  ];

  for (const monitorSettingFile of monitorSettingFiles) {
    const source = readQml(monitorSettingFile);
    const screenModelDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?required\s+property\s+ShellScreen\s+modelData/;

    assert.match(source, screenModelDelegate, `${monitorSettingFile} monitor delegate must type screen modelData as ShellScreen`);
  }
}

function testDockTabMonitorAliasesAreTyped() {
  const dockTabFile = "Modules/Panels/Settings/Tabs/DockTab.qml";
  const source = readQml(dockTabFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\.name[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s+modelData\.model[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s+modelData\.width[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s+modelData\.height/;

  assert.match(source, monitorDelegate, "DockTab monitor delegate must expose typed aliases for ShellScreen fields");
  assert.match(source, /label:\s*monitorName\s*\|\|\s*"Unknown"/, "DockTab monitor label must use monitorName");
  assert.match(source, /CompositorService\.getDisplayScale\(monitorName\)/, "DockTab monitor scale lookup must use monitorName");
  assert.match(source, /"model":\s*monitorModel/, "DockTab monitor description must use monitorModel");
  assert.match(source, /"width":\s*monitorWidth\s*\*\s*compositorScale/, "DockTab monitor description must use monitorWidth");
  assert.match(source, /"height":\s*monitorHeight\s*\*\s*compositorScale/, "DockTab monitor description must use monitorHeight");
  assert.match(source, /indexOf\(monitorName\)\s*!==\s*-1/, "DockTab monitor selection must use monitorName");
  assert.match(source, /addMonitor\(Settings\.data\.dock\.monitors,\s*monitorName\)/, "DockTab monitor add action must use monitorName");
  assert.match(source, /removeMonitor\(Settings\.data\.dock\.monitors,\s*monitorName\)/, "DockTab monitor remove action must use monitorName");

  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "DockTab monitor delegate must use monitorName after declaration");
  assert.equal((source.match(/modelData\.model/g) ?? []).length, 1, "DockTab monitor delegate must use monitorModel after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "DockTab monitor delegate must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "DockTab monitor delegate must use monitorHeight after declaration");
}

function testOsdTabTypeOptionRolesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/OsdTab.qml");
  const osdTypeDelegate = /Repeater\s*\{[\s\S]*?type:\s*OSD\.Type\.Volume[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+int\s+type[\s\S]*?required\s+property\s+string\s+key[\s\S]*?settings\.osd\.types\."\s*\+\s*key\s*\+\s*"\.label"[\s\S]*?enabledTypes\s*\|\|\s*\[\]\)\.includes\(type\)/;

  assert.match(source, osdTypeDelegate, "OsdTab OSD type delegate must type scalar roles");
  assert.doesNotMatch(source, /modelData\.(?:type|key)/, "OsdTab OSD type delegate must use typed roles instead of modelData.*");
}

function testOsdTabMonitorAliasesAreTyped() {
  const osdTabFile = "Modules/Panels/Settings/Tabs/OsdTab.qml";
  const source = readQml(osdTabFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\.name[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s+modelData\.model[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s+modelData\.width[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s+modelData\.height/;

  assert.match(source, monitorDelegate, "OsdTab monitor delegate must expose typed aliases for ShellScreen fields");
  assert.match(source, /label:\s*monitorName\s*\|\|\s*I18n\.tr\("system\.unknown"\)/, "OsdTab monitor label must use monitorName");
  assert.match(source, /CompositorService\.getDisplayScale\(monitorName\)/, "OsdTab monitor scale lookup must use monitorName");
  assert.match(source, /"model":\s*monitorModel/, "OsdTab monitor description must use monitorModel");
  assert.match(source, /"width":\s*monitorWidth\s*\*\s*compositorScale/, "OsdTab monitor description must use monitorWidth");
  assert.match(source, /"height":\s*monitorHeight\s*\*\s*compositorScale/, "OsdTab monitor description must use monitorHeight");
  assert.match(source, /indexOf\(monitorName\)\s*!==\s*-1/, "OsdTab monitor selection must use monitorName");
  assert.match(source, /addMonitor\(Settings\.data\.osd\.monitors,\s*monitorName\)/, "OsdTab monitor add action must use monitorName");
  assert.match(source, /removeMonitor\(Settings\.data\.osd\.monitors,\s*monitorName\)/, "OsdTab monitor remove action must use monitorName");

  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "OsdTab monitor delegate must use monitorName after declaration");
  assert.equal((source.match(/modelData\.model/g) ?? []).length, 1, "OsdTab monitor delegate must use monitorModel after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "OsdTab monitor delegate must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "OsdTab monitor delegate must use monitorHeight after declaration");
}

function testWallpaperServiceScannerModelIsTyped() {
  const source = readQml("Services/UI/WallpaperService.qml");
  const scannerModelDelegate = /Instantiator\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?required\s+property\s+ShellScreen\s+modelData/;

  assert.match(source, scannerModelDelegate, "WallpaperService scanner must type screen modelData as ShellScreen");
}

function testSetupDockStepMonitorModelIsTyped() {
  const source = readQml("Modules/Panels/SetupWizard/SetupDockStep.qml");
  const monitorModelDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?required\s+property\s+ShellScreen\s+modelData/;

  assert.match(source, monitorModelDelegate, "SetupDockStep monitor delegate must type screen modelData as ShellScreen");
}

function testSetupWizardProgressDelegateModelIsTyped() {
  const source = readQml("Modules/Panels/SetupWizard/SetupWizard.qml");
  const progressDelegate = /Repeater\s*\{[\s\S]*?"label":\s*"Dock"[\s\S]*?delegate:\s*RowLayout\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?icon:\s*modelData\.icon[\s\S]*?text:\s*modelData\.label/;

  assert.match(source, progressDelegate, "SetupWizard progress delegate must declare modelData and index roles");
}

function testBrightnessPanelScreenModelIsTyped() {
  const source = readQml("Modules/Panels/Brightness/BrightnessPanel.qml");
  const screenModelDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?required\s+property\s+ShellScreen\s+modelData/;

  assert.match(source, screenModelDelegate, "BrightnessPanel monitor delegate must type screen modelData as ShellScreen");
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
  testSettingsPanelTabsDelegatesAreTyped,
  testComboBoxDelegateParentIsTyped,
  testComboBoxDelegateIndexIsTyped,
  testWeatherCardForecastDelegateIndexIsTyped,
  testLockScreenForecastDelegateIndexIsTyped,
  testChangelogPanelHighlightDelegatesAreTyped,
  testNotificationDelegateIndexIsTyped,
  testWallpaperTabIntervalPresetModelDataIsTyped,
  testLauncherResultDelegatesAreTyped,
  testDateTimeTokenDelegateRolesAreTyped,
  testSetupCustomizeOptionDelegatesAreTyped,
  testColorPickerSwatchDelegatesAreTyped,
  testSetupAppearanceSchemeLoaderModelDataIsTyped,
  testFilePickerDelegatesUseTypedFileRoles,
  testTaskbarWindowDelegateRolesAreTyped,
  testShortcutsCardShortcutIdsAreTyped,
  testSectionEditorWidgetIdsAreTyped,
  testSessionMenuPowerOptionRolesAreTyped,
  testCalendarMonthDayDelegateRolesAreTyped,
  testAboutTabContributorDelegateIndexesAreTyped,
  testCustomButtonStateCheckDelegateRolesAreTyped,
  testTraySettingsBlacklistDelegateRolesAreTyped,
  testReorderCheckboxDelegateRolesAreTyped,
  testSessionMenuTabEntryDelegateRolesAreTyped,
  testColorSchemeTabSchemeModelDataIsTyped,
  testSchemeDownloaderDelegatesAreTyped,
  testControlCenterPanelCardDelegateIsTyped,
  testPanelServiceOpenedPanelIsTyped,
  testContextMenuDelegatePopupIsTyped,
  testContextMenuDelegateRolesAreTyped,
  testGeometryReferencesAreTypedItems,
  testTimeNowPropertiesAreTypedDates,
  testEffectSourcePropertiesAreTyped,
  testBarWidgetLoaderScreenIsTyped,
  testControlCenterWidgetLoaderScreenIsTyped,
  testClockSettingsFocusedInputIsTyped,
  testClockSettingsPreviewModelsAreTyped,
  testMangoPatternContainerIsTyped,
  testPopupMenuWindowContentItemIsTyped,
  testLauncherActivePluginIsTyped,
  testDockCurrentContextMenuIsTyped,
  testDockMenuItemDelegateInputsAreTyped,
  testLauncherPluginBackReferencesAreTyped,
  testCompositorBackendIsTyped,
  testPowerProfilesReferenceIsTyped,
  testUPowerBatteryReferencesAreTyped,
  testBluetoothDeviceDelegateInputsAreTyped,
  testAudioNodeHandlesAreTyped,
  testAudioPanelDeviceDelegatesAreTyped,
  testProcessPanelProcessDelegateInputsAreTyped,
  testTrayMenuItemIsTyped,
  testTrayMenuSubMenuIsTyped,
  testTrayMenuLoaderReferencesAreTyped,
  testSectionEditorRegistryIsTyped,
  testDisplayTabBrightnessMonitorIsTyped,
  testBrightnessPanelBrightnessMonitorIsTyped,
  testBrightnessServiceMonitorScreenModelAliasIsTyped,
  testBackgroundShapeContainersAreTyped,
  testWallpaperPanelScreenReferencesAreTyped,
  testWallpaperPanelMonitorTabModelIsTyped,
  testWallpaperPanelScreenViewModelIsTyped,
  testSettingsMonitorModelsAreTyped,
  testDockTabMonitorAliasesAreTyped,
  testOsdTabTypeOptionRolesAreTyped,
  testOsdTabMonitorAliasesAreTyped,
  testWallpaperServiceScannerModelIsTyped,
  testSetupDockStepMonitorModelIsTyped,
  testSetupWizardProgressDelegateModelIsTyped,
  testBrightnessPanelScreenModelIsTyped,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
