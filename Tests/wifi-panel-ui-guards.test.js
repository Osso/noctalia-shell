#!/usr/bin/env node

const assert = require("assert/strict");
const { readQml } = require("./qml-test-utils");

const panelSource = readQml("Modules/Panels/WiFi/WiFiPanel.qml");
const listSource = readQml("Modules/Panels/WiFi/WiFiNetworksList.qml");

function extractBlocks(source, componentName) {
  const blocks = [];
  const marker = `${componentName} {`;
  let start = source.indexOf(marker);
  while (start !== -1) {
    const open = source.indexOf("{", start);
    let depth = 0;
    for (let index = open; index < source.length; index++) {
      if (source[index] === "{") depth++;
      if (source[index] === "}") depth--;
      if (depth === 0) {
        blocks.push(source.slice(start, index + 1));
        start = source.indexOf(marker, index + 1);
        break;
      }
    }
  }
  return blocks;
}

function findSingleBlock(componentName, marker) {
  const matches = extractBlocks(listSource, componentName).filter(block => block.includes(marker));
  assert.equal(matches.length, 1, `${componentName} block containing ${marker} must be unique`);
  return matches[0];
}

function testNetworkRowsChooseDirectOrPasswordConnection() {
  const connectButton = findSingleBlock("NButton", "root.passwordSsid !== networkSsid");
  assert.match(connectButton, /visible:\s*!networkConnected && !networkBusy && root\.passwordSsid !== networkSsid/);
  assert.match(connectButton, /if \(savedNetwork \|\| !NetworkService\.isSecured\(networkSecurity\)\)\s*\{\s*NetworkService\.connect\(networkSsid\);\s*\} else \{\s*root\.passwordRequested\(networkSsid\);/);
  assert.match(connectButton, /enabled:\s*!NetworkService\.connecting/);
}

function testPasswordEntryProtectsAndSubmitsCredentials() {
  const passwordInput = findSingleBlock("TextInput", "id: pwdInput");
  assert.match(passwordInput, /echoMode:\s*TextInput\.Password/);
  assert.match(passwordInput, /onVisibleChanged:\s*\{\s*text = "";\s*if \(visible\) \{\s*forceActiveFocus\(\);/);
  assert.match(passwordInput, /onAccepted:\s*\{\s*if \(text && !NetworkService\.connecting\) \{\s*networkItem\.submitPassword\(text\);/);
  assert.match(listSource, /function submitPassword\(password\) \{\s*pwdInput\.text = "";\s*root\.passwordSubmitted\(networkSsid, password\);\s*\}/);
  assert.match(listSource, /function cancelPassword\(\) \{\s*pwdInput\.text = "";\s*root\.passwordCancelled\(\);\s*\}/);
  const submitButton = findSingleBlock("NButton", "pwdInput.text.length > 0");
  assert.match(submitButton, /enabled:\s*pwdInput\.text\.length > 0 && !NetworkService\.connecting/);
  assert.match(submitButton, /onClicked:\s*networkItem\.submitPassword\(pwdInput\.text\)/);
  const cancelButton = findSingleBlock("NIconButton", "networkItem.cancelPassword()");
  assert.match(cancelButton, /onClicked:\s*networkItem\.cancelPassword\(\)/);
}

function testForgetFlowRequiresExplicitConfirmation() {
  const requestButton = findSingleBlock("NIconButton", "tooltips.forget-network");
  assert.match(requestButton, /visible:\s*savedNetwork && !networkConnected && !networkBusy/);
  assert.match(requestButton, /onClicked:\s*root\.forgetRequested\(networkSsid\)/);
  assert.match(listSource, /visible:\s*root\.expandedSsid === networkSsid && !disconnectingFromNetwork && !forgettingNetwork/);
  const confirmButton = findSingleBlock("NButton", "id: forgetButton");
  assert.match(confirmButton, /onClicked:\s*root\.forgetConfirmed\(networkSsid\)/);
  const cancelButton = findSingleBlock("NIconButton", "root.forgetCancelled()");
  assert.match(cancelButton, /onClicked:\s*root\.forgetCancelled\(\)/);
}

function testBothPanelListsRouteCredentialAndForgetSignals() {
  const lists = extractBlocks(panelSource, "WiFiNetworksList");
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

const tests = [
  testNetworkRowsChooseDirectOrPasswordConnection,
  testPasswordEntryProtectsAndSubmitsCredentials,
  testForgetFlowRequiresExplicitConfirmation,
  testBothPanelListsRouteCredentialAndForgetSignals,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
