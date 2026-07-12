#!/usr/bin/env node

const assert = require("assert/strict");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const metaTestFiles = new Set([
  "Tests/qml-function-inventory.test.js",
  "Tests/runner-completeness.test.js",
  "Tests/quickshell-regression.test.sh",
  "Tests/test-runner-categories.test.sh",
]);

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

function testFiles() {
  return execFileSync("rg", ["--files", "Tests", "--glob", "*.test.js", "--glob", "*.test.sh", "--glob", "*.test.py"], {
    cwd: repoRoot,
    encoding: "utf8",
  }).trim().split("\n").filter(Boolean).sort();
}

function specFiles() {
  return fs.readdirSync(path.join(repoRoot, "docs", "specs"))
    .filter(fileName => fileName.endsWith(".md"))
    .map(fileName => path.join(repoRoot, "docs", "specs", fileName));
}

function specCorpus() {
  return specFiles()
    .map(filePath => fs.readFileSync(filePath, "utf8"))
    .join("\n");
}

function featureSpecCorpus() {
  return specFiles()
    .filter(filePath => path.basename(filePath) !== "testing.md")
    .map(filePath => fs.readFileSync(filePath, "utf8"))
    .join("\n");
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

function testQmlFunctionsStayStructurallyReferencedByTests() {
  const qmlFunctions = codeIndexJson("list", "--kind", "function").filter(isQmlSourcePath);
  const uncoveredQmlFunctions = codeIndexJson("untested").filter(isQmlSourcePath);

  assert.ok(
    qmlFunctions.length >= 1200,
    "QML source function inventory must stay broad enough to catch structural-reference regressions",
  );
  assert.deepEqual(uncoveredQmlFunctions.map(formatSymbol), [], "QML source functions must have structural references from tests according to code-index");
}

function testQmlFunctionInventoryIncludesDeclarations() {
  const qmlFunctions = codeIndexJson("list", "--kind", "function").filter(isQmlSourcePath);
  const indexedFunctions = new Set(qmlFunctions.map(formatSymbol));
  const missingDeclarations = qmlFunctionDeclarations()
    .filter(declaration => !indexedFunctions.has(formatSymbol(declaration)))
    .map(formatSymbol);

  assert.deepEqual(missingDeclarations, [], "code-index must inventory every QML function declaration");
}

function testNonTestSourceFunctionsStayStructurallyReferenced() {
  const uncoveredSourceFunctions = codeIndexJson("untested")
    .filter(entry => !isTestPath(entry))
    .map(formatSymbol);

  assert.deepEqual(uncoveredSourceFunctions, [], "non-test source functions must have structural references from tests according to code-index");
}

function testAllTestFilesAreNamedBySpecs() {
  const specs = specCorpus();
  const unmappedTestFiles = testFiles().filter(testFile => !specs.includes(testFile));

  assert.deepEqual(unmappedTestFiles, [], "every executable test file must be named by a docs/specs contract");
}

function testNonMetaTestFilesAreNamedByFeatureSpecs() {
  const featureSpecs = featureSpecCorpus();
  const unmappedFeatureTests = testFiles()
    .filter(testFile => !metaTestFiles.has(testFile))
    .filter(testFile => !featureSpecs.includes(testFile));

  assert.deepEqual(unmappedFeatureTests, [], "non-meta tests must be named by feature specs, not only the testing spec");
}

function testMetaTestAllowlistStaysIntentional() {
  const featureSpecs = featureSpecCorpus();
  const metaOnlyTests = testFiles()
    .filter(testFile => !featureSpecs.includes(testFile));

  assert.deepEqual(metaOnlyTests, [...metaTestFiles].sort(), "only explicitly allowlisted meta tests may skip feature specs");
}

function testTestingSpecDistinguishesEvidenceCategories() {
  const testingSpec = fs.readFileSync(path.join(repoRoot, "docs", "specs", "testing.md"), "utf8");

  for (const category of ["Structural reference coverage", "Executable behavior coverage", "QML lifecycle integration", "Live host probes"]) {
    assert.ok(testingSpec.includes(category), `testing spec must name evidence category: ${category}`);
  }
  assert.match(testingSpec, /does not prove runtime execution, branch coverage, QML lifecycle behavior, or integration behavior/);
}

const tests = [
  testQmlFunctionsStayStructurallyReferencedByTests,
  testQmlFunctionInventoryIncludesDeclarations,
  testNonTestSourceFunctionsStayStructurallyReferenced,
  testAllTestFilesAreNamedBySpecs,
  testNonMetaTestFilesAreNamedByFeatureSpecs,
  testMetaTestAllowlistStaysIntentional,
  testTestingSpecDistinguishesEvidenceCategories,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
