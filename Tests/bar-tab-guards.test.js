#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testBarTabAddWidgetGuards() {
  const source = readQml("Modules/Panels/Settings/Tabs/BarTab.qml");
  const body = extractFunctionBody(source, "_addWidgetToSection");

  assert.match(body, /var newWidget = \{[\s\S]*"id": widgetId[\s\S]*\}/, "_addWidgetToSection must create widget entry with id");
  assert.match(body, /if \(BarWidgetRegistry\.widgetHasUserSettings\(widgetId\)\)/, "_addWidgetToSection must copy user settings metadata only for configurable widgets");
  assert.match(body, /var metadata = BarWidgetRegistry\.widgetMetadata\[widgetId\][\s\S]*if \(metadata\)/, "_addWidgetToSection must guard missing widget metadata");
  assert.match(body, /Object\.keys\(metadata\)\.forEach\(function \(key\)[\s\S]*if \(key !== "allowUserSettings"\)[\s\S]*newWidget\[key\] = metadata\[key\]/, "_addWidgetToSection must copy metadata except allowUserSettings");
  assert.match(body, /Settings\.data\.bar\.widgets\[section\]\.push\(newWidget\)/, "_addWidgetToSection must append to the target section");
}

function testBarTabRemoveAndReorderGuards() {
  const source = readQml("Modules/Panels/Settings/Tabs/BarTab.qml");
  const removeBody = extractFunctionBody(source, "_removeWidgetFromSection");
  const reorderBody = extractFunctionBody(source, "_reorderWidgetInSection");

  assert.match(removeBody, /if \(index >= 0 && index < Settings\.data\.bar\.widgets\[section\]\.length\)/, "_removeWidgetFromSection must validate index bounds");
  assert.match(removeBody, /var newArray = Settings\.data\.bar\.widgets\[section\]\.slice\(\)[\s\S]*var removedWidgets = newArray\.splice\(index, 1\)[\s\S]*Settings\.data\.bar\.widgets\[section\] = newArray/, "_removeWidgetFromSection must replace section with copied array");
  assert.match(removeBody, /removedWidgets\[0\]\.id === "ControlCenter" && BarService\.lookupWidget\("ControlCenter"\) === undefined/, "_removeWidgetFromSection must detect missing ControlCenter after removal");
  assert.match(removeBody, /ToastService\.showWarning\(I18n\.tr\("toast\.missing-control-center\.label"\), I18n\.tr\("toast\.missing-control-center\.description"\), 12000\)/, "_removeWidgetFromSection must warn when ControlCenter would be missing");
  assert.match(reorderBody, /fromIndex >= 0 && fromIndex < Settings\.data\.bar\.widgets\[section\]\.length && toIndex >= 0 && toIndex < Settings\.data\.bar\.widgets\[section\]\.length/, "_reorderWidgetInSection must validate source and target bounds");
  assert.match(reorderBody, /var newArray = Settings\.data\.bar\.widgets\[section\]\.slice\(\)[\s\S]*var item = newArray\[fromIndex\][\s\S]*newArray\.splice\(fromIndex, 1\)[\s\S]*newArray\.splice\(toIndex, 0, item\)[\s\S]*Settings\.data\.bar\.widgets\[section\] = newArray/, "_reorderWidgetInSection must reorder through a copied array");
}

function testBarTabUpdateAndMoveGuards() {
  const source = readQml("Modules/Panels/Settings/Tabs/BarTab.qml");
  const updateBody = extractFunctionBody(source, "_updateWidgetSettingsInSection");
  const moveBody = extractFunctionBody(source, "_moveWidgetBetweenSections");

  assert.match(updateBody, /Settings\.data\.bar\.widgets\[section\]\[index\] = settings/, "_updateWidgetSettingsInSection must replace widget settings at index");
  assert.match(moveBody, /if \(index >= 0 && index < Settings\.data\.bar\.widgets\[fromSection\]\.length\)/, "_moveWidgetBetweenSections must validate source bounds");
  assert.match(moveBody, /var widget = Settings\.data\.bar\.widgets\[fromSection\]\[index\]/, "_moveWidgetBetweenSections must read source widget before mutation");
  assert.match(moveBody, /var sourceArray = Settings\.data\.bar\.widgets\[fromSection\]\.slice\(\)[\s\S]*sourceArray\.splice\(index, 1\)[\s\S]*Settings\.data\.bar\.widgets\[fromSection\] = sourceArray/, "_moveWidgetBetweenSections must remove via copied source array");
  assert.match(moveBody, /var targetArray = Settings\.data\.bar\.widgets\[toSection\]\.slice\(\)[\s\S]*targetArray\.push\(widget\)[\s\S]*Settings\.data\.bar\.widgets\[toSection\] = targetArray/, "_moveWidgetBetweenSections must append via copied target array");
}

function testBarTabAvailableWidgetModelGuards() {
  const source = readQml("Modules/Panels/Settings/Tabs/BarTab.qml");
  const locationsBody = extractFunctionBody(source, "getWidgetLocations");
  const updateModelBody = extractFunctionBody(source, "updateAvailableWidgetsModel");

  assert.match(locationsBody, /if \(!BarService\)[\s\S]*return \[\]/, "getWidgetLocations must fail closed without BarService");
  assert.match(locationsBody, /const instances = BarService\.getAllRegisteredWidgets\(\)[\s\S]*const locations = \{\}/, "getWidgetLocations must read registered widgets and collect unique locations");
  assert.match(locationsBody, /if \(instances\[i\]\.widgetId === widgetId\)[\s\S]*section === "left"[\s\S]*locations\["L"\] = true[\s\S]*section === "center"[\s\S]*locations\["C"\] = true[\s\S]*section === "right"[\s\S]*locations\["R"\] = true/, "getWidgetLocations must map sections to compact badges");
  assert.match(locationsBody, /return Object\.keys\(locations\)\.join\(''\)/, "getWidgetLocations must return compact badge string");
  assert.match(updateModelBody, /availableWidgets\.clear\(\)[\s\S]*const widgets = BarWidgetRegistry\.getAvailableWidgets\(\)/, "updateAvailableWidgetsModel must rebuild from registry");
  assert.match(updateModelBody, /availableWidgets\.append\(\{[\s\S]*"key": entry,[\s\S]*"name": entry,[\s\S]*"badgeLocations": getWidgetLocations\(entry\)/, "updateAvailableWidgetsModel must append key/name/badge model entries");
}

const tests = [
  testBarTabAddWidgetGuards,
  testBarTabRemoveAndReorderGuards,
  testBarTabUpdateAndMoveGuards,
  testBarTabAvailableWidgetModelGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
