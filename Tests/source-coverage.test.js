#!/usr/bin/env node

const assert = require("assert/strict");
const { execFileSync } = require("child_process");
const fs = require("fs");
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
  return `${relativePath(entry)}:${entry.line_start}:${entry.name}`;
}

function qmlSourceFiles() {
  return execFileSync("rg", ["--files", "--glob", "*.qml", "--glob", "!Tests/**"], {
    cwd: repoRoot,
    encoding: "utf8",
  }).trim().split("\n").filter(Boolean);
}

function qmlFunctionDeclarations() {
  const declarations = [];

  for (const relativeFilePath of qmlSourceFiles()) {
    const absoluteFilePath = path.join(repoRoot, relativeFilePath);
    const lines = fs.readFileSync(absoluteFilePath, "utf8").split("\n");

    for (const [lineIndex, line] of lines.entries()) {
      for (const match of line.matchAll(/\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/g)) {
        declarations.push({
          file_path: absoluteFilePath,
          line_start: lineIndex + 1,
          name: match[1],
        });
      }
    }
  }

  return declarations;
}

function testQmlFunctionCoverageStaysComplete() {
  const qmlFunctions = codeIndexJson("list", "--kind", "function").filter(isQmlSourcePath);
  const uncoveredQmlFunctions = codeIndexJson("untested").filter(isQmlSourcePath);

  assert.ok(
    qmlFunctions.length >= 1200,
    "QML source function inventory must stay broad enough to catch coverage regressions",
  );
  assert.deepEqual(uncoveredQmlFunctions.map(formatSymbol), [], "QML source functions must have code-index coverage");
}

function testQmlFunctionInventoryIncludesDeclarations() {
  const qmlFunctions = codeIndexJson("list", "--kind", "function").filter(isQmlSourcePath);
  const indexedFunctions = new Set(qmlFunctions.map(formatSymbol));
  const missingDeclarations = qmlFunctionDeclarations()
    .filter(declaration => !indexedFunctions.has(formatSymbol(declaration)))
    .map(formatSymbol);

  assert.deepEqual(missingDeclarations, [], "code-index must inventory every QML function declaration");
}

function testNonTestSourceFunctionsStayCovered() {
  const uncoveredSourceFunctions = codeIndexJson("untested")
    .filter(entry => !isTestPath(entry))
    .map(formatSymbol);

  assert.deepEqual(uncoveredSourceFunctions, [], "non-test source functions must have code-index coverage");
}

const tests = [
  testQmlFunctionCoverageStaysComplete,
  testQmlFunctionInventoryIncludesDeclarations,
  testNonTestSourceFunctionsStayCovered,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
