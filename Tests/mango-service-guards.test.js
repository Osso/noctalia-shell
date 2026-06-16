#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testMangoServiceTagParsingGuards() {
  const source = readQml("Services/Compositor/MangoService.qml");
  const tagBody = extractFunctionBody(source, "processTagData");

  assert.match(tagBody, /const lines = output\.trim\(\)\.split\('\\n'\)/, "processTagData must parse newline-separated mmsg output");
  assert.match(tagBody, /line\.match\(patterns\.tagDetail\)/, "processTagData must prefer detailed tag output");
  assert.match(tagBody, /const isActive = \(state & 1\) !== 0[\s\S]*const isUrgent = \(state & 2\) !== 0/, "processTagData must decode active and urgent bits");
  assert.match(tagBody, /newActiveTags\[outputName\] = tagId/, "processTagData must track active tags per output");
  assert.match(tagBody, /line\.match\(patterns\.tagBinary\)/, "processTagData must support binary tag fallback output");
  assert.match(tagBody, /const tagId = j \+ 1[\s\S]*const charIdx = occ\.length - 1 - j/, "processTagData must map binary strings right-to-left");
  assert.match(tagBody, /if \(detailedOutputTags\[key\]\)[\s\S]*continue;/, "processTagData must not duplicate detailed tags with binary fallback tags");
  assert.match(tagBody, /const metaMatch = line\.match\(patterns\.metadata\)[\s\S]*internal\.focusedTitle = val[\s\S]*internal\.focusedAppId = val/, "processTagData must capture focused window metadata");
  assert.match(tagBody, /const layoutMatch = line\.match\(patterns\.layout\)[\s\S]*root\.currentLayoutSymbol = layoutMatch\[2\]/, "processTagData must update current layout symbol");
  assert.match(tagBody, /KeyboardLayoutService\.setCurrentLayout\(kbName\)/, "processTagData must forward keyboard layout changes");
  assert.match(tagBody, /const selmonMatch = line\.match\(patterns\.selmon\)[\s\S]*root\.selectedMonitor = selmonMatch\[1\]/, "processTagData must update selected monitor");
  assert.match(tagBody, /internal\.tagStates\[outputName\] = newTagStates\[outputName\][\s\S]*internal\.activeTags\[outputName\] = newActiveTags\[outputName\]/, "processTagData must merge parsed output state");
  assert.match(tagBody, /internal\.rebuildWorkspaces\(\)[\s\S]*internal\.updateWindows\(\)/, "processTagData must refresh workspaces and windows after parsing");
}

function testMangoServiceWorkspaceAndWindowGuards() {
  const source = readQml("Services/Compositor/MangoService.qml");
  const workspaceBody = extractFunctionBody(source, "rebuildWorkspaces");
  const windowsBody = extractFunctionBody(source, "updateWindows");

  assert.match(workspaceBody, /internal\.outputIndices\[outputName\] = internal\.outputCounter\+\+/, "rebuildWorkspaces must assign stable output indices");
  assert.match(workspaceBody, /const isFocused = tag\.isActive && \(tag\.focused === 1 \|\| outputName === root\.selectedMonitor\)/, "rebuildWorkspaces must focus active selected-output tags");
  assert.match(workspaceBody, /const uniqueId = outputIdx \* 100 \+ tag\.id/, "rebuildWorkspaces must keep workspace ids unique across outputs");
  assert.match(workspaceBody, /idx: tag\.id[\s\S]*isUrgent: tag\.isUrgent[\s\S]*isOccupied: tag\.clients > 0/, "rebuildWorkspaces must preserve tag metadata for UI consumers");
  assert.match(workspaceBody, /workspaceList\.sort\(\(a, b\) =>[\s\S]*return a\.id - b\.id[\s\S]*return a\.output\.localeCompare\(b\.output\)/, "rebuildWorkspaces must sort workspaces deterministically");
  assert.match(workspaceBody, /root\.workspaces\.clear\(\)[\s\S]*root\.workspaces\.append\(workspaceList\[k\]\)[\s\S]*root\.workspaceChanged\(\)/, "rebuildWorkspaces must replace the ListModel and notify listeners");
  assert.match(windowsBody, /if \(!ToplevelManager\.toplevels\)[\s\S]*return;/, "updateWindows must no-op until toplevels are available");
  assert.match(windowsBody, /if \(!toplevel \|\| toplevel\.outliers\)[\s\S]*continue;/, "updateWindows must skip missing or outlier toplevels");
  assert.match(windowsBody, /internal\.toplevelIdMap\.has\(toplevel\)[\s\S]*internal\.toplevelIdMap\.set\(toplevel, windowId\)/, "updateWindows must keep stable ids for toplevel objects");
  assert.match(windowsBody, /isFocused && title === internal\.focusedTitle && appId === internal\.focusedAppId && internal\.focusedOutput[\s\S]*outputName = internal\.focusedOutput[\s\S]*internal\.windowOutputMap\[windowId\] = internal\.focusedOutput/, "updateWindows must prefer focused mmsg metadata for output tracking");
  assert.match(windowsBody, /internal\.activeTags\[outputName\] \|\| 1/, "updateWindows must default missing active tags to workspace 1");
  assert.match(windowsBody, /const workspaceId = outputIdx \* 100 \+ tagId/, "updateWindows must map windows onto unique workspace ids");
  assert.match(windowsBody, /fullscreen: toplevel\.fullscreen \|\| false[\s\S]*floating: toplevel\.maximized === false && toplevel\.fullscreen === false/, "updateWindows must expose fullscreen and floating state");
  assert.match(windowsBody, /if \(Object\.keys\(internal\.windowTagMap\)\.length > toplevels\.length \+ 20\)/, "updateWindows must prune stale window tracking maps");
  assert.match(windowsBody, /const signature = JSON\.stringify\(windowList\.map\(w => w\.id \+ w\.workspaceId \+ w\.isFocused\)\)/, "updateWindows must avoid redundant window notifications");
  assert.match(windowsBody, /root\.windows = windowList[\s\S]*root\.windowListChanged\(\)/, "updateWindows must publish changed windows");
  assert.match(windowsBody, /root\.focusedWindowIndex = newFocusedIdx[\s\S]*root\.activeWindowChanged\(\)/, "updateWindows must notify focused window changes");
}

function testMangoServiceScaleAndLifecycleGuards() {
  const source = readQml("Services/Compositor/MangoService.qml");
  const scaleBody = extractFunctionBody(source, "processScales");
  const initBody = extractFunctionBody(source, "initialize");
  const queryBody = extractFunctionBody(source, "queryDisplayScales");

  assert.match(scaleBody, /line\.match\(patterns\.scale\)/, "processScales must parse scale lines");
  assert.match(scaleBody, /const scale = parseFloat\(match\[2\]\)[\s\S]*internal\.monitorScales\[outputName\] = scale/, "processScales must store parsed monitor scales");
  assert.match(scaleBody, /scalesMap\[name\] = \{[\s\S]*name: name,[\s\S]*scale: internal\.monitorScales\[name\] \|\| 1\.0,[\s\S]*width: 0,[\s\S]*height: 0,[\s\S]*x: 0,[\s\S]*y: 0/, "processScales must build a CompositorService-compatible map");
  assert.match(scaleBody, /CompositorService\.onDisplayScalesUpdated\(scalesMap\)/, "processScales must notify CompositorService when available");
  assert.match(scaleBody, /root\.displayScalesChanged\(\)/, "processScales must emit display scale changes");
  assert.match(initBody, /if \(initialized\)[\s\S]*return;/, "initialize must be idempotent");
  assert.match(initBody, /scaleQuery\.running = true[\s\S]*initialQuery\.running = true[\s\S]*eventStream\.running = true/, "initialize must start scale, tag, and event queries");
  assert.match(initBody, /Quickshell\.execDetached\(\["mmsg", "-g", "-o"\]\)/, "initialize must query monitors");
  assert.match(initBody, /initialized = true/, "initialize must mark startup complete");
  assert.match(queryBody, /scaleQuery\.running = true/, "queryDisplayScales must rerun the scale query");
}

function testMangoServiceCommandGuards() {
  const source = readQml("Services/Compositor/MangoService.qml");
  const switchBody = extractFunctionBody(source, "switchToWorkspace");
  const focusBody = extractFunctionBody(source, "focusWindow");
  const closeBody = extractFunctionBody(source, "closeWindow");
  const logoutBody = extractFunctionBody(source, "logout");

  assert.match(switchBody, /const tagId = workspace\.idx \|\| workspace\.id \|\| 1/, "switchToWorkspace must prefer original tag ids");
  assert.match(switchBody, /const output = workspace\.output \|\| root\.selectedMonitor \|\| ""/, "switchToWorkspace must use workspace output or selected monitor");
  assert.match(switchBody, /const cmd = \["mmsg", "-s", "-t", tagId\.toString\(\)\]/, "switchToWorkspace must build an mmsg tag command");
  assert.match(switchBody, /Object\.keys\(internal\.monitorScales\)\.length > 1[\s\S]*cmd\.push\("-o", output\)/, "switchToWorkspace must pass output only for multi-monitor setups");
  assert.match(switchBody, /Quickshell\.execDetached\(cmd\)/, "switchToWorkspace must execute the command");
  assert.match(focusBody, /if \(window && window\.handle\)[\s\S]*window\.handle\.activate\(\)/, "focusWindow must activate handles directly");
  assert.match(focusBody, /else if \(window\.workspaceId\)[\s\S]*switchToWorkspace\(\{[\s\S]*id: window\.workspaceId,[\s\S]*output: window\.output/, "focusWindow must fallback to workspace switching");
  assert.match(closeBody, /if \(window && window\.handle\)[\s\S]*window\.handle\.close\(\)/, "closeWindow must close handles directly");
  assert.match(closeBody, /Quickshell\.execDetached\(\["mmsg", "-s", "-d", "killclient"\]\)/, "closeWindow must fallback to mmsg killclient");
  assert.match(logoutBody, /Quickshell\.execDetached\(\["mmsg", "-s", "-q"\]\)/, "logout must call mmsg quit");
}

const tests = [
  testMangoServiceTagParsingGuards,
  testMangoServiceWorkspaceAndWindowGuards,
  testMangoServiceScaleAndLifecycleGuards,
  testMangoServiceCommandGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
