const assert = require("assert/strict");
const { readQml } = require("./qml-test-utils");

const source = readQml("Services/Keyboard/LockKeysService.qml");

function testLockKeysAvoidsShellPolling() {
  assert.doesNotMatch(source, /command:\s*\["sh",\s*"-c"/, "LockKeysService must not spawn a shell for periodic LED reads");
  assert.doesNotMatch(source, /grep\s+-q/, "LockKeysService must not shell out to grep for LED state");
  assert.doesNotMatch(source, /interval:\s*200\b/, "LockKeysService poll interval must not stay at 200ms");
  assert.match(source, /readonly property int pollIntervalMs: 3000/, "LockKeysService poll interval must be 3s to reduce idle wakeups");
}

function testLockKeysReadsLedFilesDirectly() {
  assert.match(source, /readonly property var lockKeyConfigs:/, "LockKeysService must centralize lock-key LED path configuration");
  assert.match(source, /FileView\s*{/, "LockKeysService must use FileView for direct LED reads");
  assert.match(source, /function refreshAllStates\(\)/, "LockKeysService must expose a single refresh entry point");
  assert.match(source, /function applyState\(key, active\)/, "LockKeysService must preserve centralized state/signal handling");
}

function run() {
  testLockKeysAvoidsShellPolling();
  testLockKeysReadsLedFilesDirectly();
}

run();
