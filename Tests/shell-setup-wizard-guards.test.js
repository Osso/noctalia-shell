#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("shell.qml");

function qmlFunction(functionName) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", `with (ctx) { return (function() ${body}).call(ctx); }`);
}

function createSetupContext() {
  return {
    Settings: {
      shouldOpenSetupWizard: true,
    },
    HostService: {
      isReady: true,
      isNixOS: false,
    },
    setupWizardTimer: {
      starts: 0,
      restarts: 0,
      start() {
        this.starts += 1;
      },
      restart() {
        this.restarts += 1;
      },
    },
    Qt: {
      laterCalls: 0,
      callLater(callback) {
        assert.equal(typeof callback, "function");
        this.laterCalls += 1;
      },
    },
  };
}

function testCheckSetupWizardSkipsWhenDisabledOrNixos() {
  const checkSetupWizard = qmlFunction("checkSetupWizard");
  const disabledCtx = createSetupContext();
  disabledCtx.Settings.shouldOpenSetupWizard = false;
  const nixCtx = createSetupContext();
  nixCtx.HostService.isNixOS = true;

  checkSetupWizard(disabledCtx);
  checkSetupWizard(nixCtx);

  assert.equal(disabledCtx.setupWizardTimer.starts, 0);
  assert.equal(nixCtx.setupWizardTimer.starts, 0);
}

function testCheckSetupWizardWaitsForHostReadiness() {
  const checkSetupWizard = qmlFunction("checkSetupWizard");
  const ctx = createSetupContext();
  ctx.HostService.isReady = false;
  ctx.checkSetupWizard = () => {};

  checkSetupWizard(ctx);

  assert.equal(ctx.Qt.laterCalls, 1);
  assert.equal(ctx.setupWizardTimer.starts, 0);
}

function testCheckSetupWizardStartsTimerWhenReady() {
  const checkSetupWizard = qmlFunction("checkSetupWizard");
  const ctx = createSetupContext();

  checkSetupWizard(ctx);

  assert.equal(ctx.setupWizardTimer.starts, 1);
}

function testShowSetupWizardNoopsWithoutScreens() {
  const showSetupWizard = qmlFunction("showSetupWizard");
  const ctx = {
    Quickshell: {
      screens: [],
    },
    PanelService: {
      getPanel() {
        throw new Error("panel lookup should not run without screens");
      },
    },
    setupWizardTimer: {
      restart() {
        throw new Error("timer should not restart without screens");
      },
    },
  };

  showSetupWizard(ctx);
}

function testShowSetupWizardOpensLoadedPanel() {
  const showSetupWizard = qmlFunction("showSetupWizard");
  const screen = { name: "HDMI-A-1" };
  const ctx = {
    Quickshell: {
      screens: [screen],
    },
    opened: 0,
    PanelService: {
      requested: [],
      getPanel(name, targetScreen) {
        this.requested.push({ name, targetScreen });
        return {
          open: () => {
            ctx.opened += 1;
          },
        };
      },
    },
    setupWizardTimer: {
      restarts: 0,
      restart() {
        this.restarts += 1;
      },
    },
  };

  showSetupWizard(ctx);

  assert.deepEqual(ctx.PanelService.requested, [{ name: "setupWizardPanel", targetScreen: screen }]);
  assert.equal(ctx.opened, 1);
  assert.equal(ctx.setupWizardTimer.restarts, 0);
}

function testShowSetupWizardRestartsTimerWhenPanelIsMissing() {
  const showSetupWizard = qmlFunction("showSetupWizard");
  const ctx = {
    Quickshell: {
      screens: [{}],
    },
    PanelService: {
      getPanel() {
        return null;
      },
    },
    setupWizardTimer: {
      restarts: 0,
      restart() {
        this.restarts += 1;
      },
    },
  };

  showSetupWizard(ctx);

  assert.equal(ctx.setupWizardTimer.restarts, 1);
}

const tests = [
  testCheckSetupWizardSkipsWhenDisabledOrNixos,
  testCheckSetupWizardWaitsForHostReadiness,
  testCheckSetupWizardStartsTimerWhenReady,
  testShowSetupWizardNoopsWithoutScreens,
  testShowSetupWizardOpensLoadedPanel,
  testShowSetupWizardRestartsTimerWhenPanelIsMissing,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
