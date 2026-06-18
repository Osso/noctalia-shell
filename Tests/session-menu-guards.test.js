#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/SessionMenu/SessionMenu.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testSessionMenuActionSignaturesAreTyped() {
  assert.match(source, /function startTimer\(action\)/, "startTimer must accept action input");
  assert.match(source, /function executeAction\(action\)/, "executeAction must accept action input");
}

function testSessionMenuTimerGuards() {
  const startBody = extractFunctionBody(source, "startTimer");
  const cancelBody = extractFunctionBody(source, "cancelTimer");

  assert.match(startBody, /if \(!Settings\.data\.sessionMenu\.enableCountdown\)[\s\S]*executeAction\(action\)[\s\S]*return/, "startTimer must execute immediately when global countdown is disabled");
  assert.match(startBody, /for \(var i = 0; i < powerOptions\.length; i\+\+\)[\s\S]*if \(powerOptions\[i\]\.action === action\)[\s\S]*option = powerOptions\[i\]/, "startTimer must find the selected power option");
  assert.match(startBody, /if \(option && option\.countdownEnabled === false\)[\s\S]*executeAction\(action\)[\s\S]*return/, "startTimer must execute immediately when item countdown is disabled");
  assert.match(startBody, /if \(timerActive && pendingAction === action\)[\s\S]*executeAction\(action\)[\s\S]*return/, "startTimer must treat second click as immediate confirmation");
  assert.match(startBody, /pendingAction = action[\s\S]*timeRemaining = timerDuration[\s\S]*timerActive = true[\s\S]*countdownTimer\.start\(\)/, "startTimer must arm countdown state");
  assert.match(cancelBody, /timerActive = false[\s\S]*pendingAction = ""[\s\S]*timeRemaining = 0[\s\S]*countdownTimer\.stop\(\)/, "cancelTimer must clear countdown state and stop timer");
}

function testSessionMenuExecuteActionDispatch() {
  const body = extractFunctionBody(source, "executeAction");

  assert.match(body, /countdownTimer\.stop\(\)/, "executeAction must stop countdown before dispatching");
  assert.match(body, /case "lock":[\s\S]*PanelService\.lockScreen && !PanelService\.lockScreen\.active[\s\S]*PanelService\.lockScreen\.active = true/, "executeAction must activate lock screen when available");
  assert.match(body, /case "suspend":[\s\S]*if \(Settings\.data\.general\.lockOnSuspend\)[\s\S]*CompositorService\.lockAndSuspend\(\)[\s\S]*CompositorService\.suspend\(\)/, "executeAction must honor lock-on-suspend setting");
  assert.match(body, /case "hibernate":[\s\S]*CompositorService\.hibernate\(\)/, "executeAction must dispatch hibernate");
  assert.match(body, /case "reboot":[\s\S]*CompositorService\.reboot\(\)/, "executeAction must dispatch reboot");
  assert.match(body, /case "logout":[\s\S]*CompositorService\.logout\(\)/, "executeAction must dispatch logout");
  assert.match(body, /case "shutdown":[\s\S]*CompositorService\.shutdown\(\)/, "executeAction must dispatch shutdown");
  assert.match(body, /cancelTimer\(\)[\s\S]*root\.close\(\)/, "executeAction must clear timer state and close panel after dispatch");
}

function testSessionMenuNavigationGuards() {
  const nextBody = extractFunctionBody(source, "selectNextWrapped");
  const previousBody = extractFunctionBody(source, "selectPreviousWrapped");
  const firstBody = extractFunctionBody(source, "selectFirst");
  const lastBody = extractFunctionBody(source, "selectLast");
  const activateBody = extractFunctionBody(source, "activate");

  assert.match(nextBody, /if \(powerOptions\.length > 0\)[\s\S]*selectedIndex = \(selectedIndex \+ 1\) % powerOptions\.length/, "selectNextWrapped must wrap forward inside options");
  assert.match(previousBody, /if \(powerOptions\.length > 0\)[\s\S]*selectedIndex = \(\(\(selectedIndex - 1\) % powerOptions\.length\) \+ powerOptions\.length\) % powerOptions\.length/, "selectPreviousWrapped must wrap backward inside options");
  assert.match(firstBody, /selectedIndex = 0/, "selectFirst must select first option");
  assert.match(lastBody, /if \(powerOptions\.length > 0\)[\s\S]*selectedIndex = powerOptions\.length - 1[\s\S]*else[\s\S]*selectedIndex = 0/, "selectLast must clamp empty options to zero");
  assert.match(activateBody, /if \(powerOptions\.length > 0 && powerOptions\[selectedIndex\]\)[\s\S]*const option = powerOptions\[selectedIndex\][\s\S]*startTimer\(option\.action\)/, "activate must start timer for the selected option");
}

function testSessionMenuNavigationExecutesWrapAndClamp() {
  const selectNextWrapped = qmlFunction("selectNextWrapped");
  const selectPreviousWrapped = qmlFunction("selectPreviousWrapped");
  const selectFirst = qmlFunction("selectFirst");
  const selectLast = qmlFunction("selectLast");
  const ctx = {
    powerOptions: [{}, {}, {}],
    selectedIndex: 2,
  };

  selectNextWrapped(ctx);
  assert.equal(ctx.selectedIndex, 0, "next selection must wrap from last to first");

  selectPreviousWrapped(ctx);
  assert.equal(ctx.selectedIndex, 2, "previous selection must wrap from first to last");

  selectFirst(ctx);
  assert.equal(ctx.selectedIndex, 0, "selectFirst must select index zero");

  selectLast(ctx);
  assert.equal(ctx.selectedIndex, 2, "selectLast must select the final option");

  ctx.powerOptions = [];
  ctx.selectedIndex = 5;
  selectLast(ctx);
  assert.equal(ctx.selectedIndex, 0, "selectLast must clamp empty menus to zero");
}

function testSessionMenuActivateExecutesSelectedActionOnly() {
  const activate = qmlFunction("activate");
  const actions = [];
  const ctx = {
    powerOptions: [
      { action: "lock" },
      { action: "logout" },
    ],
    selectedIndex: 1,
    startTimer(action) {
      actions.push(action);
    },
  };

  activate(ctx);
  assert.deepEqual(actions, ["logout"], "activate must start the selected option action");

  ctx.selectedIndex = 5;
  activate(ctx);
  assert.deepEqual(actions, ["logout"], "activate must ignore missing selected options");
}

function testSessionMenuCountdownTicksAndExpires() {
  const tickCountdownTimer = qmlFunction("tickCountdownTimer");
  const executed = [];
  const ctx = {
    timeRemaining: 250,
    pendingAction: "shutdown",
    countdownTimer: {
      interval: 100,
    },
    executeAction(action) {
      executed.push(action);
    },
  };

  tickCountdownTimer(ctx);
  assert.equal(ctx.timeRemaining, 150, "countdown tick must subtract timer interval");
  assert.deepEqual(executed, [], "countdown must not execute before expiry");

  tickCountdownTimer(ctx);
  assert.equal(ctx.timeRemaining, 50, "countdown must keep ticking toward expiry");
  assert.deepEqual(executed, [], "countdown must still wait while positive");

  tickCountdownTimer(ctx);
  assert.equal(ctx.timeRemaining, -50, "countdown must subtract the final interval before dispatch");
  assert.deepEqual(executed, ["shutdown"], "countdown expiry must execute pending action");
}

const tests = [
  testSessionMenuActionSignaturesAreTyped,
  testSessionMenuTimerGuards,
  testSessionMenuExecuteActionDispatch,
  testSessionMenuNavigationGuards,
  testSessionMenuNavigationExecutesWrapAndClamp,
  testSessionMenuActivateExecutesSelectedActionOnly,
  testSessionMenuCountdownTicksAndExpires,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
