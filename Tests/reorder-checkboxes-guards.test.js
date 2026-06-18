#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Widgets/NReorderCheckboxes.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext(model) {
  return {
    root: {
      model,
      toggled: [],
      reordered: [],
      itemToggled(index, enabled) {
        this.toggled.push({ index, enabled });
      },
      itemsReordered(fromIndex, toIndex) {
        this.reordered.push({ fromIndex, toIndex });
      },
    },
  };
}

function testToggleItemIgnoresOutOfRangeIndexes() {
  const toggleItem = qmlFunction("toggleItem", "index");
  const model = [{ id: "clock", enabled: true }];
  const ctx = createContext(model);

  toggleItem(ctx, -1);
  toggleItem(ctx, 1);

  assert.equal(ctx.root.model, model);
  assert.deepEqual(ctx.root.toggled, []);
}

function testToggleItemIgnoresRequiredItems() {
  const toggleItem = qmlFunction("toggleItem", "index");
  const model = [{ id: "clock", enabled: true, required: true }];
  const ctx = createContext(model);

  toggleItem(ctx, 0);

  assert.equal(ctx.root.model, model);
  assert.deepEqual(ctx.root.toggled, []);
}

function testToggleItemCopiesModelAndEmitsState() {
  const toggleItem = qmlFunction("toggleItem", "index");
  const item = { id: "clock", enabled: true };
  const model = [item, { id: "tray", enabled: false }];
  const ctx = createContext(model);

  toggleItem(ctx, 0);

  assert.notEqual(ctx.root.model, model);
  assert.notEqual(ctx.root.model[0], item);
  assert.deepEqual(ctx.root.model, [
    { id: "clock", enabled: false },
    { id: "tray", enabled: false },
  ]);
  assert.deepEqual(ctx.root.toggled, [{ index: 0, enabled: false }]);
}

function testMoveItemIgnoresNoopAndOutOfRangeIndexes() {
  const moveItem = qmlFunction("moveItem", "fromIndex", "toIndex");
  const model = [{ id: "clock" }, { id: "tray" }];
  const ctx = createContext(model);

  moveItem(ctx, 0, 0);
  moveItem(ctx, -1, 1);
  moveItem(ctx, 0, 2);

  assert.equal(ctx.root.model, model);
  assert.deepEqual(ctx.root.reordered, []);
}

function testMoveItemCopiesAndReordersModel() {
  const moveItem = qmlFunction("moveItem", "fromIndex", "toIndex");
  const first = { id: "clock" };
  const second = { id: "tray" };
  const third = { id: "battery" };
  const model = [first, second, third];
  const ctx = createContext(model);

  moveItem(ctx, 0, 2);

  assert.notEqual(ctx.root.model, model);
  assert.deepEqual(ctx.root.model, [second, third, first]);
  assert.deepEqual(ctx.root.reordered, [{ fromIndex: 0, toIndex: 2 }]);
}

function testReorderCheckboxIndexInputsAreTyped() {
  assert.match(source, /function toggleItem\(index\)/, "toggleItem must type the index input");
  assert.match(source, /function moveItem\(fromIndex, toIndex\)/, "moveItem must type source and target index inputs");
}

const tests = [
  testToggleItemIgnoresOutOfRangeIndexes,
  testToggleItemIgnoresRequiredItems,
  testToggleItemCopiesModelAndEmitsState,
  testMoveItemIgnoresNoopAndOutOfRangeIndexes,
  testMoveItemCopiesAndReordersModel,
  testReorderCheckboxIndexInputsAreTyped,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
