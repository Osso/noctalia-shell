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
  assert.match(controlCenterPanel, /import qs\.Services\.Networking/, "Control Center panel must import VPNService before using it");
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
    connectProcess: { uuid: "", name: "", output: "stale", errorOutput: "stale", exitObserved: true, running: false },
  };

  connectVpn(ctx, "");
  connectVpn(ctx, "missing");
  assert.equal(ctx.connectProcess.running, false);

  ctx.connectProcess.running = true;
  connectVpn(ctx, "vpn-1");
  assert.equal(ctx.connecting, false, "running process must block a second connect even if flags desynchronize");
  ctx.connectProcess.running = false;

  connectVpn(ctx, "vpn-1");
  assert.equal(ctx.connecting, true);
  assert.equal(ctx.connectingUuid, "vpn-1");
  assert.equal(ctx.lastError, "");
  assert.deepEqual(ctx.connectProcess, { uuid: "vpn-1", name: "Work VPN", output: "", errorOutput: "", exitObserved: false, running: true });

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
    disconnectProcess: { uuid: "", name: "", output: "stale", errorOutput: "stale", exitObserved: true, running: false },
  };

  disconnectVpn(ctx, "");
  disconnectVpn(ctx, "missing");
  assert.equal(ctx.disconnectProcess.running, false);

  ctx.disconnectProcess.running = true;
  disconnectVpn(ctx, "vpn-1");
  assert.equal(ctx.disconnecting, false, "running process must block a second disconnect even if flags desynchronize");
  ctx.disconnectProcess.running = false;

  disconnectVpn(ctx, "vpn-1");
  assert.equal(ctx.disconnecting, true);
  assert.equal(ctx.disconnectingUuid, "vpn-1");
  assert.equal(ctx.lastError, "");
  assert.deepEqual(ctx.disconnectProcess, { uuid: "vpn-1", name: "Work VPN", output: "", errorOutput: "", exitObserved: false, running: true });

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

function testVpnRefreshCompletionExecutesSuccessFailureAndPendingDrain() {
  const finishRefresh = qmlFunction("finishRefresh", "exitCode", "output", "errorOutput");
  const createContext = overrides => {
    const schedules = [];
    const ctx = {
      refreshing: true,
      refreshPending: false,
      connections: { old: { uuid: "old" } },
      lastError: "",
      Logger: { w() {} },
      parseRefreshOutput(rawOutput) {
        return rawOutput ? { fresh: { uuid: "fresh", active: true } } : {};
      },
      scheduleRefresh(interval) {
        schedules.push(interval);
      },
      ...overrides,
    };
    ctx.root = ctx;
    ctx.schedules = schedules;
    return ctx;
  };

  const success = createContext({ refreshPending: true });
  finishRefresh(success, 0, "vpn output", "");
  assert.deepEqual(success.connections, { fresh: { uuid: "fresh", active: true } });
  assert.equal(success.refreshing, false);
  assert.equal(success.refreshPending, false);
  assert.deepEqual(success.schedules, [200]);

  const failure = createContext({ refreshPending: true });
  finishRefresh(failure, 10, "", "nmcli denied\nmore");
  assert.deepEqual(failure.connections, { old: { uuid: "old" } });
  assert.equal(failure.lastError, "nmcli denied");
  assert.equal(failure.refreshing, false);
  assert.deepEqual(failure.schedules, [2000]);
}

function testVpnRefreshStartFailureExecutesWithoutExitedSignal() {
  const handleRefreshStartFailure = qmlFunction("handleRefreshStartFailure", "exitObserved");
  const finishRefresh = qmlFunction("finishRefresh", "exitCode", "output", "errorOutput");
  const ctx = {
    refreshing: true,
    refreshPending: false,
    connections: {},
    lastError: "",
    Logger: { w() {} },
    parseRefreshOutput() { return {}; },
    scheduleRefresh() {},
  };
  ctx.root = ctx;
  ctx.finishRefresh = (exitCode, output, errorOutput) => finishRefresh(ctx, exitCode, output, errorOutput);

  handleRefreshStartFailure(ctx, false);
  assert.equal(ctx.refreshing, false);
  assert.match(ctx.lastError, /failed to start/);

  ctx.refreshing = true;
  ctx.lastError = "";
  handleRefreshStartFailure(ctx, true);
  assert.equal(ctx.refreshing, true);
  assert.equal(ctx.lastError, "");
}

function createVpnActionContext() {
  const connectionUpdates = [];
  const notices = [];
  const warnings = [];
  const schedules = [];
  const ctx = {
    connecting: true,
    connectingUuid: "vpn-1",
    disconnecting: true,
    disconnectingUuid: "vpn-1",
    lastError: "",
    Logger: { i() {}, w() {} },
    I18n: { tr(key) { return key; } },
    ToastService: {
      showNotice(...args) { notices.push(args); },
      showWarning(...args) { warnings.push(args); },
    },
    setConnection(uuid, data) { connectionUpdates.push([uuid, data]); },
    scheduleRefresh(interval) { schedules.push(interval); },
  };
  ctx.root = ctx;
  ctx.connectionUpdates = connectionUpdates;
  ctx.notices = notices;
  ctx.warnings = warnings;
  ctx.schedules = schedules;
  return ctx;
}

function testVpnConnectCompletionUsesExitStatus() {
  const finishConnect = qmlFunction("finishConnect", "uuid", "name", "exitCode", "output", "errorOutput");
  const success = createVpnActionContext();
  finishConnect(success, "vpn-1", "Work VPN", 0, "localized success", "");
  assert.deepEqual(success.connectionUpdates, [["vpn-1", { active: true }]]);
  assert.equal(success.connecting, false);
  assert.equal(success.connectingUuid, "");
  assert.equal(success.lastError, "");
  assert.equal(success.notices.length, 1);
  assert.deepEqual(success.schedules, [1000]);

  const reentrant = createVpnActionContext();
  Object.defineProperty(reentrant, "connecting", {
    get() { return true; },
    set(value) {
      if (!value)
        reentrant.connectingUuid = "vpn-2";
    },
  });
  finishConnect(reentrant, "vpn-1", "Work VPN", 0, "", "");
  assert.equal(reentrant.connectingUuid, "vpn-2", "completion must not clobber an action started by busy-state observers");

  const stale = createVpnActionContext();
  stale.connectingUuid = "vpn-2";
  finishConnect(stale, "vpn-1", "Work VPN", 0, "", "");
  assert.equal(stale.connecting, true, "stale completion must not clear a newer action");
  assert.equal(stale.connectingUuid, "vpn-2");
  assert.deepEqual(stale.connectionUpdates, []);

  const failure = createVpnActionContext();
  finishConnect(failure, "vpn-1", "Work VPN", 10, "stdout diagnostic\nmore", "");
  assert.deepEqual(failure.connectionUpdates, []);
  assert.equal(failure.connecting, false);
  assert.equal(failure.connectingUuid, "");
  assert.equal(failure.lastError, "stdout diagnostic");
  assert.equal(failure.warnings.length, 1);
  assert.deepEqual(failure.schedules, []);
}

function testVpnDisconnectCompletionUsesExitStatus() {
  const finishDisconnect = qmlFunction("finishDisconnect", "uuid", "name", "exitCode", "output", "errorOutput");
  const success = createVpnActionContext();
  finishDisconnect(success, "vpn-1", "Work VPN", 0, "", "");
  assert.deepEqual(success.connectionUpdates, [["vpn-1", { active: false, device: "" }]]);
  assert.equal(success.disconnecting, false);
  assert.equal(success.disconnectingUuid, "");
  assert.equal(success.notices.length, 1);
  assert.deepEqual(success.schedules, [1000]);

  const reentrant = createVpnActionContext();
  Object.defineProperty(reentrant, "disconnecting", {
    get() { return true; },
    set(value) {
      if (!value)
        reentrant.disconnectingUuid = "vpn-2";
    },
  });
  finishDisconnect(reentrant, "vpn-1", "Work VPN", 0, "", "");
  assert.equal(reentrant.disconnectingUuid, "vpn-2", "completion must not clobber an action started by busy-state observers");

  const stale = createVpnActionContext();
  stale.disconnectingUuid = "vpn-2";
  finishDisconnect(stale, "vpn-1", "Work VPN", 0, "", "");
  assert.equal(stale.disconnecting, true, "stale completion must not clear a newer action");
  assert.equal(stale.disconnectingUuid, "vpn-2");
  assert.deepEqual(stale.connectionUpdates, []);

  const failure = createVpnActionContext();
  finishDisconnect(failure, "vpn-1", "Work VPN", 10, "stdout diagnostic", "");
  assert.deepEqual(failure.connectionUpdates, []);
  assert.equal(failure.disconnecting, false);
  assert.equal(failure.lastError, "stdout diagnostic");
  assert.equal(failure.warnings.length, 1);
}

function testVpnActionStartFailuresDoNotDoubleFinalize() {
  const finishConnect = qmlFunction("finishConnect", "uuid", "name", "exitCode", "output", "errorOutput");
  const finishDisconnect = qmlFunction("finishDisconnect", "uuid", "name", "exitCode", "output", "errorOutput");
  const handleConnectStartFailure = qmlFunction("handleConnectStartFailure", "uuid", "name", "exitObserved");
  const handleDisconnectStartFailure = qmlFunction("handleDisconnectStartFailure", "uuid", "name", "exitObserved");

  const connect = createVpnActionContext();
  connect.finishConnect = (...args) => finishConnect(connect, ...args);
  handleConnectStartFailure(connect, "vpn-1", "Work VPN", false);
  assert.equal(connect.connecting, false);
  assert.match(connect.lastError, /failed to start/);
  const normalConnectExit = createVpnActionContext();
  normalConnectExit.finishConnect = (...args) => finishConnect(normalConnectExit, ...args);
  handleConnectStartFailure(normalConnectExit, "vpn-1", "Work VPN", true);
  assert.equal(normalConnectExit.connecting, true);
  assert.equal(normalConnectExit.connectingUuid, "vpn-1");
  assert.equal(normalConnectExit.warnings.length, 0);

  const disconnect = createVpnActionContext();
  disconnect.finishDisconnect = (...args) => finishDisconnect(disconnect, ...args);
  handleDisconnectStartFailure(disconnect, "vpn-1", "Work VPN", false);
  assert.equal(disconnect.disconnecting, false);
  assert.match(disconnect.lastError, /failed to start/);
  const normalDisconnectExit = createVpnActionContext();
  normalDisconnectExit.finishDisconnect = (...args) => finishDisconnect(normalDisconnectExit, ...args);
  handleDisconnectStartFailure(normalDisconnectExit, "vpn-1", "Work VPN", true);
  assert.equal(normalDisconnectExit.disconnecting, true);
  assert.equal(normalDisconnectExit.disconnectingUuid, "vpn-1");
  assert.equal(normalDisconnectExit.warnings.length, 0);
}

function testVpnActionProcessesRouteBufferedExitAndStartFailure() {
  assert.match(source, /id:\s*connectProcess[\s\S]*?property string output[\s\S]*?property string errorOutput[\s\S]*?property bool exitObserved/);
  assert.match(source, /id:\s*connectProcess[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?exitObserved = true[\s\S]*?finishConnect/);
  assert.match(source, /id:\s*connectProcess[\s\S]*?onRunningChanged:[\s\S]*?handleConnectStartFailure/);
  assert.match(source, /id:\s*disconnectProcess[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?exitObserved = true[\s\S]*?finishDisconnect/);
  assert.match(source, /id:\s*disconnectProcess[\s\S]*?onRunningChanged:[\s\S]*?handleDisconnectStartFailure/);
}

function testVpnRefreshProcessRoutesExitAndStartFailure() {
  assert.match(source, /id:\s*refreshProcess[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?finishRefresh/);
  assert.match(source, /id:\s*refreshProcess[\s\S]*?onRunningChanged:[\s\S]*?handleRefreshStartFailure/);
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
  testVpnRefreshCompletionExecutesSuccessFailureAndPendingDrain,
  testVpnRefreshStartFailureExecutesWithoutExitedSignal,
  testVpnConnectCompletionUsesExitStatus,
  testVpnDisconnectCompletionUsesExitStatus,
  testVpnActionStartFailuresDoNotDoubleFinalize,
  testVpnActionProcessesRouteBufferedExitAndStartFailure,
  testVpnRefreshProcessRoutesExitAndStartFailure,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
