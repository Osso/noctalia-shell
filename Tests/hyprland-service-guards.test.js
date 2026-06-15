#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testHyprlandStartupQueriesAndSafeUpdatePipeline() {
  const source = readQml("Services/Compositor/HyprlandService.qml");
  const initializeBody = extractFunctionBody(source, "initialize");
  const scalesBody = extractFunctionBody(source, "queryDisplayScales");
  const keyboardBody = extractFunctionBody(source, "queryKeyboardLayout");
  const updateBody = extractFunctionBody(source, "safeUpdate");

  assert.match(initializeBody, /if \(initialized\)\s+return;/, "initialize must be idempotent");
  assert.match(initializeBody, /Hyprland\.refreshWorkspaces\(\)/, "initialize must refresh Hyprland workspaces");
  assert.match(initializeBody, /Hyprland\.refreshToplevels\(\)/, "initialize must refresh Hyprland toplevels");
  assert.match(initializeBody, /Qt\.callLater\(\(\) =>[\s\S]*safeUpdateWorkspaces\(\)[\s\S]*safeUpdateWindows\(\)[\s\S]*queryDisplayScales\(\)[\s\S]*queryKeyboardLayout\(\)/, "initialize must defer initial cache refreshes");
  assert.match(initializeBody, /initialized = true/, "initialize must mark the service initialized after scheduling startup work");
  assert.match(initializeBody, /Logger\.e\("HyprlandService",\s*"Failed to initialize:",\s*e\)/, "initialize must log startup failures");
  assert.match(scalesBody, /hyprlandMonitorsProcess\.running = true/, "queryDisplayScales must start the monitors process");
  assert.match(keyboardBody, /hyprlandDevicesProcess\.running = true/, "queryKeyboardLayout must start the devices process");
  assert.match(updateBody, /safeUpdateWindows\(\)[\s\S]*safeUpdateWorkspaces\(\)[\s\S]*windowListChanged\(\)/, "safeUpdate must refresh windows and workspaces before emitting changes");
}

function testHyprlandWorkspaceAndOccupancyGuards() {
  const source = readQml("Services/Compositor/HyprlandService.qml");
  const workspacesBody = extractFunctionBody(source, "safeUpdateWorkspaces");
  const occupiedBody = extractFunctionBody(source, "getOccupiedWorkspaceIds");

  assert.match(workspacesBody, /workspaces\.clear\(\)/, "safeUpdateWorkspaces must clear stale workspace rows");
  assert.match(workspacesBody, /workspaceCache = \{\}/, "safeUpdateWorkspaces must reset the workspace cache");
  assert.match(workspacesBody, /!Hyprland\.workspaces \|\| !Hyprland\.workspaces\.values[\s\S]*return;/, "safeUpdateWorkspaces must tolerate missing Hyprland workspace data");
  assert.match(workspacesBody, /const occupiedIds = getOccupiedWorkspaceIds\(\)/, "safeUpdateWorkspaces must derive occupancy from toplevels");
  assert.match(workspacesBody, /if \(!ws \|\| ws\.id < 1\)\s+continue;/, "safeUpdateWorkspaces must skip invalid workspaces");
  assert.match(workspacesBody, /"isFocused": ws\.focused === true/, "safeUpdateWorkspaces must normalize focused state");
  assert.match(workspacesBody, /"isOccupied": occupiedIds\[ws\.id\] === true/, "safeUpdateWorkspaces must normalize occupancy state");
  assert.match(workspacesBody, /workspaceCache\[ws\.id\] = wsData[\s\S]*workspaces\.append\(wsData\)/, "safeUpdateWorkspaces must cache and append normalized workspace rows");
  assert.match(workspacesBody, /Logger\.e\("HyprlandService",\s*"Error updating workspaces:",\s*e\)/, "safeUpdateWorkspaces must log update failures");
  assert.match(occupiedBody, /const occupiedIds = \{\}/, "getOccupiedWorkspaceIds must default to an empty map");
  assert.match(occupiedBody, /!Hyprland\.toplevels \|\| !Hyprland\.toplevels\.values[\s\S]*return occupiedIds/, "getOccupiedWorkspaceIds must fail closed when toplevels are unavailable");
  assert.match(occupiedBody, /const wsId = toplevel\.workspace \? toplevel\.workspace\.id : null/, "getOccupiedWorkspaceIds must read workspace IDs defensively");
  assert.match(occupiedBody, /occupiedIds\[wsId\] = true/, "getOccupiedWorkspaceIds must mark occupied workspace IDs");
  assert.match(occupiedBody, /return occupiedIds/, "getOccupiedWorkspaceIds must return the occupancy map");
}

function testHyprlandWindowDataNormalizationGuards() {
  const source = readQml("Services/Compositor/HyprlandService.qml");
  const windowsBody = extractFunctionBody(source, "safeUpdateWindows");
  const extractBody = extractFunctionBody(source, "extractWindowData");
  const titleBody = extractFunctionBody(source, "getAppTitle");
  const appIdBody = extractFunctionBody(source, "getAppId");
  const propertyBody = extractFunctionBody(source, "safeGetProperty");

  assert.match(windowsBody, /const windowsList = \[\]/, "safeUpdateWindows must rebuild a fresh window list");
  assert.match(windowsBody, /windowCache = \{\}/, "safeUpdateWindows must reset stale window cache entries");
  assert.match(windowsBody, /!Hyprland\.toplevels \|\| !Hyprland\.toplevels\.values[\s\S]*windows = \[\][\s\S]*focusedWindowIndex = -1[\s\S]*return;/, "safeUpdateWindows must clear window state when toplevels are unavailable");
  assert.match(windowsBody, /const windowData = extractWindowData\(toplevel\)/, "safeUpdateWindows must normalize each toplevel through extractWindowData");
  assert.match(windowsBody, /windowCache\[windowData\.id\] = windowData/, "safeUpdateWindows must cache windows by normalized ID");
  assert.match(windowsBody, /if \(windowData\.isFocused\)[\s\S]*newFocusedIndex = windowsList\.length - 1/, "safeUpdateWindows must track the focused window index");
  assert.match(windowsBody, /if \(newFocusedIndex !== focusedWindowIndex\)[\s\S]*activeWindowChanged\(\)/, "safeUpdateWindows must emit activeWindowChanged only when focus changes");
  assert.match(extractBody, /if \(!toplevel\)\s+return null;/, "extractWindowData must reject empty toplevels");
  assert.match(extractBody, /const windowId = safeGetProperty\(toplevel,\s*"address",\s*""\)/, "extractWindowData must use safeGetProperty for window IDs");
  assert.match(extractBody, /if \(!windowId\)\s+return null;/, "extractWindowData must reject windows without IDs");
  assert.match(extractBody, /const appId = getAppId\(toplevel\)[\s\S]*const title = getAppTitle\(toplevel\)/, "extractWindowData must derive app ID and title through helpers");
  assert.match(extractBody, /"workspaceId": wsId \|\| -1/, "extractWindowData must default missing workspace IDs");
  assert.match(extractBody, /"isFocused": focused/, "extractWindowData must expose focused state");
  assert.match(titleBody, /toplevel\.wayland\.title[\s\S]*return title/, "getAppTitle must prefer Wayland titles");
  assert.match(titleBody, /return safeGetProperty\(toplevel,\s*"title",\s*""\)/, "getAppTitle must fall back to safe title access");
  assert.match(appIdBody, /if \(!toplevel\)\s+return "";/, "getAppId must reject empty toplevels");
  assert.match(appIdBody, /toplevel\.wayland\.appId[\s\S]*return appId/, "getAppId must prefer Wayland app IDs");
  assert.match(appIdBody, /safeGetProperty\(toplevel,\s*"class",\s*""\)/, "getAppId must try class");
  assert.match(appIdBody, /safeGetProperty\(toplevel,\s*"initialClass",\s*""\)/, "getAppId must try initialClass");
  assert.match(appIdBody, /safeGetProperty\(toplevel,\s*"appId",\s*""\)/, "getAppId must try appId");
  assert.match(appIdBody, /String\(ipcData\.class \|\| ipcData\.initialClass \|\| ipcData\.appId \|\| ipcData\.wm_class \|\| ""\)/, "getAppId must fall back to last IPC object fields");
  assert.match(propertyBody, /const value = obj\[prop\]/, "safeGetProperty must access properties dynamically");
  assert.match(propertyBody, /value !== undefined && value !== null[\s\S]*return String\(value\)/, "safeGetProperty must stringify present values");
  assert.match(propertyBody, /return defaultValue/, "safeGetProperty must return the fallback on missing or failed property access");
}

function testHyprlandKeyboardAndActionHandlersDelegateSafely() {
  const source = readQml("Services/Compositor/HyprlandService.qml");
  const layoutBody = extractFunctionBody(source, "handleActiveLayoutEvent");
  const switchBody = extractFunctionBody(source, "switchToWorkspace");
  const focusBody = extractFunctionBody(source, "focusWindow");
  const closeBody = extractFunctionBody(source, "closeWindow");
  const logoutBody = extractFunctionBody(source, "logout");

  assert.match(layoutBody, /const parenthesisPos = ev\.lastIndexOf\('\('\)/, "handleActiveLayoutEvent must find optional parenthesized keyboard names");
  assert.match(layoutBody, /beforeParenthesis = ev\.substring\(0,\s*parenthesisPos\)/, "handleActiveLayoutEvent must ignore trailing parenthesized metadata");
  assert.match(layoutBody, /const layoutNameStart = beforeParenthesis\.lastIndexOf\(','\) \+ 1/, "handleActiveLayoutEvent must derive layout from the comma-delimited event suffix");
  assert.match(layoutBody, /const layoutName = ev\.substring\(layoutNameStart\)/, "handleActiveLayoutEvent must preserve the selected layout text");
  assert.match(layoutBody, /KeyboardLayoutService\.setCurrentLayout\(layoutName\)/, "handleActiveLayoutEvent must forward the selected layout");
  assert.match(layoutBody, /Logger\.e\("HyprlandService",\s*"Error handling activelayout:",\s*e\)/, "handleActiveLayoutEvent must log parse failures");
  assert.match(switchBody, /Hyprland\.dispatch\(`workspace \$\{workspace\.idx\}`\)/, "switchToWorkspace must dispatch the workspace action");
  assert.match(switchBody, /Logger\.e\("HyprlandService",\s*"Failed to switch workspace:",\s*e\)/, "switchToWorkspace must log dispatch failures");
  assert.match(focusBody, /Hyprland\.dispatch\(`focuswindow address:0x\$\{window\.id\.toString\(\)\}`\)/, "focusWindow must dispatch focus by window address");
  assert.match(focusBody, /Logger\.e\("HyprlandService",\s*"Failed to switch window:",\s*e\)/, "focusWindow must log dispatch failures");
  assert.match(closeBody, /Hyprland\.dispatch\(`killwindow address:0x\$\{window\.id\}`\)/, "closeWindow must dispatch kill by window address");
  assert.match(closeBody, /Logger\.e\("HyprlandService",\s*"Failed to close window:",\s*e\)/, "closeWindow must log dispatch failures");
  assert.match(logoutBody, /Quickshell\.execDetached\(\["hyprctl",\s*"dispatch",\s*"exit"\]\)/, "logout must use hyprctl dispatch exit");
  assert.match(logoutBody, /Logger\.e\("HyprlandService",\s*"Failed to logout:",\s*e\)/, "logout must log failures");
}

const tests = [
  testHyprlandStartupQueriesAndSafeUpdatePipeline,
  testHyprlandWorkspaceAndOccupancyGuards,
  testHyprlandWindowDataNormalizationGuards,
  testHyprlandKeyboardAndActionHandlersDelegateSafely,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
