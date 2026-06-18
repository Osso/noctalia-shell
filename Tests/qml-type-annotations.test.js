#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function qmlFiles() {
  const files = [];
  const pending = [repoRoot];

  while (pending.length > 0) {
    const current = pending.pop();

    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (entry.name === ".git" || entry.name === "node_modules")
        continue;

      const fullPath = path.join(current, entry.name);

      if (entry.isDirectory()) {
        pending.push(fullPath);
      } else if (entry.isFile() && entry.name.endsWith(".qml")) {
        files.push(path.relative(repoRoot, fullPath));
      }
    }
  }

  return files.sort();
}

function testQmlFunctionSignaturesAvoidUnsupportedTypeAnnotations() {
  const annotatedFunctions = [];
  const annotatedReturns = [];

  for (const qmlFile of qmlFiles()) {
    const lines = readQml(qmlFile).split("\n");
    let inIpcHandler = false;
    let ipcDepth = 0;

    lines.forEach((line, index) => {
      const opens = (line.match(/\{/g) || []).length;
      const closes = (line.match(/\}/g) || []).length;

      if (/\bIpcHandler\s*\{/.test(line)) {
        inIpcHandler = true;
        ipcDepth = opens - closes;
        return;
      }

      if (inIpcHandler) {
        ipcDepth += opens - closes;
        if (ipcDepth <= 0)
          inIpcHandler = false;
        return;
      }

      if (/\bfunction\s+[A-Za-z_$][\w$]*\s*\([^)]*:\s*[A-Za-z_]/.test(line)
        || /\bfunction\s*\([^)]*:\s*[A-Za-z_]/.test(line)) {
        annotatedFunctions.push(`${qmlFile}:${index + 1}: ${line.trim()}`);
      }

      if (/\)\s*:\s*[A-Za-z_][A-Za-z0-9_<>]*\s*\{/.test(line)) {
        annotatedReturns.push(`${qmlFile}:${index + 1}: ${line.trim()}`);
      }
    });
  }

  assert.deepEqual(annotatedFunctions, [], "Quickshell 0.3.0 does not support JavaScript function parameter type annotations");
  assert.deepEqual(annotatedReturns, [], "Quickshell 0.3.0 does not support JavaScript function return type annotations");
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

function testPopupContextMenuOpenHelpersAreTyped() {
  const source = readQml("Widgets/NPopupContextMenu.qml");

  assert.match(source, /function\s+openAt\(x,\s*y,\s*item\)/, "NPopupContextMenu.openAt must accept coordinates and anchor item");
  assert.match(source, /function\s+openAtItem\(item,\s*mouseX,\s*mouseY\)/, "NPopupContextMenu.openAtItem must accept anchor item and mouse coordinates");
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
  const source = readQml(tooltipServiceFile);

  assertPropertyType(tooltipServiceFile, "activeTooltip", "Tooltip");
  assertPropertyType(tooltipServiceFile, "pendingTooltip", "Tooltip");
  assert.match(source, /function show\(target, text, direction, delay, fontFamily\)/, "TooltipService.show must accept target and text inputs while keeping optional display inputs flexible");
  assert.match(source, /function updateText\(newText\)/, "TooltipService.updateText must accept replacement tooltip text");
}

function testSmartPanelButtonItemIsTyped() {
  assertPropertyType("Modules/MainScreen/SmartPanel.qml", "buttonItem", "Item");
}

function testSmartPanelPanelRegionIsTyped() {
  const source = readQml("Modules/MainScreen/SmartPanel.qml");

  assertPropertyType("Modules/MainScreen/SmartPanel.qml", "panelRegion", "Item");
  assertNoPropertyType("Modules/MainScreen/SmartPanel.qml", "panelRegion", "var");
  assert.match(source, /readonly\s+property\s+Item\s+panelRegion:\s*panelBackground/, "SmartPanel panelRegion must expose panelBackground geometry for AllBackgrounds");
  assert.doesNotMatch(source, /readonly\s+property\s+Item\s+panelRegion:\s*panelContent\.maskRegion/, "SmartPanel panelRegion must not resolve through panelContent component state");
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

function testAllScreensScreenNameAliasIsTyped() {
  const source = readQml("Modules/MainScreen/AllScreens.qml");
  const screenDelegate = /Variants\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+currentScreenName:\s*modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?function\s+screenName\(\)\s*\{[\s\S]*?return\s+currentScreenName;/;

  assert.match(source, screenDelegate, "AllScreens delegate must expose a null-safe typed screen name alias");
  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "AllScreens delegate must use currentScreenName after declaration");
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

function testNotificationWatcherTargetsAreTyped() {
  const notificationServiceFile = "Services/System/NotificationService.qml";

  assertPropertyType(notificationServiceFile, "targetNotification", "Notification");
  assertPropertyType(notificationServiceFile, "targetDataId", "string");
  assertNoPropertyType(notificationServiceFile, "targetNotification", "var");
  assertNoPropertyType(notificationServiceFile, "targetDataId", "var");
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

function testMediaCardWallpaperChangeInputsAreTyped() {
  const source = readQml("Modules/Cards/MediaCard.qml");

  assert.match(source, /function onWallpaperChanged\(screenName, path\)/, "MediaCard wallpaper change handler must accept signal payloads");
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
  const notificationDelegate = /Repeater\s*\{[\s\S]*?model:\s*notificationModel[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+real\s+progress[\s\S]*?required\s+property\s+int\s+urgency[\s\S]*?required\s+property\s+string\s+appName[\s\S]*?required\s+property\s+string\s+summary[\s\S]*?required\s+property\s+string\s+body[\s\S]*?required\s+property\s+string\s+originalImage[\s\S]*?required\s+property\s+string\s+actionsJson[\s\S]*?required\s+property\s+date\s+timestamp[\s\S]*?animationDelay:\s*index\s*\*\s*100[\s\S]*?text:\s*appName\s*\|\|\s*"Unknown App"[\s\S]*?Time\.formatRelativeTime\(timestamp\)[\s\S]*?text:\s*summary\s*\|\|\s*I18n\.tr\("general\.no-summary"\)[\s\S]*?text:\s*body\s*\|\|\s*""/;

  assert.match(source, notificationDelegate, "Notification card delegate must declare typed roles before using notification fields");
  assert.doesNotMatch(source, /required\s+property\s+var\s+timestamp/, "Notification card timestamp role must use the date type");
  assert.doesNotMatch(source, /model\.(?:appName|summary|body|timestamp|urgency|originalImage|actionsJson|progress)/, "Notification card delegate must use typed roles instead of model.* display fields");
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

function testLauncherListImageAliasesAreTyped() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const listDelegate = /NListView\s*\{[\s\S]*?model:\s*results[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*entry[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+bool\s+resultIsImage:\s*modelData\s*\?\s*modelData\.isImage\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+string\s+resultEmojiChar:\s*modelData\s*\?\s*\(modelData\.emojiChar\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+resultClipboardId:\s*modelData\s*\?\s*\(modelData\.clipboardId\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+resultMime:\s*modelData\s*\?\s*\(modelData\.mime\s*\|\|\s*""\)\s*:\s*""[\s\S]*?currentClipboardId:\s*resultIsImage\s*\?\s*resultClipboardId\s*:\s*""[\s\S]*?ClipboardService\.decodeToDataUrl\(currentClipboardId,\s*resultMime,\s*null\)/;

  assert.match(source, listDelegate, "Launcher list result delegate must expose typed image/emoji aliases");
}

function testLauncherGridImageAliasesAreTyped() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const gridDelegate = /GridView\s*\{[\s\S]*?model:\s*results[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*gridEntry[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+bool\s+resultIsImage:\s*modelData\s*\?\s*modelData\.isImage\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+string\s+resultEmojiChar:\s*modelData\s*\?\s*\(modelData\.emojiChar\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+resultClipboardId:\s*modelData\s*\?\s*\(modelData\.clipboardId\s*\|\|\s*""\)\s*:\s*""[\s\S]*?visible:\s*resultIsImage\s*&&\s*!resultEmojiChar[\s\S]*?ClipboardService\.getImageData\(resultClipboardId\)[\s\S]*?visible:\s*!resultIsImage\s*&&\s*!resultEmojiChar\s*\|\|\s*\(resultIsImage\s*&&\s*gridImagePreview\.status\s*===\s*Image\.Error\)/;

  assert.match(source, gridDelegate, "Launcher grid result delegate must expose typed image/emoji aliases");
}

function testLauncherListDisplayAliasesAreTyped() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const listDelegate = /NListView\s*\{[\s\S]*?model:\s*results[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*entry[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+string\s+resultIcon:\s*modelData\s*\?\s*\(modelData\.icon\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+resultName:\s*modelData\s*\?\s*\(modelData\.name\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+resultDescription:\s*modelData\s*\?\s*\(modelData\.description\s*\|\|\s*""\)\s*:\s*""[\s\S]*?ThemeIcons\.iconFromName\(resultIcon,\s*"application-x-executable"\)[\s\S]*?resultName\.charAt\(0\)\.toUpperCase\(\)[\s\S]*?const desc = resultDescription[\s\S]*?text:\s*resultName\s*\|\|\s*"Unknown"[\s\S]*?text:\s*resultDescription/;

  assert.match(source, listDelegate, "Launcher list result delegate must expose typed display aliases");
}

function testLauncherGridDisplayAliasesAreTyped() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const gridDelegate = /GridView\s*\{[\s\S]*?model:\s*results[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*gridEntry[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+string\s+resultIcon:\s*modelData\s*\?\s*\(modelData\.icon\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+resultName:\s*modelData\s*\?\s*\(modelData\.name\s*\|\|\s*""\)\s*:\s*""[\s\S]*?ThemeIcons\.iconFromName\(resultIcon,\s*"application-x-executable"\)[\s\S]*?resultName\.charAt\(0\)\.toUpperCase\(\)[\s\S]*?text:\s*resultName\s*\|\|\s*"Unknown"/;

  assert.match(source, gridDelegate, "Launcher grid result delegate must expose typed display aliases");
}

function testDateTimeTokenDelegateRolesAreTyped() {
  const source = readQml("Widgets/NDateTimeTokens.qml");
  const tokenDelegate = /delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*tokenDelegate[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+category[\s\S]*?required\s+property\s+string\s+token[\s\S]*?required\s+property\s+string\s+description[\s\S]*?root\.tokenClicked\(token\)[\s\S]*?getCategoryColor\(category\)[\s\S]*?text:\s*description[\s\S]*?toString\(root\.sampleDate,\s*token\)/;

  assert.match(source, tokenDelegate, "NDateTimeTokens delegate must type scalar token roles");
  assert.match(source, /function getCategoryColor\(category\)/, "NDateTimeTokens category color helper must accept category input");
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
  const themeSwatchDelegate = /model:\s*\[[\s\S]*?name:\s*"mPrimary"[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+swatchName:\s*modelData\s*\?\s*\(modelData\.name\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+color\s+swatchColor:\s*modelData\s*\?\s*\(modelData\.color\s*\|\|\s*Color\.transparent\)\s*:\s*Color\.transparent[\s\S]*?color:\s*swatchColor/;
  const paletteSwatchDelegate = /Repeater\s*\{[\s\S]*?model:\s*ColorList\.colors[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+swatchName:\s*modelData\s*\?\s*\(modelData\.name\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+color\s+swatchColor:\s*modelData\s*\?\s*\(modelData\.color\s*\|\|\s*Color\.transparent\)\s*:\s*Color\.transparent[\s\S]*?color:\s*swatchColor/;

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

function testVpnConnectionRowsAreTyped() {
  const listSource = readQml("Modules/Panels/VPN/VPNConnectionsList.qml");
  const itemSource = readQml("Modules/Panels/VPN/VPNConnectionItem.qml");
  const rowDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.model[\s\S]*?VPNConnectionItem\s*\{[\s\S]*?required\s+property\s+string\s+uuid[\s\S]*?required\s+property\s+string\s+name[\s\S]*?required\s+property\s+bool\s+active[\s\S]*?connectionUuid:\s*uuid[\s\S]*?connectionName:\s*name[\s\S]*?connectionActive:\s*active/;

  assert.match(listSource, rowDelegate, "VPNConnectionsList delegate must type connection scalar roles");
  assert.doesNotMatch(listSource, /connection:\s*modelData/, "VPNConnectionsList must pass typed scalar roles instead of raw modelData");
  assertPropertyType("Modules/Panels/VPN/VPNConnectionItem.qml", "connectionUuid", "string");
  assertPropertyType("Modules/Panels/VPN/VPNConnectionItem.qml", "connectionName", "string");
  assertPropertyType("Modules/Panels/VPN/VPNConnectionItem.qml", "connectionActive", "bool");
  assert.doesNotMatch(itemSource, /connection\.(?:uuid|name|active)/, "VPNConnectionItem must use typed connection properties instead of connection.* field reads");
}

function testSectionEditorWidgetIdsAreTyped() {
  const source = readQml("Widgets/NSectionEditor.qml");
  const widgetDelegate = /Repeater\s*\{[\s\S]*?model:\s*widgetModel[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*widgetItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+id[\s\S]*?readonly\s+property\s+string\s+widgetId:\s*id[\s\S]*?widgetHasUserSettings\(widgetId\)[\s\S]*?text:\s*widgetId[\s\S]*?"widgetId":\s*widgetId/;

  assert.match(source, widgetDelegate, "NSectionEditor widget delegate must type id role");
  assert.doesNotMatch(source, /modelData\.id/, "NSectionEditor widget delegate must use typed id role instead of modelData.id");
  assert.doesNotMatch(source, /widgetHasUserSettings\(id\)|text:\s*id|"widgetId":\s*id/, "NSectionEditor widget delegate must use widgetId after declaration");
}

function testSessionMenuPowerOptionRolesAreTyped() {
  const source = readQml("Modules/Panels/SessionMenu/SessionMenu.qml");
  const powerOptionDelegate = /Repeater\s*\{[\s\S]*?model:\s*powerOptions[\s\S]*?delegate:\s*PowerButton\s*\{[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+string\s+action:\s*modelData\s*\?\s*\(modelData\.action\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+optionIsShutdown:\s*modelData\s*\?\s*modelData\.isShutdown\s*===\s*true\s*:\s*false[\s\S]*?icon:\s*modelData\s*\?\s*\(modelData\.icon\s*\|\|\s*""\)\s*:\s*""[\s\S]*?title:\s*modelData\s*\?\s*\(modelData\.title\s*\|\|\s*""\)\s*:\s*""[\s\S]*?isShutdown:\s*optionIsShutdown[\s\S]*?isSelected:\s*index\s*===\s*selectedIndex[\s\S]*?startTimer\(action\)[\s\S]*?pending:\s*timerActive\s*&&\s*pendingAction\s*===\s*action/;

  assert.match(source, powerOptionDelegate, "SessionMenu power option delegate must expose null-safe aliases from the JS object model");
}

function testCalendarMonthDayDelegateRolesAreTyped() {
  const source = readQml("Modules/Cards/CalendarMonthCard.qml");
  const dayDelegate = /Repeater\s*\{[\s\S]*?model:\s*grid\.daysModel[\s\S]*?Item\s*\{[\s\S]*?id:\s*dayCell[\s\S]*?required\s+property\s+int\s+day[\s\S]*?required\s+property\s+int\s+month[\s\S]*?required\s+property\s+int\s+year[\s\S]*?required\s+property\s+bool\s+today[\s\S]*?required\s+property\s+bool\s+currentMonth[\s\S]*?text:\s*dayCell\.day[\s\S]*?hasEventsOnDate\(dayCell\.year,\s*dayCell\.month,\s*dayCell\.day\)/;
  const weekNumberDelegate = /model:\s*parent\.weekNumbers[\s\S]*?Item\s*\{[\s\S]*?required\s+property\s+int\s+modelData[\s\S]*?text:\s*modelData/;

  assert.match(source, dayDelegate, "CalendarMonthCard day delegate must type scalar date roles");
  assert.match(source, weekNumberDelegate, "CalendarMonthCard week-number delegate must type numeric modelData");
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
  const checkboxDelegate = /ListView\s*\{[\s\S]*?model:\s*root\.model[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?id:\s*delegateItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+id[\s\S]*?required\s+property\s+string\s+text[\s\S]*?readonly\s+property\s+bool\s+itemEnabled:\s*modelData\s*\?\s*modelData\.enabled\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+required:\s*modelData\s*\?\s*modelData\.required\s*===\s*true\s*:\s*false[\s\S]*?root\.disabledIds\s*\|\|\s*\[\]\)\.indexOf\(id\)[\s\S]*?color:\s*delegateItem\.itemEnabled\s*\?[\s\S]*?visible:\s*delegateItem\.itemEnabled/;

  assert.match(source, checkboxDelegate, "NReorderCheckboxes delegate must type item roles and readonly derived flags");
  assert.doesNotMatch(source, /required\s+property\s+bool\s+enabled/, "NReorderCheckboxes must not bind the enabled role to Item.enabled");
  assert.doesNotMatch(source, /modelData\.(?:id|text)/, "NReorderCheckboxes delegate must use typed roles instead of modelData.*");
}

function testSessionMenuTabEntryDelegateRolesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/SessionMenuTab.qml");
  const entryDelegate = /ListView\s*\{[\s\S]*?model:\s*entriesModel[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?id:\s*delegateItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+id[\s\S]*?required\s+property\s+string\s+text[\s\S]*?required\s+property\s+bool\s+countdownEnabled[\s\S]*?readonly\s+property\s+bool\s+entryEnabled:\s*modelData\s*\?\s*modelData\.enabled\s*===\s*true\s*:\s*false[\s\S]*?color:\s*delegateItem\.entryEnabled\s*\?\s*Color\.mPrimary[\s\S]*?text:\s*delegateItem\.text[\s\S]*?checked:\s*delegateItem\.countdownEnabled/;

  assert.match(source, entryDelegate, "SessionMenuTab entry delegate must type scalar roles and expose a strict readonly enabled alias");
  assert.doesNotMatch(source, /required\s+property\s+bool\s+enabled/, "SessionMenuTab must not bind the enabled role to Item.enabled");
  assert.doesNotMatch(source, /(?<!readonly\s)property\s+bool\s+entryEnabled/, "SessionMenuTab entryEnabled alias must be readonly");
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
  const cardDelegate = /Repeater\s*\{[\s\S]*?model:\s*Settings\.data\.controlCenter\.cards[\s\S]*?Loader\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+string\s+cardId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+cardEnabled:\s*modelData\s*\?\s*modelData\.enabled\s*===\s*true\s*:\s*false[\s\S]*?active:\s*cardEnabled[\s\S]*?switch\s*\(cardId\)/;

  assert.match(source, cardDelegate, "ControlCenterPanel card delegate must type card aliases");
  assert.equal((source.match(/modelData\.id/g) ?? []).length, 1, "ControlCenterPanel card delegate must use cardId after declaration");
  assert.equal((source.match(/modelData\.enabled/g) ?? []).length, 1, "ControlCenterPanel card delegate must use cardEnabled after declaration");
}

function testClockPanelCardDelegateIsTyped() {
  const source = readQml("Modules/Panels/Clock/ClockPanel.qml");
  const cardDelegate = /Repeater\s*\{[\s\S]*?model:\s*Settings\.data\.calendar\.cards[\s\S]*?Loader\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+string\s+cardId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+cardEnabled:\s*modelData\s*\?\s*modelData\.enabled\s*===\s*true\s*:\s*false[\s\S]*?active:\s*cardEnabled[\s\S]*?switch\s*\(cardId\)/;

  assert.match(source, cardDelegate, "ClockPanel card delegate must type card aliases");
  assert.equal((source.match(/modelData\.id/g) ?? []).length, 1, "ClockPanel card delegate must use cardId after declaration");
  assert.equal((source.match(/modelData\.enabled/g) ?? []).length, 1, "ClockPanel card delegate must use cardEnabled after declaration");
}

function testPanelServiceOpenedPanelIsTyped() {
  assertPropertyType("Services/UI/PanelService.qml", "openedPanel", "SmartPanel");
}

function testContextMenuDelegatePopupIsTyped() {
  assertPropertyType("Widgets/NContextMenu.qml", "popup", "Popup");
}

function testContextMenuDelegateRolesAreTyped() {
  const source = readQml("Widgets/NContextMenu.qml");
  const delegateRoles = /delegate:\s*ItemDelegate\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+bool\s+itemVisible:\s+modelData\s*\?\s*modelData\.visible\s*!==\s*false\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+itemEnabled:\s+modelData\s*\?\s*modelData\.enabled\s*!==\s*false\s*:\s*false[\s\S]*?readonly\s+property\s+string\s+itemIcon:\s+modelData\s*\?\s*\(modelData\.icon\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+hasIcon:\s*itemIcon\s*!==\s*""[\s\S]*?readonly\s+property\s+string\s+itemText:\s+modelData\s*\?\s*\(modelData\.label\s*\|\|\s*modelData\.text\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+itemAction:\s+modelData\s*\?\s*\(modelData\.action\s*\|\|\s*modelData\.key\s*\|\|\s*index\.toString\(\)\)\s*:\s*index\.toString\(\)/;

  assert.match(source, /function openAt\(x, y\)/, "NContextMenu openAt must accept coordinate inputs");
  assert.match(source, /function openAtItem\(item, mouseX, mouseY\)/, "NContextMenu openAtItem must accept anchor and coordinate inputs");
  assert.match(source, delegateRoles, "NContextMenu delegate must declare null-safe typed aliases for menu entry fields");
  assert.match(source, /height:\s*itemVisible\s*\?\s*root\.itemHeight\s*:\s*0/, "NContextMenu delegate height must use itemVisible");
  assert.match(source, /visible:\s*itemVisible/, "NContextMenu delegate visible binding must use itemVisible");
  assert.match(source, /opacity:\s*itemEnabled\s*\?\s*1\.0\s*:\s*0\.5/, "NContextMenu delegate opacity must use itemEnabled");
  assert.match(source, /enabled:\s*itemEnabled/, "NContextMenu delegate enabled binding must use itemEnabled");
  assert.match(source, /visible:\s*hasIcon/, "NContextMenu icon visibility must use hasIcon");
  assert.match(source, /icon:\s*itemIcon/, "NContextMenu icon must use itemIcon");
  assert.match(source, /text:\s*itemText/, "NContextMenu label must use itemText");
  assert.match(source, /Layout\.leftMargin:\s*hasIcon\s*\?\s*0\s*:\s*root\.itemPadding/, "NContextMenu label margin must use hasIcon");
  assert.match(source, /popup\.triggered\(itemAction\)/, "NContextMenu click handler must use itemAction");
}

function testPopupContextMenuDelegateRolesAreTyped() {
  const source = readQml("Widgets/NPopupContextMenu.qml");
  const delegateRoles = /delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*menuItem[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+bool\s+itemVisible:\s+modelData\s*\?\s*modelData\.visible\s*!==\s*false\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+itemEnabled:\s+modelData\s*\?\s*modelData\.enabled\s*!==\s*false\s*:\s*false[\s\S]*?readonly\s+property\s+string\s+itemIcon:\s+modelData\s*\?\s*\(modelData\.icon\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+hasIcon:\s*itemIcon\s*!==\s*""[\s\S]*?readonly\s+property\s+string\s+itemText:\s+modelData\s*\?\s*\(modelData\.label\s*\|\|\s*modelData\.text\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+itemAction:\s+modelData\s*\?\s*\(modelData\.action\s*\|\|\s*modelData\.key\s*\|\|\s*index\.toString\(\)\)\s*:\s*index\.toString\(\)/;

  assert.match(source, delegateRoles, "NPopupContextMenu delegate must declare null-safe typed aliases for menu entry fields");
  assert.match(source, /Layout\.preferredHeight:\s*itemVisible\s*\?\s*root\.itemHeight\s*:\s*0/, "NPopupContextMenu delegate height must use itemVisible");
  assert.match(source, /visible:\s*itemVisible/, "NPopupContextMenu delegate visible binding must use itemVisible");
  assert.match(source, /opacity:\s*menuItem\.itemEnabled\s*\?\s*1\.0\s*:\s*0\.5/, "NPopupContextMenu opacity must use itemEnabled");
  assert.match(source, /visible:\s*menuItem\.hasIcon/, "NPopupContextMenu icon visibility must use hasIcon");
  assert.match(source, /icon:\s*menuItem\.itemIcon/, "NPopupContextMenu icon must use itemIcon");
  assert.match(source, /text:\s*menuItem\.itemText/, "NPopupContextMenu label must use itemText");
  assert.match(source, /enabled:\s*menuItem\.itemEnabled\s*&&\s*root\.visible/, "NPopupContextMenu mouse area must use itemEnabled");
  assert.match(source, /root\.triggered\(menuItem\.itemAction\)/, "NPopupContextMenu click handler must use itemAction");
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

function testBarWidgetDelegatesUseTypedWidgetIdAliases() {
  const source = readQml("Modules/Bar/Bar.qml");

  assert.equal((source.match(/readonly\s+property\s+string\s+configuredWidgetId:\s*modelData\s*\?\s*modelData\.id\s*:\s*""/g) ?? []).length, 6, "Bar widget delegates must declare null-safe typed widget id aliases");
  assert.equal((source.match(/widgetId:\s*configuredWidgetId/g) ?? []).length, 6, "Bar widget delegates must assign widgetId from the typed alias");
  assert.equal((source.match(/"widgetId":\s*configuredWidgetId/g) ?? []).length, 6, "Bar widget delegates must pass widgetId props from the typed alias");
  assert.equal((source.match(/modelData\.id/g) ?? []).length, 6, "Bar widget delegates must only read modelData.id when declaring the alias");
  assert.doesNotMatch(source, /widgetId:\s*modelData\.id/, "Bar widget delegates must not assign widgetId directly from modelData.id");
  assert.doesNotMatch(source, /"widgetId":\s*modelData\.id/, "Bar widget delegates must not pass widgetId props directly from modelData.id");
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

function testDockMenuToplevelIsTyped() {
  const dockMenuFile = "Modules/Dock/DockMenu.qml";

  assertPropertyType(dockMenuFile, "toplevel", "Toplevel");
  assertNoPropertyType(dockMenuFile, "toplevel", "var");
}

function testDockMenuItemDelegateInputsAreTyped() {
  const source = readQml("Modules/Dock/DockMenu.qml");
  const itemDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.items[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+menuIcon:\s*modelData\s*\?\s*\(modelData\.icon\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+menuText:\s*modelData\s*\?\s*\(modelData\.text\s*\|\|\s*""\)\s*:\s*""[\s\S]*?icon:\s*menuIcon[\s\S]*?text:\s*menuText/;

  assert.match(source, itemDelegate, "DockMenu item delegate must expose typed aliases for icon and text");
  assert.equal((source.match(/modelData\.icon/g) ?? []).length, 1, "DockMenu item delegate must use menuIcon after declaration");
  assert.equal((source.match(/modelData\.text/g) ?? []).length, 1, "DockMenu item delegate must use menuText after declaration");
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
  const deviceDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.model[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+BluetoothDevice\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+bool\s+devicePairing:\s*modelData\s*\?\s*modelData\.pairing\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+deviceBlocked:\s*modelData\s*\?\s*modelData\.blocked\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+deviceConnected:\s*modelData\s*\?\s*modelData\.connected\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+deviceConnecting:\s*modelData\s*\?\s*modelData\.state\s*===\s*BluetoothDeviceState\.Connecting\s*:\s*false[\s\S]*?readonly\s+property\s+string\s+deviceDisplayName:\s*modelData\s*\?\s*\(modelData\.name\s*\|\|\s*modelData\.deviceName\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+hasSignalStrength:\s*modelData\s*\?\s*modelData\.signalStrength\s*!==\s*undefined\s*:\s*false[\s\S]*?readonly\s+property\s+int\s+deviceSignalStrength:\s*modelData\s*\?\s*\(modelData\.signalStrength\s*\|\|\s*0\)\s*:\s*0[\s\S]*?readonly\s+property\s+bool\s+showSignalStrength:\s*deviceSignalStrength\s*>\s*0\s*&&\s*!devicePairing\s*&&\s*!deviceBlocked[\s\S]*?readonly\s+property\s+bool\s+hasBattery:\s*modelData\s*\?\s*modelData\.batteryAvailable\s*===\s*true\s*:\s*false[\s\S]*?BluetoothService\.canConnect\(modelData\)[\s\S]*?devicePairing\s*\|\|\s*deviceConnecting[\s\S]*?text:\s*deviceDisplayName[\s\S]*?font\.weight:\s*deviceConnected\s*\?[\s\S]*?visible:\s*hasSignalStrength[\s\S]*?visible:\s*showSignalStrength[\s\S]*?text:\s*showSignalStrength\s*\?\s*deviceSignalStrength\s*\+\s*"%"[\s\S]*?visible:\s*hasBattery[\s\S]*?visible:\s*!deviceConnecting[\s\S]*?if\s*\(devicePairing\)[\s\S]*?if\s*\(deviceBlocked\)[\s\S]*?if\s*\(deviceConnected\)/;

  assert.match(source, deviceDelegate, "BluetoothDevicesList device delegate must type modelData and expose stable status aliases");
}

function testBluetoothServiceDeviceModelIsTyped() {
  const bluetoothServiceFile = "Services/Networking/BluetoothService.qml";

  assertPropertyType(bluetoothServiceFile, "devices", "ObjectModel");
  assertNoPropertyType(bluetoothServiceFile, "devices", "var");
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
  const sinkDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sinks[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+deviceId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+deviceDescription:\s*modelData\s*\?\s*\(modelData\.description\s*\|\|\s*deviceId\)\s*:\s*deviceId[\s\S]*?text:\s*deviceDescription[\s\S]*?checked:\s*AudioService\.sink\s*\?\s*AudioService\.sink\.id\s*===\s*deviceId\s*:\s*false/;
  const sourceDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sources[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+deviceId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+deviceDescription:\s*modelData\s*\?\s*\(modelData\.description\s*\|\|\s*deviceId\)\s*:\s*deviceId[\s\S]*?text:\s*deviceDescription[\s\S]*?checked:\s*AudioService\.source\s*\?\s*AudioService\.source\.id\s*===\s*deviceId\s*:\s*false/;

  assert.match(source, sinkDelegate, "AudioPanel sink delegate must type modelData, index, and stable aliases");
  assert.match(source, sourceDelegate, "AudioPanel source delegate must type modelData, index, and stable aliases");
  assert.equal((source.match(/modelData\.id/g) ?? []).length, 2, "AudioPanel delegates must use deviceId after declaration");
  assert.equal((source.match(/modelData\.description/g) ?? []).length, 2, "AudioPanel delegates must use deviceDescription after declaration");
}

function testAudioTabDeviceDelegatesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/AudioTab.qml");
  const sinkDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sinks[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?readonly\s+property\s+string\s+deviceId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+deviceDescription:\s*modelData\s*\?\s*\(modelData\.description\s*\|\|\s*deviceId\)\s*:\s*deviceId[\s\S]*?text:\s*deviceDescription[\s\S]*?checked:\s*AudioService\.sink\s*&&\s*AudioService\.sink\.id\s*===\s*deviceId/;
  const sourceDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sources[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?readonly\s+property\s+string\s+deviceId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+deviceDescription:\s*modelData\s*\?\s*\(modelData\.description\s*\|\|\s*deviceId\)\s*:\s*deviceId[\s\S]*?text:\s*deviceDescription[\s\S]*?checked:\s*AudioService\.source\s*&&\s*AudioService\.source\.id\s*===\s*deviceId/;

  assert.match(source, sinkDelegate, "AudioTab sink delegate must expose stable device aliases");
  assert.match(source, sourceDelegate, "AudioTab source delegate must expose stable device aliases");
  assert.equal((source.match(/modelData\.id/g) ?? []).length, 2, "AudioTab delegates must use deviceId after declaration");
  assert.equal((source.match(/modelData\.description/g) ?? []).length, 2, "AudioTab delegates must use deviceDescription after declaration");
}

function testProcessPanelProcessDelegateInputsAreTyped() {
  const source = readQml("Modules/Panels/Process/ProcessPanel.qml");
  const processDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.processList[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+processCommand:\s*modelData\s*\?\s*\(modelData\.command\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+processName:\s*modelData\s*\?\s*\(modelData\.displayName\s*\|\|\s*processCommand\)\s*:\s*processCommand[\s\S]*?readonly\s+property\s+real\s+processCpu:\s*modelData\s*\?\s*\(modelData\.cpu\s*\|\|\s*0\)\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+processMemoryKb:\s*modelData\s*\?\s*\(modelData\.memoryKB\s*\|\|\s*0\)\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+processPid:\s*modelData\s*\?\s*\(modelData\.pid\s*\|\|\s*0\)\s*:\s*0[\s\S]*?readonly\s+property\s+color\s+processCpuColor:[\s\S]*?processCpu\s*>\s*50[\s\S]*?ProcessService\.getProcessIcon\(processCommand\)[\s\S]*?text:\s*processName[\s\S]*?ProcessService\.formatCpu\(processCpu\)[\s\S]*?color:\s*processCpuColor[\s\S]*?ProcessService\.formatMemory\(processMemoryKb\)[\s\S]*?processPid\.toString\(\)/;

  assert.match(source, processDelegate, "ProcessPanel process delegate must declare typed aliases for process fields");
  assert.equal((source.match(/modelData\.command/g) ?? []).length, 1, "ProcessPanel process delegate must use processCommand after declaration");
  assert.equal((source.match(/modelData\.displayName/g) ?? []).length, 1, "ProcessPanel process delegate must use processName after declaration");
  assert.equal((source.match(/modelData\.cpu/g) ?? []).length, 1, "ProcessPanel process delegate must use processCpu after declaration");
  assert.equal((source.match(/modelData\.memoryKB/g) ?? []).length, 1, "ProcessPanel process delegate must use processMemoryKb after declaration");
  assert.equal((source.match(/modelData\.pid/g) ?? []).length, 1, "ProcessPanel process delegate must use processPid after declaration");
}

function testTrayMenuItemIsTyped() {
  const trayMenuFile = "Modules/Bar/Extras/TrayMenu.qml";
  const source = readQml(trayMenuFile);
  const trayEntryDelegate = /Repeater\s*\{[\s\S]*?model:\s*opener\.children\s*\?[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*entry[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+bool\s+isSeparator:\s*modelData\s*\?\s*modelData\.isSeparator\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+hasChildren:\s*modelData\s*\?\s*modelData\.hasChildren\s*:\s*false[\s\S]*?readonly\s+property\s+var\s+menuItem:\s*modelData\s*\|\|\s*null[\s\S]*?if\s*\(entry\.menuItem\s*&&\s*!entry\.isSeparator\)[\s\S]*?if\s*\(entry\.hasChildren\)[\s\S]*?"menu":\s*entry\.menuItem[\s\S]*?entry\.menuItem\.triggered\(\)/;

  assertPropertyType(trayMenuFile, "trayItem", "SystemTrayItem");
  assertNoPropertyType(trayMenuFile, "trayItem", "var");
  assert.match(source, trayEntryDelegate, "TrayMenu entry delegate must use typed aliases for interaction state");
  assert.equal((source.match(/modelData\.isSeparator/g) ?? []).length, 1, "TrayMenu entry delegate must use isSeparator after declaration");
  assert.equal((source.match(/modelData\.hasChildren/g) ?? []).length, 1, "TrayMenu entry delegate must use hasChildren after declaration");
  assert.doesNotMatch(source, /modelData\.triggered\(\)/, "TrayMenu entry delegate must use menuItem when triggering actions");
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

function testTrayPopupMenuWindowReferencesAreTyped() {
  const trayMenuFiles = [
    "Modules/Bar/Widgets/Tray.qml",
    "Modules/Panels/Tray/TrayDrawerPanel.qml",
  ];

  for (const trayMenuFile of trayMenuFiles) {
    assertPropertyType(trayMenuFile, "popupMenuWindow", "QtObject");
    assertNoPropertyType(trayMenuFile, "popupMenuWindow", "var");
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
  const monitorComponent = /component\s+Monitor:\s+QtObject\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+screenModel:\s+modelData\s*\?\s*modelData\.model\s*:\s*""/;

  assert.match(source, monitorComponent, "BrightnessService Monitor must expose null-safe typed screenModel alias from ShellScreen modelData");
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

function testPanelBackgroundPanelReferenceIsTyped() {
  const panelBackgroundFile = "Modules/MainScreen/Backgrounds/PanelBackground.qml";

  assertPropertyType(panelBackgroundFile, "panel", "Item");
  assertNoPropertyType(panelBackgroundFile, "panel", "var");
}

function testBarBackgroundBarReferenceIsTyped() {
  const backgroundFiles = [
    "Modules/MainScreen/Backgrounds/AllBackgrounds.qml",
    "Modules/MainScreen/Backgrounds/BarBackground.qml",
  ];

  for (const backgroundFile of backgroundFiles) {
    assertPropertyType(backgroundFile, "bar", "Item");
    assertNoPropertyType(backgroundFile, "bar", "var");
  }
}

function testBackgroundWindowRootStaysUntypedForPanelWindow() {
  const backgroundFiles = [
    "Modules/MainScreen/Backgrounds/AllBackgrounds.qml",
    "Modules/MainScreen/Backgrounds/BarBackground.qml",
  ];

  for (const backgroundFile of backgroundFiles) {
    assertPropertyType(backgroundFile, "windowRoot", "var");
    assertNoPropertyType(backgroundFile, "windowRoot", "Item");
  }
}

function testBackgroundScreenAliasesAreTyped() {
  const source = readQml("Modules/Background/Background.qml");
  const screenDelegate = /Variants\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?delegate:\s*Loader\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s*modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s*modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s*modelData\s*\?\s*modelData\.height\s*:\s*0[\s\S]*?screenName\s*===\s*monitorName[\s\S]*?CompositorService\.getDisplayScale\(monitorName\)[\s\S]*?monitorWidth\s*\*\s*compositorScale[\s\S]*?monitorHeight\s*\*\s*compositorScale[\s\S]*?WallpaperService\.getWallpaper\(monitorName\)/;

  assert.match(source, screenDelegate, "Background screen delegate must expose null-safe typed screen aliases");
  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "Background must use monitorName after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "Background must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "Background must use monitorHeight after declaration");
}

function testOverviewScreenAliasIsTyped() {
  const source = readQml("Modules/Background/Overview.qml");
  const screenDelegate = /Variants\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?delegate:\s*PanelWindow\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s*modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?Loading overview for Niri on",\s*monitorName[\s\S]*?screenName\s*===\s*monitorName[\s\S]*?WallpaperService\.getWallpaper\(monitorName\)/;

  assert.match(source, screenDelegate, "Overview screen delegate must expose null-safe typed monitorName alias");
  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "Overview must use monitorName after declaration");
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
  const monitorTabModel = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?NTabButton\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+screenName:\s*modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?text:\s*screenName\s*\|\|\s*`Screen \$\{index \+ 1\}`/;

  assert.match(source, monitorTabModel, "WallpaperPanel monitor tabs must expose a null-safe typed screenName alias");
  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "WallpaperPanel monitor tabs must use screenName after declaration");
}

function testWallpaperPanelScreenViewModelIsTyped() {
  const source = readQml("Modules/Panels/Wallpaper/WallpaperPanel.qml");
  const screenViewModel = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?delegate:\s*WallpaperScreenView\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?targetScreen:\s*modelData/;

  assert.match(source, screenViewModel, "WallpaperPanel screen views must type screen modelData as ShellScreen");
}

function testWallpaperPanelWallhavenDelegateAliasesAreTyped() {
  const source = readQml("Modules/Panels/Wallpaper/WallpaperPanel.qml");
  const wallhavenDelegate = /delegate:\s*ColumnLayout\s*\{[\s\S]*?id:\s*wallhavenItem[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+thumbnailUrl:\s*\(modelData\s*&&\s*typeof\s+WallhavenService\s*!==\s*"undefined"\)\s*\?\s*WallhavenService\.getThumbnailUrl\(modelData,\s*"large"\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+wallpaperId:\s*\(modelData\s*&&\s*modelData\.id\)\s*\|\|\s*""[\s\S]*?source:\s*thumbnailUrl[\s\S]*?text:\s*wallpaperId\s*\|\|\s*I18n\.tr\("wallpaper\.unknown"\)/;

  assert.match(source, wallhavenDelegate, "WallpaperPanel Wallhaven delegate must expose readonly typed aliases");
  assert.equal((source.match(/modelData\.id/g) ?? []).length, 1, "WallpaperPanel Wallhaven delegate must use wallpaperId after declaration");
}

function testWallpaperTabMonitorNameAliasIsTyped() {
  const wallpaperTabFile = "Modules/Panels/Settings/Tabs/WallpaperTab.qml";
  const source = readQml(wallpaperTabFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*ColumnLayout\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\s*\?\s*modelData\.name\s*:\s*""/;

  assert.match(source, monitorDelegate, "WallpaperTab monitor delegate must expose null-safe typed monitorName alias from ShellScreen modelData");
  assert.match(source, /text:\s*\(monitorName\s*\|\|\s*"Unknown"\)/, "WallpaperTab monitor label must use monitorName");
  assert.match(source, /WallpaperService\.getMonitorDirectory\(monitorName\)/, "WallpaperTab monitor directory lookup must use monitorName");
  assert.match(source, /WallpaperService\.setMonitorDirectory\(monitorName,\s*text\)/, "WallpaperTab monitor directory save must use monitorName");
  assert.match(source, /specificFolderMonitorName\s*=\s*monitorName/, "WallpaperTab folder picker state must use monitorName");

  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "WallpaperTab monitor delegate must use monitorName after declaration");
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

function testBarTabMonitorAliasesAreTyped() {
  const barTabFile = "Modules/Panels/Settings/Tabs/BarTab.qml";
  const source = readQml(barTabFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s+modelData\s*\?\s*modelData\.model\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s+modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s+modelData\s*\?\s*modelData\.height\s*:\s*0/;

  assert.match(source, monitorDelegate, "BarTab monitor delegate must expose null-safe typed aliases for ShellScreen fields");
  assert.match(source, /label:\s*monitorName\s*\|\|\s*"Unknown"/, "BarTab monitor label must use monitorName");
  assert.match(source, /CompositorService\.getDisplayScale\(monitorName\)/, "BarTab monitor scale lookup must use monitorName");
  assert.match(source, /"model":\s*monitorModel/, "BarTab monitor description must use monitorModel");
  assert.match(source, /"width":\s*monitorWidth\s*\*\s*compositorScale/, "BarTab monitor description must use monitorWidth");
  assert.match(source, /"height":\s*monitorHeight\s*\*\s*compositorScale/, "BarTab monitor description must use monitorHeight");
  assert.match(source, /indexOf\(monitorName\)\s*!==\s*-1/, "BarTab monitor selection must use monitorName");
  assert.match(source, /addMonitor\(Settings\.data\.bar\.monitors,\s*monitorName\)/, "BarTab monitor add action must use monitorName");
  assert.match(source, /removeMonitor\(Settings\.data\.bar\.monitors,\s*monitorName\)/, "BarTab monitor remove action must use monitorName");

  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "BarTab monitor delegate must use monitorName after declaration");
  assert.equal((source.match(/modelData\.model/g) ?? []).length, 1, "BarTab monitor delegate must use monitorModel after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "BarTab monitor delegate must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "BarTab monitor delegate must use monitorHeight after declaration");
}

function testDisplayTabMonitorAliasesAreTyped() {
  const displayTabFile = "Modules/Panels/Settings/Tabs/DisplayTab.qml";
  const source = readQml(displayTabFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s*modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s*modelData\s*\?\s*modelData\.model\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s*modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s*modelData\s*\?\s*modelData\.height\s*:\s*0/;

  assert.match(source, monitorDelegate, "DisplayTab monitor delegate must expose null-safe typed aliases for ShellScreen fields");
  assert.match(source, /BrightnessService\.getMonitorForScreen\(modelData\)/, "DisplayTab brightness lookup must keep using the typed ShellScreen object");
  assert.match(source, /label:\s*monitorName\s*\|\|\s*"Unknown"/, "DisplayTab monitor label must use monitorName");
  assert.match(source, /CompositorService\.getDisplayScale\(monitorName\)/, "DisplayTab monitor scale lookup must use monitorName");
  assert.match(source, /"model":\s*monitorModel/, "DisplayTab monitor description must use monitorModel");
  assert.match(source, /"width":\s*monitorWidth\s*\*\s*compositorScale/, "DisplayTab monitor description must use monitorWidth");
  assert.match(source, /"height":\s*monitorHeight\s*\*\s*compositorScale/, "DisplayTab monitor description must use monitorHeight");

  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "DisplayTab monitor delegate must use monitorName after declaration");
  assert.equal((source.match(/modelData\.model/g) ?? []).length, 1, "DisplayTab monitor delegate must use monitorModel after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "DisplayTab monitor delegate must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "DisplayTab monitor delegate must use monitorHeight after declaration");
}

function testDockTabMonitorAliasesAreTyped() {
  const dockTabFile = "Modules/Panels/Settings/Tabs/DockTab.qml";
  const source = readQml(dockTabFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s+modelData\s*\?\s*modelData\.model\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s+modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s+modelData\s*\?\s*modelData\.height\s*:\s*0/;

  assert.match(source, monitorDelegate, "DockTab monitor delegate must expose null-safe typed aliases for ShellScreen fields");
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
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s+modelData\s*\?\s*modelData\.model\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s+modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s+modelData\s*\?\s*modelData\.height\s*:\s*0/;

  assert.match(source, monitorDelegate, "OsdTab monitor delegate must expose null-safe typed aliases for ShellScreen fields");
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

function testNotificationsTabMonitorAliasesAreTyped() {
  const notificationsTabFile = "Modules/Panels/Settings/Tabs/NotificationsTab.qml";
  const source = readQml(notificationsTabFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s+modelData\s*\?\s*modelData\.model\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s+modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s+modelData\s*\?\s*modelData\.height\s*:\s*0/;

  assert.match(source, monitorDelegate, "NotificationsTab monitor delegate must expose null-safe typed aliases for ShellScreen fields");
  assert.match(source, /label:\s*monitorName\s*\|\|\s*I18n\.tr\("system\.unknown"\)/, "NotificationsTab monitor label must use monitorName");
  assert.match(source, /CompositorService\.getDisplayScale\(monitorName\)/, "NotificationsTab monitor scale lookup must use monitorName");
  assert.match(source, /"model":\s*monitorModel/, "NotificationsTab monitor description must use monitorModel");
  assert.match(source, /"width":\s*monitorWidth\s*\*\s*compositorScale/, "NotificationsTab monitor description must use monitorWidth");
  assert.match(source, /"height":\s*monitorHeight\s*\*\s*compositorScale/, "NotificationsTab monitor description must use monitorHeight");
  assert.match(source, /indexOf\(monitorName\)\s*!==\s*-1/, "NotificationsTab monitor selection must use monitorName");
  assert.match(source, /addMonitor\(Settings\.data\.notifications\.monitors,\s*monitorName\)/, "NotificationsTab monitor add action must use monitorName");
  assert.match(source, /removeMonitor\(Settings\.data\.notifications\.monitors,\s*monitorName\)/, "NotificationsTab monitor remove action must use monitorName");

  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "NotificationsTab monitor delegate must use monitorName after declaration");
  assert.equal((source.match(/modelData\.model/g) ?? []).length, 1, "NotificationsTab monitor delegate must use monitorModel after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "NotificationsTab monitor delegate must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "NotificationsTab monitor delegate must use monitorHeight after declaration");
}

function testWallpaperServiceScannerModelIsTyped() {
  const source = readQml("Services/UI/WallpaperService.qml");
  const scannerModelDelegate = /Instantiator\s*\{[\s\S]*?model:\s*Quickshell\.screens[\s\S]*?delegate:\s*FolderListModel\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+screenName:\s*modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?property\s+string\s+currentDirectory:\s*root\.getMonitorDirectory\(screenName\)/;

  assert.match(source, scannerModelDelegate, "WallpaperService scanner must expose a null-safe typed screenName alias");
  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "WallpaperService scanner must use screenName after declaration");
}

function testSetupDockStepMonitorModelIsTyped() {
  const source = readQml("Modules/Panels/SetupWizard/SetupDockStep.qml");
  const monitorModelDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?required\s+property\s+ShellScreen\s+modelData/;

  assert.match(source, monitorModelDelegate, "SetupDockStep monitor delegate must type screen modelData as ShellScreen");
}

function testSetupDockStepMonitorAliasesAreTyped() {
  const setupDockStepFile = "Modules/Panels/SetupWizard/SetupDockStep.qml";
  const source = readQml(setupDockStepFile);
  const monitorDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NCheckbox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s+modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s+modelData\s*\?\s*modelData\.model\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s+modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s+modelData\s*\?\s*modelData\.height\s*:\s*0/;

  assert.match(source, monitorDelegate, "SetupDockStep monitor delegate must expose null-safe typed aliases for ShellScreen fields");
  assert.match(source, /label:\s*monitorName\s*\|\|\s*"Unknown"/, "SetupDockStep monitor label must use monitorName");
  assert.match(source, /CompositorService\.getDisplayScale\(monitorName\)/, "SetupDockStep monitor scale lookup must use monitorName");
  assert.match(source, /"model":\s*monitorModel/, "SetupDockStep monitor description must use monitorModel");
  assert.match(source, /"width":\s*monitorWidth\s*\*\s*compositorScale/, "SetupDockStep monitor description must use monitorWidth");
  assert.match(source, /"height":\s*monitorHeight\s*\*\s*compositorScale/, "SetupDockStep monitor description must use monitorHeight");
  assert.match(source, /indexOf\(monitorName\)\s*!==\s*-1/, "SetupDockStep monitor selection must use monitorName");
  assert.match(source, /arr\.indexOf\(monitorName\)\s*===\s*-1/, "SetupDockStep monitor add guard must use monitorName");
  assert.match(source, /arr\.push\(monitorName\)/, "SetupDockStep monitor add action must use monitorName");
  assert.match(source, /return\s+n\s*!==\s*monitorName/, "SetupDockStep monitor remove filter must use monitorName");

  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "SetupDockStep monitor delegate must use monitorName after declaration");
  assert.equal((source.match(/modelData\.model/g) ?? []).length, 1, "SetupDockStep monitor delegate must use monitorModel after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "SetupDockStep monitor delegate must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "SetupDockStep monitor delegate must use monitorHeight after declaration");
}

function testSetupWizardProgressDelegateModelIsTyped() {
  const source = readQml("Modules/Panels/SetupWizard/SetupWizard.qml");
  const progressDelegate = /Repeater\s*\{[\s\S]*?"label":\s*"Dock"[\s\S]*?delegate:\s*RowLayout\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+stepIcon:\s*modelData\s*\?\s*\(modelData\.icon\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+stepLabel:\s*modelData\s*\?\s*\(modelData\.label\s*\|\|\s*""\)\s*:\s*""[\s\S]*?icon:\s*stepIcon[\s\S]*?text:\s*stepLabel/;

  assert.match(source, progressDelegate, "SetupWizard progress delegate must expose typed aliases for icon and label");
  assert.equal((source.match(/modelData\.icon/g) ?? []).length, 1, "SetupWizard progress delegate must use stepIcon after declaration");
  assert.equal((source.match(/modelData\.label/g) ?? []).length, 1, "SetupWizard progress delegate must use stepLabel after declaration");
}

function testBrightnessPanelScreenModelIsTyped() {
  const source = readQml("Modules/Panels/Brightness/BrightnessPanel.qml");
  const screenModelDelegate = /Repeater\s*\{[\s\S]*?model:\s*Quickshell\.screens(?:\s*\|\|\s*\[\])?[\s\S]*?delegate:\s*NBox\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+monitorName:\s*modelData\s*\?\s*modelData\.name\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+monitorModel:\s*modelData\s*\?\s*modelData\.model\s*:\s*""[\s\S]*?readonly\s+property\s+int\s+monitorWidth:\s*modelData\s*\?\s*modelData\.width\s*:\s*0[\s\S]*?readonly\s+property\s+int\s+monitorHeight:\s*modelData\s*\?\s*modelData\.height\s*:\s*0/;

  assert.match(source, screenModelDelegate, "BrightnessPanel monitor delegate must expose null-safe typed screen aliases");
  assert.match(source, /label:\s*monitorName\s*\|\|\s*"Unknown"/, "BrightnessPanel monitor label must use monitorName");
  assert.match(source, /CompositorService\.getDisplayScale\(monitorName\)/, "BrightnessPanel monitor scale lookup must use monitorName");
  assert.match(source, /"model":\s*monitorModel/, "BrightnessPanel monitor description must use monitorModel");
  assert.match(source, /"width":\s*monitorWidth\s*\*\s*compositorScale/, "BrightnessPanel monitor description must use monitorWidth");
  assert.match(source, /"height":\s*monitorHeight\s*\*\s*compositorScale/, "BrightnessPanel monitor description must use monitorHeight");
  assert.equal((source.match(/modelData\.name/g) ?? []).length, 1, "BrightnessPanel monitor delegate must use monitorName after declaration");
  assert.equal((source.match(/modelData\.model/g) ?? []).length, 1, "BrightnessPanel monitor delegate must use monitorModel after declaration");
  assert.equal((source.match(/modelData\.width/g) ?? []).length, 1, "BrightnessPanel monitor delegate must use monitorWidth after declaration");
  assert.equal((source.match(/modelData\.height/g) ?? []).length, 1, "BrightnessPanel monitor delegate must use monitorHeight after declaration");
}

function testWiFiNetworkDelegateAliasesAreTyped() {
  const source = readQml("Modules/Panels/WiFi/WiFiNetworksList.qml");
  const networkDelegate = /Repeater\s*\{[\s\S]*?model:\s*root\.model[\s\S]*?Rectangle\s*\{[\s\S]*?id:\s*networkItem[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+string\s+networkSsid:\s*modelData\s*\?\s*\(modelData\.ssid\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+networkConnected:\s*modelData\s*\?\s*modelData\.connected\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+int\s+networkSignal:\s*modelData\s*\?\s*\(modelData\.signal\s*\|\|\s*0\)\s*:\s*0[\s\S]*?readonly\s+property\s+string\s+networkSecurity:\s*modelData\s*\?\s*\(modelData\.security\s*\|\|\s*"Open"\)\s*:\s*"Open"[\s\S]*?readonly\s+property\s+bool\s+networkExisting:\s*modelData\s*\?\s*modelData\.existing\s*===\s*true\s*:\s*false[\s\S]*?readonly\s+property\s+bool\s+networkCached:\s*modelData\s*\?\s*modelData\.cached\s*===\s*true\s*:\s*false/;

  assert.match(source, networkDelegate, "WiFiNetworksList delegate must type stable network aliases");
  assert.equal((source.match(/modelData\.ssid/g) ?? []).length, 1, "WiFiNetworksList delegate must use networkSsid after declaration");
  assert.equal((source.match(/modelData\.connected/g) ?? []).length, 1, "WiFiNetworksList delegate must use networkConnected after declaration");
  assert.equal((source.match(/modelData\.signal/g) ?? []).length, 1, "WiFiNetworksList delegate must use networkSignal after declaration");
  assert.equal((source.match(/modelData\.security/g) ?? []).length, 1, "WiFiNetworksList delegate must use networkSecurity after declaration");
  assert.equal((source.match(/modelData\.existing/g) ?? []).length, 1, "WiFiNetworksList delegate must use networkExisting after declaration");
  assert.equal((source.match(/modelData\.cached/g) ?? []).length, 1, "WiFiNetworksList delegate must use networkCached after declaration");
}

const tests = [
  testQmlFunctionSignaturesAvoidUnsupportedTypeAnnotations,
  testSliderCutoutColorsAreTyped,
  testPopupAnchorItemsAreTyped,
  testPopupContextMenuOpenHelpersAreTyped,
  testTooltipTargetItemIsTyped,
  testTooltipServiceCallsUseTargetItemFirst,
  testTooltipServiceTracksTypedTooltipInstances,
  testSmartPanelButtonItemIsTyped,
  testSmartPanelPanelRegionIsTyped,
  testMainScreenPanelPlaceholdersAreTyped,
  testAllScreensScreenNameAliasIsTyped,
  testPanelContentItemsAreTyped,
  testPanelServiceLockScreenIsTyped,
  testNotificationServerInstanceIsTyped,
  testNotificationWatcherTargetsAreTyped,
  testSettingsPanelActiveScrollViewIsTyped,
  testSettingsPanelTabsDelegatesAreTyped,
  testComboBoxDelegateParentIsTyped,
  testComboBoxDelegateIndexIsTyped,
  testWeatherCardForecastDelegateIndexIsTyped,
  testMediaCardWallpaperChangeInputsAreTyped,
  testLockScreenForecastDelegateIndexIsTyped,
  testChangelogPanelHighlightDelegatesAreTyped,
  testNotificationDelegateIndexIsTyped,
  testWallpaperTabIntervalPresetModelDataIsTyped,
  testLauncherResultDelegatesAreTyped,
  testLauncherListImageAliasesAreTyped,
  testLauncherGridImageAliasesAreTyped,
  testLauncherListDisplayAliasesAreTyped,
  testLauncherGridDisplayAliasesAreTyped,
  testDateTimeTokenDelegateRolesAreTyped,
  testSetupCustomizeOptionDelegatesAreTyped,
  testColorPickerSwatchDelegatesAreTyped,
  testSetupAppearanceSchemeLoaderModelDataIsTyped,
  testFilePickerDelegatesUseTypedFileRoles,
  testTaskbarWindowDelegateRolesAreTyped,
  testShortcutsCardShortcutIdsAreTyped,
  testVpnConnectionRowsAreTyped,
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
  testClockPanelCardDelegateIsTyped,
  testPanelServiceOpenedPanelIsTyped,
  testContextMenuDelegatePopupIsTyped,
  testContextMenuDelegateRolesAreTyped,
  testPopupContextMenuDelegateRolesAreTyped,
  testGeometryReferencesAreTypedItems,
  testTimeNowPropertiesAreTypedDates,
  testEffectSourcePropertiesAreTyped,
  testBarWidgetLoaderScreenIsTyped,
  testBarWidgetDelegatesUseTypedWidgetIdAliases,
  testControlCenterWidgetLoaderScreenIsTyped,
  testClockSettingsFocusedInputIsTyped,
  testClockSettingsPreviewModelsAreTyped,
  testMangoPatternContainerIsTyped,
  testPopupMenuWindowContentItemIsTyped,
  testLauncherActivePluginIsTyped,
  testDockCurrentContextMenuIsTyped,
  testDockMenuToplevelIsTyped,
  testDockMenuItemDelegateInputsAreTyped,
  testLauncherPluginBackReferencesAreTyped,
  testCompositorBackendIsTyped,
  testPowerProfilesReferenceIsTyped,
  testUPowerBatteryReferencesAreTyped,
  testBluetoothDeviceDelegateInputsAreTyped,
  testBluetoothServiceDeviceModelIsTyped,
  testAudioNodeHandlesAreTyped,
  testAudioPanelDeviceDelegatesAreTyped,
  testAudioTabDeviceDelegatesAreTyped,
  testProcessPanelProcessDelegateInputsAreTyped,
  testTrayMenuItemIsTyped,
  testTrayMenuSubMenuIsTyped,
  testTrayMenuLoaderReferencesAreTyped,
  testTrayPopupMenuWindowReferencesAreTyped,
  testSectionEditorRegistryIsTyped,
  testDisplayTabBrightnessMonitorIsTyped,
  testBrightnessPanelBrightnessMonitorIsTyped,
  testBrightnessServiceMonitorScreenModelAliasIsTyped,
  testBackgroundShapeContainersAreTyped,
  testPanelBackgroundPanelReferenceIsTyped,
  testBarBackgroundBarReferenceIsTyped,
  testBackgroundWindowRootStaysUntypedForPanelWindow,
  testBackgroundScreenAliasesAreTyped,
  testOverviewScreenAliasIsTyped,
  testWallpaperPanelScreenReferencesAreTyped,
  testWallpaperPanelMonitorTabModelIsTyped,
  testWallpaperPanelScreenViewModelIsTyped,
  testWallpaperPanelWallhavenDelegateAliasesAreTyped,
  testWallpaperTabMonitorNameAliasIsTyped,
  testSettingsMonitorModelsAreTyped,
  testBarTabMonitorAliasesAreTyped,
  testDisplayTabMonitorAliasesAreTyped,
  testDockTabMonitorAliasesAreTyped,
  testOsdTabTypeOptionRolesAreTyped,
  testOsdTabMonitorAliasesAreTyped,
  testNotificationsTabMonitorAliasesAreTyped,
  testWallpaperServiceScannerModelIsTyped,
  testSetupDockStepMonitorModelIsTyped,
  testSetupDockStepMonitorAliasesAreTyped,
  testSetupWizardProgressDelegateModelIsTyped,
  testBrightnessPanelScreenModelIsTyped,
  testWiFiNetworkDelegateAliasesAreTyped,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
