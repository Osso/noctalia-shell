#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/ControlCenter/ControlCenterPanel.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testControlCenterCardsLoadOnlyWhilePanelOpen() {
  const shouldLoadCard = qmlFunction("shouldLoadCard", "cardEnabled", "cardId");
  const ctx = {
    root: {
      isPanelOpen: false,
    },
    Settings: {
      data: {
        location: {
          weatherEnabled: true,
        },
      },
    },
  };

  assert.match(source, /function shouldLoadCard\(cardEnabled, cardId\)/, "Control Center panel must centralize card loader activation");
  assert.match(source, /active:\s*root\.shouldLoadCard\(cardEnabled, cardId\)/, "Control Center card loaders must be inactive while the panel is closed");
  assert.equal(shouldLoadCard(ctx, true, "media-sysmon-card"), false);

  ctx.root.isPanelOpen = true;
  assert.equal(shouldLoadCard(ctx, false, "media-sysmon-card"), false);
  assert.equal(shouldLoadCard(ctx, true, "media-sysmon-card"), true);
  assert.equal(shouldLoadCard(ctx, true, "weather-card"), true);

  ctx.Settings.data.location.weatherEnabled = false;
  assert.equal(shouldLoadCard(ctx, true, "weather-card"), false);
}

const tests = [
  testControlCenterCardsLoadOnlyWhilePanelOpen,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
