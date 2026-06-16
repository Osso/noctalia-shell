#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/ControlCenter/Widgets/CustomButton.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testCustomButtonWidgetUpdatesPropertiesFromSettings() {
  const updateProperties = qmlFunction("_updatePropertiesFromSettings");
  let updateStateCalls = 0;
  const ctx = {
    widgetSettings: {
      onClicked: "left-command",
      onRightClicked: "right-command",
      onMiddleClicked: "middle-command",
      stateChecksJson: '[{"command":"pgrep app","icon":"app-icon"}]',
      generalTooltipText: "Launch App",
      enableOnStateLogic: true,
    },
    onClickedCommand: "",
    onRightClickedCommand: "",
    onMiddleClickedCommand: "",
    stateChecksJson: "[]",
    _parsedStateChecks: [],
    generalTooltipText: "",
    enableOnStateLogic: false,
    updateState() {
      updateStateCalls += 1;
    },
  };

  updateProperties(ctx);

  assert.equal(ctx.onClickedCommand, "left-command");
  assert.equal(ctx.onRightClickedCommand, "right-command");
  assert.equal(ctx.onMiddleClickedCommand, "middle-command");
  assert.deepEqual(ctx._parsedStateChecks, [{ command: "pgrep app", icon: "app-icon" }]);
  assert.equal(ctx.generalTooltipText, "Launch App");
  assert.equal(ctx.enableOnStateLogic, true);
  assert.equal(updateStateCalls, 1);
}

function testCustomButtonWidgetHandlesMissingAndInvalidSettings() {
  const updateProperties = qmlFunction("_updatePropertiesFromSettings");
  const errors = [];
  let updateStateCalls = 0;
  const ctx = {
    widgetSettings: null,
    onClickedCommand: "existing",
    onRightClickedCommand: "existing-right",
    onMiddleClickedCommand: "existing-middle",
    stateChecksJson: "[]",
    _parsedStateChecks: [{ command: "existing" }],
    generalTooltipText: "Existing",
    enableOnStateLogic: true,
    console: {
      error(...args) {
        errors.push(args);
      },
    },
    updateState() {
      updateStateCalls += 1;
    },
  };

  updateProperties(ctx);

  assert.equal(ctx.onClickedCommand, "existing");
  assert.deepEqual(ctx._parsedStateChecks, [{ command: "existing" }]);
  assert.equal(updateStateCalls, 0);

  ctx.widgetSettings = {
    stateChecksJson: "not json",
  };
  updateProperties(ctx);

  assert.equal(ctx.onClickedCommand, "");
  assert.equal(ctx.onRightClickedCommand, "");
  assert.equal(ctx.onMiddleClickedCommand, "");
  assert.deepEqual(ctx._parsedStateChecks, []);
  assert.equal(ctx.generalTooltipText, "Custom Button");
  assert.equal(ctx.enableOnStateLogic, false);
  assert.equal(updateStateCalls, 1);
  assert.equal(errors.length, 1);
  assert.equal(errors[0][0], "CustomButton: Failed to parse stateChecksJson:");
}

function testCustomButtonWidgetCheckNextStateSkipsInvalidChecksAndStartsProcess() {
  const checkNextState = qmlFunction("_checkNextState");
  const ctx = {
    _currentStateCheckIndex: 0,
    _parsedStateChecks: [
      null,
      {},
      { command: "pgrep app", icon: "app-icon" },
    ],
    stateCheckProcessExecutor: {
      running: false,
    },
    widgetSettings: {
      icon: "default-icon",
    },
    _isHot: true,
    _activeStateIcon: "",
    _checkNextState() {
      checkNextState(ctx);
    },
  };

  checkNextState(ctx);

  assert.equal(ctx._currentStateCheckIndex, 2);
  assert.equal(ctx.stateCheckProcessExecutor.running, true);
  assert.equal(ctx._isHot, true);
}

function testCustomButtonWidgetCheckNextStateFallsBackWhenNoChecksMatch() {
  const checkNextState = qmlFunction("_checkNextState");
  const ctx = {
    _currentStateCheckIndex: 2,
    _parsedStateChecks: [{ command: "one" }],
    stateCheckProcessExecutor: {
      running: false,
    },
    widgetSettings: {
      icon: "default-icon",
    },
    _isHot: true,
    _activeStateIcon: "old-icon",
  };

  checkNextState(ctx);

  assert.equal(ctx._isHot, false);
  assert.equal(ctx._activeStateIcon, "default-icon");
  assert.equal(ctx.stateCheckProcessExecutor.running, false);
}

function testCustomButtonWidgetUpdateStateRestartsOnlyWhenLogicEnabled() {
  const updateState = qmlFunction("updateState");
  let restarts = 0;
  const ctx = {
    enableOnStateLogic: false,
    _parsedStateChecks: [{ command: "pgrep app" }],
    _isHot: true,
    _activeStateIcon: "old-icon",
    widgetSettings: {
      icon: "default-icon",
    },
    stateUpdateTimer: {
      restart() {
        restarts += 1;
      },
    },
  };

  updateState(ctx);

  assert.equal(ctx._isHot, false);
  assert.equal(ctx._activeStateIcon, "default-icon");
  assert.equal(restarts, 0);

  ctx.enableOnStateLogic = true;
  ctx._parsedStateChecks = [{ command: "pgrep app" }];
  updateState(ctx);

  assert.equal(restarts, 1);
}

function testCustomButtonWidgetBuildTooltipTextIncludesConfiguredCommands() {
  const buildTooltipText = qmlFunction("_buildTooltipText");

  assert.equal(buildTooltipText({
    generalTooltipText: "Custom Button",
    onClickedCommand: "",
    onRightClickedCommand: "",
    onMiddleClickedCommand: "",
  }), "Custom Button");

  assert.equal(buildTooltipText({
    generalTooltipText: "Launcher",
    onClickedCommand: "left",
    onRightClickedCommand: "right",
    onMiddleClickedCommand: "middle",
  }), "Launcher\nLeft click: left\nRight click: right\nMiddle click: middle");
}

const tests = [
  testCustomButtonWidgetUpdatesPropertiesFromSettings,
  testCustomButtonWidgetHandlesMissingAndInvalidSettings,
  testCustomButtonWidgetCheckNextStateSkipsInvalidChecksAndStartsProcess,
  testCustomButtonWidgetCheckNextStateFallsBackWhenNoChecksMatch,
  testCustomButtonWidgetUpdateStateRestartsOnlyWhenLogicEnabled,
  testCustomButtonWidgetBuildTooltipTextIncludesConfiguredCommands,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
