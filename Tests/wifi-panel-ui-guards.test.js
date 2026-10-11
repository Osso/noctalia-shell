#!/usr/bin/env node

const assert = require("assert/strict");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const {
  extractComponentBlocks,
  readQml,
  stripQmlComments,
} = require("./qml-test-utils");

const panelSource = stripQmlComments(readQml("Modules/Panels/WiFi/WiFiPanel.qml"));

function testProductionListActionsAndGeometry() {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "wifi-list-proof-"));
  try {
    execFileSync(
      "python3",
      [
        path.join(__dirname, "wifi-networks-list-warnings.test.py"),
        "behavior",
        "--snapshot",
        path.join(temporary, "geometry.json"),
      ],
      { cwd: path.resolve(__dirname, ".."), stdio: "inherit", timeout: 60000 },
    );
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
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
  testProductionListActionsAndGeometry,
  testBothPanelListsRouteCredentialAndForgetSignals,
]) {
  test();
  console.log(`ok ${test.name}`);
}
