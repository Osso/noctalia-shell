#!/usr/bin/env node

const assert = require("assert/strict");
const { execFileSync } = require("child_process");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function codeIndexJson(...args) {
  return JSON.parse(execFileSync("code-index", args, {
    cwd: repoRoot,
    encoding: "utf8",
    maxBuffer: 50 * 1024 * 1024,
  }));
}

function relativePath(entry) {
  return path.relative(repoRoot, entry.file_path);
}

function isTestPath(entry) {
  return relativePath(entry).startsWith("Tests/");
}

function isQmlSourcePath(entry) {
  return relativePath(entry).endsWith(".qml") && !isTestPath(entry);
}

function formatSymbol(entry) {
  return `${relativePath(entry)}:${entry.name}`;
}

function testQmlFunctionCoverageStaysComplete() {
  const qmlFunctions = codeIndexJson("list", "--kind", "function").filter(isQmlSourcePath);
  const uncoveredQmlFunctions = codeIndexJson("untested").filter(isQmlSourcePath);

  assert.ok(
    qmlFunctions.length >= 1000,
    "QML source function inventory must stay broad enough to catch coverage regressions",
  );
  assert.deepEqual(uncoveredQmlFunctions.map(formatSymbol), [], "QML source functions must have code-index coverage");
}

function testNonTestSourceFunctionsStayCovered() {
  const uncoveredSourceFunctions = codeIndexJson("untested")
    .filter(entry => !isTestPath(entry))
    .map(formatSymbol);

  assert.deepEqual(uncoveredSourceFunctions, [], "non-test source functions must have code-index coverage");
}

const tests = [
  testQmlFunctionCoverageStaysComplete,
  testNonTestSourceFunctionsStayCovered,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
