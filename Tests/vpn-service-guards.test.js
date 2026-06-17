#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Networking/VPNService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
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

  assert.match(source, /function parseRefreshOutput\(rawOutput: string\)/, "parseRefreshOutput must type raw nmcli output");
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
