#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const idleInhibitorSource = readQml("Services/Power/IdleInhibitorService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(idleInhibitorSource, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testIdleInhibitorInitializationAndStrategyDetection() {
  const source = readQml("Services/Power/IdleInhibitorService.qml");
  const initBody = extractFunctionBody(source, "init");
  const detectBody = extractFunctionBody(source, "detectStrategy");

  assert.match(initBody, /Logger\.i\("IdleInhibitor", "Service started"\)/, "init must log service startup");
  assert.match(initBody, /detectStrategy\(\)/, "init must detect the inhibition backend");
  assert.match(detectBody, /if \(strategy === "auto"\)/, "detectStrategy must only probe in auto mode");
  assert.match(detectBody, /Quickshell\.execDetached\(\["which", "systemd-inhibit"\]\)/, "detectStrategy must probe systemd-inhibit first");
  assert.match(detectBody, /strategy = "systemd"[\s\S]*Logger\.d\("IdleInhibitor", "Using systemd-inhibit strategy"\)[\s\S]*return;/, "detectStrategy must select systemd when available");
  assert.match(detectBody, /Quickshell\.execDetached\(\["which", "wayhibitor"\]\)/, "detectStrategy must probe wayhibitor as fallback");
  assert.match(detectBody, /strategy = "wayland"[\s\S]*Logger\.d\("IdleInhibitor", "Using wayhibitor strategy"\)[\s\S]*return;/, "detectStrategy must select wayland when available");
  assert.match(detectBody, /Logger\.w\("IdleInhibitor", "No suitable inhibitor found - will try systemd as fallback"\)/, "detectStrategy must warn when probes fail");
  assert.match(detectBody, /strategy = "systemd"; \/\/ Fallback to systemd even if not detected/, "detectStrategy must fall back to systemd");
}

function testIdleInhibitorRegistryAndStateTransitions() {
  const source = readQml("Services/Power/IdleInhibitorService.qml");
  const addBody = extractFunctionBody(source, "addInhibitor");
  const removeBody = extractFunctionBody(source, "removeInhibitor");
  const updateBody = extractFunctionBody(source, "updateInhibition");
  const startBody = extractFunctionBody(source, "startInhibition");
  const stopBody = extractFunctionBody(source, "stopInhibition");

  assert.match(addBody, /if \(activeInhibitors\.includes\(id\)\)[\s\S]*return false/, "addInhibitor must reject duplicate inhibitors");
  assert.match(addBody, /activeInhibitors\.push\(id\)/, "addInhibitor must record the inhibitor id");
  assert.match(addBody, /updateInhibition\(reason\)/, "addInhibitor must update system inhibition with the new reason");
  assert.match(addBody, /return true/, "addInhibitor must report successful additions");
  assert.match(removeBody, /const index = activeInhibitors\.indexOf\(id\)/, "removeInhibitor must locate the inhibitor id");
  assert.match(removeBody, /if \(index === -1\)[\s\S]*return false/, "removeInhibitor must reject unknown inhibitors");
  assert.match(removeBody, /activeInhibitors\.splice\(index, 1\)/, "removeInhibitor must remove known inhibitors");
  assert.match(removeBody, /updateInhibition\(\)/, "removeInhibitor must refresh system inhibition");
  assert.match(updateBody, /const shouldInhibit = activeInhibitors\.length > 0/, "updateInhibition must derive desired state from active inhibitors");
  assert.match(updateBody, /if \(shouldInhibit === isInhibited\)[\s\S]*return;/, "updateInhibition must avoid redundant backend changes");
  assert.match(updateBody, /if \(shouldInhibit\)[\s\S]*startInhibition\(newReason\)[\s\S]*else[\s\S]*stopInhibition\(\)/, "updateInhibition must start or stop inhibition based on active ids");
  assert.match(startBody, /reason = newReason/, "startInhibition must store the active reason");
  assert.match(startBody, /if \(strategy === "systemd"\)[\s\S]*startSystemdInhibition\(\)/, "startInhibition must use the systemd backend");
  assert.match(startBody, /else if \(strategy === "wayland"\)[\s\S]*startWaylandInhibition\(\)/, "startInhibition must use the wayland backend");
  assert.match(startBody, /Logger\.w\("IdleInhibitor", "No inhibition strategy available"\)[\s\S]*return;/, "startInhibition must fail closed for unknown strategies");
  assert.match(startBody, /isInhibited = true/, "startInhibition must mark inhibition active after starting backend");
  assert.match(stopBody, /if \(!isInhibited\)\s+return;/, "stopInhibition must be idempotent when already stopped");
  assert.match(stopBody, /if \(inhibitorProcess\.running\)[\s\S]*inhibitorProcess\.signal\(15\)/, "stopInhibition must terminate the backend process");
  assert.match(stopBody, /isInhibited = false/, "stopInhibition must mark inhibition inactive");
}

function testIdleInhibitorBackendLaunchersAndManualToggle() {
  const source = readQml("Services/Power/IdleInhibitorService.qml");
  const systemdBody = extractFunctionBody(source, "startSystemdInhibition");
  const waylandBody = extractFunctionBody(source, "startWaylandInhibition");
  const manualBody = extractFunctionBody(source, "manualToggle");

  assert.match(systemdBody, /inhibitorProcess\.command = \["systemd-inhibit", "--what=idle", "--why=" \+ reason, "--mode=block", "sleep", "infinity"\]/, "startSystemdInhibition must launch a blocking systemd inhibitor");
  assert.match(systemdBody, /inhibitorProcess\.running = true/, "startSystemdInhibition must start the process");
  assert.match(waylandBody, /inhibitorProcess\.command = \["wayhibitor"\]/, "startWaylandInhibition must launch wayhibitor");
  assert.match(waylandBody, /inhibitorProcess\.running = true/, "startWaylandInhibition must start the process");
  assert.match(manualBody, /timeout = null/, "manualToggle must clear an existing timeout");
  assert.match(manualBody, /if \(activeInhibitors\.includes\("manual"\)\)[\s\S]*removeManualInhibitor\(\)[\s\S]*return false/, "manualToggle must disable an existing manual inhibitor");
  assert.match(manualBody, /else[\s\S]*addManualInhibitor\(null\)[\s\S]*return true/, "manualToggle must enable manual inhibition without timeout");
}

function testIdleInhibitorTimeoutAndManualHelpers() {
  const source = readQml("Services/Power/IdleInhibitorService.qml");
  const changeBody = extractFunctionBody(source, "changeTimeout");
  const removeManualBody = extractFunctionBody(source, "removeManualInhibitor");
  const addManualBody = extractFunctionBody(source, "addManualInhibitor");

  assert.match(changeBody, /if \(timeout == null && delta < 0\)[\s\S]*return;/, "changeTimeout must ignore negative changes without an active timeout");
  assert.match(changeBody, /if \(timeout == null && delta > 0\)[\s\S]*addManualInhibitor\(timeout \+ delta\)[\s\S]*return;/, "changeTimeout must create a timed manual inhibitor");
  assert.match(changeBody, /if \(timeout \+ delta <= 0\)[\s\S]*removeManualInhibitor\(\)[\s\S]*return;/, "changeTimeout must remove expired manual inhibition");
  assert.match(changeBody, /if \(timeout \+ delta > 0\)[\s\S]*addManualInhibitor\(timeout \+ delta\)[\s\S]*return;/, "changeTimeout must update positive timeouts");
  assert.match(removeManualBody, /if \(timeout !== null\)[\s\S]*timeout = null/, "removeManualInhibitor must clear timeout state");
  assert.match(removeManualBody, /if \(inhibitorTimeout\.running\)[\s\S]*inhibitorTimeout\.stop\(\)/, "removeManualInhibitor must stop the timeout timer");
  assert.match(removeManualBody, /if \(activeInhibitors\.includes\("manual"\)\)[\s\S]*removeInhibitor\("manual"\)/, "removeManualInhibitor must remove the manual inhibitor id");
  assert.match(removeManualBody, /ToastService\.showNotice\(I18n\.tr\("tooltips\.keep-awake"\), I18n\.tr\("toast\.keep-awake\.disabled"\), "keep-awake-off"\)/, "removeManualInhibitor must notify the user");
  assert.match(addManualBody, /if \(!activeInhibitors\.includes\("manual"\)\)[\s\S]*addInhibitor\("manual", "Manually activated by user"\)/, "addManualInhibitor must add the manual inhibitor id");
  assert.match(addManualBody, /ToastService\.showNotice\(I18n\.tr\("tooltips\.keep-awake"\), I18n\.tr\("toast\.keep-awake\.enabled"\), "keep-awake-on"\)/, "addManualInhibitor must notify the user");
  assert.match(addManualBody, /if \(timeoutSec === null && timeout === null\)[\s\S]*return;/, "addManualInhibitor must leave untimed inhibition untimed");
  assert.match(addManualBody, /else if \(timeoutSec !== null && timeout === null\)[\s\S]*timeout = timeoutSec[\s\S]*inhibitorTimeout\.start\(\)/, "addManualInhibitor must start timer for a new timeout");
  assert.match(addManualBody, /else if \(timeoutSec !== null && timeout !== null\)[\s\S]*timeout = timeoutSec/, "addManualInhibitor must update an existing timeout");
  assert.match(addManualBody, /else if \(timeoutSec === null && timeout !== null\)[\s\S]*timeout = null[\s\S]*inhibitorTimeout\.stop\(\)/, "addManualInhibitor must clear an existing timeout");
}

function testChangeTimeoutExecutesStateTransitions() {
  const changeTimeout = qmlFunction("changeTimeout", "delta");
  const ctx = {
    timeout: null,
    addedTimeouts: [],
    removed: 0,
    addManualInhibitor(timeoutSec) {
      this.addedTimeouts.push(timeoutSec);
      this.timeout = timeoutSec;
    },
    removeManualInhibitor() {
      this.removed++;
      this.timeout = null;
    },
  };

  changeTimeout(ctx, -5);
  assert.deepEqual(ctx.addedTimeouts, []);
  assert.equal(ctx.removed, 0);
  assert.equal(ctx.timeout, null);

  changeTimeout(ctx, 30);
  assert.deepEqual(ctx.addedTimeouts, [30]);
  assert.equal(ctx.timeout, 30);

  changeTimeout(ctx, -40);
  assert.equal(ctx.removed, 1);
  assert.equal(ctx.timeout, null);

  ctx.timeout = 15;
  changeTimeout(ctx, 10);
  assert.deepEqual(ctx.addedTimeouts, [30, 25]);
  assert.equal(ctx.timeout, 25);
}

const tests = [
  testIdleInhibitorInitializationAndStrategyDetection,
  testIdleInhibitorRegistryAndStateTransitions,
  testIdleInhibitorBackendLaunchersAndManualToggle,
  testIdleInhibitorTimeoutAndManualHelpers,
  testChangeTimeoutExecutesStateTransitions,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
