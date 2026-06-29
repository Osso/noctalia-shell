#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Networking/VPNService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testVpnPollingLifecycleGuards() {
  const barWidget = readQml("Modules/Bar/Widgets/VPN.qml");
  const controlCenterPanel = readQml("Modules/Panels/ControlCenter/ControlCenterPanel.qml");
  const panel = readQml("Modules/Panels/VPN/VPNPanel.qml");
  const beginBody = extractFunctionBody(source, "beginPolling");
  const endBody = extractFunctionBody(source, "endPolling");
  const isActiveBody = extractFunctionBody(source, "isPollingActive");
  const updateBody = extractFunctionBody(barWidget, "updateVpnPolling");
  const controlUpdateBody = extractFunctionBody(controlCenterPanel, "updateVpnPanelPolling");
  const shortcutBody = extractFunctionBody(controlCenterPanel, "shortcutSectionHasVpn");
  const hasShortcutBody = extractFunctionBody(controlCenterPanel, "hasVpnShortcut");

  assert.match(source, /property int pollingRefs: 0/, "VPNService must ref-count polling consumers");
  assert.match(source, /running: root\.isPollingActive\(\)/, "VPN refresh timer must run only while polling is active");
  assert.match(source, /Component\.onCompleted: \{\s*Logger\.i\("VPN", "Service started with lazy polling"\);\s*\}/, "VPNService must not start nmcli refresh at startup without consumers");
  assert.match(beginBody, /pollingRefs = pollingRefs \+ 1[\s\S]*refresh\(\)/, "beginPolling must increment refs and refresh immediately");
  assert.match(endBody, /pollingRefs = Math\.max\(0, pollingRefs - 1\)/, "endPolling must clamp refs at zero");
  assert.match(isActiveBody, /return pollingRefs > 0/, "isPollingActive must report positive refs");
  assert.match(updateBody, /VPNService\.beginPolling\(\)[\s\S]*VPNService\.endPolling\(\)/, "bar VPN widget must hold a polling ref only while visible");
  assert.match(shortcutBody, /Settings\.data\.controlCenter\.shortcuts\[section\] \|\| \[\][\s\S]*widgets\[i\]\.id === "VPN"/, "Control Center panel must detect configured VPN shortcuts");
  assert.match(hasShortcutBody, /shortcutSectionHasVpn\("left"\) \|\| shortcutSectionHasVpn\("right"\)/, "Control Center panel must check both shortcut sections");
  assert.match(controlUpdateBody, /const shouldRegister = shouldPoll && hasVpnShortcut\(\)[\s\S]*VPNService\.beginPolling\(\)[\s\S]*VPNService\.endPolling\(\)/, "Control Center panel must hold a polling ref only while open and containing a VPN shortcut");
  assert.match(panel, /onOpened:[\s\S]*VPNService\.beginPolling\(\)[\s\S]*onClosed:[\s\S]*VPNService\.endPolling\(\)/, "VPN panel must hold a polling ref while open");
}

function testControlCenterVpnPollingExecutes() {
  const controlCenterPanel = readQml("Modules/Panels/ControlCenter/ControlCenterPanel.qml");
  const shortcutSectionHasVpn = new Function("ctx", "section", `with (ctx) { return (function(section) ${extractFunctionBody(controlCenterPanel, "shortcutSectionHasVpn")}).call(ctx, section); }`);
  const hasVpnShortcut = new Function("ctx", `with (ctx) { return (function() ${extractFunctionBody(controlCenterPanel, "hasVpnShortcut")}).call(ctx); }`);
  const updateVpnPanelPolling = new Function("ctx", "shouldPoll", `with (ctx) { return (function(shouldPoll) ${extractFunctionBody(controlCenterPanel, "updateVpnPanelPolling")}).call(ctx, shouldPoll); }`);
  const calls = [];
  const ctx = {
    Settings: {
      data: {
        controlCenter: {
          shortcuts: {
            left: [{ id: "WiFi" }],
            right: [{ id: "VPN" }],
          },
        },
      },
    },
    vpnPollingRegistered: false,
    shortcutSectionHasVpn(section) {
      return shortcutSectionHasVpn(ctx, section);
    },
    hasVpnShortcut() {
      return hasVpnShortcut(ctx);
    },
    VPNService: {
      beginPolling() {
        calls.push("begin");
      },
      endPolling() {
        calls.push("end");
      },
    },
  };

  assert.equal(shortcutSectionHasVpn(ctx, "left"), false);
  assert.equal(shortcutSectionHasVpn(ctx, "right"), true);
  assert.equal(hasVpnShortcut(ctx), true);
  updateVpnPanelPolling(ctx, true);
  updateVpnPanelPolling(ctx, true);
  updateVpnPanelPolling(ctx, false);
  updateVpnPanelPolling(ctx, false);
  assert.deepEqual(calls, ["begin", "end"]);
}

function testVpnPollingRefsExecute() {
  const beginPolling = qmlFunction("beginPolling");
  const endPolling = qmlFunction("endPolling");
  const isPollingActive = qmlFunction("isPollingActive");
  let refreshes = 0;
  const ctx = {
    pollingRefs: 0,
    refresh() {
      refreshes++;
    },
  };

  assert.equal(isPollingActive(ctx), false);
  beginPolling(ctx);
  beginPolling(ctx);
  assert.equal(ctx.pollingRefs, 2);
  assert.equal(refreshes, 2);
  assert.equal(isPollingActive(ctx), true);
  endPolling(ctx);
  endPolling(ctx);
  endPolling(ctx);
  assert.equal(ctx.pollingRefs, 0);
  assert.equal(isPollingActive(ctx), false);
}

function testVpnRefreshGuardsConcurrentRuns() {
  const refresh = qmlFunction("refresh");
  const ctx = {
    refreshing: true,
    refreshPending: false,
    lastError: "old error",
    refreshProcess: { running: false },
  };

  refresh(ctx);
  assert.equal(ctx.refreshPending, true);
  assert.equal(ctx.lastError, "old error");
  assert.equal(ctx.refreshProcess.running, false);

  ctx.refreshing = false;
  refresh(ctx);
  assert.equal(ctx.refreshing, true);
  assert.equal(ctx.lastError, "");
  assert.equal(ctx.refreshProcess.running, true);
}

function testVpnConnectGuardsAndStartsProcess() {
  const connectVpn = qmlFunction("connect", "uuid");
  const ctx = {
    connecting: false,
    connectingUuid: "",
    lastError: "old error",
    connections: {
      "vpn-1": { name: "Work VPN" },
    },
    connectProcess: { uuid: "", name: "", running: false },
  };

  connectVpn(ctx, "");
  connectVpn(ctx, "missing");
  assert.equal(ctx.connectProcess.running, false);

  connectVpn(ctx, "vpn-1");
  assert.equal(ctx.connecting, true);
  assert.equal(ctx.connectingUuid, "vpn-1");
  assert.equal(ctx.lastError, "");
  assert.deepEqual(ctx.connectProcess, { uuid: "vpn-1", name: "Work VPN", running: true });

  ctx.connectProcess.running = false;
  connectVpn(ctx, "vpn-1");
  assert.equal(ctx.connectProcess.running, false);
}

function testVpnDisconnectGuardsAndStartsProcess() {
  const disconnectVpn = qmlFunction("disconnect", "uuid");
  const ctx = {
    disconnecting: false,
    disconnectingUuid: "",
    lastError: "old error",
    connections: {
      "vpn-1": { name: "Work VPN" },
    },
    disconnectProcess: { uuid: "", name: "", running: false },
  };

  disconnectVpn(ctx, "");
  disconnectVpn(ctx, "missing");
  assert.equal(ctx.disconnectProcess.running, false);

  disconnectVpn(ctx, "vpn-1");
  assert.equal(ctx.disconnecting, true);
  assert.equal(ctx.disconnectingUuid, "vpn-1");
  assert.equal(ctx.lastError, "");
  assert.deepEqual(ctx.disconnectProcess, { uuid: "vpn-1", name: "Work VPN", running: true });

  ctx.disconnectProcess.running = false;
  disconnectVpn(ctx, "vpn-1");
  assert.equal(ctx.disconnectProcess.running, false);
}

function testVpnToggleDelegatesByConnectionState() {
  const toggle = qmlFunction("toggle", "uuid");
  const calls = [];
  const ctx = {
    connections: {
      active: { active: true },
      inactive: { active: false },
    },
    connect(uuid) {
      calls.push(["connect", uuid]);
    },
    disconnect(uuid) {
      calls.push(["disconnect", uuid]);
    },
  };

  toggle(ctx, "missing");
  toggle(ctx, "active");
  toggle(ctx, "inactive");

  assert.deepEqual(calls, [
    ["disconnect", "active"],
    ["connect", "inactive"],
  ]);
}

function testVpnSetConnectionReplacesKnownConnectionOnly() {
  const setConnection = qmlFunction("setConnection", "uuid", "data");
  const original = {
    "vpn-1": { uuid: "vpn-1", name: "Work VPN", active: false },
  };
  const ctx = {
    connections: original,
  };

  setConnection(ctx, "", { active: true });
  setConnection(ctx, "missing", { active: true });
  assert.equal(ctx.connections, original);

  setConnection(ctx, "vpn-1", { active: true, device: "tun0" });
  assert.notEqual(ctx.connections, original);
  assert.deepEqual(ctx.connections["vpn-1"], {
    uuid: "vpn-1",
    name: "Work VPN",
    active: true,
    device: "tun0",
  });
}

function testVpnScheduleRefreshRestartsTimer() {
  const scheduleRefresh = qmlFunction("scheduleRefresh", "interval");
  let restarts = 0;
  const ctx = {
    delayedRefreshTimer: {
      interval: 1000,
      restart() {
        restarts++;
      },
    },
  };

  scheduleRefresh(ctx, 250);

  assert.equal(ctx.delayedRefreshTimer.interval, 250);
  assert.equal(restarts, 1);
}

function testVpnParsesRefreshOutput() {
  const parseRefreshOutput = qmlFunction("parseRefreshOutput", "rawOutput");

  assert.match(source, /function parseRefreshOutput\(rawOutput\)/, "parseRefreshOutput must type raw nmcli output");
  assert.deepEqual(parseRefreshOutput({}, [
    "Work:VPN:11111111-1111-1111-1111-111111111111:vpn:tun0",
    "Wire:Guard:22222222-2222-2222-2222-222222222222:wireguard:--",
    "Home WiFi:33333333-3333-3333-3333-333333333333:802-11-wireless:wlan0",
    "malformed",
    "Missing UUID::vpn:tun1",
  ].join("\n")), {
    "11111111-1111-1111-1111-111111111111": {
      uuid: "11111111-1111-1111-1111-111111111111",
      name: "Work:VPN",
      device: "tun0",
      active: true,
    },
    "22222222-2222-2222-2222-222222222222": {
      uuid: "22222222-2222-2222-2222-222222222222",
      name: "Wire:Guard",
      device: "--",
      active: false,
    },
  });
  assert.deepEqual(parseRefreshOutput({}, ""), {});
}

const tests = [
  testVpnPollingLifecycleGuards,
  testControlCenterVpnPollingExecutes,
  testVpnPollingRefsExecute,
  testVpnRefreshGuardsConcurrentRuns,
  testVpnConnectGuardsAndStartsProcess,
  testVpnDisconnectGuardsAndStartsProcess,
  testVpnToggleDelegatesByConnectionState,
  testVpnSetConnectionReplacesKnownConnectionOnly,
  testVpnScheduleRefreshRestartsTimer,
  testVpnParsesRefreshOutput,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
