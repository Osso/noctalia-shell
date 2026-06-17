#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function assertViewMethodForwarders(source, targetId, label) {
  const positionBody = extractFunctionBody(source, "positionViewAtIndex");
  const beginningBody = extractFunctionBody(source, "positionViewAtBeginning");
  const endBody = extractFunctionBody(source, "positionViewAtEnd");
  const forceLayoutBody = extractFunctionBody(source, "forceLayout");
  const cancelFlickBody = extractFunctionBody(source, "cancelFlick");
  const flickBody = extractFunctionBody(source, "flick");
  const incrementBody = extractFunctionBody(source, "incrementCurrentIndex");
  const decrementBody = extractFunctionBody(source, "decrementCurrentIndex");
  const indexAtBody = extractFunctionBody(source, "indexAt");
  const itemAtBody = extractFunctionBody(source, "itemAt");
  const itemAtIndexBody = extractFunctionBody(source, "itemAtIndex");

  assert.match(positionBody, new RegExp(`${targetId}\\.positionViewAtIndex\\(index, mode\\)`), `${label} must forward positionViewAtIndex`);
  assert.match(beginningBody, new RegExp(`${targetId}\\.positionViewAtBeginning\\(\\)`), `${label} must forward positionViewAtBeginning`);
  assert.match(endBody, new RegExp(`${targetId}\\.positionViewAtEnd\\(\\)`), `${label} must forward positionViewAtEnd`);
  assert.match(forceLayoutBody, new RegExp(`${targetId}\\.forceLayout\\(\\)`), `${label} must forward forceLayout`);
  assert.match(cancelFlickBody, new RegExp(`${targetId}\\.cancelFlick\\(\\)`), `${label} must forward cancelFlick`);
  assert.match(flickBody, new RegExp(`${targetId}\\.flick\\(xVelocity, yVelocity\\)`), `${label} must forward flick velocities`);
  assert.match(incrementBody, new RegExp(`${targetId}\\.incrementCurrentIndex\\(\\)`), `${label} must forward incrementCurrentIndex`);
  assert.match(decrementBody, new RegExp(`${targetId}\\.decrementCurrentIndex\\(\\)`), `${label} must forward decrementCurrentIndex`);
  assert.match(indexAtBody, new RegExp(`return ${targetId}\\.indexAt\\(x, y\\)`), `${label} must return indexAt results`);
  assert.match(itemAtBody, new RegExp(`return ${targetId}\\.itemAt\\(x, y\\)`), `${label} must return itemAt results`);
  assert.match(itemAtIndexBody, new RegExp(`return ${targetId}\\.itemAtIndex\\(index\\)`), `${label} must return itemAtIndex results`);
}

function assertViewMethodSignaturesAreTyped(source, label) {
  assert.match(source, /function positionViewAtIndex\(index: int, mode: int\)/, `${label} must type position index and mode inputs`);
  assert.match(source, /function flick\(xVelocity: real, yVelocity: real\)/, `${label} must type flick velocity inputs`);
  assert.match(source, /function indexAt\(x: real, y: real\)/, `${label} must type indexAt coordinates`);
  assert.match(source, /function itemAt\(x: real, y: real\)/, `${label} must type itemAt coordinates`);
  assert.match(source, /function itemAtIndex\(index: int\)/, `${label} must type itemAtIndex input`);
}

function testNGridViewForwardsGridViewMethods() {
  const source = readQml("Widgets/NGridView.qml");

  assert.match(source, /property alias model: gridView\.model/, "NGridView must expose GridView model alias");
  assert.match(source, /property alias delegate: gridView\.delegate/, "NGridView must expose GridView delegate alias");
  assert.match(source, /property alias currentIndex: gridView\.currentIndex/, "NGridView must expose currentIndex alias");
  assert.match(source, /readonly property bool verticalScrollBarActive:[\s\S]*return gridView\.contentHeight > gridView\.height/, "NGridView must compute scrollbar activity from GridView content");
  assertViewMethodForwarders(source, "gridView", "NGridView");
  assertViewMethodSignaturesAreTyped(source, "NGridView");
}

function testNListViewForwardsListViewMethods() {
  const source = readQml("Widgets/NListView.qml");

  assert.match(source, /property alias model: listView\.model/, "NListView must expose ListView model alias");
  assert.match(source, /property alias delegate: listView\.delegate/, "NListView must expose ListView delegate alias");
  assert.match(source, /property alias currentIndex: listView\.currentIndex/, "NListView must expose currentIndex alias");
  assert.match(source, /readonly property bool verticalScrollBarActive:[\s\S]*return listView\.contentHeight > listView\.height/, "NListView must compute scrollbar activity from ListView content");
  assertViewMethodForwarders(source, "listView", "NListView");
  assertViewMethodSignaturesAreTyped(source, "NListView");
}

const tests = [
  testNGridViewForwardsGridViewMethods,
  testNListViewForwardsListViewMethods,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
