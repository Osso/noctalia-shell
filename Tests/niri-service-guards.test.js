#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testNiriStartupCommandsInitializeSocketsAndQueries() {
  const source = readQml("Services/Compositor/NiriService.qml");
  const initializeBody = extractFunctionBody(source, "initialize");
  const sendBody = extractFunctionBody(source, "sendSocketCommand");
  const streamBody = extractFunctionBody(source, "startEventStream");
  const workspacesBody = extractFunctionBody(source, "updateWorkspaces");
  const windowsBody = extractFunctionBody(source, "updateWindows");
  const scalesBody = extractFunctionBody(source, "queryDisplayScales");

  assert.match(initializeBody, /niriEventStream\.connected = true/, "initialize must connect the event stream socket");
  assert.match(initializeBody, /niriCommandSocket\.connected = true/, "initialize must connect the command socket");
  assert.match(initializeBody, /startEventStream\(\)/, "initialize must start the event stream");
  assert.match(initializeBody, /updateWorkspaces\(\)/, "initialize must query initial workspaces");
  assert.match(initializeBody, /updateWindows\(\)/, "initialize must query initial windows");
  assert.match(initializeBody, /queryDisplayScales\(\)/, "initialize must query initial display scales");
  assert.match(sendBody, /sock\.write\(JSON\.stringify\(command\) \+ "\\n"\)/, "sendSocketCommand must write newline-delimited JSON");
  assert.match(sendBody, /sock\.flush\(\)/, "sendSocketCommand must flush the socket");
  assert.match(streamBody, /sendSocketCommand\(niriEventStream,\s*"EventStream"\)/, "startEventStream must request Niri EventStream");
  assert.match(workspacesBody, /sendSocketCommand\(niriCommandSocket,\s*"Workspaces"\)/, "updateWorkspaces must request Niri workspaces");
  assert.match(windowsBody, /sendSocketCommand\(niriCommandSocket,\s*"Windows"\)/, "updateWindows must request Niri windows");
  assert.match(scalesBody, /sendSocketCommand\(niriCommandSocket,\s*"Outputs"\)/, "queryDisplayScales must request Niri outputs");
}

function testNiriOutputAndWorkspaceRecollectionNormalizeData() {
  const source = readQml("Services/Compositor/NiriService.qml");
  const outputsBody = extractFunctionBody(source, "recollectOutputs");
  const workspacesBody = extractFunctionBody(source, "recollectWorkspaces");

  assert.match(outputsBody, /const scales = \{\}/, "recollectOutputs must build a display scale map");
  assert.match(outputsBody, /for \(const outputName in outputsData\)/, "recollectOutputs must scan all output entries");
  assert.match(outputsBody, /const logical = output\.logical \|\| \{\}/, "recollectOutputs must tolerate missing logical output data");
  assert.match(outputsBody, /const currentMode = modes\[currentModeIdx\] \|\| \{\}/, "recollectOutputs must tolerate missing current mode data");
  assert.match(outputsBody, /"scale": logical\.scale \|\| 1\.0/, "recollectOutputs must default missing scale to 1");
  assert.match(outputsBody, /"refresh_rate": currentMode\.refresh_rate \|\| 0/, "recollectOutputs must default missing refresh rate");
  assert.match(outputsBody, /CompositorService\.onDisplayScalesUpdated\(scales\)/, "recollectOutputs must forward scales to CompositorService");
  assert.match(workspacesBody, /const workspacesList = \[\]/, "recollectWorkspaces must build a normalized workspace list");
  assert.match(workspacesBody, /"isFocused": ws\.is_focused === true/, "recollectWorkspaces must normalize focused state");
  assert.match(workspacesBody, /"isOccupied": ws\.active_window_id \? true : false/, "recollectWorkspaces must normalize occupancy");
  assert.match(workspacesBody, /a\.output\.localeCompare\(b\.output\)/, "recollectWorkspaces must group workspaces by output");
  assert.match(workspacesBody, /return a\.idx - b\.idx/, "recollectWorkspaces must sort workspaces by index inside an output");
  assert.match(workspacesBody, /workspaces\.clear\(\)/, "recollectWorkspaces must clear stale model rows");
  assert.match(workspacesBody, /workspaces\.append\(workspacesList\[i\]\)/, "recollectWorkspaces must append normalized rows");
  assert.match(workspacesBody, /workspaceChanged\(\)/, "recollectWorkspaces must emit workspaceChanged");
}

function testNiriWindowDataHelpersNormalizeAndSortWindows() {
  const source = readQml("Services/Compositor/NiriService.qml");
  const positionBody = extractFunctionBody(source, "getWindowPosition");
  const outputBody = extractFunctionBody(source, "getWindowOutput");
  const dataBody = extractFunctionBody(source, "getWindowData");
  const compareBody = extractFunctionBody(source, "compareWindows");
  const recollectBody = extractFunctionBody(source, "recollectWindows");

  assert.match(positionBody, /layout\.pos_in_scrolling_layout/, "getWindowPosition must prefer scrolling layout positions");
  assert.match(positionBody, /"x": layout\.pos_in_scrolling_layout\[0\]/, "getWindowPosition must read x from Niri layout data");
  assert.match(positionBody, /"x": floatingWindowPosition/, "getWindowPosition must push floating windows to the end");
  assert.match(outputBody, /workspaces\.get\(i\)\.id === win\.workspace_id[\s\S]*return workspaces\.get\(i\)\.output/, "getWindowOutput must match windows to workspace outputs");
  assert.match(outputBody, /return null/, "getWindowOutput must return null for unknown workspaces");
  assert.match(dataBody, /"title": win\.title \|\| ""/, "getWindowData must normalize missing titles");
  assert.match(dataBody, /"appId": win\.app_id \|\| ""/, "getWindowData must normalize missing app IDs");
  assert.match(dataBody, /"workspaceId": win\.workspace_id \|\| -1/, "getWindowData must normalize missing workspace IDs");
  assert.match(dataBody, /"isFocused": win\.is_focused === true/, "getWindowData must normalize focused state");
  assert.match(dataBody, /"output": getWindowOutput\(win\) \|\| ""/, "getWindowData must include output names");
  assert.match(dataBody, /"position": getWindowPosition\(win\.layout\)/, "getWindowData must include normalized positions");
  assert.match(compareBody, /a\.workspaceId !== b\.workspaceId[\s\S]*return a\.workspaceId - b\.workspaceId/, "compareWindows must sort by workspace first");
  assert.match(compareBody, /a\.position\.x !== b\.position\.x[\s\S]*return a\.position\.x - b\.position\.x/, "compareWindows must sort by x position second");
  assert.match(compareBody, /return a\.position\.y - b\.position\.y/, "compareWindows must sort by y position last");
  assert.match(recollectBody, /windowsList\.push\(getWindowData\(win\)\)/, "recollectWindows must normalize every Niri window");
  assert.match(recollectBody, /windowsList\.sort\(compareWindows\)/, "recollectWindows must apply window sort order");
  assert.match(recollectBody, /focusedWindowIndex = -1/, "recollectWindows must reset focused index before scanning");
  assert.match(recollectBody, /if \(windowsList\[i\]\.isFocused\)[\s\S]*focusedWindowIndex = i/, "recollectWindows must store focused window index");
  assert.match(recollectBody, /activeWindowChanged\(\)/, "recollectWindows must emit activeWindowChanged");
}

function testNiriWindowEventHandlersMaintainWindowState() {
  const source = readQml("Services/Compositor/NiriService.qml");
  const openedBody = extractFunctionBody(source, "handleWindowOpenedOrChanged");
  const closedBody = extractFunctionBody(source, "handleWindowClosed");
  const changedBody = extractFunctionBody(source, "handleWindowsChanged");
  const focusBody = extractFunctionBody(source, "handleWindowFocusChanged");
  const layoutsBody = extractFunctionBody(source, "handleWindowLayoutsChanged");

  assert.match(openedBody, /const existingIndex = windows\.findIndex\(w => w\.id === windowData\.id\)/, "handleWindowOpenedOrChanged must find existing windows by id");
  assert.match(openedBody, /windows\[existingIndex\] = newWindow/, "handleWindowOpenedOrChanged must update existing windows");
  assert.match(openedBody, /windows\.push\(newWindow\)/, "handleWindowOpenedOrChanged must append new windows");
  assert.match(openedBody, /windows\.sort\(compareWindows\)/, "handleWindowOpenedOrChanged must preserve sort order");
  assert.match(openedBody, /activeWindowChanged\(\)/, "handleWindowOpenedOrChanged must emit activeWindowChanged when focus changes");
  assert.match(closedBody, /const windowIndex = windows\.findIndex\(w => w\.id === windowId\)/, "handleWindowClosed must find the closed window");
  assert.match(closedBody, /maximizedWindows\.splice\(maximizedIndex,\s*1\)/, "handleWindowClosed must remove closed maximized windows");
  assert.match(closedBody, /Settings\.data\.bar\.floating = originalBarFloatingState/, "handleWindowClosed must restore bar floating state");
  assert.match(closedBody, /focusedWindowIndex = -1/, "handleWindowClosed must clear focus when closing focused window");
  assert.match(closedBody, /focusedWindowIndex--/, "handleWindowClosed must shift focused index after earlier removals");
  assert.match(closedBody, /windows\.splice\(windowIndex,\s*1\)/, "handleWindowClosed must remove the closed window");
  assert.match(changedBody, /const windowsData = eventData\.windows[\s\S]*recollectWindows\(windowsData\)/, "handleWindowsChanged must recollect all windows");
  assert.match(focusBody, /if \(windows\[focusedWindowIndex\]\)[\s\S]*windows\[focusedWindowIndex\]\.isFocused = false/, "handleWindowFocusChanged must clear old focus");
  assert.match(focusBody, /windows\[newIndex\]\.isFocused = true/, "handleWindowFocusChanged must mark new focus");
  assert.match(layoutsBody, /for \(const change of eventData\.changes\)/, "handleWindowLayoutsChanged must inspect every layout change");
  assert.match(layoutsBody, /Math\.abs\(windowWidth - outputWidth\) < 10/, "handleWindowLayoutsChanged must detect horizontal maximize bounds");
  assert.match(layoutsBody, /Settings\.data\.bar\.floating = false/, "handleWindowLayoutsChanged must disable floating bar for maximized windows");
  assert.match(layoutsBody, /Settings\.data\.bar\.outerCorners = false/, "handleWindowLayoutsChanged must disable outer corners for maximized windows");
  assert.match(layoutsBody, /Settings\.data\.bar\.outerCorners = originalBarOuterCornersState/, "handleWindowLayoutsChanged must restore outer corner state");
  assert.match(layoutsBody, /windowListChanged\(\)/, "handleWindowLayoutsChanged must emit windowListChanged");
}

function testNiriOverviewKeyboardAndActionHandlersDelegateSafely() {
  const source = readQml("Services/Compositor/NiriService.qml");
  const overviewBody = extractFunctionBody(source, "handleOverviewOpenedOrClosed");
  const layoutsChangedBody = extractFunctionBody(source, "handleKeyboardLayoutsChanged");
  const layoutSwitchedBody = extractFunctionBody(source, "handleKeyboardLayoutSwitched");
  const switchBody = extractFunctionBody(source, "switchToWorkspace");
  const focusBody = extractFunctionBody(source, "focusWindow");
  const closeBody = extractFunctionBody(source, "closeWindow");
  const logoutBody = extractFunctionBody(source, "logout");

  assert.match(overviewBody, /overviewActive = eventData\.is_open/, "handleOverviewOpenedOrClosed must mirror Niri overview state");
  assert.match(layoutsChangedBody, /keyboardLayouts = eventData\.keyboard_layouts\.names/, "handleKeyboardLayoutsChanged must store available layout names");
  assert.match(layoutsChangedBody, /KeyboardLayoutService\.setCurrentLayout\(layoutName\)/, "handleKeyboardLayoutsChanged must forward current layout");
  assert.match(layoutSwitchedBody, /const layoutName = keyboardLayouts\[eventData\.idx\]/, "handleKeyboardLayoutSwitched must read the switched layout index");
  assert.match(layoutSwitchedBody, /KeyboardLayoutService\.setCurrentLayout\(layoutName\)/, "handleKeyboardLayoutSwitched must forward switched layout");
  assert.match(switchBody, /Quickshell\.execDetached\(\["niri",\s*"msg",\s*"action",\s*"focus-workspace",\s*workspace\.idx\.toString\(\)\]\)/, "switchToWorkspace must call niri focus-workspace");
  assert.match(focusBody, /Quickshell\.execDetached\(\["niri",\s*"msg",\s*"action",\s*"focus-window",\s*"--id",\s*window\.id\.toString\(\)\]\)/, "focusWindow must call niri focus-window by id");
  assert.match(closeBody, /Quickshell\.execDetached\(\["niri",\s*"msg",\s*"action",\s*"close-window",\s*"--id",\s*window\.id\.toString\(\)\]\)/, "closeWindow must call niri close-window by id");
  assert.match(logoutBody, /Quickshell\.execDetached\(\["niri",\s*"msg",\s*"action",\s*"quit",\s*"--skip-confirmation"\]\)/, "logout must call niri quit without confirmation");
}

const tests = [
  testNiriStartupCommandsInitializeSocketsAndQueries,
  testNiriOutputAndWorkspaceRecollectionNormalizeData,
  testNiriWindowDataHelpersNormalizeAndSortWindows,
  testNiriWindowEventHandlersMaintainWindowState,
  testNiriOverviewKeyboardAndActionHandlersDelegateSafely,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
