#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testPanelRegistrationGuards() {
  const source = readQml("Services/UI/PanelService.qml");
  const registerPanelBody = extractFunctionBody(source, "registerPanel");
  const registerPopupBody = extractFunctionBody(source, "registerPopupMenuWindow");

  assert.match(registerPanelBody, /registeredPanels\[panel\.objectName\] = panel/, "registerPanel must store panels by objectName");
  assert.match(registerPanelBody, /Logger\.d\("PanelService", "Registered panel:", panel\.objectName\)/, "registerPanel must log registered panel names");
  assert.match(registerPopupBody, /if \(!screen \|\| !window\)[\s\S]*return/, "registerPopupMenuWindow must ignore missing screen or window");
  assert.match(registerPopupBody, /var key = screen\.name[\s\S]*popupMenuWindows\[key\] = window/, "registerPopupMenuWindow must store windows by screen name");
  assert.match(registerPopupBody, /popupMenuWindowRegistered\(screen\)/, "registerPopupMenuWindow must emit registration signal");
}

function testPanelLookupGuards() {
  const source = readQml("Services/UI/PanelService.qml");
  const getPopupBody = extractFunctionBody(source, "getPopupMenuWindow");
  const getPanelBody = extractFunctionBody(source, "getPanel");
  const hasPanelBody = extractFunctionBody(source, "hasPanel");

  assert.match(getPopupBody, /if \(!screen\)[\s\S]*return null/, "getPopupMenuWindow must return null without a screen");
  assert.match(getPopupBody, /return popupMenuWindows\[screen\.name\] \|\| null/, "getPopupMenuWindow must fall back to null for unknown screens");
  assert.match(getPanelBody, /if \(!screen\)[\s\S]*for \(var key in registeredPanels\)[\s\S]*key\.startsWith\(name \+ "-"\)[\s\S]*return registeredPanels\[key\]/, "getPanel must fall back to first matching panel when screen is missing");
  assert.match(getPanelBody, /var panelKey = `\$\{name\}-\$\{screen\.name\}`/, "getPanel must include screen name in panel keys");
  assert.match(getPanelBody, /if \(registeredPanels\[panelKey\]\)[\s\S]*return registeredPanels\[panelKey\]/, "getPanel must return already registered screen panel");
  assert.match(getPanelBody, /Logger\.w\("PanelService", "Panel not found:", panelKey\)[\s\S]*return null/, "getPanel must log and fail closed for missing panel keys");
  assert.match(hasPanelBody, /return name in registeredPanels/, "hasPanel must query registered panel keys");
}

function testPanelOpenCloseGuards() {
  const source = readQml("Services/UI/PanelService.qml");
  const willOpenBody = extractFunctionBody(source, "willOpenPanel");
  const closedBody = extractFunctionBody(source, "closedPanel");

  assert.match(willOpenBody, /if \(openedPanel && openedPanel !== panel\)[\s\S]*openedPanel\.close\(\)/, "willOpenPanel must close a different open panel");
  assert.match(willOpenBody, /openedPanel = panel[\s\S]*willOpen\(\)/, "willOpenPanel must set openedPanel before emitting");
  assert.match(closedBody, /if \(openedPanel && openedPanel === panel\)[\s\S]*openedPanel = null/, "closedPanel must clear only the active panel");
  assert.match(closedBody, /didClose\(\)/, "closedPanel must emit didClose");
}

const tests = [
  testPanelRegistrationGuards,
  testPanelLookupGuards,
  testPanelOpenCloseGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
