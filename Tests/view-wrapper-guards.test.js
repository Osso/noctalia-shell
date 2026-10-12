#!/usr/bin/env node

const assert = require("assert/strict");
const path = require("path");
const { spawnSync } = require("child_process");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function executeMethod(source, targetId, view, name, args, values) {
  const body = extractFunctionBody(source, name);
  const execute = new Function("ctx", ...args, `with (ctx) ${body}`);
  return execute({ [targetId]: view }, ...values);
}

function testViewWrapperMethodArgumentsAndResults() {
  for (const [file, targetId] of [
    ["NGridView", "gridView"],
    ["NListView", "listView"],
  ]) {
    const source = readQml(`Widgets/${file}.qml`);
    const view = {
      position: null,
      layoutVersion: 0,
      velocity: null,
      positionViewAtIndex(index, mode) {
        this.position = [index, mode];
      },
      positionViewAtBeginning() {
        this.position = "beginning";
      },
      positionViewAtEnd() {
        this.position = "end";
      },
      forceLayout() {
        this.layoutVersion += 1;
      },
      cancelFlick() {
        this.velocity = [0, 0];
      },
      flick(x, y) {
        this.velocity = [x, y];
      },
      indexAt(x, y) {
        return x === 12.5 && y === 47.25 ? 7 : -1;
      },
      itemAt(x, y) {
        return x === 12.5 && y === 47.25 ? item : null;
      },
      itemAtIndex(index) {
        return index === 7 ? item : null;
      },
    };
    const item = { label: "seventh item" };
    const execute = (name, args = [], values = []) =>
      executeMethod(source, targetId, view, name, args, values);
    execute("positionViewAtIndex", ["index", "mode"], [7, 3]);
    assert.deepEqual(view.position, [7, 3]);
    execute("positionViewAtBeginning");
    assert.equal(view.position, "beginning");
    execute("positionViewAtEnd");
    assert.equal(view.position, "end");
    execute("forceLayout");
    assert.equal(view.layoutVersion, 1);
    execute("flick", ["xVelocity", "yVelocity"], [-123.5, 456.25]);
    assert.deepEqual(view.velocity, [-123.5, 456.25]);
    execute("cancelFlick");
    assert.deepEqual(view.velocity, [0, 0]);
    assert.equal(execute("indexAt", ["x", "y"], [12.5, 47.25]), 7);
    assert.equal(execute("indexAt", ["x", "y"], [0, 0]), -1);
    assert.equal(execute("itemAt", ["x", "y"], [12.5, 47.25]), item);
    assert.equal(execute("itemAt", ["x", "y"], [0, 0]), null);
    assert.equal(execute("itemAtIndex", ["index"], [7]), item);
    assert.equal(execute("itemAtIndex", ["index"], [-1]), null);
  }
}

function testViewWrappersOffscreenContract() {
  const result = spawnSync(
    "python3",
    [path.join(__dirname, "grid-list-warnings.test.py"), "runtime"],
    {
      encoding: "utf8",
      timeout: 90000,
      env: { ...process.env, QT_FORCE_STDERR_LOGGING: "1" },
    },
  );
  assert.ifError(result.error);
  const output = result.stdout + result.stderr;
  process.stdout.write(output);
  assert.equal(result.status, 0, output);
  assert.match(
    output,
    /15 passed, 0 failed/,
    "grid/list aliases, selection, bounds, wrapping and scrollbar checks must finish",
  );
}

const tests = [
  testViewWrapperMethodArgumentsAndResults,
  testViewWrappersOffscreenContract,
];
for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
