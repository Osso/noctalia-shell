#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Tabs/OsdTab.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testOsdTabAddTypeAppendsMissingTypeWithoutMutatingInput() {
  const addType = qmlFunction("addType", "list", "type");
  const existing = ["brightness"];

  const updated = addType({}, existing, "volume");

  assert.deepEqual(updated, ["brightness", "volume"]);
  assert.deepEqual(existing, ["brightness"]);
}

function testOsdTabAddTypeKeepsExistingTypeOnlyOnceAndHandlesEmptyList() {
  const addType = qmlFunction("addType", "list", "type");

  assert.deepEqual(addType({}, ["brightness"], "brightness"), ["brightness"]);
  assert.deepEqual(addType({}, null, "volume"), ["volume"]);
}

function testOsdTabRemoveTypeFiltersMatchesWithoutMutatingInput() {
  const removeType = qmlFunction("removeType", "list", "type");
  const existing = ["brightness", "volume", "brightness"];

  const updated = removeType({}, existing, "brightness");

  assert.deepEqual(updated, ["volume"]);
  assert.deepEqual(existing, ["brightness", "volume", "brightness"]);
}

function testOsdTabRemoveTypeHandlesEmptyListAndMissingType() {
  const removeType = qmlFunction("removeType", "list", "type");

  assert.deepEqual(removeType({}, null, "volume"), []);
  assert.deepEqual(removeType({}, ["brightness"], "volume"), ["brightness"]);
}

const tests = [
  testOsdTabAddTypeAppendsMissingTypeWithoutMutatingInput,
  testOsdTabAddTypeKeepsExistingTypeOnlyOnceAndHandlesEmptyList,
  testOsdTabRemoveTypeFiltersMatchesWithoutMutatingInput,
  testOsdTabRemoveTypeHandlesEmptyListAndMissingType,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
