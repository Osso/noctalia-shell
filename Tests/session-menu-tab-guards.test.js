#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Tabs/SessionMenuTab.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext(entriesModel) {
  const saveEntries = qmlFunction("saveEntries");
  const ctx = {
    entriesModel,
    Settings: {
      data: {
        sessionMenu: {
          powerOptions: [],
        },
      },
    },
  };
  ctx.saveEntries = () => saveEntries(ctx);
  return ctx;
}

function testSessionMenuTabSaveEntriesPersistsActionsAndCountdownDefaults() {
  const saveEntries = qmlFunction("saveEntries");
  const ctx = createContext([
    {
      id: "lock",
      enabled: true,
      countdownEnabled: false,
    },
    {
      id: "logout",
      enabled: false,
    },
  ]);

  saveEntries(ctx);

  assert.deepEqual(ctx.Settings.data.sessionMenu.powerOptions, [
    {
      action: "lock",
      enabled: true,
      countdownEnabled: false,
    },
    {
      action: "logout",
      enabled: false,
      countdownEnabled: true,
    },
  ]);
}

function testSessionMenuTabUpdateEntryCopiesModelAndPersistsChanges() {
  const updateEntry = qmlFunction("updateEntry", "idx", "properties");
  const originalEntry = {
    id: "lock",
    enabled: true,
    countdownEnabled: true,
  };
  const untouchedEntry = {
    id: "shutdown",
    enabled: true,
    countdownEnabled: false,
  };
  const ctx = createContext([originalEntry, untouchedEntry]);

  assert.match(source, /function updateEntry\(idx: int, properties\)/, "updateEntry must type the entry index while keeping the patch object flexible");
  updateEntry(ctx, 0, {
    enabled: false,
  });

  assert.notEqual(ctx.entriesModel[0], originalEntry);
  assert.equal(ctx.entriesModel[1], untouchedEntry);
  assert.deepEqual(ctx.entriesModel, [
    {
      id: "lock",
      enabled: false,
      countdownEnabled: true,
    },
    untouchedEntry,
  ]);
  assert.deepEqual(ctx.Settings.data.sessionMenu.powerOptions, [
    {
      action: "lock",
      enabled: false,
      countdownEnabled: true,
    },
    {
      action: "shutdown",
      enabled: true,
      countdownEnabled: false,
    },
  ]);
}

function testSessionMenuTabReorderEntriesMovesItemAndPersistsOrder() {
  const reorderEntries = qmlFunction("reorderEntries", "fromIndex", "toIndex");
  const ctx = createContext([
    {
      id: "lock",
      enabled: true,
      countdownEnabled: true,
    },
    {
      id: "reboot",
      enabled: true,
      countdownEnabled: false,
    },
    {
      id: "shutdown",
      enabled: false,
      countdownEnabled: true,
    },
  ]);

  assert.match(source, /function reorderEntries\(fromIndex: int, toIndex: int\)/, "reorderEntries must type both move indexes");
  reorderEntries(ctx, 0, 2);

  assert.deepEqual(ctx.entriesModel.map(entry => entry.id), ["reboot", "shutdown", "lock"]);
  assert.deepEqual(ctx.Settings.data.sessionMenu.powerOptions.map(entry => entry.action), ["reboot", "shutdown", "lock"]);
}

const tests = [
  testSessionMenuTabSaveEntriesPersistsActionsAndCountdownDefaults,
  testSessionMenuTabUpdateEntryCopiesModelAndPersistsChanges,
  testSessionMenuTabReorderEntriesMovesItemAndPersistsOrder,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
