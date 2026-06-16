#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

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

const tests = [
  testNetworkServiceCacheAndWifiStateGuards,
  testNetworkServiceScanAndConnectionGuards,
  testNetworkServiceForgetAndStatusGuards,
  testNetworkServiceIconAndSecurityHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
