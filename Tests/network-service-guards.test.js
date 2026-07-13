#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const serviceSource = readQml("Services/Networking/NetworkService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(serviceSource, functionName);
  const args = argNames.join(", ");
  return new Function(
    "ctx",
    ...argNames,
    `with (ctx) { return (function(${args}) ${body}).call(ctx, ${args}); }`,
  );
}

function testNetworkServiceCacheAndWifiStateGuards() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const saveBody = extractFunctionBody(source, "saveCache");
  const syncBody = extractFunctionBody(source, "syncWifiState");
  const enabledBody = extractFunctionBody(source, "setWifiEnabled");
  const statusBody = extractFunctionBody(source, "refreshNetworkStatus");
  const startBody = extractFunctionBody(source, "beginActivePolling");
  const stopBody = extractFunctionBody(source, "endActivePolling");

  assert.match(saveBody, /saveDebounce\.restart\(\)/, "saveCache must debounce disk writes");
  assert.match(syncBody, /wifiStateProcess\.running = true/, "syncWifiState must query the live Wi-Fi radio state");
  assert.match(statusBody, /ethernetStateProcess\.running = true/, "refreshNetworkStatus must refresh Ethernet state on demand");
  assert.match(statusBody, /connectivityCheckProcess\.running = true/, "refreshNetworkStatus must refresh connectivity on demand");
  assert.match(startBody, /activePollingRefs\+\+/, "beginActivePolling must retain active UI users");
  assert.match(startBody, /refreshNetworkStatus\(\)/, "beginActivePolling must refresh status immediately");
  assert.match(startBody, /scan\(\)/, "beginActivePolling must scan when the Wi-Fi UI opens");
  assert.match(stopBody, /Math\.max\(0, activePollingRefs - 1\)/, "endActivePolling must release active UI users safely");
  assert.match(enabledBody, /Settings\.data\.network\.wifiEnabled = enabled/, "setWifiEnabled must update the setting first");
  assert.match(enabledBody, /wifiStateEnableProcess\.running = true/, "setWifiEnabled must run the nmcli radio command");
}

function testNetworkServiceIdlePollingGuards() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const completedBlock = source.match(/Component\.onCompleted:\s*\{([\s\S]*?)\n  \}/)[1];

  assert.match(source, /property int activePollingRefs: 0/, "NetworkService must track active polling consumers");
  assert.match(source, /readonly property bool activePolling: activePollingRefs > 0/, "NetworkService must expose active polling state");
  assert.match(source, /id: ethernetCheckTimer[\s\S]*running: root\.activePolling[\s\S]*if \(!ethernetStateProcess\.running\)/, "Ethernet timer must run only for active consumers and avoid overlapping nmcli runs");
  assert.match(source, /id: connectivityCheckTimer[\s\S]*running: root\.activePolling[\s\S]*if \(!connectivityCheckProcess\.running\)/, "Connectivity timer must run only for active consumers and avoid overlapping nmcli runs");
  assert.doesNotMatch(completedBlock, /scan\(\)/, "NetworkService startup must not perform a background Wi-Fi scan");
  assert.match(completedBlock, /refreshNetworkStatus\(\)/, "NetworkService startup must do a cheap status refresh instead of scanning");
  assert.match(source, /onTriggered:\s*\{\s*if \(root\.activePolling\) \{\s*scan\(\);\s*\}\s*\}/, "Delayed scan timer must not rescan while idle");
  assert.match(source, /Connectivity check error:[\s\S]*root\.applyConnectivityResult\("unknown"\)/, "Connectivity check errors must use the explicit unknown transition");
}

function testWiFiPanelControlsActivePolling() {
  const panelSource = readQml("Modules/Panels/WiFi/WiFiPanel.qml");
  const onOpenedBlock = panelSource.match(/onOpened:\s*\{([\s\S]*?)\n  \}/)[1];

  assert.match(onOpenedBlock, /NetworkService\.beginActivePolling\(\)/, "Wi-Fi panel opening must start active polling and scan through NetworkService");
  assert.match(panelSource, /onClosed:\s*\{[\s\S]*NetworkService\.endActivePolling\(\)/, "Wi-Fi panel closing must release active polling");
  assert.doesNotMatch(onOpenedBlock, /NetworkService\.scan\(\)/, "Wi-Fi panel must not bypass active polling on open");
}

function testNetworkServiceScanAndConnectionGuards() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const scanBody = extractFunctionBody(source, "scan");
  const connectBody = extractFunctionBody(source, "connect");
  const disconnectBody = extractFunctionBody(source, "disconnect");

  assert.match(scanBody, /if \(!Settings\.data\.network\.wifiEnabled\)\s+return;/, "scan must no-op while Wi-Fi is disabled");
  assert.match(scanBody, /if \(scanning\)[\s\S]*ignoreScanResults = true[\s\S]*scanPending = true[\s\S]*return;/, "scan must queue a rescan instead of racing active scans");
  assert.match(scanBody, /scanning = true[\s\S]*lastError = ""[\s\S]*ignoreScanResults = false/, "scan must reset scan state before launching");
  assert.match(scanBody, /profileCheckProcess\.running = true/, "scan must refresh known profiles before scanning networks");
  assert.match(connectBody, /if \(!ssid \|\| connecting \|\| connectProcess\.running\)\s+return;/, "connect must reject empty and overlapping connection requests");
  assert.match(connectBody, /connecting = true[\s\S]*connectingTo = ssid[\s\S]*lastError = ""/, "connect must set busy state and clear stale errors");
  assert.match(connectBody, /\(networks\[ssid\] && networks\[ssid\]\.existing\) \|\| cachedNetworks\[ssid\]/, "connect must reuse existing or cached profiles");
  assert.match(connectBody, /connectProcess\.mode = "saved"[\s\S]*connectProcess\.password = ""/, "connect must avoid passwords for saved profiles");
  assert.match(connectBody, /connectProcess\.mode = "new"[\s\S]*connectProcess\.password = password/, "connect must pass passwords for new profiles");
  assert.match(connectBody, /connectProcess\.running = true/, "connect must launch the connection process");
  assert.match(disconnectBody, /if \(!ssid \|\| disconnectingFrom \|\| disconnectProcess\.running\)\s+return;/, "disconnect must reject empty and overlapping requests");
  assert.match(disconnectBody, /disconnectingFrom = ssid[\s\S]*disconnectProcess\.ssid = ssid[\s\S]*disconnectProcess\.running = true/, "disconnect must track and launch the target disconnect");
}

function testNetworkServiceForgetAndStatusGuards() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const forgetBody = extractFunctionBody(source, "forget");
  const statusBody = extractFunctionBody(source, "updateNetworkStatus");
  const deviceBody = extractFunctionBody(source, "applyDeviceStateOutput");

  assert.match(forgetBody, /forgettingNetwork = ssid/, "forget must expose the busy SSID");
  assert.doesNotMatch(forgetBody, /delete known\[ssid\]/, "forget must not mutate cache before process success");
  assert.match(forgetBody, /forgetProcess\.ssid = ssid[\s\S]*forgetProcess\.running = true/, "forget must launch the system profile delete process");
  assert.match(statusBody, /for \(let key in nets\)[\s\S]*nets\[key\]\.connected = false/, "updateNetworkStatus must disconnect other active networks");
  assert.match(statusBody, /if \(nets\[ssid\]\)[\s\S]*nets\[ssid\]\.connected = connected[\s\S]*nets\[ssid\]\.existing = true[\s\S]*nets\[ssid\]\.cached = true/, "updateNetworkStatus must mark existing targets as known");
  assert.match(statusBody, /else if \(connected\)[\s\S]*"ssid": ssid[\s\S]*"security": "--"[\s\S]*"signal": 100[\s\S]*"connected": true/, "updateNetworkStatus must synthesize connected entries missing from the scan list");
  assert.match(statusBody, /networks = \(\{\}\)[\s\S]*networks = nets/, "updateNetworkStatus must force a property-change notification");
  assert.match(source, /command: \["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"\]/, "passive device status must request connection names");
  assert.match(deviceBody, /parts\[1\] === "wifi" && parts\[2\] === "connected"/, "passive device status must detect connected Wi-Fi devices");
  assert.match(deviceBody, /updateNetworkStatus\(wifiConnection, true\)/, "passive device status must synthesize connected Wi-Fi networks for bar icons");
  assert.match(deviceBody, /else \{[\s\S]*nets\[key\]\.connected = false[\s\S]*networks = nets/, "passive device status must clear stale connected Wi-Fi when no Wi-Fi device is connected");
}

function testNetworkServiceIconAndSecurityHelpers() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const iconBody = extractFunctionBody(source, "signalIcon");
  const securedBody = extractFunctionBody(source, "isSecured");

  assert.match(iconBody, /if \(isConnected && root\.networkConnectivity !== "unknown" && !root\.internetConnectivity\)\s+return "world-off"/, "signalIcon must show disconnected-world only for known captive or offline networks");
  assert.match(iconBody, /if \(signal >= 80\)\s+return "wifi"/, "signalIcon must map strong signal");
  assert.match(iconBody, /if \(signal >= 50\)\s+return "wifi-2"/, "signalIcon must map medium signal");
  assert.match(iconBody, /if \(signal >= 20\)\s+return "wifi-1"/, "signalIcon must map weak signal");
  assert.match(iconBody, /return "wifi-0"/, "signalIcon must map missing or very weak signal");
  assert.match(securedBody, /return security && security !== "--" && security\.trim\(\) !== ""/, "isSecured must reject missing, placeholder, and blank security values");
}

function testNetworkServiceParsesNmcliScanOutput() {
  const parseNetworkScanOutput = qmlFunction("parseNetworkScanOutput", "text", "existingProfiles", "knownNetworks", "lastConnected");
  const warnings = [];
  const ctx = {
    Logger: {
      w(...args) {
        warnings.push(args);
      },
    },
  };
  const parsed = parseNetworkScanOutput(ctx, [
    "Cafe:Guest:WPA2:55:",
    "Home:Network:WPA2:70:*",
    "Home:Network:WPA2:85:",
    "OpenNet::10:",
    "malformed",
  ].join("\n"), {
    "Home:Network": true,
  }, {
    "Cafe:Guest": true,
  }, "OldNet");

  assert.match(serviceSource, /function parseNetworkScanOutput\(text, existingProfiles, knownNetworks, lastConnected\)/, "parseNetworkScanOutput must type raw text and last-connected inputs");
  assert.deepEqual(parsed.networks, {
    "Cafe:Guest": {
      ssid: "Cafe:Guest",
      security: "WPA2",
      signal: 55,
      connected: false,
      existing: false,
      cached: true,
    },
    "Home:Network": {
      ssid: "Home:Network",
      security: "WPA2",
      signal: 85,
      connected: true,
      existing: true,
      cached: false,
    },
    OpenNet: {
      ssid: "OpenNet",
      security: "--",
      signal: 10,
      connected: false,
      existing: false,
      cached: false,
    },
  });
  assert.equal(parsed.lastConnected, "Home:Network");
  assert.equal(parsed.shouldSaveCache, true);
  assert.equal(warnings.length, 1);
}

function testNetworkServiceStateCommandsExecute() {
  const saveCache = qmlFunction("saveCache");
  const syncWifiState = qmlFunction("syncWifiState");
  const setWifiEnabled = qmlFunction("setWifiEnabled", "enabled");
  const scan = qmlFunction("scan");
  const restarts = [];
  const debugLogs = [];
  const ctx = {
    Settings: { data: { network: { wifiEnabled: true } } },
    saveDebounce: { restart() { restarts.push("save"); } },
    wifiStateProcess: { running: false },
    wifiStateEnableProcess: { running: false },
    profileCheckProcess: { running: false },
    scanning: false,
    ignoreScanResults: false,
    scanPending: false,
    lastError: "stale",
    Logger: { d(...args) { debugLogs.push(args); } },
  };

  saveCache(ctx);
  syncWifiState(ctx);
  setWifiEnabled(ctx, false);
  scan(ctx);
  assert.deepEqual(restarts, ["save"], "saveCache must debounce cache writes");
  assert.equal(ctx.wifiStateProcess.running, true, "syncWifiState must query Wi-Fi state");
  assert.equal(ctx.Settings.data.network.wifiEnabled, false, "setWifiEnabled must update the setting");
  assert.equal(ctx.wifiStateEnableProcess.running, true, "setWifiEnabled must start the nmcli radio process");
  assert.equal(ctx.profileCheckProcess.running, false, "scan must no-op while Wi-Fi disabled");

  ctx.Settings.data.network.wifiEnabled = true;
  scan(ctx);
  assert.equal(ctx.scanning, true, "scan must enter scanning state");
  assert.equal(ctx.lastError, "", "scan must clear stale errors");
  assert.equal(ctx.ignoreScanResults, false, "scan must accept fresh results for a new scan");
  assert.equal(ctx.profileCheckProcess.running, true, "scan must refresh known profiles before scanning");

  scan(ctx);
  assert.equal(ctx.ignoreScanResults, true, "scan must ignore in-flight results when rescanning");
  assert.equal(ctx.scanPending, true, "scan must queue a pending rescan");
  assert.equal(debugLogs.length > 0, true, "scan must log queued rescans");
}

function testNetworkServiceConnectionStatusAndIconsExecute() {
  const connect = qmlFunction("connect", "ssid", "password");
  const disconnect = qmlFunction("disconnect", "ssid");
  const forget = qmlFunction("forget", "ssid");
  const updateNetworkStatus = qmlFunction("updateNetworkStatus", "ssid", "connected");
  const applyDeviceStateOutput = qmlFunction("applyDeviceStateOutput", "text");
  const signalIcon = qmlFunction("signalIcon", "signal", "isConnected");
  const isSecured = qmlFunction("isSecured", "security");
  const saveCalls = [];
  const ctx = {
    root: null,
    networks: {
      Home: { existing: true, connected: true },
      Cafe: { existing: false, connected: false },
    },
    cachedNetworks: { Office: true },
    connecting: false,
    connectingTo: "",
    disconnectingFrom: "",
    forgettingNetwork: "",
    lastError: "old",
    internetConnectivity: false,
    networkConnectivity: "unknown",
    ethernetConnected: true,
    cacheAdapter: {
      knownNetworks: { Home: true, Office: true },
      lastConnected: "Home",
    },
    connectProcess: { generation: 0, running: false },
    disconnectProcess: { generation: 0, running: false },
    forgetProcess: {},
    saveCache() {
      saveCalls.push({ ...this.cacheAdapter.knownNetworks, lastConnected: this.cacheAdapter.lastConnected });
    },
    Logger: { d() {} },
  };
  ctx.root = ctx;
  ctx.updateNetworkStatus = (ssid, connected) => updateNetworkStatus(ctx, ssid, connected);

  connect(ctx, "Office", "secret");
  assert.equal(ctx.connecting, true, "connect must set busy state");
  assert.equal(ctx.connectingTo, "Office", "connect must track target SSID");
  assert.equal(ctx.lastError, "", "connect must clear stale errors");
  assert.equal(ctx.connectProcess.mode, "saved", "connect must reuse cached profiles");
  assert.equal(ctx.connectProcess.password, "", "saved profiles must not retain typed passwords");
  assert.equal(ctx.connectProcess.running, true, "connect must start the connect process");

  const savedCommand = { ...ctx.connectProcess };
  connect(ctx, "Cafe", "guest");
  assert.deepEqual(ctx.connectProcess, savedCommand, "connect must ignore duplicate connection requests while busy");

  ctx.connecting = false;
  ctx.connectProcess.running = false;
  connect(ctx, "Cafe", "guest");
  assert.equal(ctx.connectProcess.mode, "new", "connect must create new profiles when no cache exists");
  assert.equal(ctx.connectProcess.password, "guest", "new profiles must keep supplied passwords");

  disconnect(ctx, "Home");
  assert.equal(ctx.disconnectingFrom, "Home", "disconnect must track target SSID");
  assert.equal(ctx.disconnectProcess.ssid, "Home", "disconnect must pass SSID to process");
  assert.equal(ctx.disconnectProcess.running, true, "disconnect must start the disconnect process");

  forget(ctx, "Home");
  assert.equal(ctx.forgettingNetwork, "Home", "forget must track target SSID");
  assert.equal(ctx.cacheAdapter.knownNetworks.Home, true, "forget must preserve cache until process success");
  assert.equal(ctx.cacheAdapter.knownNetworks.Office, true, "forget must preserve other cached networks");
  assert.equal(ctx.cacheAdapter.lastConnected, "Home", "forget must preserve lastConnected until process success");
  assert.deepEqual(saveCalls, [], "forget must not persist cache changes before process success");
  assert.equal(ctx.forgetProcess.ssid, "Home", "forget must pass SSID to the forget process");
  assert.equal(ctx.forgetProcess.running, true, "forget must start the forget process");

  updateNetworkStatus(ctx, "Cafe", true);
  assert.equal(ctx.networks.Home.connected, false, "updateNetworkStatus must clear other connected networks");
  assert.equal(ctx.networks.Cafe.connected, true, "updateNetworkStatus must mark target connected");
  assert.equal(ctx.networks.Cafe.existing, true, "connected targets must become known profiles");
  assert.equal(ctx.networks.Cafe.cached, true, "connected targets must become cached");

  updateNetworkStatus(ctx, "NewNet", true);
  assert.equal(ctx.networks.NewNet.signal, 100, "missing connected networks must be synthesized");

  applyDeviceStateOutput(ctx, "wlan0:wifi:connected:ossonet\nenp1s0:ethernet:unavailable:\n");
  assert.equal(ctx.ethernetConnected, false, "passive device state must update Ethernet state");
  assert.equal(ctx.networks.ossonet.connected, true, "passive device state must synthesize connected Wi-Fi by connection name");
  assert.equal(ctx.networks.ossonet.signal, 100, "synthesized passive Wi-Fi entries must have usable signal for icons");
  applyDeviceStateOutput(ctx, "wlan0:wifi:disconnected:\nenp1s0:ethernet:unavailable:\n");
  assert.equal(ctx.networks.ossonet.connected, false, "passive disconnected Wi-Fi state must clear stale connected networks");
  updateNetworkStatus(ctx, "MissingDisconnected", false);
  assert.equal(ctx.networks.MissingDisconnected, undefined, "disconnected missing networks must not be synthesized");
  assert.equal(signalIcon(ctx, 90, true), "wifi", "unknown connectivity must default to connected Wi-Fi icon");
  ctx.networkConnectivity = "limited";
  assert.equal(signalIcon(ctx, 90, true), "world-off", "known offline networks must show world-off");
  ctx.internetConnectivity = true;
  assert.equal(signalIcon(ctx, 90, false), "wifi", "strong signal must use wifi icon");
  assert.equal(signalIcon(ctx, 55, false), "wifi-2", "medium signal must use wifi-2 icon");
  assert.equal(signalIcon(ctx, 25, false), "wifi-1", "weak signal must use wifi-1 icon");
  assert.equal(signalIcon(ctx, 5, false), "wifi-0", "very weak signal must use wifi-0 icon");
  assert.equal(isSecured(ctx, "WPA2"), true, "non-placeholder security must be secured");
  assert.equal(isSecured(ctx, "--"), false, "placeholder security must be unsecured");
  assert.equal(isSecured(ctx, "  "), false, "blank security must be unsecured");
}

function testNetworkScanFailureClearsStateAndSchedulesCorrectRetry() {
  const finishScanFailure = qmlFunction("finishScanFailure", "message");
  const createContext = overrides => {
    const ctx = {
      scanning: true,
      scanPending: false,
      activePolling: false,
      lastError: "",
      delayedScanTimer: {
        interval: 0,
        restarts: 0,
        restart() {
          this.restarts += 1;
        },
      },
      ...overrides,
    };
    ctx.root = ctx;
    return ctx;
  };

  const pending = createContext({ scanPending: true });
  finishScanFailure(pending, "nmcli failed");
  assert.equal(pending.scanning, false);
  assert.equal(pending.lastError, "nmcli failed");
  assert.equal(pending.scanPending, false);
  assert.equal(pending.delayedScanTimer.interval, 100);
  assert.equal(pending.delayedScanTimer.restarts, 1);

  const active = createContext({ activePolling: true });
  finishScanFailure(active, "nmcli missing");
  assert.equal(active.delayedScanTimer.interval, 5000);
  assert.equal(active.delayedScanTimer.restarts, 1);

  const idle = createContext({ activePolling: false });
  finishScanFailure(idle, "nmcli missing");
  assert.equal(idle.delayedScanTimer.restarts, 0);
}

function testNetworkProfileAndScanExitFailuresExecute() {
  const finishScanFailure = qmlFunction("finishScanFailure", "message");
  const finishProfileCheck = qmlFunction("finishProfileCheck", "exitCode", "output", "errorOutput");
  const finishNetworkScan = qmlFunction("finishNetworkScan", "exitCode", "output", "errorOutput");
  const createContext = () => {
    const ctx = {
      scanning: true,
      scanPending: false,
      activePolling: false,
      ignoreScanResults: false,
      lastError: "",
      delayedScanTimer: { interval: 0, restart() {} },
      scanProcess: { existingProfiles: {}, running: false },
    };
    ctx.root = ctx;
    ctx.finishScanFailure = message => finishScanFailure(ctx, message);
    ctx.root.finishScanFailure = ctx.finishScanFailure;
    return ctx;
  };

  const profileFailure = createContext();
  finishProfileCheck(profileFailure, 127, "", "nmcli missing");
  assert.equal(profileFailure.scanning, false);
  assert.equal(profileFailure.lastError, "nmcli missing");
  assert.equal(profileFailure.scanProcess.running, false);

  const scanFailure = createContext();
  finishNetworkScan(scanFailure, 10, "partial", "scan denied");
  assert.equal(scanFailure.scanning, false);
  assert.equal(scanFailure.lastError, "scan denied");

  const superseded = createContext();
  superseded.ignoreScanResults = true;
  superseded.scanPending = true;
  superseded.lastError = "connection failed";
  superseded.finishSupersededScan = () => qmlFunction("finishSupersededScan")(superseded);
  superseded.root.finishSupersededScan = superseded.finishSupersededScan;
  finishNetworkScan(superseded, 10, "", "obsolete error");
  assert.equal(superseded.lastError, "connection failed");
  assert.equal(superseded.scanPending, false);
}

function testNetworkProfileAndScanSuccessParityExecutes() {
  const finishScanFailure = qmlFunction("finishScanFailure", "message");
  const finishProfileCheck = qmlFunction("finishProfileCheck", "exitCode", "output", "errorOutput");
  const finishNetworkScan = qmlFunction("finishNetworkScan", "exitCode", "output", "errorOutput");
  const ctx = {
    scanning: true,
    scanPending: false,
    activePolling: false,
    ignoreScanResults: false,
    networks: {},
    lastError: "",
    delayedScanTimer: { restart() {} },
    scanProcess: { existingProfiles: {}, exitObserved: true, running: false },
    cacheAdapter: { knownNetworks: {}, lastConnected: "" },
    Logger: { d() {} },
    saveCache() {},
    parseNetworkScanOutput() {
      return {
        networks: { Home: { ssid: "Home", signal: 80 } },
        shouldSaveCache: false,
        lastConnected: "",
      };
    },
    logNetworkChanges() {},
  };
  ctx.root = ctx;
  ctx.finishScanFailure = message => finishScanFailure(ctx, message);
  ctx.root.finishScanFailure = ctx.finishScanFailure;
  ctx.root.finishSupersededScan = () => qmlFunction("finishSupersededScan")(ctx);

  finishProfileCheck(ctx, 0, "Home\nOffice\n", "");
  assert.deepEqual(ctx.scanProcess.existingProfiles, { Home: true, Office: true });
  assert.equal(ctx.scanProcess.running, true);

  finishNetworkScan(ctx, 0, "scan output", "");
  assert.deepEqual(ctx.networks, { Home: { ssid: "Home", signal: 80 } });
  assert.equal(ctx.scanning, false);
  assert.equal(ctx.lastError, "");
}

function testNetworkScanStartFailureExecutesWithoutExitedSignal() {
  const handleScanStartFailure = qmlFunction("handleScanStartFailure", "processName", "exitObserved");
  const finishScanFailure = qmlFunction("finishScanFailure", "message");
  const ctx = {
    scanning: true,
    scanPending: false,
    activePolling: false,
    lastError: "",
    delayedScanTimer: { restart() {} },
  };
  ctx.root = ctx;
  ctx.finishScanFailure = message => finishScanFailure(ctx, message);

  handleScanStartFailure(ctx, "profile check", false);
  assert.equal(ctx.scanning, false);
  assert.match(ctx.lastError, /profile check failed to start/);

  ctx.scanning = true;
  ctx.lastError = "";
  handleScanStartFailure(ctx, "profile check", true);
  assert.equal(ctx.scanning, true, "normal exited path must not finalize again from runningChanged");
  assert.equal(ctx.lastError, "");
}

function createConnectionActionContext() {
  const updates = [];
  const notices = [];
  const scans = [];
  const ctx = {
    connecting: true,
    connectingTo: "Home",
    disconnectingFrom: "Home",
    lastError: "",
    activePolling: true,
    cacheAdapter: { knownNetworks: {}, lastConnected: "" },
    connectProcess: { generation: 1, password: "secret" },
    disconnectProcess: { generation: 1 },
    delayedScanTimer: { interval: 0, restart() { scans.push(this.interval); } },
    Logger: { i() {}, w() {} },
    I18n: { tr(key) { return key; } },
    ToastService: { showNotice(...args) { notices.push(args); } },
    saveCache() {},
    updateNetworkStatus(ssid, connected) { updates.push([ssid, connected]); },
    refreshNetworkStatus() {},
  };
  ctx.root = ctx;
  ctx.updates = updates;
  ctx.notices = notices;
  ctx.scans = scans;
  return ctx;
}

function testNetworkConnectCompletionUsesExitStatusAndIdentity() {
  const finishConnect = qmlFunction("finishConnect", "ssid", "generation", "exitCode", "output", "errorOutput");
  const success = createConnectionActionContext();
  finishConnect(success, "Home", 1, 0, "localized output", "");
  assert.equal(success.connecting, false);
  assert.equal(success.connectingTo, "");
  assert.equal(success.connectProcess.password, "");
  assert.deepEqual(success.updates, [["Home", true]]);
  assert.equal(success.cacheAdapter.lastConnected, "Home");
  assert.equal(success.notices.length, 1);
  assert.deepEqual(success.scans, [5000]);

  const failure = createConnectionActionContext();
  finishConnect(failure, "Home", 1, 10, "", "permission denied\nmore");
  assert.equal(failure.connecting, false);
  assert.equal(failure.connectProcess.password, "");
  assert.equal(failure.lastError, "permission denied");
  assert.deepEqual(failure.updates, []);
  assert.deepEqual(failure.scans, []);

  const stale = createConnectionActionContext();
  stale.connectProcess.generation = 2;
  stale.connectingTo = "Office";
  finishConnect(stale, "Home", 1, 0, "", "");
  assert.equal(stale.connecting, true);
  assert.equal(stale.connectingTo, "Office");
  assert.deepEqual(stale.updates, []);
}

function testNetworkDisconnectCompletionUsesExitStatusAndIdentity() {
  const finishDisconnect = qmlFunction("finishDisconnect", "ssid", "generation", "exitCode", "output", "errorOutput");
  const success = createConnectionActionContext();
  finishDisconnect(success, "Home", 1, 0, "", "");
  assert.equal(success.disconnectingFrom, "");
  assert.deepEqual(success.updates, [["Home", false]]);
  assert.equal(success.notices.length, 1);
  assert.deepEqual(success.scans, [1000]);

  const failure = createConnectionActionContext();
  finishDisconnect(failure, "Home", 1, 10, "stdout diagnostic", "");
  assert.equal(failure.disconnectingFrom, "");
  assert.equal(failure.lastError, "stdout diagnostic");
  assert.deepEqual(failure.updates, []);
  assert.deepEqual(failure.scans, []);

  const stale = createConnectionActionContext();
  stale.disconnectProcess.generation = 2;
  stale.disconnectingFrom = "Office";
  finishDisconnect(stale, "Home", 1, 0, "", "");
  assert.equal(stale.disconnectingFrom, "Office");
  assert.deepEqual(stale.updates, []);
}

function testNetworkActionStartFailureAndProcessRouting() {
  const finishConnect = qmlFunction("finishConnect", "ssid", "generation", "exitCode", "output", "errorOutput");
  const finishDisconnect = qmlFunction("finishDisconnect", "ssid", "generation", "exitCode", "output", "errorOutput");
  const handleConnectStartFailure = qmlFunction("handleConnectStartFailure", "ssid", "generation", "exitObserved");
  const handleDisconnectStartFailure = qmlFunction("handleDisconnectStartFailure", "ssid", "generation", "exitObserved");
  const connect = createConnectionActionContext();
  connect.finishConnect = (...args) => finishConnect(connect, ...args);
  handleConnectStartFailure(connect, "Home", 1, false);
  assert.match(connect.lastError, /failed to start/);
  assert.equal(connect.connectProcess.password, "");

  const disconnect = createConnectionActionContext();
  disconnect.finishDisconnect = (...args) => finishDisconnect(disconnect, ...args);
  handleDisconnectStartFailure(disconnect, "Home", 1, false);
  assert.match(disconnect.lastError, /failed to start/);

  const source = readQml("Services/Networking/NetworkService.qml");
  assert.match(source, /id:\s*connectProcess[\s\S]*?onExited:[\s\S]*?finishConnect[\s\S]*?onRunningChanged:[\s\S]*?handleConnectStartFailure/);
  assert.match(source, /id:\s*disconnectProcess[\s\S]*?onExited:[\s\S]*?finishDisconnect[\s\S]*?onRunningChanged:[\s\S]*?handleDisconnectStartFailure/);
}

function testPassiveStatusCompletionUsesExitAuthority() {
  const finishEthernetState = qmlFunction("finishEthernetState", "exitCode", "output", "errorOutput");
  const finishWifiState = qmlFunction("finishWifiState", "exitCode", "output", "errorOutput");
  const ethernetOutputs = [];
  const ctx = {
    ethernetConnected: true,
    Settings: { data: { network: { wifiEnabled: true } } },
    Logger: { d() {}, w() {} },
    applyDeviceStateOutput(text) { ethernetOutputs.push(text); },
  };
  ctx.root = ctx;

  finishEthernetState(ctx, 10, "", "nmcli failed");
  assert.deepEqual(ethernetOutputs, [], "failed Ethernet status must preserve prior state");
  assert.equal(ctx.ethernetConnected, true);
  finishEthernetState(ctx, 0, "eth0:ethernet:connected:Wired", "");
  assert.deepEqual(ethernetOutputs, ["eth0:ethernet:connected:Wired"]);

  finishWifiState(ctx, 10, "", "nmcli failed");
  assert.equal(ctx.Settings.data.network.wifiEnabled, true, "failed Wi-Fi status must preserve the setting");
  finishWifiState(ctx, 0, "disabled\n", "");
  assert.equal(ctx.Settings.data.network.wifiEnabled, false);
}

function testPassiveStatusProcessesRouteExitAndStartFailure() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const finishEthernetState = qmlFunction("finishEthernetState", "exitCode", "output", "errorOutput");
  const finishWifiState = qmlFunction("finishWifiState", "exitCode", "output", "errorOutput");
  const handleEthernetStateStartFailure = qmlFunction("handleEthernetStateStartFailure", "exitObserved");
  const handleWifiStateStartFailure = qmlFunction("handleWifiStateStartFailure", "exitObserved");
  const ctx = {
    Settings: { data: { network: { wifiEnabled: true } } },
    Logger: { d() {}, w() {} },
    applyDeviceStateOutput() { throw new Error("failed start must not mutate Ethernet state"); },
  };
  ctx.root = ctx;
  ctx.finishEthernetState = (...args) => finishEthernetState(ctx, ...args);
  ctx.finishWifiState = (...args) => finishWifiState(ctx, ...args);

  handleEthernetStateStartFailure(ctx, false);
  handleWifiStateStartFailure(ctx, false);
  assert.equal(ctx.Settings.data.network.wifiEnabled, true);
  handleEthernetStateStartFailure(ctx, true);
  handleWifiStateStartFailure(ctx, true);
  assert.match(source, /id:\s*ethernetStateProcess[\s\S]*?onExited:[\s\S]*?finishEthernetState[\s\S]*?onRunningChanged:[\s\S]*?handleEthernetStateStartFailure/);
  assert.match(source, /id:\s*wifiStateProcess[\s\S]*?onExited:[\s\S]*?finishWifiState[\s\S]*?onRunningChanged:[\s\S]*?handleWifiStateStartFailure/);
}

function createConnectivityContext() {
  const scans = [];
  const warnings = [];
  const ctx = {
    networkConnectivity: "full",
    internetConnectivity: true,
    activePolling: true,
    cachedLastConnected: "Home",
    connectivityCheckProcess: { failedChecks: 0, generation: 0 },
    pingCheckProcess: { running: false, generation: 0 },
    Logger: { i() {} },
    I18n: { tr(key) { return key; } },
    ToastService: { showWarning(...args) { warnings.push(args); } },
    scan() { scans.push(true); },
  };
  ctx.root = ctx;
  ctx.scans = scans;
  ctx.warnings = warnings;
  return ctx;
}

function testConnectivityTransitionsRejectStalePingResults() {
  const applyConnectivityResult = qmlFunction("applyConnectivityResult", "result");
  const finishPingCheck = qmlFunction("finishPingCheck", "generation", "exitCode");
  const ctx = createConnectivityContext();

  applyConnectivityResult(ctx, "none");
  assert.equal(ctx.networkConnectivity, "none");
  assert.equal(ctx.internetConnectivity, false);

  applyConnectivityResult(ctx, "full");
  assert.equal(ctx.networkConnectivity, "full");
  assert.equal(ctx.internetConnectivity, true);

  applyConnectivityResult(ctx, "limited");
  applyConnectivityResult(ctx, "limited");
  applyConnectivityResult(ctx, "limited");
  assert.equal(ctx.networkConnectivity, "limited");
  assert.equal(ctx.internetConnectivity, false);
  assert.equal(ctx.pingCheckProcess.running, true);
  const staleGeneration = ctx.pingCheckProcess.generation;
  applyConnectivityResult(ctx, "limited");
  assert.equal(ctx.connectivityCheckProcess.generation, staleGeneration, "equivalent degraded polls must not invalidate the active fallback");

  ctx.pingCheckProcess.running = false;
  applyConnectivityResult(ctx, "full");
  finishPingCheck(ctx, staleGeneration, 0);
  assert.equal(ctx.networkConnectivity, "full");
  assert.equal(ctx.internetConnectivity, true, "late ping success must not overwrite a newer full result");
}

function testConnectivityFallbackAvoidsOverlapAndHandlesFailure() {
  const applyConnectivityResult = qmlFunction("applyConnectivityResult", "result");
  const finishPingCheck = qmlFunction("finishPingCheck", "generation", "exitCode");
  const handlePingStartFailure = qmlFunction("handlePingStartFailure", "generation", "exitObserved");
  const ctx = createConnectivityContext();
  ctx.pingCheckProcess.running = true;

  applyConnectivityResult(ctx, "portal");
  applyConnectivityResult(ctx, "portal");
  applyConnectivityResult(ctx, "portal");
  assert.equal(ctx.pingCheckProcess.generation, 0, "active ping must not be replaced by an overlapping fallback");

  ctx.pingCheckProcess.running = false;
  applyConnectivityResult(ctx, "portal");
  const generation = ctx.pingCheckProcess.generation;
  finishPingCheck(ctx, generation, 1);
  assert.equal(ctx.internetConnectivity, false);
  assert.equal(ctx.connectivityCheckProcess.failedChecks, 0);
  assert.equal(ctx.warnings.length, 1);
  assert.equal(ctx.scans.length, 1);

  const failedStart = createConnectivityContext();
  failedStart.finishPingCheck = (...args) => finishPingCheck(failedStart, ...args);
  failedStart.connectivityCheckProcess.generation = 4;
  handlePingStartFailure(failedStart, 4, false);
  assert.equal(failedStart.internetConnectivity, false);
  assert.equal(failedStart.warnings.length, 1);

  const exited = createConnectivityContext();
  exited.finishPingCheck = (...args) => finishPingCheck(exited, ...args);
  exited.connectivityCheckProcess.generation = 4;
  handlePingStartFailure(exited, 4, true);
  assert.equal(exited.warnings.length, 0, "normal exit must not be finalized twice");
}

function createForgetContext() {
  const saves = [];
  const restarts = [];
  const ctx = {
    forgettingNetwork: "Home",
    lastError: "",
    activePolling: true,
    cacheAdapter: {
      knownNetworks: { Home: { password: "secret" }, Office: {} },
      lastConnected: "Home",
    },
    networks: { Home: { cached: true, existing: true }, Office: { cached: true } },
    delayedScanTimer: {
      interval: 0,
      restart() { restarts.push(this.interval); },
    },
    saveCache() { saves.push("save"); },
    Logger: { i() {}, d() {}, w() {} },
  };
  ctx.root = ctx;
  ctx.saves = saves;
  ctx.restarts = restarts;
  return ctx;
}

function testNetworkForgetMutatesCacheOnlyAfterSuccessfulExit() {
  const forget = qmlFunction("forget", "ssid");
  const finishForget = qmlFunction("finishForget", "ssid", "exitCode", "output", "errorOutput");
  const ctx = createForgetContext();
  ctx.forgettingNetwork = "";
  ctx.forgetProcess = { ssid: "", output: "stale", errorOutput: "stale", exitObserved: true, running: false };

  forget(ctx, "Home");
  assert.deepEqual(ctx.cacheAdapter.knownNetworks, { Home: { password: "secret" }, Office: {} });
  assert.equal(ctx.cacheAdapter.lastConnected, "Home");
  assert.deepEqual(ctx.saves, []);

  finishForget(ctx, "Home", 0, "Deleted profile", "");
  assert.deepEqual(ctx.cacheAdapter.knownNetworks, { Office: {} });
  assert.equal(ctx.cacheAdapter.lastConnected, "");
  assert.equal(ctx.networks.Home.cached, false);
  assert.equal(ctx.networks.Home.existing, false);
  assert.deepEqual(ctx.saves, ["save"]);
  assert.equal(ctx.forgettingNetwork, "");
  assert.deepEqual(ctx.restarts, [5000]);
}

function testNetworkForgetFailurePreservesStateAndIdentity() {
  const finishForget = qmlFunction("finishForget", "ssid", "exitCode", "output", "errorOutput");
  const failure = createForgetContext();
  finishForget(failure, "Home", 10, "", "permission denied\nmore");
  assert.deepEqual(failure.cacheAdapter.knownNetworks, { Home: { password: "secret" }, Office: {} });
  assert.equal(failure.cacheAdapter.lastConnected, "Home");
  assert.equal(failure.networks.Home.cached, true);
  assert.equal(failure.lastError, "permission denied");
  assert.equal(failure.forgettingNetwork, "");
  assert.deepEqual(failure.restarts, [], "failure must not schedule a scan that clears its diagnostic");

  const stale = createForgetContext();
  stale.forgettingNetwork = "Office";
  finishForget(stale, "Home", 0, "Deleted", "");
  assert.deepEqual(stale.cacheAdapter.knownNetworks, { Home: { password: "secret" }, Office: {} });
  assert.equal(stale.forgettingNetwork, "Office");
}

function testNetworkForgetStartFailureAndProcessRouting() {
  const finishForget = qmlFunction("finishForget", "ssid", "exitCode", "output", "errorOutput");
  const handleForgetStartFailure = qmlFunction("handleForgetStartFailure", "ssid", "exitObserved");
  const ctx = createForgetContext();
  ctx.finishForget = (...args) => finishForget(ctx, ...args);
  handleForgetStartFailure(ctx, "Home", false);
  assert.match(ctx.lastError, /failed to start/);
  assert.equal(ctx.forgettingNetwork, "");

  const normal = createForgetContext();
  normal.finishForget = (...args) => finishForget(normal, ...args);
  handleForgetStartFailure(normal, "Home", true);
  assert.equal(normal.forgettingNetwork, "Home");
  assert.equal(normal.lastError, "");

  const source = readQml("Services/Networking/NetworkService.qml");
  assert.match(source, /id:\s*forgetProcess[\s\S]*?property string output[\s\S]*?property string errorOutput[\s\S]*?property bool exitObserved/);
  assert.match(source, /id:\s*forgetProcess[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?exitObserved = true[\s\S]*?finishForget/);
  assert.match(source, /id:\s*forgetProcess[\s\S]*?onRunningChanged:[\s\S]*?handleForgetStartFailure/);
}

function testNetworkScanProcessesRouteExitAndStartFailure() {
  const source = readQml("Services/Networking/NetworkService.qml");
  assert.match(source, /id:\s*profileCheckProcess[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?finishProfileCheck/);
  assert.match(source, /id:\s*profileCheckProcess[\s\S]*?onRunningChanged:[\s\S]*?handleScanStartFailure/);
  assert.match(source, /id:\s*scanProcess[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?finishNetworkScan/);
  assert.match(source, /id:\s*scanProcess[\s\S]*?onRunningChanged:[\s\S]*?handleScanStartFailure/);
  extractFunctionBody(source, "finishProfileCheck");
  extractFunctionBody(source, "finishNetworkScan");
  extractFunctionBody(source, "logNetworkChanges");
}

const tests = [
  testNetworkServiceCacheAndWifiStateGuards,
  testNetworkServiceIdlePollingGuards,
  testWiFiPanelControlsActivePolling,
  testNetworkServiceScanAndConnectionGuards,
  testNetworkServiceForgetAndStatusGuards,
  testNetworkServiceIconAndSecurityHelpers,
  testNetworkServiceParsesNmcliScanOutput,
  testNetworkServiceStateCommandsExecute,
  testNetworkServiceConnectionStatusAndIconsExecute,
  testNetworkScanFailureClearsStateAndSchedulesCorrectRetry,
  testNetworkProfileAndScanExitFailuresExecute,
  testNetworkProfileAndScanSuccessParityExecutes,
  testNetworkScanStartFailureExecutesWithoutExitedSignal,
  testNetworkConnectCompletionUsesExitStatusAndIdentity,
  testNetworkDisconnectCompletionUsesExitStatusAndIdentity,
  testNetworkActionStartFailureAndProcessRouting,
  testPassiveStatusCompletionUsesExitAuthority,
  testPassiveStatusProcessesRouteExitAndStartFailure,
  testConnectivityTransitionsRejectStalePingResults,
  testConnectivityFallbackAvoidsOverlapAndHandlesFailure,
  testNetworkForgetMutatesCacheOnlyAfterSuccessfulExit,
  testNetworkForgetFailurePreservesStateAndIdentity,
  testNetworkForgetStartFailureAndProcessRouting,
  testNetworkScanProcessesRouteExitAndStartFailure,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
