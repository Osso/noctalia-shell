#!/usr/bin/env node

const assert = require("assert/strict");
const {
  extractComponentBlocks,
  findComponentBlock,
  readQml,
  stripQmlComments,
} = require("./qml-test-utils");

const panelSource = stripQmlComments(readQml("Modules/Panels/WiFi/WiFiPanel.qml"));
const listSource = stripQmlComments(readQml("Modules/Panels/WiFi/WiFiNetworksList.qml"));
const listBlock = (componentName, marker) => findComponentBlock(listSource, componentName, marker);

function testNetworkRowsChooseDirectOrPasswordConnection() {
  const connectButton = listBlock("NButton", "root.passwordSsid !== networkSsid");
  assert.match(connectButton, /visible:\s*!networkConnected && !networkBusy && root\.passwordSsid !== networkSsid/);
  assert.match(connectButton, /if \(savedNetwork \|\| !NetworkService\.isSecured\(networkSecurity\)\)\s*\{\s*NetworkService\.connect\(networkSsid\);\s*\} else \{\s*root\.passwordRequested\(networkSsid\);/);
  assert.match(connectButton, /enabled:\s*!NetworkService\.connecting/);
}

function testPasswordEntryProtectsAndSubmitsCredentials() {
  const passwordInput = listBlock("TextInput", "id: pwdInput");
  assert.match(passwordInput, /echoMode:\s*TextInput\.Password/);
  assert.match(passwordInput, /onVisibleChanged:\s*\{\s*text = "";\s*if \(visible\) \{\s*forceActiveFocus\(\);/);
  assert.match(passwordInput, /onAccepted:\s*\{\s*if \(text && !NetworkService\.connecting\) \{\s*networkItem\.submitPassword\(text\);/);
  assert.match(listSource, /function submitPassword\(password\) \{\s*pwdInput\.text = "";\s*root\.passwordSubmitted\(networkSsid, password\);\s*\}/);
  assert.match(listSource, /function cancelPassword\(\) \{\s*pwdInput\.text = "";\s*root\.passwordCancelled\(\);\s*\}/);
  const submitButton = listBlock("NButton", "pwdInput.text.length > 0");
  assert.match(submitButton, /enabled:\s*pwdInput\.text\.length > 0 && !NetworkService\.connecting/);
  assert.match(submitButton, /onClicked:\s*networkItem\.submitPassword\(pwdInput\.text\)/);
  const cancelButton = listBlock("NIconButton", "networkItem.cancelPassword()");
  assert.match(cancelButton, /onClicked:\s*networkItem\.cancelPassword\(\)/);
}

function testForgetFlowRequiresExplicitConfirmation() {
  const requestButton = listBlock("NIconButton", "tooltips.forget-network");
  assert.match(requestButton, /visible:\s*savedNetwork && !networkConnected && !networkBusy/);
  assert.match(requestButton, /onClicked:\s*root\.forgetRequested\(networkSsid\)/);
  assert.match(listSource, /visible:\s*root\.expandedSsid === networkSsid && !disconnectingFromNetwork && !forgettingNetwork/);
  const confirmButton = listBlock("NButton", "id: forgetButton");
  assert.match(confirmButton, /onClicked:\s*root\.forgetConfirmed\(networkSsid\)/);
  const cancelButton = listBlock("NIconButton", "root.forgetCancelled()");
  assert.match(cancelButton, /onClicked:\s*root\.forgetCancelled\(\)/);
}

function testBothPanelListsRouteCredentialAndForgetSignals() {
  const lists = extractComponentBlocks(panelSource, "WiFiNetworksList");
  assert.equal(lists.length, 2, "panel must contain known and available network lists");
  for (const block of lists) {
    assert.match(block, /onPasswordRequested:\s*ssid => \{\s*root\.passwordSsid = ssid;\s*root\.expandedSsid = "";/);
    assert.match(block, /onPasswordSubmitted:\s*\(ssid, password\) => \{\s*NetworkService\.connect\(ssid, password\);\s*root\.passwordSsid = "";/);
    assert.match(block, /onPasswordCancelled:\s*root\.passwordSsid = ""/);
    assert.match(block, /onForgetRequested:\s*ssid => root\.expandedSsid = root\.expandedSsid === ssid \? "" : ssid/);
    assert.match(block, /onForgetConfirmed:\s*ssid => \{\s*NetworkService\.forget\(ssid\);\s*root\.expandedSsid = "";/);
    assert.match(block, /onForgetCancelled:\s*root\.expandedSsid = ""/);
  }
}

for (const test of [
  testNetworkRowsChooseDirectOrPasswordConnection,
  testPasswordEntryProtectsAndSubmitsCredentials,
  testForgetFlowRequiresExplicitConfirmation,
  testBothPanelListsRouteCredentialAndForgetSignals,
]) {
  test();
  console.log(`ok ${test.name}`);
}
