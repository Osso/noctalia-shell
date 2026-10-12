#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("node:child_process");
const { extractComponentBlocks, extractFunctionBody, stripQmlComments } = require("./qml-test-utils");
const { assertOwnedProperties } = require("./qml-type-inventory");

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

function extractAnnotatedSignatures(source) {
  let code = stripQmlComments(source);
  // IPC has a separate typed wire contract; retain the inventory's original scope.
  for (const block of extractComponentBlocks(code, "IpcHandler"))
    code = code.replace(block, "");

  const declaration = /^[ \t]*function\s*([A-Za-z_$][\w$]*)?\s*\(([^)]*)\)\s*(?::\s*([\w<>.]+))?\s*\{/gm;
  return Array.from(code.matchAll(declaration))
    .filter(match => match[2].includes(":") || match[3])
    .map(match => {
      const parameters = match[2].replace(/\s+/g, "").replace(/,/g, ", ");
      const returnType = match[3] ? `: ${match[3]}` : "";
      return `${match[1] || "<anonymous>"}(${parameters})${returnType}`;
    });
}

function testAnnotatedSignatureExtraction() {
  const source = `Item {
    // function ignored(value: int): bool {}
    IpcHandler {
      function wire(value: string): void { const nested = {}; }
    }
    function typed(
      condition: bool, /* argument contract */ message: string
    ): void { }
    function untyped(value) { }
    function returnOnly(): Item { }
  }`;
  assert.deepEqual(extractAnnotatedSignatures(source), [
    "typed(condition:bool, message:string): void",
    "returnOnly(): Item",
  ]);
}

function testQmlFunctionTypeContractInventory() {
  const inventory = qmlFiles().flatMap(qmlFile =>
    extractAnnotatedSignatures(readQml(qmlFile)).map(signature => `${qmlFile}: ${signature}`));

  // Declaration inventory, not behavior proof. Runtime gates below execute these
  // annotations on installed Qt/Quickshell. Popup methods use an offscreen
  // QtObject owner; this does not prove native PanelWindow/layershell lifecycle.
  assert.deepEqual(inventory, [
    "Modules/Bar/Widgets/Tray.qml: bindTrayContext(owner:Tray): void",
    "Modules/MainScreen/PopupMenuWindow.qml: initializeTrayMenu(menu:var): void",
    "Modules/MainScreen/PopupMenuWindow.qml: hideContent(menu:var): void",
    "Tests/Qml/CompositorServiceHarness.qml: fixtureBackend(): Backend",
    "Tests/Qml/LocationServiceHarness.qml: require(condition:bool, message:string): void",
    "Tests/Qml/LocationTabWarningsHarness.qml: descendants(item:Item): var",
    "Tests/Qml/ServiceCohortHarness.qml: selectBackend(hyprland): var",
  ], "Update the typed contract inventory and runtime evidence together when signatures change");
}

function testAnnotatedFunctionRuntimeContracts() {
  const gates = [
    ["tray-widget-reload.test.py"],
    ["location-service-runtime.test.py", "runtime"],
    ["location-tab-warnings.test.py", "behavior"],
  ];
  for (const [runner, ...args] of gates) {
    const result = spawnSync("python3", [path.join(__dirname, runner), ...args], {
      encoding: "utf8",
      timeout: 120000,
      maxBuffer: 4 * 1024 * 1024,
    });
    assert.ifError(result.error);
    assert.equal(result.status, 0, `${runner}\n${result.stdout}${result.stderr}`);
    process.stdout.write(result.stdout);
  }
}

function testAnnotatedPopupFunctionRuntimeContracts() {
  const source = readQml("Modules/MainScreen/PopupMenuWindow.qml");
  const declarations = ["initializeTrayMenu", "hideContent"].map(name => {
    const signature = source.match(new RegExp(`function\\s+${name}\\([^)]*\\)\\s*:\\s*\\w+\\s*`));
    assert.notEqual(signature, null, `missing annotated declaration: ${name}`);
    return signature[0] + extractFunctionBody(source, name);
  }).join("\n");
  const harness = `import QtQuick
import QtTest
TestCase {
  name: "AnnotatedPopupFunctions"
  QtObject {
    id: root
    property QtObject screen: QtObject {}
    property QtObject activeMenu: null
    ${declarations}
  }
  QtObject {
    id: menu
    property QtObject screen: null
    property int hidden: 0
    property int closed: 0
    function hideMenu() { hidden++; }
    function close() { closed++; }
  }
  QtObject {
    id: closeOnly
    property int closed: 0
    function close() { closed++; }
  }
  function test_initialize_and_hide() {
    root.initializeTrayMenu(menu);
    compare(menu.screen, root.screen);
    compare(root.activeMenu, menu);
    root.initializeTrayMenu(null);
    compare(root.activeMenu, menu);
    root.hideContent(menu);
    compare(menu.hidden, 1);
    compare(menu.closed, 0);
    root.hideContent(closeOnly);
    compare(closeOnly.closed, 1);
    root.hideContent(null);
    compare(menu.hidden, 1);
    compare(closeOnly.closed, 1);
  }
}`;
  runOffscreenAnnotatedHarness(harness);
}

function runOffscreenAnnotatedHarness(harness) {
  const script = `
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, sys.argv[1])
import importlib.util
spec = importlib.util.spec_from_file_location("media", Path(sys.argv[1]) / "media-mini-warnings.test.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix="noctalia-typed-functions-") as temporary:
    directory = Path(temporary)
    (directory / "tst_functions.qml").write_text(sys.stdin.read())
    result = subprocess.run(["/usr/lib/qt6/bin/qmltestrunner", "-input", str(directory)], env=module.isolate_environment(directory), capture_output=True, text=True, timeout=30)
    print(result.stdout + result.stderr, end="")
    sys.exit(result.returncode)
`;
  const result = spawnSync("python3", ["-c", script, __dirname], {
    input: harness,
    encoding: "utf8",
    timeout: 60000,
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /Totals: 3 passed, 0 failed/);
  assert.doesNotMatch(result.stdout + result.stderr,
    /QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:/);
  process.stdout.write(result.stdout);
}

function testAnnotatedBackendFixtureRuntimeContracts() {
  // The two legacy CLI entrypoints read real settings. Stage only their private
  // runtime fixtures; QtTest still executes the unchanged annotated helpers.
  const script = `
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, sys.argv[1])
def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(sys.argv[1]) / (name + ".test.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
for name in ("compositor-service-warnings", "service-cohort-warnings"):
    with tempfile.TemporaryDirectory(prefix="noctalia-typed-backend-") as temporary:
        directory = Path(temporary)
        module = load(name)
        if name == "compositor-service-warnings":
            module.stage_runtime(directory, None)
        else:
            module.stage_runtime(directory)
        environment = load("media-mini-warnings").isolate_environment(directory)
        result = subprocess.run(["/usr/lib/qt6/bin/qmltestrunner", "-input", str(directory), "-import", str(directory)], env=environment, capture_output=True, text=True, timeout=45)
        print(result.stdout + result.stderr, end="")
        if result.returncode:
            sys.exit(result.returncode)
`;
  const result = spawnSync("python3", ["-c", script, __dirname], {
    encoding: "utf8",
    timeout: 120000,
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.doesNotMatch(result.stdout + result.stderr,
    /QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:/);
  process.stdout.write(result.stdout);
}

function testOwnedPropertyInventory() {
  const contract = { index: "required int", name: "readonly string" };
  const valid = `Item {
    delegate: Rectangle {
      id: row
      readonly property string name: "{ property var index }"
      function probe() { const braces = /[{}]/; return \`\${braces}\`; }
      required property int index
    }
  }`;
  assertOwnedProperties(valid, "Rectangle", "row", contract);
  assertOwnedProperties(valid.replace("delegate: Rectangle", "component Row: Rectangle"), "Rectangle", "row", contract);
  for (
    const invalid of [
      valid.replace("required property int index", "property int index"),
      valid.replace("required property int index", "required property var index"),
      valid.replace("readonly property string name", "property string name"),
      valid.replace("readonly property string name", "readonly property int name"),
      valid.replace("required property int index", "// required property int index"),
      valid.replace("required property int index", "Item { required property int index }"),
      valid.replace("required property int index", "required property int index; required property int index"),
      valid.replace("required property int index", "").replace("id: row", "id: other"),
      valid.replace("id: row", "id: other"),
      valid.replace("delegate: Rectangle", "delegate: Item"),
    ]
  ) {
    assert.throws(() => assertOwnedProperties(invalid, "Rectangle", "row", contract), assert.AssertionError);
  }
  const wrongOwner = `Item {
    Rectangle { id: row; readonly property string name: "row" }
    Rectangle { id: sibling; required property int index }
  }`;
  assert.throws(() => assertOwnedProperties(wrongOwner, "Rectangle", "row", contract), assert.AssertionError);
  const region = "PanelWindow { id: root; readonly property Backgrounds.BackgroundRegion region }";
  const regionContract = { region: "readonly Backgrounds.BackgroundRegion" };
  assertOwnedProperties(region, "PanelWindow", "root", regionContract);
  for (const wrongType of ["Item", "var", "BackgroundsXBackgroundRegion"]) {
    assert.throws(
      () =>
        assertOwnedProperties(
          region.replace("Backgrounds.BackgroundRegion", wrongType),
          "PanelWindow",
          "root",
          regionContract,
        ),
      assert.AssertionError,
    );
  }
}

// These checks inventory declarations on their literal owners, not UI behavior.
// Existing executable gates above remain separate; no field-use/order regex is a
// substitute for those gates or for each feature's dedicated runtime harness.
function assertQmlOwner(relativePath, componentType, ownerId, expected) {
  return assertOwnedProperties(readQml(relativePath), componentType, ownerId, expected);
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
  assertQmlOwner("Modules/MainScreen/SmartPanel.qml", "Item", "root", {
    panelRegion: "readonly BackgroundRegion",
  });

  const source = readQml("Modules/MainScreen/SmartPanel.qml");

  assert.match(source, /readonly\s+property\s+BackgroundRegion\s+panelRegion:\s*panelBackground/);

  assert.doesNotMatch(source, /panelRegion:\s*panelContent\.maskRegion/);
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

  assertQmlOwner(
    "Modules/MainScreen/MainScreen.qml",
    "PanelWindow",
    "root",
    Object.fromEntries(placeholderNames.map((name) => [name, "readonly Backgrounds.BackgroundRegion"])),
  );
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
  assertQmlOwner("Modules/Panels/Settings/SettingsPanel.qml", "Rectangle", "tabItem", {
    index: "required int",
    icon: "required string",
    label: "required string",
  });

  assertQmlOwner("Modules/Panels/Settings/SettingsPanel.qml", "Loader", "tabLoader", {
    index: "required int",
    loadedContent: "readonly Item",
  });

  assert.doesNotMatch(readQml("Modules/Panels/Settings/SettingsPanel.qml"), /modelData\.(?:icon|label)/);
}

function testComboBoxDelegateParentIsTyped() {
  assertPropertyType("Widgets/NComboBox.qml", "parentComboBox", "ComboBox");
}

function testComboBoxDelegateIndexIsTyped() {
  const delegate = assertQmlOwner("Widgets/NComboBox.qml", "ItemDelegate", "delegateRoot", {
    widgetOwner: "required NComboBox",
    index: "required int",
    parentComboBox: "required ComboBox",
    itemIndex: "int",
  });

  assert.match(delegate, /property\s+int\s+itemIndex:\s*delegateRoot\.index/);

  assert.match(readQml("Widgets/NComboBox.qml"), /delegate:\s*OptionDelegate\s*\{/);
}

function testWeatherCardForecastDelegateIndexIsTyped() {
  const delegate = assertQmlOwner("Modules/Cards/WeatherCard.qml", "ColumnLayout", "forecastDay", {
    index: "required int",
  });

  assert.match(delegate, /daily\.time\[forecastDay\.index\]/);
}

function testMediaCardWallpaperChangeInputsAreTyped() {
  const source = readQml("Modules/Cards/MediaCard.qml");

  assert.match(source, /function onWallpaperChanged\(screenName, path\)/, "MediaCard wallpaper change handler must accept signal payloads");
}

function testLockScreenForecastDelegateIndexIsTyped() {
  const delegate = assertQmlOwner("Modules/LockScreen/LockScreen.qml", "ColumnLayout", "forecastDay", {
    index: "required int",
  });

  assert.match(delegate, /daily\.time\[forecastDay\.index\]/);
}

function testChangelogPanelHighlightDelegatesAreTyped() {
  const section = assertQmlOwner("Modules/Panels/Changelog/ChangelogPanel.qml", "ColumnLayout", "releaseSection", {
    entries: "required var",
  });

  assertOwnedProperties(section, "NText", undefined, {
    modelData: "required string",
    headingLevel: "readonly int",
  });

  assert.doesNotMatch(section, /modelData\.entries/);
}

function testNotificationDelegateIndexIsTyped() {
  const card = assertQmlOwner("Modules/Notification/Notification.qml", "Item", "card", {
    index: "required int",
    id: "required string",
    progress: "required real",
    urgency: "required int",
    appName: "required string",
    summary: "required string",
    body: "required string",
    originalImage: "required string",
    actionsJson: "required string",
    timestamp: "required date",
    notificationId: "string",
    animationDelay: "readonly int",
  });

  assert.doesNotMatch(card, /model\.(?:id|appName|summary|body|timestamp|urgency|originalImage|actionsJson|progress)/);
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
  const delegate = assertQmlOwner("Widgets/NDateTimeTokens.qml", "Rectangle", "tokenDelegate", {
    index: "required int",
    category: "required string",
    token: "required string",
    description: "required string",
  });

  assert.match(readQml("Widgets/NDateTimeTokens.qml"), /function getCategoryColor\(category\)/);

  assert.doesNotMatch(delegate, /required\s+property\s+var\s+modelData|modelData\.(?:category|token|description)/);
}

function testSetupCustomizeOptionDelegatesAreTyped() {
  assertQmlOwner("Modules/Panels/SetupWizard/SetupCustomizeStep.qml", "Rectangle", "positionDelegate", {
    key: "required string",
    name: "required string",
  });

  assertQmlOwner("Modules/Panels/SetupWizard/SetupCustomizeStep.qml", "Rectangle", "densityDelegate", {
    key: "required string",
    name: "required string",
  });

  assert.doesNotMatch(readQml("Modules/Panels/SetupWizard/SetupCustomizeStep.qml"), /modelData\.(?:key|name)/);
}

function testColorPickerSwatchDelegatesAreTyped() {
  const source = readQml("Widgets/NColorPickerDialog.qml");
  const themeSwatchDelegate = /model:\s*\[[\s\S]*?name:\s*"mPrimary"[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+swatchName:\s*modelData\s*\?\s*\(modelData\.name\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+color\s+swatchColor:\s*modelData\s*\?\s*\(modelData\.color\s*\|\|\s*NColor\.transparent\)\s*:\s*NColor\.transparent[\s\S]*?color:\s*swatchColor/;
  const paletteSwatchDelegate = /Repeater\s*\{[\s\S]*?model:\s*ColorList\.colors[\s\S]*?Rectangle\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+swatchName:\s*modelData\s*\?\s*\(modelData\.name\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+color\s+swatchColor:\s*modelData\s*\?\s*\(modelData\.color\s*\|\|\s*NColor\.transparent\)\s*:\s*NColor\.transparent[\s\S]*?color:\s*swatchColor/;

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

function testSetupAppearanceSchemeLoaderRolesAreTyped() {
  const loader = assertQmlOwner("Modules/Panels/SetupWizard/SetupAppearanceStep.qml", "Item", "schemeLoader", {
    schemePath: "required string",
    appearanceOwner: "required var",
  });

  assertQmlOwner("Modules/Panels/SetupWizard/SetupAppearanceStep.qml", "Rectangle", "matugenOption", {
    key: "required string",
    name: "required string",
  });

  assert.match(loader, /path:\s*schemeLoader\.schemePath/);

  assert.doesNotMatch(loader, /required\s+property\s+string\s+modelData/);
}

function testFilePickerDelegatesUseTypedFileRoles() {
  for (const ownerId of ["gridItem", "listItem"]) {
    const delegate = assertQmlOwner("Widgets/NFilePicker.qml", "Rectangle", ownerId, {
      picker: "required NFilePicker",
      fileName: "required string",
      filePath: "required string",
      fileIsDir: "required bool",
      fileSize: "required int",
    });
    assert.doesNotMatch(delegate, /model\.file(?:Name|Path|IsDir|Size)/);
  }
}

function testTaskbarWindowDelegateRolesAreTyped() {
  const source = readQml("Modules/Bar/Widgets/Taskbar.qml");
  const taskbarDelegate = /Repeater\s*\{[\s\S]*?model:\s*CompositorService\.windows[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+appId[\s\S]*?required\s+property\s+string\s+title[\s\S]*?required\s+property\s+string\s+output[\s\S]*?required\s+property\s+int\s+workspaceId[\s\S]*?required\s+property\s+bool\s+isFocused/;

  assert.match(source, taskbarDelegate, "Taskbar window delegate must type scalar window roles");
  assert.doesNotMatch(source, /modelData\.(?:appId|title|output|workspaceId|isFocused)/, "Taskbar window delegate must use typed scalar roles instead of modelData.* field reads");
}

function testShortcutsCardWidgetInputsAreTyped() {
  // Object models inject modelData; widgetId is a typed inherited input, not an id role.

  for (const side of ["leftContent", "rightContent"]) {
    const content = assertQmlOwner("Modules/Cards/ShortcutsCard.qml", "RowLayout", side, {});
    const loader = assertOwnedProperties(content, "ControlCenterWidgetLoader", undefined, {
      modelData: "required var",
      index: "required int",
    });
    assert.match(loader, /widgetId:\s*modelData\.id/);
  }

  assertQmlOwner("Modules/Panels/ControlCenter/ControlCenterWidgetLoader.qml", "Item", "root", {
    widgetId: "required string",
    widgetScreen: "required ShellScreen",
    widgetProps: "required var",
  });
}

function testVpnConnectionRowsAreTyped() {
  const delegate = assertQmlOwner(
    "Modules/Panels/VPN/VPNConnectionsList.qml",
    "VPNConnectionItem",
    "connectionDelegate",
    {
      active: "required bool",
      name: "required string",
      uuid: "required string",
    },
  );

  assert.doesNotMatch(delegate, /connection:\s*modelData/);

  assertQmlOwner("Modules/Panels/VPN/VPNConnectionItem.qml", "Rectangle", "root", {
    connectionActive: "required bool",
    connectionName: "required string",
    connectionUuid: "required string",
  });
}

function testSectionEditorWidgetIdsAreTyped() {
  const source = readQml("Widgets/NSectionEditor.qml");
  const widgetDelegate = /Repeater\s*\{[\s\S]*?model:\s*widgetModel[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?id:\s*widgetItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?required\s+property\s+string\s+id[\s\S]*?readonly\s+property\s+string\s+widgetId:\s*id[\s\S]*?widgetHasUserSettings\(widgetId\)[\s\S]*?text:\s*widgetId[\s\S]*?"widgetId":\s*widgetId/;

  assert.match(source, widgetDelegate, "NSectionEditor widget delegate must type id role");
  assert.doesNotMatch(source, /modelData\.id/, "NSectionEditor widget delegate must use typed id role instead of modelData.id");
  assert.doesNotMatch(source, /widgetHasUserSettings\(id\)|text:\s*id|"widgetId":\s*id/, "NSectionEditor widget delegate must use widgetId after declaration");
}

function testSessionMenuPowerOptionRolesAreTyped() {
  assertQmlOwner("Modules/Panels/SessionMenu/SessionMenu.qml", "PowerButton", "powerOption", {
    index: "required int",
    modelData: "required var",
    action: "readonly string",
    optionIsShutdown: "readonly bool",
  });

  assertQmlOwner("Modules/Panels/SessionMenu/SessionMenu.qml", "Rectangle", "buttonRoot", {
    icon: "string",
    title: "string",
    pending: "bool",
    isShutdown: "bool",
    isSelected: "bool",
    timeRemaining: "int",
  });
}

function testCalendarMonthDayDelegateRolesAreTyped() {
  const source = readQml("Modules/Cards/CalendarMonthCard.qml");
  const dayDelegate = /Repeater\s*\{[\s\S]*?model:\s*grid\.daysModel[\s\S]*?Item\s*\{[\s\S]*?id:\s*dayCell[\s\S]*?required\s+property\s+int\s+day[\s\S]*?required\s+property\s+int\s+month[\s\S]*?required\s+property\s+int\s+year[\s\S]*?required\s+property\s+bool\s+today[\s\S]*?required\s+property\s+bool\s+currentMonth[\s\S]*?text:\s*dayCell\.day[\s\S]*?hasEventsOnDate\(dayCell\.year,\s*dayCell\.month,\s*dayCell\.day\)/;
  const weekNumberDelegate = /model:\s*parent\.weekNumbers[\s\S]*?Item\s*\{[\s\S]*?required\s+property\s+int\s+modelData[\s\S]*?text:\s*modelData/;

  assert.match(source, dayDelegate, "CalendarMonthCard day delegate must type scalar date roles");
  assert.match(source, weekNumberDelegate, "CalendarMonthCard week-number delegate must type numeric modelData");
  assert.doesNotMatch(source, /modelData\.(?:day|month|year|today|currentMonth)/, "CalendarMonthCard day delegate must use typed roles instead of modelData scalar date reads");
}

function testAboutTabContributorModelDataIsTyped() {
  // Sliced contributor arrays inject objects, not an unused numeric index role.

  for (const ownerId of ["contributorCard", "contributorLink"]) {
    assertQmlOwner("Modules/Panels/Settings/Tabs/AboutTab.qml", "Rectangle", ownerId, {
      modelData: "required var",
    });
  }
}

function testCustomButtonStateCheckDelegateRolesAreTyped() {
  const delegate = assertQmlOwner(
    "Modules/Panels/Settings/ControlCenter/WidgetSettings/CustomButtonSettings.qml",
    "Item",
    "stateCheckDelegate",
    {
      command: "required string",
      icon: "required string",
      index: "required int",
    },
  );

  assert.doesNotMatch(delegate, /model\.(?:command|icon)/);
}

function testTraySettingsBlacklistDelegateRolesAreTyped() {
  const delegate = assertQmlOwner(
    "Modules/Panels/Settings/Bar/WidgetSettings/TraySettings.qml",
    "Item",
    "blacklistDelegate",
    {
      rule: "required string",
      index: "required int",
    },
  );

  assert.doesNotMatch(delegate, /model\.rule/);
}

function testReorderCheckboxDelegateRolesAreTyped() {
  const delegate = assertQmlOwner("Widgets/NReorderCheckboxes.qml", "Item", "delegateItem", {
    widgetOwner: "required NReorderCheckboxes",
    ownerView: "required ListView",
    index: "required int",
    modelData: "required var",
    id: "required string",
    text: "required string",
    itemEnabled: "readonly bool",
    required: "readonly bool",
    isDisabled: "readonly bool",
    canDrag: "readonly bool",
  });

  assert.doesNotMatch(delegate, /required\s+property\s+bool\s+enabled|modelData\.(?:id|text)/);

  assert.match(readQml("Widgets/NReorderCheckboxes.qml"), /delegate:\s*ChecklistItem\s*\{/);
}

function testSessionMenuTabEntryDelegateRolesAreTyped() {
  const source = readQml("Modules/Panels/Settings/Tabs/SessionMenuTab.qml");
  const entryDelegate = /ListView\s*\{[\s\S]*?model:\s*entriesModel[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?id:\s*delegateItem[\s\S]*?required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+id[\s\S]*?required\s+property\s+string\s+text[\s\S]*?required\s+property\s+bool\s+countdownEnabled[\s\S]*?readonly\s+property\s+bool\s+entryEnabled:\s*modelData\s*\?\s*modelData\.enabled\s*===\s*true\s*:\s*false[\s\S]*?color:\s*delegateItem\.entryEnabled\s*\?\s*NColor\.mPrimary[\s\S]*?text:\s*delegateItem\.text[\s\S]*?checked:\s*delegateItem\.countdownEnabled/;

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
  const cardDelegate = /Repeater\s*\{[\s\S]*?model:\s*Settings\.data\.controlCenter\.cards[\s\S]*?Loader\s*\{[\s\S]*?required\s+property\s+var\s+modelData[\s\S]*?readonly\s+property\s+string\s+cardId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+bool\s+cardEnabled:\s*modelData\s*\?\s*modelData\.enabled\s*===\s*true\s*:\s*false[\s\S]*?active:\s*root\.shouldLoadCard\(cardEnabled,\s*cardId\)[\s\S]*?switch\s*\(cardId\)/;

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

function testContextMenuPopupOwnerContract() {
  // The component itself owns Popup API; no valid delegate popup proxy existed.

  const popup = assertQmlOwner("Widgets/NContextMenu.qml", "Popup", "root", {
    model: "alias",
    itemHeight: "real",
    itemPadding: "real",
    verticalPolicy: "int",
    horizontalPolicy: "int",
  });

  assert.match(popup, /signal\s+triggered\(string\s+action\)/);

  assert.doesNotMatch(popup, /property\s+\w+\s+popup\b/);
}

function testContextMenuDelegateRolesAreTyped() {
  const delegate = assertQmlOwner("Widgets/NContextMenu.qml", "ItemDelegate", "menuItem", {
    modelData: "required var",
    index: "required int",
    itemVisible: "readonly bool",
    itemEnabled: "readonly bool",
    itemIcon: "readonly string",
    hasIcon: "readonly bool",
    itemText: "readonly string",
    itemAction: "readonly string",
  });

  assert.match(delegate, /root\.triggered\(menuItem\.itemAction\)/);

  assert.match(readQml("Widgets/NContextMenu.qml"), /function openAt\(x, y\)/);

  assert.match(readQml("Widgets/NContextMenu.qml"), /function openAtItem\(item, mouseX, mouseY\)/);
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

function testGeometryOwnersAreTyped() {
  assertQmlOwner("Modules/Bar/Bar.qml", "Item", "root", {
    barItem: "readonly Item",
    barRegion: "readonly Item",
  });

  assertQmlOwner("Modules/MainScreen/MainScreen.qml", "Backgrounds.BackgroundRegion", "barPlaceholder", {
    screen: "ShellScreen",
    screenWidth: "readonly real",
    screenHeight: "readonly real",
  });

  assertQmlOwner("Modules/MainScreen/SmartPanel.qml", "Item", "root", {
    panelRegion: "readonly BackgroundRegion",
  });

  assertQmlOwner("Modules/MainScreen/Backgrounds/PanelBackground.qml", "ShapePath", "root", {
    panelBg: "readonly BackgroundRegion",
  });

  assertOwnedProperties(readQml("Modules/MainScreen/Backgrounds/BackgroundRegion.qml"), "Item", undefined, {
    topLeftCornerState: "int",
    topRightCornerState: "int",
    bottomRightCornerState: "int",
    bottomLeftCornerState: "int",
  });
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

  const previews = extractComponentBlocks(source, "Repeater")
    .filter((block) =>
      /model:\s*I18n\.locale\.toString\(root\.now,\s*root\.valueFormat(?:Horizontal|Vertical)\.trim\(\)\)/.test(block)
    );

  assert.equal(previews.length, 2, "horizontal and vertical typed preview delegates");

  for (const preview of previews) {
    assertOwnedProperties(preview, "NText", undefined, { modelData: "required string" });
  }

  assert.match(source, /toString\(root\.now,\s*root\.valueFormatHorizontal\.trim\(\)\)/);

  assert.match(source, /toString\(root\.now,\s*root\.valueFormatVertical\.trim\(\)\)/);
}

function testMangoPatternContainerIsTyped() {
  assertQmlOwner("Services/Compositor/MangoService.qml", "QtObject", "internal", {
    _patterns: "readonly QtObject",
  });

  assertQmlOwner("Services/Compositor/MangoService.qml", "QtObject", "patterns", {
    tagDetail: "readonly var",
    tagBinary: "readonly var",
    layout: "readonly var",
    metadata: "readonly var",
    kbLayout: "readonly var",
    scale: "readonly var",
    selmon: "readonly var",
  });
}

function testPopupMenuWindowActiveMenuIsTyped() {
  const popupMenuWindowFile = "Modules/MainScreen/PopupMenuWindow.qml";

  assertPropertyType(popupMenuWindowFile, "activeMenu", "QtObject");
  assertNoPropertyType(popupMenuWindowFile, "activeMenu", "var");
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
  assertQmlOwner("Modules/Dock/DockMenu.qml", "Rectangle", "menuEntry", {
    modelData: "required var",
    index: "required int",
    menuIcon: "readonly string",
    menuText: "readonly string",
  });
}

function testLauncherPluginBackReferencesAreTyped() {
  for (const plugin of ["Applications", "Calculator", "Clipboard"]) {
    assertPropertyType(`Modules/Panels/Launcher/Plugins/${plugin}Plugin.qml`, "launcher", "Item");
  }

  assertQmlOwner("Modules/Panels/Launcher/Plugins/EmojiPlugin.qml", "Item", "root", {
    launcher: "Launcher",
  });
}

function testCompositorBackendIsTyped() {
  const compositorServiceFile = "Services/Compositor/CompositorService.qml";

  assertPropertyType(compositorServiceFile, "backend", "Item");
  assertNoPropertyType(compositorServiceFile, "backend", "var");
}

function testPowerProfilesReferenceIsTyped() {
  assertQmlOwner("Services/Power/PowerProfileService.qml", "Singleton", "root", {
    powerProfiles: "readonly PowerProfiles",
  });
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
  const device = assertQmlOwner("Modules/Panels/Bluetooth/BluetoothDevicesList.qml", "Rectangle", "device", {
    modelData: "required BluetoothDevice",
    index: "required int",
    devicePairing: "readonly bool",
    deviceBlocked: "readonly bool",
    deviceConnected: "readonly bool",
    deviceConnecting: "readonly bool",
    deviceDisplayName: "readonly string",
    hasBattery: "readonly bool",
    canConnect: "readonly bool",
    canDisconnect: "readonly bool",
    isBusy: "readonly bool",
  });

  // Installed BluetoothDevice has no signal-strength API (bluetooth.md).

  assert.doesNotMatch(
    device,
    /\b(?:hasSignalStrength|deviceSignalStrength|showSignalStrength)\b|modelData\.signalStrength/,
  );
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
  const sinkDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sinks[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+deviceId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+deviceDescription:\s*modelData\s*\?\s*\(modelData\.description\s*\|\|\s*deviceId\)\s*:\s*deviceId[\s\S]*?text:\s*deviceDescription/;
  const sourceDelegate = /Repeater\s*\{[\s\S]*?model:\s*AudioService\.sources[\s\S]*?NRadioButton\s*\{[\s\S]*?required\s+property\s+PwNode\s+modelData[\s\S]*?required\s+property\s+int\s+index[\s\S]*?readonly\s+property\s+string\s+deviceId:\s*modelData\s*\?\s*\(modelData\.id\s*\|\|\s*""\)\s*:\s*""[\s\S]*?readonly\s+property\s+string\s+deviceDescription:\s*modelData\s*\?\s*\(modelData\.description\s*\|\|\s*deviceId\)\s*:\s*deviceId[\s\S]*?text:\s*deviceDescription/;

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
  assertQmlOwner("Modules/Panels/Process/ProcessPanel.qml", "Rectangle", "processDelegate", {
    modelData: "required var",
    index: "required int",
    processCommand: "readonly string",
    processName: "readonly string",
    processCpu: "readonly real",
    processMemoryKb: "readonly int",
    processPid: "readonly int",
    processCpuColor: "readonly color",
  });
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
  assertQmlOwner("Modules/Bar/Widgets/Tray.qml", "Item", "root", {
    popupMenuWindow: "readonly QtObject",
  });

  assertQmlOwner("Modules/Bar/Widgets/Tray.qml", "Item", "trayDelegate", {
    popupMenuWindow: "QtObject",
  });

  assertQmlOwner("Modules/Panels/Tray/TrayDrawerPanel.qml", "SmartPanel", "root", {
    popupMenuWindow: "readonly PopupMenuWindow",
  });
}

function testSectionEditorRegistryIsTyped() {
  const sectionEditorFile = "Widgets/NSectionEditor.qml";

  assertPropertyType(sectionEditorFile, "widgetRegistry", "QtObject");
  assertNoPropertyType(sectionEditorFile, "widgetRegistry", "var");
}

function testDisplayTabBrightnessMonitorIsTyped() {
  assertQmlOwner("Modules/Panels/Settings/Tabs/DisplayTab.qml", "Rectangle", "monitorCard", {
    brightnessMonitor: "BrightnessService.Monitor",
  });
}

function testBrightnessPanelBrightnessMonitorIsTyped() {
  assertQmlOwner("Modules/Panels/Brightness/BrightnessPanel.qml", "NBox", "monitorBox", {
    brightnessMonitor: "BrightnessService.Monitor",
  });
}

function testBrightnessServiceMonitorScreenModelAliasIsTyped() {
  const brightnessServiceFile = "Services/Hardware/BrightnessService.qml";
  const source = readQml(brightnessServiceFile);
  const monitorComponent = /component\s+Monitor:\s+QtObject\s*\{[\s\S]*?required\s+property\s+ShellScreen\s+modelData[\s\S]*?readonly\s+property\s+string\s+screenModel:\s+modelData\s*\?\s*modelData\.model\s*:\s*""/;

  assert.match(source, monitorComponent, "BrightnessService Monitor must expose null-safe typed screenModel alias from ShellScreen modelData");
  // Display detection behavior is covered by brightness-service-guards.test.js
  // and Qml/BrightnessServiceOffscreenHarness.qml, not source construction.

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
  assertQmlOwner("Modules/MainScreen/Backgrounds/PanelBackground.qml", "ShapePath", "root", {
    panel: "required BackgroundRegion",
  });
}

function testBarBackgroundBarReferenceIsTyped() {
  assertQmlOwner("Modules/MainScreen/Backgrounds/AllBackgrounds.qml", "Item", "root", {
    bar: "required BackgroundRegion",
  });

  assertQmlOwner("Modules/MainScreen/Backgrounds/BarBackground.qml", "ShapePath", "root", {
    bar: "required BackgroundRegion",
  });
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
  assertQmlOwner("Modules/Background/Background.qml", "Loader", "wallpaperLoader", {
    modelData: "required ShellScreen",
  });

  const window = assertQmlOwner("Modules/Background/Background.qml", "PanelWindow", "root", {
    monitorScreen: "readonly ShellScreen",
    monitorName: "readonly string",
    monitorWidth: "readonly int",
    monitorHeight: "readonly int",
  });

  assert.match(window, /monitorScreen:\s*wallpaperLoader\.modelData/);
}

function testOverviewScreenAliasIsTyped() {
  assertQmlOwner("Modules/Background/Overview.qml", "PanelWindow", "panelWindow", {
    modelData: "required ShellScreen",
    monitorName: "readonly string",
  });
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
  assertQmlOwner("Modules/Panels/Wallpaper/WallpaperPanel.qml", "ColumnLayout", "wallhavenItem", {
    owningGrid: "readonly WallhavenGrid",
    screenView: "readonly WallhavenView",
    modelData: "required var",
    index: "required int",
    thumbnailUrl: "readonly string",
    wallpaperId: "readonly string",
  });

  assert.match(readQml("Modules/Panels/Wallpaper/WallpaperPanel.qml"), /delegate:\s*WallhavenWallpaperDelegate\s*\{/);
}

function testWallpaperTabMonitorNameAliasIsTyped() {
  assertQmlOwner("Modules/Panels/Settings/Tabs/WallpaperTab.qml", "ColumnLayout", "monitorDirectory", {
    modelData: "required ShellScreen",
    monitorName: "readonly string",
  });
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
  assertQmlOwner("Modules/Panels/Settings/Tabs/BarTab.qml", "NCheckbox", "monitorCheckbox", {
    modelData: "required ShellScreen",
    monitorName: "readonly string",
    monitorModel: "readonly string",
    monitorWidth: "readonly int",
    monitorHeight: "readonly int",
  });
}

function testDisplayTabMonitorAliasesAreTyped() {
  assertQmlOwner("Modules/Panels/Settings/Tabs/DisplayTab.qml", "Rectangle", "monitorCard", {
    modelData: "required ShellScreen",
    monitorName: "readonly string",
    monitorModel: "readonly string",
    monitorWidth: "readonly int",
    monitorHeight: "readonly int",
  });
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
  assertQmlOwner("Services/UI/WallpaperService.qml", "FolderListModel", "wallpaperScanner", {
    modelData: "required ShellScreen",
    screenName: "readonly string",
    currentDirectory: "string",
  });
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
  assertQmlOwner("Modules/Panels/SetupWizard/SetupWizard.qml", "RowLayout", "progressStep", {
    modelData: "required var",
    index: "required int",
    stepIcon: "readonly string",
    stepLabel: "readonly string",
  });
}

function testBrightnessPanelScreenModelIsTyped() {
  assertQmlOwner("Modules/Panels/Brightness/BrightnessPanel.qml", "NBox", "monitorBox", {
    modelData: "required ShellScreen",
    monitorName: "readonly string",
    monitorModel: "readonly string",
    monitorWidth: "readonly int",
    monitorHeight: "readonly int",
  });
}

function testWiFiNetworkDelegateAliasesAreTyped() {
  assertQmlOwner("Modules/Panels/WiFi/WiFiNetworksList.qml", "Rectangle", "networkItem", {
    modelData: "required var",
    networkSsid: "readonly string",
    networkConnected: "readonly bool",
    networkSignal: "readonly int",
    networkSecurity: "readonly string",
    networkExisting: "readonly bool",
    networkCached: "readonly bool",
  });
}

const tests = [
  testOwnedPropertyInventory,
  testAnnotatedSignatureExtraction,
  testQmlFunctionTypeContractInventory,
  testAnnotatedFunctionRuntimeContracts,
  testAnnotatedPopupFunctionRuntimeContracts,
  testAnnotatedBackendFixtureRuntimeContracts,
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
  testSetupAppearanceSchemeLoaderRolesAreTyped,
  testFilePickerDelegatesUseTypedFileRoles,
  testTaskbarWindowDelegateRolesAreTyped,
  testShortcutsCardWidgetInputsAreTyped,
  testVpnConnectionRowsAreTyped,
  testSectionEditorWidgetIdsAreTyped,
  testSessionMenuPowerOptionRolesAreTyped,
  testCalendarMonthDayDelegateRolesAreTyped,
  testAboutTabContributorModelDataIsTyped,
  testCustomButtonStateCheckDelegateRolesAreTyped,
  testTraySettingsBlacklistDelegateRolesAreTyped,
  testReorderCheckboxDelegateRolesAreTyped,
  testSessionMenuTabEntryDelegateRolesAreTyped,
  testColorSchemeTabSchemeModelDataIsTyped,
  testSchemeDownloaderDelegatesAreTyped,
  testControlCenterPanelCardDelegateIsTyped,
  testClockPanelCardDelegateIsTyped,
  testPanelServiceOpenedPanelIsTyped,
  testContextMenuPopupOwnerContract,
  testContextMenuDelegateRolesAreTyped,
  testPopupContextMenuDelegateRolesAreTyped,
  testGeometryOwnersAreTyped,
  testTimeNowPropertiesAreTypedDates,
  testEffectSourcePropertiesAreTyped,
  testBarWidgetLoaderScreenIsTyped,
  testBarWidgetDelegatesUseTypedWidgetIdAliases,
  testControlCenterWidgetLoaderScreenIsTyped,
  testClockSettingsFocusedInputIsTyped,
  testClockSettingsPreviewModelsAreTyped,
  testMangoPatternContainerIsTyped,
  testPopupMenuWindowActiveMenuIsTyped,
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
