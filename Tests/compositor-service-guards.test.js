#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Compositor/CompositorService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testCompositorDetectionSelectsOneBackend() {
  const body = extractFunctionBody(source, "detectCompositor");

  assert.match(body, /Quickshell\.env\("HYPRLAND_INSTANCE_SIGNATURE"\)/, "detectCompositor must inspect Hyprland signature");
  assert.match(body, /Quickshell\.env\("NIRI_SOCKET"\)/, "detectCompositor must inspect Niri socket");
  assert.match(body, /Quickshell\.env\("SWAYSOCK"\)/, "detectCompositor must inspect Sway socket");
  assert.match(body, /Quickshell\.env\("XDG_CURRENT_DESKTOP"\)/, "detectCompositor must inspect current desktop");
  assert.match(body, /currentDesktop && currentDesktop\.toLowerCase\(\)\.includes\("mango"\)[\s\S]*backendLoader\.sourceComponent = mangoComponent/, "detectCompositor must prefer Mango desktop detection");
  assert.match(body, /niriSocket && niriSocket\.length > 0[\s\S]*backendLoader\.sourceComponent = niriComponent/, "detectCompositor must select Niri when NIRI_SOCKET is present");
  assert.match(body, /hyprlandSignature && hyprlandSignature\.length > 0[\s\S]*backendLoader\.sourceComponent = hyprlandComponent/, "detectCompositor must select Hyprland when its signature is present");
  assert.match(body, /swaySock && swaySock\.length > 0[\s\S]*backendLoader\.sourceComponent = swayComponent/, "detectCompositor must select Sway when SWAYSOCK is present");
  assert.match(body, /Always fallback to Niri[\s\S]*isNiri = true[\s\S]*backendLoader\.sourceComponent = niriComponent/, "detectCompositor must fall back to Niri");
}

function testCompositorDisplayScaleCacheGuardsShellState() {
  const loadBody = extractFunctionBody(source, "loadDisplayScalesFromState");
  const updateBody = extractFunctionBody(source, "updateDisplayScales");
  const saveBody = extractFunctionBody(source, "saveDisplayScalesToCache");
  const infoBody = extractFunctionBody(source, "getDisplayInfo");

  assert.match(loadBody, /const cached = ShellState\.getDisplay\(\)/, "loadDisplayScalesFromState must read ShellState display data");
  assert.match(loadBody, /cached && Object\.keys\(cached\)\.length > 0[\s\S]*displayScales = cached/, "loadDisplayScalesFromState must restore cached display scales");
  assert.match(loadBody, /displayScalesLoaded = true/, "loadDisplayScalesFromState must mark display scale loading complete");
  assert.match(loadBody, /Logger\.e\("CompositorService",\s*"Failed to load display scales:",\s*error\)/, "loadDisplayScalesFromState must log ShellState load failures");
  assert.match(updateBody, /if \(!backend \|\| !backend\.queryDisplayScales\)/, "updateDisplayScales must guard missing backend support");
  assert.match(updateBody, /Logger\.w\("CompositorService",\s*"Backend does not support display scale queries"\)/, "updateDisplayScales must log unsupported backends");
  assert.match(updateBody, /backend\.queryDisplayScales\(\)/, "updateDisplayScales must delegate supported queries to the backend");
  assert.match(saveBody, /ShellState\.setDisplay\(displayScales\)/, "saveDisplayScalesToCache must persist display scales");
  assert.match(saveBody, /Logger\.e\("CompositorService",\s*"Failed to save display scales:",\s*error\)/, "saveDisplayScalesToCache must log ShellState save failures");
  assert.match(infoBody, /if \(!displayName \|\| !displayScales\[displayName\]\)[\s\S]*return null/, "getDisplayInfo must return null for missing displays");
  assert.match(infoBody, /return displayScales\[displayName\]/, "getDisplayInfo must return the cached display metadata");
}

function testCompositorSyncAndWindowQueriesMirrorBackendModels() {
  const setupBody = extractFunctionBody(source, "setupBackendConnections");
  const syncWorkspacesBody = extractFunctionBody(source, "syncWorkspaces");
  const syncWindowsBody = extractFunctionBody(source, "syncWindows");
  const focusedBody = extractFunctionBody(source, "getFocusedWindow");
  const focusedTitleBody = extractFunctionBody(source, "getFocusedWindowTitle");
  const cleanAppBody = extractFunctionBody(source, "getCleanAppName");
  const windowsForWorkspaceBody = extractFunctionBody(source, "getWindowsForWorkspace");
  const currentWorkspaceBody = extractFunctionBody(source, "getCurrentWorkspace");
  const activeWorkspacesBody = extractFunctionBody(source, "getActiveWorkspaces");

  assert.match(setupBody, /if \(!backend\)\s+return;/, "setupBackendConnections must ignore missing backends");
  assert.match(setupBody, /backend\.workspaceChanged\.connect\(\(\) =>[\s\S]*syncWorkspaces\(\)[\s\S]*workspaceChanged\(\)/, "setupBackendConnections must sync and forward workspace changes");
  assert.match(setupBody, /backend\.activeWindowChanged\.connect\(\(\) =>[\s\S]*syncWindows\(\)[\s\S]*activeWindowChanged\(\)/, "setupBackendConnections must sync and forward active window changes");
  assert.match(setupBody, /backend\.focusedWindowIndexChanged\.connect\(\(\) =>[\s\S]*focusedWindowIndex = backend\.focusedWindowIndex/, "setupBackendConnections must mirror focused window index");
  assert.match(syncWorkspacesBody, /workspaces\.clear\(\)/, "syncWorkspaces must clear stale workspace rows");
  assert.match(syncWorkspacesBody, /const ws = backend\.workspaces[\s\S]*workspaces\.append\(ws\.get\(i\)\)/, "syncWorkspaces must append backend workspace rows");
  assert.match(syncWindowsBody, /windows\.clear\(\)/, "syncWindows must clear stale window rows");
  assert.match(syncWindowsBody, /const ws = backend\.windows[\s\S]*windows\.append\(ws\[i\]\)/, "syncWindows must append backend window rows");
  assert.match(focusedBody, /focusedWindowIndex >= 0 && focusedWindowIndex < windows\.count[\s\S]*return windows\.get\(focusedWindowIndex\)/, "getFocusedWindow must bounds-check the focused index");
  assert.match(focusedTitleBody, /title\.replace\(\/\(\\r\\n\|\\n\|\\r\)\/g,\s*""\)/, "getFocusedWindowTitle must strip line breaks from titles");
  assert.match(cleanAppBody, /\(appId \|\| ""\)\.split\("\."\)\.pop\(\) \|\| fallbackTitle \|\| "Unknown"/, "getCleanAppName must fall back from app id to title to Unknown");
  assert.match(windowsForWorkspaceBody, /window\.workspaceId === workspaceId[\s\S]*windowsInWs\.push\(window\)/, "getWindowsForWorkspace must filter by workspace id");
  assert.match(currentWorkspaceBody, /if \(ws\.isFocused\)[\s\S]*return ws/, "getCurrentWorkspace must return the focused workspace");
  assert.match(activeWorkspacesBody, /if \(ws\.isActive\)[\s\S]*activeWorkspaces\.push\(ws\)/, "getActiveWorkspaces must collect active workspaces");
}

function testCompositorBackendDelegatesFailClosed() {
  const switchBody = extractFunctionBody(source, "switchToWorkspace");
  const focusBody = extractFunctionBody(source, "focusWindow");
  const closeBody = extractFunctionBody(source, "closeWindow");
  const logoutBody = extractFunctionBody(source, "logout");

  assert.match(switchBody, /backend && backend\.switchToWorkspace[\s\S]*backend\.switchToWorkspace\(workspace\)/, "switchToWorkspace must delegate to capable backends");
  assert.match(switchBody, /Logger\.w\("Compositor",\s*"No backend available for workspace switching"\)/, "switchToWorkspace must warn when unsupported");
  assert.match(focusBody, /backend && backend\.focusWindow[\s\S]*backend\.focusWindow\(window\)/, "focusWindow must delegate to capable backends");
  assert.match(focusBody, /Logger\.w\("Compositor",\s*"No backend available for window focus"\)/, "focusWindow must warn when unsupported");
  assert.match(closeBody, /backend && backend\.closeWindow[\s\S]*backend\.closeWindow\(window\)/, "closeWindow must delegate to capable backends");
  assert.match(closeBody, /Logger\.w\("Compositor",\s*"No backend available for window closing"\)/, "closeWindow must warn when unsupported");
  assert.match(logoutBody, /backend && backend\.logout[\s\S]*Logger\.i\("Compositor",\s*"Logout requested"\)[\s\S]*backend\.logout\(\)/, "logout must log and delegate to capable backends");
  assert.match(logoutBody, /Logger\.w\("Compositor",\s*"No backend available for logout"\)/, "logout must warn when unsupported");
}

function testCompositorSessionCommandsAndLockSuspendFallbacks() {
  const shutdownBody = extractFunctionBody(source, "shutdown");
  const rebootBody = extractFunctionBody(source, "reboot");
  const suspendBody = extractFunctionBody(source, "suspend");
  const hibernateBody = extractFunctionBody(source, "hibernate");
  const lockBody = extractFunctionBody(source, "lockAndSuspend");

  assert.match(shutdownBody, /Quickshell\.execDetached\(\["sh",\s*"-c",\s*"systemctl poweroff \|\| loginctl poweroff"\]\)/, "shutdown must support systemctl and loginctl fallback");
  assert.match(rebootBody, /Quickshell\.execDetached\(\["sh",\s*"-c",\s*"systemctl reboot \|\| loginctl reboot"\]\)/, "reboot must support systemctl and loginctl fallback");
  assert.match(suspendBody, /Quickshell\.execDetached\(\["sh",\s*"-c",\s*"systemctl suspend \|\| loginctl suspend"\]\)/, "suspend must support systemctl and loginctl fallback");
  assert.match(hibernateBody, /Quickshell\.execDetached\(\["sh",\s*"-c",\s*"systemctl hibernate \|\| loginctl hibernate"\]\)/, "hibernate must support systemctl and loginctl fallback");
  assert.match(lockBody, /PanelService && PanelService\.lockScreen && PanelService\.lockScreen\.active[\s\S]*suspend\(\)[\s\S]*return;/, "lockAndSuspend must suspend immediately when already locked");
  assert.match(lockBody, /PanelService\.lockScreen\.active = true/, "lockAndSuspend must activate the lock screen first");
  assert.match(lockBody, /lockAndSuspendCheckCount = 0/, "lockAndSuspend must reset polling attempts");
  assert.match(lockBody, /lockAndSuspendTimer\.start\(\)/, "lockAndSuspend must wait for the lock screen before suspending");
  assert.match(lockBody, /Logger\.w\("Compositor",\s*"Lock screen not available, suspending without lock"\)[\s\S]*suspend\(\)/, "lockAndSuspend must fall back when lock screen is unavailable");
  assert.match(lockBody, /catch \(e\)[\s\S]*Logger\.w\("Compositor",\s*"Failed to activate lock screen before suspend: " \+ e\)[\s\S]*suspend\(\)/, "lockAndSuspend must suspend on lock activation failure");
}

function listModel(items) {
  return {
    count: items.length,
    get(index) {
      return items[index];
    },
  };
}

function testCompositorWindowHelpersExecuteFallbacks() {
  const getDisplayInfo = qmlFunction("getDisplayInfo", "displayName");
  const getFocusedWindow = qmlFunction("getFocusedWindow");
  const getFocusedWindowTitle = qmlFunction("getFocusedWindowTitle");
  const getCleanAppName = qmlFunction("getCleanAppName", "appId", "fallbackTitle");
  const getWindowsForWorkspace = qmlFunction("getWindowsForWorkspace", "workspaceId");
  const windows = [
    { title: "Terminal\n", workspaceId: 1 },
    { title: "Browser", workspaceId: 2 },
    { title: undefined, workspaceId: 1 },
  ];
  const ctx = {
    displayScales: {
      "HDMI-A-1": { scale: 1.25, x: 0, y: 0 },
    },
    focusedWindowIndex: 0,
    windows: listModel(windows),
  };

  assert.deepEqual(getDisplayInfo(ctx, "HDMI-A-1"), { scale: 1.25, x: 0, y: 0 }, "getDisplayInfo must return known display data");
  assert.equal(getDisplayInfo(ctx, "DP-1"), null, "getDisplayInfo must return null for missing displays");
  assert.deepEqual(getFocusedWindow(ctx), windows[0], "getFocusedWindow must return the focused window model item");
  assert.equal(getFocusedWindowTitle(ctx), "Terminal", "getFocusedWindowTitle must strip line breaks");
  ctx.focusedWindowIndex = 99;
  assert.equal(getFocusedWindow(ctx), null, "getFocusedWindow must return null for invalid indexes");
  assert.equal(getFocusedWindowTitle(ctx), "", "getFocusedWindowTitle must fail closed for invalid indexes");
  assert.equal(getCleanAppName(ctx, "org.kde.dolphin", "Files"), "Dolphin", "getCleanAppName must use the final reverse-domain segment");
  assert.equal(getCleanAppName(ctx, "", "fallback"), "Fallback", "getCleanAppName must capitalize fallback titles");
  assert.deepEqual(getWindowsForWorkspace(ctx, 1), [windows[0], windows[2]], "getWindowsForWorkspace must filter by workspace id");
}

function testCompositorWorkspaceHelpersExecuteModelLookups() {
  const getCurrentWorkspace = qmlFunction("getCurrentWorkspace");
  const getActiveWorkspaces = qmlFunction("getActiveWorkspaces");
  const workspaces = [
    { id: 1, isFocused: false, isActive: true },
    { id: 2, isFocused: true, isActive: true },
    { id: 3, isFocused: false, isActive: false },
  ];
  const ctx = {
    workspaces: listModel(workspaces),
  };

  assert.deepEqual(getCurrentWorkspace(ctx), workspaces[1], "getCurrentWorkspace must return the focused workspace");
  assert.deepEqual(getActiveWorkspaces(ctx), [workspaces[0], workspaces[1]], "getActiveWorkspaces must return every active workspace");
  ctx.workspaces = listModel(workspaces.map(workspace => ({ ...workspace, isFocused: false })));
  assert.equal(getCurrentWorkspace(ctx), null, "getCurrentWorkspace must return null when no workspace is focused");
}

const tests = [
  testCompositorDetectionSelectsOneBackend,
  testCompositorDisplayScaleCacheGuardsShellState,
  testCompositorSyncAndWindowQueriesMirrorBackendModels,
  testCompositorBackendDelegatesFailClosed,
  testCompositorSessionCommandsAndLockSuspendFallbacks,
  testCompositorWindowHelpersExecuteFallbacks,
  testCompositorWorkspaceHelpersExecuteModelLookups,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
