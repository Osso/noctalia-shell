#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Networking/BluetoothService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBluetoothServiceInitializationAndDeviceOrdering() {
  const initBody = extractFunctionBody(source, "init");
  const sortBody = extractFunctionBody(source, "sortDevices");

  assert.match(initBody, /Logger\.i\("Bluetooth",\s*"Service started"\)/, "init must log service startup");
  assert.match(sortBody, /return devices\.sort\(\(a,\s*b\) =>/, "sortDevices must sort the provided device array");
  assert.match(sortBody, /var aName = a\.name \|\| a\.deviceName \|\| ""/, "sortDevices must fall back from name to deviceName");
  assert.match(sortBody, /aName\.includes\(" "\) && aName\.length > 3/, "sortDevices must prefer devices with human-readable names");
  assert.match(sortBody, /if \(aHasRealName && !bHasRealName\)\s+return -1/, "sortDevices must place named devices first");
  assert.match(sortBody, /var aSignal = \(a\.signalStrength !== undefined && a\.signalStrength > 0\) \? a\.signalStrength : 0/, "sortDevices must normalize missing signal strength");
  assert.match(sortBody, /return bSignal - aSignal/, "sortDevices must order remaining devices by signal strength");
}

function testBluetoothServiceDeviceIconAndActionEligibility() {
  const iconBody = extractFunctionBody(source, "getDeviceIcon");
  const canConnectBody = extractFunctionBody(source, "canConnect");
  const canDisconnectBody = extractFunctionBody(source, "canDisconnect");
  const busyBody = extractFunctionBody(source, "isDeviceBusy");

  assert.match(iconBody, /if \(!device\)[\s\S]*return "bt-device-generic"/, "getDeviceIcon must handle missing devices");
  assert.match(iconBody, /var name = \(device\.name \|\| device\.deviceName \|\| ""\)\.toLowerCase\(\)/, "getDeviceIcon must normalize names");
  assert.match(iconBody, /icon\.includes\("headset"\) \|\| icon\.includes\("audio"\) \|\| name\.includes\("headphone"\)/, "getDeviceIcon must detect headphones");
  assert.match(iconBody, /icon\.includes\("mouse"\) \|\| name\.includes\("mouse"\)/, "getDeviceIcon must detect mice");
  assert.match(iconBody, /icon\.includes\("keyboard"\) \|\| name\.includes\("keyboard"\)/, "getDeviceIcon must detect keyboards");
  assert.match(iconBody, /icon\.includes\("phone"\) \|\| name\.includes\("phone"\) \|\| name\.includes\("iphone"\)/, "getDeviceIcon must detect phones");
  assert.match(iconBody, /icon\.includes\("watch"\) \|\| name\.includes\("watch"\)/, "getDeviceIcon must detect watches");
  assert.match(iconBody, /icon\.includes\("speaker"\) \|\| name\.includes\("speaker"\)/, "getDeviceIcon must detect speakers");
  assert.match(iconBody, /icon\.includes\("display"\) \|\| name\.includes\("tv"\)/, "getDeviceIcon must detect displays");
  assert.match(iconBody, /return "bt-device-generic"/, "getDeviceIcon must fall back to a generic icon");
  assert.match(canConnectBody, /if \(!device\)\s+return false/, "canConnect must reject missing devices");
  assert.match(canConnectBody, /return !device\.connected && !device\.pairing && !device\.blocked/, "canConnect must only allow idle unblocked disconnected devices");
  assert.match(canDisconnectBody, /if \(!device\)\s+return false/, "canDisconnect must reject missing devices");
  assert.match(canDisconnectBody, /return device\.connected && !device\.pairing && !device\.blocked/, "canDisconnect must only allow idle unblocked connected devices");
  assert.match(busyBody, /if \(!device\)[\s\S]*return false/, "isDeviceBusy must reject missing devices");
  assert.match(busyBody, /return device\.pairing \|\| device\.state === BluetoothDeviceState\.Disconnecting \|\| device\.state === BluetoothDeviceState\.Connecting/, "isDeviceBusy must include pairing and transition states");
}

function testBluetoothServiceStatusSignalAndBatteryHelpers() {
  const statusBody = extractFunctionBody(source, "getStatusString");
  const strengthBody = extractFunctionBody(source, "getSignalStrength");
  const batteryBody = extractFunctionBody(source, "getBattery");
  const signalIconBody = extractFunctionBody(source, "getSignalIcon");

  assert.match(statusBody, /device\.state === BluetoothDeviceState\.Connecting[\s\S]*I18n\.tr\("bluetooth\.panel\.connecting"\)/, "getStatusString must report connecting devices");
  assert.match(statusBody, /if \(device\.pairing\)[\s\S]*I18n\.tr\("bluetooth\.panel\.pairing"\)/, "getStatusString must report pairing devices");
  assert.match(statusBody, /if \(device\.blocked\)[\s\S]*I18n\.tr\("bluetooth\.panel\.blocked"\)/, "getStatusString must report blocked devices");
  assert.match(statusBody, /return ""/, "getStatusString must return an empty string for normal devices");
  assert.match(strengthBody, /if \(!device \|\| device\.signalStrength === undefined \|\| device\.signalStrength <= 0\)[\s\S]*return "Signal: Unknown"/, "getSignalStrength must handle missing signal");
  assert.match(strengthBody, /if \(signal >= 80\)[\s\S]*return "Signal: Excellent"/, "getSignalStrength must label excellent signal");
  assert.match(strengthBody, /if \(signal >= 60\)[\s\S]*return "Signal: Good"/, "getSignalStrength must label good signal");
  assert.match(strengthBody, /if \(signal >= 40\)[\s\S]*return "Signal: Fair"/, "getSignalStrength must label fair signal");
  assert.match(strengthBody, /if \(signal >= 20\)[\s\S]*return "Signal: Poor"/, "getSignalStrength must label poor signal");
  assert.match(strengthBody, /return "Signal: Very poor"/, "getSignalStrength must label very poor signal");
  assert.match(batteryBody, /return `Battery: \$\{Math\.round\(device\.battery \* 100\)\}%`/, "getBattery must format battery percentage");
  assert.match(signalIconBody, /if \(!device \|\| device\.signalStrength === undefined \|\| device\.signalStrength <= 0\)[\s\S]*return "antenna-bars-off"/, "getSignalIcon must handle missing signal");
  assert.match(signalIconBody, /if \(signal >= 80\)[\s\S]*return "antenna-bars-5"/, "getSignalIcon must map excellent signal");
  assert.match(signalIconBody, /if \(signal >= 60\)[\s\S]*return "antenna-bars-4"/, "getSignalIcon must map good signal");
  assert.match(signalIconBody, /if \(signal >= 40\)[\s\S]*return "antenna-bars-3"/, "getSignalIcon must map fair signal");
  assert.match(signalIconBody, /if \(signal >= 20\)[\s\S]*return "antenna-bars-2"/, "getSignalIcon must map poor signal");
  assert.match(signalIconBody, /return "antenna-bars-1"/, "getSignalIcon must map very poor signal");
}

function testBluetoothServiceDeviceActionsAndAdapterToggleFailClosed() {
  const connectBody = extractFunctionBody(source, "connectDeviceWithTrust");
  const disconnectBody = extractFunctionBody(source, "disconnectDevice");
  const forgetBody = extractFunctionBody(source, "forgetDevice");
  const enabledBody = extractFunctionBody(source, "setBluetoothEnabled");

  assert.match(connectBody, /if \(!device\)[\s\S]*return;/, "connectDeviceWithTrust must ignore missing devices");
  assert.match(connectBody, /device\.trusted = true[\s\S]*device\.connect\(\)/, "connectDeviceWithTrust must trust before connecting");
  assert.match(disconnectBody, /if \(!device\)[\s\S]*return;/, "disconnectDevice must ignore missing devices");
  assert.match(disconnectBody, /device\.disconnect\(\)/, "disconnectDevice must call disconnect");
  assert.match(forgetBody, /if \(!device\)[\s\S]*return;/, "forgetDevice must ignore missing devices");
  assert.match(forgetBody, /device\.trusted = false[\s\S]*device\.forget\(\)/, "forgetDevice must untrust before forgetting");
  assert.match(enabledBody, /if \(!adapter\)[\s\S]*Logger\.w\("Bluetooth",\s*"No adapter available"\)[\s\S]*return;/, "setBluetoothEnabled must fail closed without an adapter");
  assert.match(enabledBody, /Logger\.i\("Bluetooth",\s*"SetBluetoothEnabled",\s*state\)/, "setBluetoothEnabled must log requested state");
  assert.match(enabledBody, /adapter\.enabled = state/, "setBluetoothEnabled must update adapter enabled state");
}

function testBluetoothServiceSortDevicesPrefersNamedThenSignal() {
  const sortDevices = qmlFunction("sortDevices", "devices");
  const ctx = {};
  const devices = [
    { name: "z", signalStrength: 90 },
    { name: "Desk Speaker", signalStrength: 10 },
    { deviceName: "Office Mouse", signalStrength: 30 },
    { name: "a", signalStrength: 40 },
  ];

  const sorted = sortDevices(ctx, devices);

  assert.deepEqual(sorted.map(device => device.name || device.deviceName), ["Office Mouse", "Desk Speaker", "z", "a"], "sortDevices must prefer human-readable names, then order each group by signal strength");
}

function testBluetoothServiceIconAndActionHelpersExecute() {
  const getDeviceIcon = qmlFunction("getDeviceIcon", "device");
  const canConnect = qmlFunction("canConnect", "device");
  const canDisconnect = qmlFunction("canDisconnect", "device");
  const ctx = {};

  assert.equal(getDeviceIcon(ctx, null), "bt-device-generic", "missing devices must use generic icon");
  assert.equal(getDeviceIcon(ctx, { name: "Arctis Nova" }), "bt-device-headphones", "headset names must map to headphones");
  assert.equal(getDeviceIcon(ctx, { icon: "input-mouse" }), "bt-device-mouse", "mouse icon metadata must map to mouse");
  assert.equal(getDeviceIcon(ctx, { name: "Living Room TV" }), "bt-device-tv", "TV names must map to display icon");
  assert.equal(canConnect(ctx, { connected: false, pairing: false, blocked: false }), true, "idle disconnected devices must be connectable");
  assert.equal(canConnect(ctx, { connected: false, pairing: true, blocked: false }), false, "pairing devices must not be connectable");
  assert.equal(canDisconnect(ctx, { connected: true, pairing: false, blocked: false }), true, "connected idle devices must be disconnectable");
  assert.equal(canDisconnect(ctx, { connected: true, pairing: false, blocked: true }), false, "blocked devices must not be disconnectable");
}

function createWifiBlockedCheckContext(blocked, adapterEnabled) {
  const wifiStates = [];
  const notices = [];
  const warnings = [];
  const ctx = {
    blocked,
    airplaneModeToggled: false,
    adapter: adapterEnabled === null ? null : { enabled: adapterEnabled },
    discoveryTimer: { running: false },
    I18n: { tr(key) { return key; } },
    Logger: {
      d() {},
      w(...args) { warnings.push(args.join(" ")); },
    },
    NetworkService: { setWifiEnabled(state) { wifiStates.push(state); } },
    ToastService: { showNotice(...args) { notices.push(args); } },
  };
  ctx.root = ctx;
  ctx.parseWifiBlockedOutput = output => qmlFunction("parseWifiBlockedOutput", "output")(ctx, output);
  ctx.showBluetoothStateNotice = () => qmlFunction("showBluetoothStateNotice")(ctx);
  ctx.wifiStates = wifiStates;
  ctx.notices = notices;
  ctx.warnings = warnings;
  return ctx;
}

function testBluetoothRfkillStartResetsBufferedProcessState() {
  const startWifiBlockedCheck = qmlFunction("startWifiBlockedCheck");
  const ctx = {
    checkWifiBlocked: {
      output: "stale output",
      errorOutput: "stale error",
      exitObserved: true,
      running: false,
    },
  };

  startWifiBlockedCheck(ctx);
  assert.equal(ctx.checkWifiBlocked.output, "", "new probes must discard stale stdout");
  assert.equal(ctx.checkWifiBlocked.errorOutput, "", "new probes must discard stale stderr");
  assert.equal(ctx.checkWifiBlocked.exitObserved, false, "new probes must reset exit observation");
  assert.equal(ctx.checkWifiBlocked.running, true, "new probes must start the process");
}

function testBluetoothRfkillResultsGateAirplaneModeMutation() {
  const finishWifiBlockedCheck = qmlFunction("finishWifiBlockedCheck", "exitCode", "output", "errorOutput");

  const blocked = createWifiBlockedCheckContext(true, false);
  finishWifiBlockedCheck(blocked, 0, "0: phy0: Wireless LAN\n\tSoft blocked: yes\n", "");
  assert.deepEqual(blocked.wifiStates, [false], "matching blocked states must disable Wi-Fi");
  assert.equal(blocked.notices.at(-1)[1], "toast.airplane-mode.enabled", "matching blocked states must show airplane-mode enabled");
  assert.equal(blocked.airplaneModeToggled, false, "airplane-mode suppression must be released after handling");

  const unblocked = createWifiBlockedCheckContext(false, true);
  finishWifiBlockedCheck(unblocked, 0, "0: phy0: Wireless LAN\n\tSoft blocked: no\n", "");
  assert.deepEqual(unblocked.wifiStates, [true], "matching unblocked states must enable Wi-Fi");
  assert.equal(unblocked.notices.at(-1)[1], "toast.airplane-mode.disabled", "matching unblocked states must show airplane-mode disabled");
}

function testBluetoothRfkillFailuresPreserveWifiAndShowBluetoothState() {
  const finishWifiBlockedCheck = qmlFunction("finishWifiBlockedCheck", "exitCode", "output", "errorOutput");

  for (const [exitCode, output, errorOutput] of [
    [1, "", "permission denied"],
    [0, "", ""],
    [0, "unexpected output", ""],
    [0, "Soft blocked: yesterday", ""],
    [0, "Soft blocked: none", ""],
  ]) {
    const ctx = createWifiBlockedCheckContext(true, false);
    finishWifiBlockedCheck(ctx, exitCode, output, errorOutput);
    assert.deepEqual(ctx.wifiStates, [], "failed or malformed probes must not mutate Wi-Fi");
    assert.equal(ctx.notices.at(-1)[1], "toast.bluetooth.disabled", "probe failures must retain Bluetooth state feedback");
    assert.equal(ctx.airplaneModeToggled, false, "probe failures must release airplane-mode suppression");
    assert.equal(ctx.warnings.length, 1, "probe failures must log one diagnostic");
  }

  const missingAdapter = createWifiBlockedCheckContext(false, null);
  finishWifiBlockedCheck(missingAdapter, 0, "Soft blocked: no", "");
  assert.deepEqual(missingAdapter.wifiStates, [], "adapter loss before successful completion must not mutate Wi-Fi");
  assert.equal(missingAdapter.notices.at(-1)[1], "toast.bluetooth.disabled", "adapter loss must still produce bounded state feedback");
  assert.match(missingAdapter.warnings.at(-1), /adapter.*unavailable/, "adapter loss must log its concrete cause");
}

function testBluetoothRfkillFailedStartUsesRunningChanged() {
  const handleWifiBlockedCheckStartFailure = qmlFunction("handleWifiBlockedCheckStartFailure", "exitObserved");
  const ctx = createWifiBlockedCheckContext(false, true);
  ctx.finishWifiBlockedCheck = (...args) => qmlFunction("finishWifiBlockedCheck", "exitCode", "output", "errorOutput")(ctx, ...args);

  handleWifiBlockedCheckStartFailure(ctx, false);
  assert.equal(ctx.warnings.length, 1, "failed start must produce a diagnostic");
  assert.deepEqual(ctx.wifiStates, [], "failed start must not mutate Wi-Fi");

  const warningCount = ctx.warnings.length;
  handleWifiBlockedCheckStartFailure(ctx, true);
  assert.equal(ctx.warnings.length, warningCount, "normal exit must not be finalized twice");
}

function testBluetoothRfkillProcessRoutesBufferedExitAndStartFailure() {
  assert.match(source, /id:\s*checkWifiBlocked[\s\S]*?property string output[\s\S]*?property string errorOutput[\s\S]*?property bool exitObserved/);
  assert.match(source, /id:\s*checkWifiBlocked[\s\S]*?onExited:\s*function\s*\(exitCode\)[\s\S]*?exitObserved = true[\s\S]*?finishWifiBlockedCheck/);
  assert.match(source, /id:\s*checkWifiBlocked[\s\S]*?onRunningChanged:\s*\{[\s\S]*?handleWifiBlockedCheckStartFailure[\s\S]*?exitObserved = false/);
}

function testBluetoothServiceStatusSignalBatteryAndBusyHelpersExecute() {
  const getStatusString = qmlFunction("getStatusString", "device");
  const getSignalStrength = qmlFunction("getSignalStrength", "device");
  const getSignalIcon = qmlFunction("getSignalIcon", "device");
  const getBattery = qmlFunction("getBattery", "device");
  const isDeviceBusy = qmlFunction("isDeviceBusy", "device");
  const ctx = {
    BluetoothDeviceState: {
      Connecting: 1,
      Disconnecting: 2,
    },
    I18n: {
      tr(key) {
        return key;
      },
    },
  };

  assert.equal(getStatusString(ctx, { state: 1 }), "bluetooth.panel.connecting", "connecting state must return connecting translation key");
  assert.equal(getStatusString(ctx, { state: 0, pairing: true }), "bluetooth.panel.pairing", "pairing state must return pairing translation key");
  assert.equal(getStatusString(ctx, { state: 0, blocked: true }), "bluetooth.panel.blocked", "blocked state must return blocked translation key");
  assert.equal(getSignalStrength(ctx, null), "Signal: Unknown", "missing signal must be unknown");
  assert.equal(getSignalStrength(ctx, { signalStrength: 60 }), "Signal: Good", "60 signal must be good");
  assert.equal(getSignalIcon(ctx, { signalStrength: 19 }), "antenna-bars-1", "very poor signal must use one bar");
  assert.equal(getSignalIcon(ctx, { signalStrength: 80 }), "antenna-bars-5", "excellent signal must use five bars");
  assert.equal(getBattery(ctx, { battery: 0.876 }), "Battery: 88%", "battery helper must round percentages");
  assert.equal(isDeviceBusy(ctx, { pairing: false, state: 2 }), true, "disconnecting devices must be busy");
  assert.equal(isDeviceBusy(ctx, { pairing: false, state: 0 }), false, "idle devices must not be busy");
}

const tests = [
  testBluetoothServiceInitializationAndDeviceOrdering,
  testBluetoothServiceDeviceIconAndActionEligibility,
  testBluetoothServiceStatusSignalAndBatteryHelpers,
  testBluetoothServiceDeviceActionsAndAdapterToggleFailClosed,
  testBluetoothServiceSortDevicesPrefersNamedThenSignal,
  testBluetoothServiceIconAndActionHelpersExecute,
  testBluetoothRfkillStartResetsBufferedProcessState,
  testBluetoothRfkillResultsGateAirplaneModeMutation,
  testBluetoothRfkillFailuresPreserveWifiAndShowBluetoothState,
  testBluetoothRfkillFailedStartUsesRunningChanged,
  testBluetoothRfkillProcessRoutesBufferedExitAndStartFailure,
  testBluetoothServiceStatusSignalBatteryAndBusyHelpersExecute,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
