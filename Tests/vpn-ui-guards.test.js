#!/usr/bin/env node

const assert = require("assert/strict");
const {
  extractComponentBlocks,
  extractHandlerBlock,
  findComponentBlock,
  readQml,
  stripQmlComments,
} = require("./qml-test-utils");

const panel = stripQmlComments(readQml("Modules/Panels/VPN/VPNPanel.qml"));
const item = stripQmlComments(readQml("Modules/Panels/VPN/VPNConnectionItem.qml"));
const bar = stripQmlComments(readQml("Modules/Bar/Widgets/VPN.qml"));
const controlCenter = stripQmlComments(readQml("Modules/Panels/ControlCenter/Widgets/VPN.qml"));

function testPanelOwnsPollingAndRendersBothConnectionGroups() {
  assert.match(panel, /onOpened:\s*VPNService\.beginPolling\(\)/);
  assert.match(panel, /onClosed:\s*VPNService\.endPolling\(\)/);
  const lists = extractComponentBlocks(panel, "VPNConnectionsList");
  assert.equal(lists.length, 2);
  assert.match(lists[0], /^\s*label:\s*I18n\.tr\("vpn\.panel\.active-connections"\)\s*$/m);
  assert.match(lists[0], /^\s*model:\s*VPNService\.activeConnections\s*$/m);
  assert.match(lists[1], /^\s*label:\s*I18n\.tr\("vpn\.panel\.available-connections"\)\s*$/m);
  assert.match(lists[1], /^\s*model:\s*VPNService\.inactiveConnections\s*$/m);
  const refreshButton = findComponentBlock(panel, "NIconButton", "tooltips.refresh");
  assert.match(refreshButton, /onClicked:\s*VPNService\.refresh\(\)/);
}

function testConnectionRowRoutesOneBusySafeAction() {
  assert.match(item, /readonly property bool isConnecting:\s*VPNService\.connectingUuid === connectionUuid/);
  assert.match(item, /readonly property bool isDisconnecting:\s*VPNService\.disconnectingUuid === connectionUuid/);
  assert.match(item, /^\s*readonly property bool isBusy:\s*isConnecting \|\| isDisconnecting\s*$/m);
  const buttons = extractComponentBlocks(item, "NButton");
  assert.equal(buttons.length, 1);
  assert.match(buttons[0], /^\s*enabled:\s*!isBusy\s*$/m);
  assert.match(buttons[0], /if \(isActive\) \{\s*VPNService\.disconnect\(connectionUuid\);\s*\} else \{\s*VPNService\.connect\(connectionUuid\);/);
}

function testControlCenterTogglesTheScreenVpnPanel() {
  const clicked = extractHandlerBlock(controlCenter, "onClicked");
  assert.match(clicked, /PanelService\.getPanel\("vpnPanel", screen\)/);
  assert.match(clicked, /if \(panel\)\s*panel\.toggle\(this\)/);
}

function testBarMenuRoutesVpnAndSettingsActions() {
  const menu = findComponentBlock(bar, "NPopupContextMenu", "id: contextMenu");
  assert.match(menu, /"action":\s*"disconnect:" \+ conn\.uuid/);
  assert.match(menu, /"action":\s*"connect:" \+ conn\.uuid/);
  assert.match(menu, /"action":\s*"widget-settings"/);
  const triggered = extractHandlerBlock(menu, "onTriggered");
  assert.match(triggered, /if \(action === "widget-settings"\) \{\s*BarService\.openWidgetSettings\(screen, section, sectionWidgetIndex, widgetId, widgetSettings\);\s*return;/);
  assert.match(triggered, /if \(action\.startsWith\("connect:"\)\) \{\s*const uuid = action\.substring\("connect:"\.length\);\s*VPNService\.connect\(uuid\);\s*return;/);
  assert.match(triggered, /if \(action\.startsWith\("disconnect:"\)\) \{\s*const uuid = action\.substring\("disconnect:"\.length\);\s*VPNService\.disconnect\(uuid\);/);
  const pill = findComponentBlock(bar, "BarPill", "id: pill");
  for (const handler of ["onClicked", "onRightClicked"]) {
    const body = extractHandlerBlock(pill, handler);
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
