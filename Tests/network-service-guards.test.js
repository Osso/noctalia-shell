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

  assert.match(saveBody, /saveDebounce\.restart\(\)/, "saveCache must debounce disk writes");
  assert.match(syncBody, /wifiStateProcess\.running = true/, "syncWifiState must query the live Wi-Fi radio state");
  assert.match(enabledBody, /Settings\.data\.network\.wifiEnabled = enabled/, "setWifiEnabled must update the setting first");
  assert.match(enabledBody, /wifiStateEnableProcess\.running = true/, "setWifiEnabled must run the nmcli radio command");
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
  assert.match(connectBody, /if \(connecting\)\s+return;/, "connect must ignore duplicate connection requests");
  assert.match(connectBody, /connecting = true[\s\S]*connectingTo = ssid[\s\S]*lastError = ""/, "connect must set busy state and clear stale errors");
  assert.match(connectBody, /\(networks\[ssid\] && networks\[ssid\]\.existing\) \|\| cachedNetworks\[ssid\]/, "connect must reuse existing or cached profiles");
  assert.match(connectBody, /connectProcess\.mode = "saved"[\s\S]*connectProcess\.password = ""/, "connect must avoid passwords for saved profiles");
  assert.match(connectBody, /connectProcess\.mode = "new"[\s\S]*connectProcess\.password = password/, "connect must pass passwords for new profiles");
  assert.match(connectBody, /connectProcess\.running = true/, "connect must launch the connection process");
  assert.match(disconnectBody, /disconnectingFrom = ssid[\s\S]*disconnectProcess\.ssid = ssid[\s\S]*disconnectProcess\.running = true/, "disconnect must track and launch the target disconnect");
}

function testNetworkServiceForgetAndStatusGuards() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const forgetBody = extractFunctionBody(source, "forget");
  const statusBody = extractFunctionBody(source, "updateNetworkStatus");

  assert.match(forgetBody, /forgettingNetwork = ssid/, "forget must expose the busy SSID");
  assert.match(forgetBody, /let known = cacheAdapter\.knownNetworks[\s\S]*delete known\[ssid\][\s\S]*cacheAdapter\.knownNetworks = known/, "forget must remove the SSID from cached known networks");
  assert.match(forgetBody, /if \(cacheAdapter\.lastConnected === ssid\)[\s\S]*cacheAdapter\.lastConnected = ""/, "forget must clear lastConnected when deleting that SSID");
  assert.match(forgetBody, /saveCache\(\)/, "forget must persist cache changes");
  assert.match(forgetBody, /forgetProcess\.ssid = ssid[\s\S]*forgetProcess\.running = true/, "forget must launch the system profile delete process");
  assert.match(statusBody, /for \(let key in nets\)[\s\S]*nets\[key\]\.connected = false/, "updateNetworkStatus must disconnect other active networks");
  assert.match(statusBody, /if \(nets\[ssid\]\)[\s\S]*nets\[ssid\]\.connected = connected[\s\S]*nets\[ssid\]\.existing = true[\s\S]*nets\[ssid\]\.cached = true/, "updateNetworkStatus must mark existing targets as known");
  assert.match(statusBody, /else if \(connected\)[\s\S]*"ssid": ssid[\s\S]*"security": "--"[\s\S]*"signal": 100[\s\S]*"connected": true/, "updateNetworkStatus must synthesize connected entries missing from the scan list");
  assert.match(statusBody, /networks = \(\{\}\)[\s\S]*networks = nets/, "updateNetworkStatus must force a property-change notification");
}

function testNetworkServiceIconAndSecurityHelpers() {
  const source = readQml("Services/Networking/NetworkService.qml");
  const iconBody = extractFunctionBody(source, "signalIcon");
  const securedBody = extractFunctionBody(source, "isSecured");

  assert.match(iconBody, /if \(isConnected && !root\.internetConnectivity\)\s+return "world-off"/, "signalIcon must show disconnected-world for captive or offline networks");
  assert.match(iconBody, /if \(signal >= 80\)\s+return "wifi"/, "signalIcon must map strong signal");
  assert.match(iconBody, /if \(signal >= 50\)\s+return "wifi-2"/, "signalIcon must map medium signal");
  assert.match(iconBody, /if \(signal >= 20\)\s+return "wifi-1"/, "signalIcon must map weak signal");
  assert.match(iconBody, /return "wifi-0"/, "signalIcon must map missing or very weak signal");
  assert.match(securedBody, /return security && security !== "--" && security\.trim\(\) !== ""/, "isSecured must reject missing, placeholder, and blank security values");
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
    cacheAdapter: {
      knownNetworks: { Home: true, Office: true },
      lastConnected: "Home",
    },
    connectProcess: {},
    disconnectProcess: {},
    forgetProcess: {},
    saveCache() {
      saveCalls.push({ ...this.cacheAdapter.knownNetworks, lastConnected: this.cacheAdapter.lastConnected });
    },
  };
  ctx.root = ctx;

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
  connect(ctx, "Cafe", "guest");
  assert.equal(ctx.connectProcess.mode, "new", "connect must create new profiles when no cache exists");
  assert.equal(ctx.connectProcess.password, "guest", "new profiles must keep supplied passwords");

  disconnect(ctx, "Home");
  assert.equal(ctx.disconnectingFrom, "Home", "disconnect must track target SSID");
  assert.equal(ctx.disconnectProcess.ssid, "Home", "disconnect must pass SSID to process");
  assert.equal(ctx.disconnectProcess.running, true, "disconnect must start the disconnect process");

  forget(ctx, "Home");
  assert.equal(ctx.forgettingNetwork, "Home", "forget must track target SSID");
  assert.equal(ctx.cacheAdapter.knownNetworks.Home, undefined, "forget must remove target from known network cache");
  assert.equal(ctx.cacheAdapter.knownNetworks.Office, true, "forget must preserve other cached networks");
  assert.equal(ctx.cacheAdapter.lastConnected, "", "forget must clear lastConnected when forgetting the last connected SSID");
  assert.deepEqual(saveCalls, [{ Office: true, lastConnected: "" }], "forget must persist cache changes");
  assert.equal(ctx.forgetProcess.ssid, "Home", "forget must pass SSID to the forget process");
  assert.equal(ctx.forgetProcess.running, true, "forget must start the forget process");

  updateNetworkStatus(ctx, "Cafe", true);
  assert.equal(ctx.networks.Home.connected, false, "updateNetworkStatus must clear other connected networks");
  assert.equal(ctx.networks.Cafe.connected, true, "updateNetworkStatus must mark target connected");
  assert.equal(ctx.networks.Cafe.existing, true, "connected targets must become known profiles");
  assert.equal(ctx.networks.Cafe.cached, true, "connected targets must become cached");

  updateNetworkStatus(ctx, "NewNet", true);
  assert.equal(ctx.networks.NewNet.signal, 100, "missing connected networks must be synthesized");
  updateNetworkStatus(ctx, "MissingDisconnected", false);
  assert.equal(ctx.networks.MissingDisconnected, undefined, "disconnected missing networks must not be synthesized");
  assert.equal(signalIcon(ctx, 90, true), "world-off", "connected offline networks must show world-off");
  ctx.internetConnectivity = true;
  assert.equal(signalIcon(ctx, 90, false), "wifi", "strong signal must use wifi icon");
  assert.equal(signalIcon(ctx, 55, false), "wifi-2", "medium signal must use wifi-2 icon");
  assert.equal(signalIcon(ctx, 25, false), "wifi-1", "weak signal must use wifi-1 icon");
  assert.equal(signalIcon(ctx, 5, false), "wifi-0", "very weak signal must use wifi-0 icon");
  assert.equal(isSecured(ctx, "WPA2"), true, "non-placeholder security must be secured");
  assert.equal(isSecured(ctx, "--"), false, "placeholder security must be unsecured");
  assert.equal(isSecured(ctx, "  "), false, "blank security must be unsecured");
}

const tests = [
  testNetworkServiceCacheAndWifiStateGuards,
  testNetworkServiceScanAndConnectionGuards,
  testNetworkServiceForgetAndStatusGuards,
  testNetworkServiceIconAndSecurityHelpers,
  testNetworkServiceStateCommandsExecute,
  testNetworkServiceConnectionStatusAndIconsExecute,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
