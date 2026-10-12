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
const item = stripQmlComments(
  readQml("Modules/Panels/VPN/VPNConnectionItem.qml"),
);
const bar = stripQmlComments(readQml("Modules/Bar/Widgets/VPN.qml"));
const controlCenter = stripQmlComments(
  readQml("Modules/Panels/ControlCenter/Widgets/VPN.qml"),
);

function evaluateBinding(block, property, ctx) {
  const match = block.match(
    new RegExp(`^\\s*(?:readonly property \\w+ )?${property}:\\s*(.+)$`, "m"),
  );
  assert.ok(match, `missing ${property} binding`);
  if (match[1] === "{") {
    return executeHandler(block, property, ctx);
  }
  return new Function("ctx", `with (ctx) { return (${match[1]}); }`)(ctx);
}

function executeHandler(block, handler, ctx, ...args) {
  const match = block.match(new RegExp(`^\\s*${handler}:\\s*(.+)$`, "m"));
  assert.ok(match, `missing ${handler} handler`);
  if (!match[1].includes("{")) {
    return new Function("ctx", `with (ctx) { ${match[1]}; }`)(ctx);
  }
  const declaration = extractHandlerBlock(block, handler);
  const body = declaration.slice(declaration.indexOf("{"));
  const prefix = match[1].slice(0, match[1].indexOf("{"));
  const callback = prefix.includes("=>")
    ? `${prefix}${body}`
    : `function() ${body}`;
  return new Function(
    "ctx",
    "args",
    `with (ctx) { return (${callback}).apply(ctx, args); }`,
  )(ctx, args);
}

function testPanelOwnsPollingAndRendersBothConnectionGroups() {
  const calls = [];
  const VPNService = {
    activeConnections: [{ uuid: "work", name: "Work", active: true }],
    inactiveConnections: [{ uuid: "home", name: "Home", active: false }],
    beginPolling() {
      calls.push("begin");
    },
    endPolling() {
      calls.push("end");
    },
    refresh() {
      calls.push("refresh");
    },
  };
  const ctx = { VPNService, I18n: { tr: (key) => key } };
  executeHandler(panel, "onOpened", ctx);
  const lists = extractComponentBlocks(panel, "VPNConnectionsList");
  assert.deepEqual(
    lists.map((list) => evaluateBinding(list, "label", ctx)),
    ["vpn.panel.active-connections", "vpn.panel.available-connections"],
  );
  assert.deepEqual(
    lists.map((list) => evaluateBinding(list, "model", ctx)),
    [
      [{ uuid: "work", name: "Work", active: true }],
      [{ uuid: "home", name: "Home", active: false }],
    ],
  );
  executeHandler(
    findComponentBlock(panel, "NIconButton", "tooltips.refresh"),
    "onClicked",
    ctx,
  );
  executeHandler(panel, "onClosed", ctx);
  assert.deepEqual(calls, ["begin", "refresh", "end"]);
}

function testConnectionRowRoutesOneBusySafeAction() {
  const calls = [];
  const VPNService = {
    connectingUuid: "",
    disconnectingUuid: "",
    connect: (uuid) => calls.push(["connect", uuid]),
    disconnect: (uuid) => calls.push(["disconnect", uuid]),
  };
  const root = { connectionUuid: "work", connectionActive: false };
  const ctx = { root, VPNService };
  for (const property of [
    "isActive",
    "isConnecting",
    "isDisconnecting",
    "isBusy",
  ]) {
    Object.defineProperty(root, property, {
      get: () => evaluateBinding(item, property, ctx),
    });
  }
  const buttons = extractComponentBlocks(item, "NButton");
  assert.equal(buttons.length, 1);
  const clickEnabledButton = () => {
    if (evaluateBinding(buttons[0], "enabled", ctx)) {
      executeHandler(buttons[0], "onClicked", ctx);
    }
  };
  clickEnabledButton();
  root.connectionActive = true;
  clickEnabledButton();
  for (const pending of ["connectingUuid", "disconnectingUuid"]) {
    VPNService[pending] = "work";
    assert.equal(root.isBusy, true);
    assert.equal(evaluateBinding(buttons[0], "enabled", ctx), false);
    clickEnabledButton();
    VPNService[pending] = "other";
    assert.equal(evaluateBinding(buttons[0], "enabled", ctx), true);
    VPNService[pending] = "";
  }
  assert.deepEqual(calls, [
    ["connect", "work"],
    ["disconnect", "work"],
  ]);
}

function testControlCenterTogglesTheScreenVpnPanel() {
  const calls = [];
  const screens = [{ name: "DP-1" }, { name: "HDMI-A-1" }];
  for (const screen of screens) {
    const ctx = {
      screen,
      PanelService: {
        getPanel(name, requestedScreen) {
          assert.equal(name, "vpnPanel");
          assert.equal(requestedScreen, screen);
          return { toggle: (owner) => calls.push([requestedScreen, owner]) };
        },
      },
    };
    executeHandler(controlCenter, "onClicked", ctx);
    assert.equal(calls.at(-1)[1], ctx);
  }
  assert.deepEqual(
    calls.map((call) => call[0]),
    screens,
  );
  executeHandler(controlCenter, "onClicked", {
    screen: screens[0],
    PanelService: { getPanel: () => null },
  });
  assert.equal(calls.length, 2);
}

function testBarMenuRoutesVpnAndSettingsActions() {
  const menu = findComponentBlock(bar, "NPopupContextMenu", "id: contextMenu");
  const calls = [];
  const root = {
    screen: { name: "DP-1" },
    section: "right",
    sectionWidgetIndex: 2,
    widgetId: "VPN",
    widgetSettings: { displayMode: "alwaysShow" },
  };
  const pill = {};
  const contextMenu = {
    implicitWidth: 200,
    implicitHeight: 100,
    openAtItem: (...args) => calls.push(["open", ...args]),
  };
  let popupAvailable = true;
  const ctx = {
    root,
    screen: root.screen,
    pill,
    contextMenu,
    I18n: { tr: (key, data) => (data ? `${key}:${data.name}` : key) },
    VPNService: {
      activeConnections: [{ uuid: "work:1", name: "Work" }],
      inactiveConnections: [{ uuid: "home:2", name: "Home" }],
      connect: (uuid) => calls.push(["connect", uuid]),
      disconnect: (uuid) => calls.push(["disconnect", uuid]),
    },
    PanelService: {
      getPopupMenuWindow(screen) {
        assert.equal(screen, root.screen);
        return popupAvailable
          ? {
              close: () => calls.push(["close"]),
              showContextMenu: (menu) => calls.push(["show", menu]),
            }
          : null;
      },
    },
    BarService: {
      openWidgetSettings: (...args) => calls.push(["settings", ...args]),
      getContextMenuPosition(anchor, width, height) {
        assert.equal(anchor, pill);
        assert.deepEqual([width, height], [200, 100]);
        return { x: 10, y: 20 };
      },
    },
  };
  const entries = evaluateBinding(menu, "model", ctx);
  assert.deepEqual(entries, [
    {
      label: "context-menu.disconnect-vpn:Work",
      action: "disconnect:work:1",
      icon: "shield-off",
    },
    {
      label: "context-menu.connect-vpn:Home",
      action: "connect:home:2",
      icon: "shield-lock",
    },
    {
      label: "context-menu.widget-settings",
      action: "widget-settings",
      icon: "settings",
    },
  ]);
  for (const entry of entries)
    executeHandler(menu, "onTriggered", ctx, entry.action);
  assert.deepEqual(calls, [
    ["close"],
    ["disconnect", "work:1"],
    ["close"],
    ["connect", "home:2"],
    ["close"],
    ["settings", root.screen, "right", 2, "VPN", root.widgetSettings],
  ]);
  calls.length = 0;
  executeHandler(menu, "onTriggered", ctx, "");
  executeHandler(menu, "onTriggered", ctx, "unknown");
  assert.deepEqual(calls, [["close"], ["close"]]);
  const pillBlock = findComponentBlock(bar, "BarPill", "id: pill");
  for (const handler of ["onClicked", "onRightClicked"]) {
    calls.length = 0;
    executeHandler(pillBlock, handler, ctx);
    assert.deepEqual(calls, [
      ["show", contextMenu],
      ["open", pill, 10, 20],
    ]);
    popupAvailable = false;
    calls.length = 0;
    executeHandler(pillBlock, handler, ctx);
    assert.deepEqual(calls, []);
    popupAvailable = true;
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
