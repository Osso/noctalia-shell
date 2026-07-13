#!/usr/bin/env node

const assert = require("assert/strict");
const { readQml } = require("./qml-test-utils");

function stripComments(source) {
  let result = "";
  let quote = "";
  for (let index = 0; index < source.length; index++) {
    const current = source[index];
    const next = source[index + 1];
    if (quote) {
      result += current;
      if (current === "\\") {
        result += next || "";
        index++;
      } else if (current === quote) {
        quote = "";
      }
    } else if (current === '"' || current === "'" || current === "`") {
      quote = current;
      result += current;
    } else if (current === "/" && next === "/") {
      while (index < source.length && source[index] !== "\n") index++;
      result += "\n";
    } else if (current === "/" && next === "*") {
      index += 2;
      while (index < source.length - 1 && !(source[index] === "*" && source[index + 1] === "/")) index++;
      index++;
    } else {
      result += current;
    }
  }
  return result;
}

const panel = stripComments(readQml("Modules/Panels/VPN/VPNPanel.qml"));
const item = stripComments(readQml("Modules/Panels/VPN/VPNConnectionItem.qml"));
const bar = stripComments(readQml("Modules/Bar/Widgets/VPN.qml"));
const controlCenter = stripComments(readQml("Modules/Panels/ControlCenter/Widgets/VPN.qml"));

function extractBlocks(source, componentName) {
  const marker = `${componentName} {`;
  const blocks = [];
  let start = source.indexOf(marker);
  while (start !== -1) {
    const open = source.indexOf("{", start);
    let depth = 0;
    let end = -1;
    let quote = "";
    for (let index = open; index < source.length; index++) {
      const current = source[index];
      if (quote) {
        if (current === "\\") index++;
        else if (current === quote) quote = "";
        continue;
      }
      if (current === '"' || current === "'" || current === "`") {
        quote = current;
        continue;
      }
      if (current === "{") depth++;
      if (current === "}") depth--;
      if (depth === 0) {
        end = index;
        break;
      }
    }
    assert.notEqual(end, -1, `unterminated ${componentName} block`);
    blocks.push(source.slice(start, end + 1));
    start = source.indexOf(marker, end + 1);
  }
  return blocks;
}

function extractHandler(source, handlerName) {
  const marker = `${handlerName}:`;
  const start = source.indexOf(marker);
  assert.notEqual(start, -1, `missing ${handlerName} handler`);
  const open = source.indexOf("{", start);
  let depth = 0;
  let quote = "";
  for (let index = open; index < source.length; index++) {
    const current = source[index];
    if (quote) {
      if (current === "\\") index++;
      else if (current === quote) quote = "";
      continue;
    }
    if (current === '"' || current === "'" || current === "`") {
      quote = current;
      continue;
    }
    if (current === "{") depth++;
    if (current === "}") depth--;
    if (depth === 0) return source.slice(start, index + 1);
  }
  assert.fail(`unterminated ${handlerName} handler`);
}

function findSingleBlock(source, componentName, marker) {
  const matches = extractBlocks(source, componentName).filter(block => block.includes(marker));
  assert.equal(matches.length, 1, `${componentName} block containing ${marker} must be unique`);
  return matches[0];
}

function testPanelOwnsPollingAndRendersBothConnectionGroups() {
  assert.match(panel, /onOpened:\s*VPNService\.beginPolling\(\)/);
  assert.match(panel, /onClosed:\s*VPNService\.endPolling\(\)/);
  const lists = extractBlocks(panel, "VPNConnectionsList");
  assert.equal(lists.length, 2);
  assert.match(lists[0], /^\s*label:\s*I18n\.tr\("vpn\.panel\.active-connections"\)\s*$/m);
  assert.match(lists[0], /^\s*model:\s*VPNService\.activeConnections\s*$/m);
  assert.match(lists[1], /^\s*label:\s*I18n\.tr\("vpn\.panel\.available-connections"\)\s*$/m);
  assert.match(lists[1], /^\s*model:\s*VPNService\.inactiveConnections\s*$/m);
  const refreshButton = findSingleBlock(panel, "NIconButton", "tooltips.refresh");
  assert.match(refreshButton, /onClicked:\s*VPNService\.refresh\(\)/);
}

function testConnectionRowRoutesOneBusySafeAction() {
  assert.match(item, /readonly property bool isConnecting:\s*VPNService\.connectingUuid === connectionUuid/);
  assert.match(item, /readonly property bool isDisconnecting:\s*VPNService\.disconnectingUuid === connectionUuid/);
  assert.match(item, /^\s*readonly property bool isBusy:\s*isConnecting \|\| isDisconnecting\s*$/m);
  const buttons = extractBlocks(item, "NButton");
  assert.equal(buttons.length, 1);
  assert.match(buttons[0], /^\s*enabled:\s*!isBusy\s*$/m);
  assert.match(buttons[0], /if \(isActive\) \{\s*VPNService\.disconnect\(connectionUuid\);\s*\} else \{\s*VPNService\.connect\(connectionUuid\);/);
}

function testControlCenterTogglesTheScreenVpnPanel() {
  const clicked = extractHandler(controlCenter, "onClicked");
  assert.match(clicked, /PanelService\.getPanel\("vpnPanel", screen\)/);
  assert.match(clicked, /if \(panel\)\s*panel\.toggle\(this\)/);
}

function testBarMenuRoutesVpnAndSettingsActions() {
  const menu = findSingleBlock(bar, "NPopupContextMenu", "id: contextMenu");
  assert.match(menu, /"action":\s*"disconnect:" \+ conn\.uuid/);
  assert.match(menu, /"action":\s*"connect:" \+ conn\.uuid/);
  assert.match(menu, /"action":\s*"widget-settings"/);
  const triggered = extractHandler(menu, "onTriggered");
  assert.match(triggered, /if \(action === "widget-settings"\) \{\s*BarService\.openWidgetSettings\(screen, section, sectionWidgetIndex, widgetId, widgetSettings\);\s*return;/);
  assert.match(triggered, /if \(action\.startsWith\("connect:"\)\) \{\s*const uuid = action\.substring\("connect:"\.length\);\s*VPNService\.connect\(uuid\);\s*return;/);
  assert.match(triggered, /if \(action\.startsWith\("disconnect:"\)\) \{\s*const uuid = action\.substring\("disconnect:"\.length\);\s*VPNService\.disconnect\(uuid\);/);
  const pill = findSingleBlock(bar, "BarPill", "id: pill");
  for (const handler of ["onClicked", "onRightClicked"]) {
    const body = extractHandler(pill, handler);
    assert.match(body, /popupMenuWindow\.showContextMenu\(contextMenu\)/);
    assert.match(body, /contextMenu\.openAtItem\(pill, pos\.x, pos\.y\)/);
  }
}

for (const test of [
  testPanelOwnsPollingAndRendersBothConnectionGroups,
  testConnectionRowRoutesOneBusySafeAction,
  testControlCenterTogglesTheScreenVpnPanel,
  testBarMenuRoutesVpnAndSettingsActions,
]) {
  test();
  console.log(`ok ${test.name}`);
}
