#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testDockMenuWidthAndItems() {
  const source = readQml("Modules/Dock/DockMenu.qml");
  const widthBody = extractFunctionBody(source, "calculateMenuWidth");
  const initBody = extractFunctionBody(source, "initItems");

  assert.match(widthBody, /let maxWidth = 0/, "calculateMenuWidth must start from zero width");
  assert.match(widthBody, /if \(root\.items && root\.items\.length > 0\)/, "calculateMenuWidth must tolerate empty menus");
  assert.match(widthBody, /let itemWidth = Style\.marginS \* 2/, "calculateMenuWidth must include horizontal margins");
  assert.match(widthBody, /if \(item\.icon && item\.icon !== ""\)[\s\S]*itemWidth \+= Style\.fontSizeL \+ Style\.marginS/, "calculateMenuWidth must include icon width and spacing");
  assert.match(widthBody, /textMeasure\.text = item\.text \|\| ""[\s\S]*textMeasure\.forceLayout\(\)[\s\S]*itemWidth \+= textMeasure\.contentWidth/, "calculateMenuWidth must measure item text width");
  assert.match(widthBody, /menuContentWidth = Math\.max\(160, maxWidth\)/, "calculateMenuWidth must enforce minimum width");
  assert.match(initBody, /const isRunning = root\.toplevel && ToplevelManager && ToplevelManager\.toplevels\.values\.includes\(root\.toplevel\)/, "initItems must detect running toplevels");
  assert.match(initBody, /const isPinned = root\.toplevel && root\.isAppPinned\(root\.toplevel\.appId\)/, "initItems must detect pinned apps");
  assert.match(initBody, /if \(isRunning\)[\s\S]*"icon": "eye"[\s\S]*handleFocus\(\)/, "initItems must add focus action for running apps");
  assert.match(initBody, /"icon": !isPinned \? "pin" : "unpin"[\s\S]*"text": !isPinned \? I18n\.tr\("dock\.menu\.pin"\) : I18n\.tr\("dock\.menu\.unpin"\)[\s\S]*handlePin\(\)/, "initItems must add pin or unpin action");
  assert.match(initBody, /if \(isRunning\)[\s\S]*"icon": "close"[\s\S]*handleClose\(\)/, "initItems must add close action for running apps");
  assert.match(initBody, /DesktopEntries\.heuristicLookup\) \? DesktopEntries\.heuristicLookup\(appId\) : DesktopEntries\.byId\(appId\)/, "initItems must resolve desktop entries");
  assert.match(initBody, /entry\.actions\.forEach\(function \(action\)[\s\S]*"text": action\.name[\s\S]*action\.execute\(\)/, "initItems must append desktop entry actions");
  assert.match(initBody, /root\.items = next[\s\S]*Qt\.callLater\(\(\) =>[\s\S]*calculateMenuWidth\(\)/, "initItems must publish items and recalculate width later");
}

function testDockMenuPinHelpers() {
  const source = readQml("Modules/Dock/DockMenu.qml");
  const normalizeBody = extractFunctionBody(source, "normalizeAppId");
  const desktopBody = extractFunctionBody(source, "getDesktopEntryId");
  const pinnedBody = extractFunctionBody(source, "isAppPinned");
  const toggleBody = extractFunctionBody(source, "toggleAppPin");

  assert.match(normalizeBody, /if \(!appId \|\| typeof appId !== 'string'\)\s+return ""/, "normalizeAppId must reject missing or non-string ids");
  assert.match(normalizeBody, /return appId\.toLowerCase\(\)\.trim\(\)/, "normalizeAppId must normalize case and whitespace");
  assert.match(desktopBody, /if \(!appId\)\s+return appId/, "getDesktopEntryId must return missing app ids unchanged");
  assert.match(desktopBody, /DesktopEntries\.heuristicLookup[\s\S]*const entry = DesktopEntries\.heuristicLookup\(appId\)[\s\S]*if \(entry && entry\.id\)[\s\S]*return entry\.id/, "getDesktopEntryId must prefer heuristic desktop entry lookup");
  assert.match(desktopBody, /DesktopEntries\.byId[\s\S]*const entry = DesktopEntries\.byId\(appId\)[\s\S]*if \(entry && entry\.id\)[\s\S]*return entry\.id/, "getDesktopEntryId must fall back to direct desktop entry lookup");
  assert.match(desktopBody, /return appId/, "getDesktopEntryId must fall back to the original app id");
  assert.match(pinnedBody, /if \(!appId\)\s+return false/, "isAppPinned must reject missing app ids");
  assert.match(pinnedBody, /const pinnedApps = Settings\.data\.dock\.pinnedApps \|\| \[\]/, "isAppPinned must tolerate missing pinned app settings");
  assert.match(pinnedBody, /const normalizedId = normalizeAppId\(appId\)/, "isAppPinned must normalize the target id");
  assert.match(pinnedBody, /return pinnedApps\.some\(pinnedId => normalizeAppId\(pinnedId\) === normalizedId\)/, "isAppPinned must compare ids case-insensitively");
  assert.match(toggleBody, /if \(!appId\)\s+return;/, "toggleAppPin must reject missing app ids");
  assert.match(toggleBody, /const desktopEntryId = getDesktopEntryId\(appId\)[\s\S]*const normalizedId = normalizeAppId\(desktopEntryId\)/, "toggleAppPin must pin canonical desktop entry ids");
  assert.match(toggleBody, /let pinnedApps = \(Settings\.data\.dock\.pinnedApps \|\| \[\]\)\.slice\(\)/, "toggleAppPin must copy pinned app settings before mutation");
  assert.match(toggleBody, /const existingIndex = pinnedApps\.findIndex\(pinnedId => normalizeAppId\(pinnedId\) === normalizedId\)/, "toggleAppPin must find existing pins case-insensitively");
  assert.match(toggleBody, /if \(isPinned\)[\s\S]*pinnedApps\.splice\(existingIndex, 1\)[\s\S]*else[\s\S]*pinnedApps\.push\(desktopEntryId\)/, "toggleAppPin must unpin existing apps or pin new ones");
  assert.match(toggleBody, /Settings\.data\.dock\.pinnedApps = pinnedApps/, "toggleAppPin must persist the updated pinned apps");
}

function testDockMenuActionsAndHovering() {
  const source = readQml("Modules/Dock/DockMenu.qml");
  const hideBody = extractFunctionBody(source, "hide");
  const hoverBody = extractFunctionBody(source, "getHoveredItem");
  const focusBody = extractFunctionBody(source, "handleFocus");
  const pinBody = extractFunctionBody(source, "handlePin");
  const closeBody = extractFunctionBody(source, "handleClose");

  assert.match(hideBody, /visible = false[\s\S]*root\.items\.length = 0/, "hide must close the menu and clear items");
  assert.match(hoverBody, /const itemHeight = 32[\s\S]*const startY = Style\.marginM[\s\S]*const relativeY = mouseY - startY/, "getHoveredItem must account for menu margin and item height");
  assert.match(hoverBody, /if \(relativeY < 0\)\s+return -1/, "getHoveredItem must reject positions above the menu");
  assert.match(hoverBody, /const itemIndex = Math\.floor\(relativeY \/ itemHeight\)/, "getHoveredItem must compute hovered item index");
  assert.match(hoverBody, /return itemIndex >= 0 && itemIndex < root\.items\.length \? itemIndex : -1/, "getHoveredItem must clamp to existing items");
  assert.match(focusBody, /if \(root\.toplevel && root\.toplevel\.activate\)[\s\S]*root\.toplevel\.activate\(\)/, "handleFocus must activate focusable toplevels");
  assert.match(focusBody, /root\.requestClose\(\)/, "handleFocus must request menu close");
  assert.match(pinBody, /if \(root\.toplevel && root\.toplevel\.appId\)[\s\S]*root\.toggleAppPin\(root\.toplevel\.appId\)/, "handlePin must toggle the toplevel app pin");
  assert.match(pinBody, /root\.requestClose\(\)/, "handlePin must request menu close");
  assert.match(closeBody, /const isValidToplevel = root\.toplevel && ToplevelManager && ToplevelManager\.toplevels\.values\.includes\(root\.toplevel\)/, "handleClose must validate the toplevel before closing");
  assert.match(closeBody, /if \(isValidToplevel && root\.toplevel\.close\)[\s\S]*root\.toplevel\.close\(\)/, "handleClose must close valid toplevels");
  assert.match(closeBody, /if \(root\.onAppClosed && typeof root\.onAppClosed === "function"\)[\s\S]*Qt\.callLater\(root\.onAppClosed\)/, "handleClose must schedule dock refresh callback");
  assert.match(closeBody, /root\.hide\(\)[\s\S]*root\.requestClose\(\)/, "handleClose must hide and request close");
}

const tests = [
  testDockMenuWidthAndItems,
  testDockMenuPinHelpers,
  testDockMenuActionsAndHovering,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
