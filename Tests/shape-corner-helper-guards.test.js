#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testShapeCornerHelperSignaturesAreTyped() {
  const source = readQml("Modules/MainScreen/Backgrounds/ShapeCornerHelper.qml");

  assert.match(source, /function getMultX\(cornerState: int\): int/, "getMultX must type corner state input and multiplier output");
  assert.match(source, /function getMultY\(cornerState: int\): int/, "getMultY must type corner state input and multiplier output");
  assert.match(source, /function getArcDirection\(multX: int, multY: int\): int/, "getArcDirection must type multiplier inputs and arc direction output");
  assert.match(source, /function getArcDirectionFromState\(cornerState: int\): int/, "getArcDirectionFromState must type corner state input and arc direction output");
  assert.match(source, /function getFlattenedRadius\(dimension: real, requestedRadius: real\): real/, "getFlattenedRadius must type dimensions and radius output");
  assert.match(source, /function shouldFlatten\(width: real, height: real, radius: real\): bool/, "shouldFlatten must type dimensions and boolean output");
}

function testShapeCornerHelperMultiplierGuards() {
  const source = readQml("Modules/MainScreen/Backgrounds/ShapeCornerHelper.qml");
  const getMultXBody = extractFunctionBody(source, "getMultX");
  const getMultYBody = extractFunctionBody(source, "getMultY");
  const getDirectionBody = extractFunctionBody(source, "getArcDirection");
  const getDirectionFromStateBody = extractFunctionBody(source, "getArcDirectionFromState");

  assert.match(getMultXBody, /return cornerState === 1 \? -1 : 1/, "getMultX must invert only horizontal corner state");
  assert.match(getMultYBody, /return cornerState === 2 \? -1 : 1/, "getMultY must invert only vertical corner state");
  assert.match(getDirectionBody, /\(\(multX < 0\) !== \(multY < 0\)\) \? PathArc\.Counterclockwise : PathArc\.Clockwise/, "getArcDirection must use XOR inversion for arc direction");
  assert.match(getDirectionFromStateBody, /const multX = getMultX\(cornerState\)[\s\S]*const multY = getMultY\(cornerState\)[\s\S]*return getArcDirection\(multX, multY\)/, "getArcDirectionFromState must compose multiplier helpers");
}

function testShapeCornerHelperFlattenGuards() {
  const source = readQml("Modules/MainScreen/Backgrounds/ShapeCornerHelper.qml");
  const getFlattenedRadiusBody = extractFunctionBody(source, "getFlattenedRadius");
  const shouldFlattenBody = extractFunctionBody(source, "shouldFlatten");

  assert.match(getFlattenedRadiusBody, /if \(dimension < requestedRadius \* 2\)[\s\S]*return dimension \/ 2[\s\S]*return requestedRadius/, "getFlattenedRadius must clamp radius when dimension is too small");
  assert.match(shouldFlattenBody, /return width < radius \* 2 \|\| height < radius \* 2/, "shouldFlatten must check both dimensions against diameter");
}

const tests = [
  testShapeCornerHelperSignaturesAreTyped,
  testShapeCornerHelperMultiplierGuards,
  testShapeCornerHelperFlattenGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
