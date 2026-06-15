#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testSwayStartupQueriesAndSafeUpdatePipeline() {
  const source = readQml("Services/Compositor/SwayService.qml");
  const initializeBody = extractFunctionBody(source, "initialize");
  const scalesBody = extractFunctionBody(source, "queryDisplayScales");
  const keyboardBody = extractFunctionBody(source, "queryKeyboardLayout");
  const updateBody = extractFunctionBody(source, "safeUpdate");

  assert.match(initializeBody, /if \(initialized\)\s+return;/, "initialize must be idempotent");
  assert.match(initializeBody, /I3\.refreshWorkspaces\(\)/, "initialize must refresh Sway workspaces");
  assert.match(initializeBody, /I3\.dispatch\('\(\["input"\]\)'\)/, "initialize must subscribe to input events");
  assert.match(initializeBody, /Qt\.callLater\(\(\) =>[\s\S]*safeUpdateWorkspaces\(\)[\s\S]*safeUpdateWindows\(\)[\s\S]*queryDisplayScales\(\)[\s\S]*queryKeyboardLayout\(\)/, "initialize must defer initial cache refreshes");
  assert.match(initializeBody, /initialized = true/, "initialize must mark the service initialized");
  assert.match(initializeBody, /Logger\.e\("SwayService",\s*"Failed to initialize:",\s*e\)/, "initialize must log startup failures");
  assert.match(scalesBody, /swayOutputsProcess\.running = true/, "queryDisplayScales must start the outputs process");
  assert.match(keyboardBody, /swayInputsProcess\.running = true/, "queryKeyboardLayout must start the inputs process");
  assert.match(updateBody, /safeUpdateWindows\(\)[\s\S]*safeUpdateWorkspaces\(\)[\s\S]*windowListChanged\(\)/, "safeUpdate must refresh windows and workspaces before emitting changes");
}

function testSwayWorkspaceAndWindowNormalizationGuards() {
  const source = readQml("Services/Compositor/SwayService.qml");
  const workspacesBody = extractFunctionBody(source, "safeUpdateWorkspaces");
  const windowsBody = extractFunctionBody(source, "safeUpdateWindows");
  const extractBody = extractFunctionBody(source, "extractWindowData");
  const appIdBody = extractFunctionBody(source, "getAppId");
  const propertyBody = extractFunctionBody(source, "safeGetProperty");

  assert.match(workspacesBody, /workspaces\.clear\(\)/, "safeUpdateWorkspaces must clear stale workspace rows");
  assert.match(workspacesBody, /!I3\.workspaces \|\| !I3\.workspaces\.values[\s\S]*return;/, "safeUpdateWorkspaces must tolerate missing I3 workspace data");
  assert.match(workspacesBody, /const hlWorkspaces = I3\.workspaces\.values/, "safeUpdateWorkspaces must read I3 workspace values");
  assert.match(workspacesBody, /if \(!ws \|\| ws\.id < 1\)\s+continue;/, "safeUpdateWorkspaces must skip invalid workspaces");
  assert.match(workspacesBody, /"idx": ws\.num/, "safeUpdateWorkspaces must expose Sway workspace numbers");
  assert.match(workspacesBody, /"isFocused": ws\.focused === true/, "safeUpdateWorkspaces must normalize focused state");
  assert.match(workspacesBody, /"isOccupied": true/, "safeUpdateWorkspaces must treat listed Sway workspaces as occupied");
  assert.match(workspacesBody, /"handle": ws/, "safeUpdateWorkspaces must retain the workspace handle for actions");
  assert.match(workspacesBody, /workspaces\.append\(wsData\)/, "safeUpdateWorkspaces must append normalized workspace rows");
  assert.match(workspacesBody, /Logger\.e\("SwayService",\s*"Error updating workspaces:",\s*e\)/, "safeUpdateWorkspaces must log failures");
  assert.match(windowsBody, /const windowsList = \[\]/, "safeUpdateWindows must rebuild a fresh window list");
  assert.match(windowsBody, /!ToplevelManager\.toplevels \|\| !ToplevelManager\.toplevels\.values[\s\S]*windows = \[\][\s\S]*focusedWindowIndex = -1[\s\S]*return;/, "safeUpdateWindows must clear state when toplevels are unavailable");
  assert.match(windowsBody, /const windowData = extractWindowData\(toplevel\)/, "safeUpdateWindows must normalize every toplevel");
  assert.match(windowsBody, /if \(windowData\.isFocused\)[\s\S]*newFocusedIndex = windowsList\.length - 1/, "safeUpdateWindows must track the focused window index");
  assert.match(windowsBody, /if \(newFocusedIndex !== focusedWindowIndex\)[\s\S]*activeWindowChanged\(\)/, "safeUpdateWindows must emit activeWindowChanged only when focus changes");
  assert.match(extractBody, /if \(!toplevel\)\s+return null;/, "extractWindowData must reject empty toplevels");
  assert.match(extractBody, /const appId = getAppId\(toplevel\)/, "extractWindowData must derive app IDs through helper");
  assert.match(extractBody, /const title = safeGetProperty\(toplevel,\s*"title",\s*""\)/, "extractWindowData must safely read titles");
  assert.match(extractBody, /"handle": toplevel/, "extractWindowData must keep the toplevel handle for actions");
  assert.match(appIdBody, /if \(!toplevel\)\s+return "";/, "getAppId must reject missing toplevels");
  assert.match(appIdBody, /return toplevel\.appId/, "getAppId must read Sway toplevel appId");
  assert.match(propertyBody, /const value = obj\[prop\]/, "safeGetProperty must access properties dynamically");
  assert.match(propertyBody, /value !== undefined && value !== null[\s\S]*return String\(value\)/, "safeGetProperty must stringify present values");
  assert.match(propertyBody, /return defaultValue/, "safeGetProperty must return the fallback on missing or failed property access");
}

function testSwayInputAndActionHandlersDelegateSafely() {
  const source = readQml("Services/Compositor/SwayService.qml");
  const inputBody = extractFunctionBody(source, "handleInputEvent");
  const switchBody = extractFunctionBody(source, "switchToWorkspace");
  const focusBody = extractFunctionBody(source, "focusWindow");
  const closeBody = extractFunctionBody(source, "closeWindow");
  const logoutBody = extractFunctionBody(source, "logout");

  assert.match(inputBody, /const parenthesisPos = ev\.lastIndexOf\('\('\)/, "handleInputEvent must find optional parenthesized keyboard names");
  assert.match(inputBody, /beforeParenthesis = ev\.substring\(0,\s*parenthesisPos\)/, "handleInputEvent must ignore trailing parenthesized metadata");
  assert.match(inputBody, /const layoutNameStart = beforeParenthesis\.lastIndexOf\(','\) \+ 1/, "handleInputEvent must derive layout from comma-delimited event suffix");
  assert.match(inputBody, /const layoutName = ev\.substring\(layoutNameStart\)/, "handleInputEvent must preserve selected layout text");
  assert.match(inputBody, /KeyboardLayoutService\.setCurrentLayout\(layoutName\)/, "handleInputEvent must forward the selected layout");
  assert.match(inputBody, /Logger\.e\("HyprlandService",\s*"Error handling activelayout:",\s*e\)/, "handleInputEvent must log parse failures");
  assert.match(switchBody, /workspace\.handle\.activate\(\)/, "switchToWorkspace must activate the workspace handle");
  assert.match(switchBody, /Logger\.e\("SwayService",\s*"Failed to switch workspace:",\s*e\)/, "switchToWorkspace must log failures");
  assert.match(focusBody, /window\.handle\.activate\(\)/, "focusWindow must activate the toplevel handle");
  assert.match(focusBody, /Logger\.e\("SwayService",\s*"Failed to switch window:",\s*e\)/, "focusWindow must log failures");
  assert.match(closeBody, /window\.handle\.close\(\)/, "closeWindow must close the toplevel handle");
  assert.match(closeBody, /Logger\.e\("SwayService",\s*"Failed to close window:",\s*e\)/, "closeWindow must log failures");
  assert.match(logoutBody, /Quickshell\.execDetached\(\["swaymsg",\s*"exit"\]\)/, "logout must request Sway exit");
  assert.match(logoutBody, /Logger\.e\("SwayService",\s*"Failed to logout:",\s*e\)/, "logout must log failures");
}

const tests = [
  testSwayStartupQueriesAndSafeUpdatePipeline,
  testSwayWorkspaceAndWindowNormalizationGuards,
  testSwayInputAndActionHandlersDelegateSafely,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
