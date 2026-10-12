#!/usr/bin/env node

const assert = require("assert/strict");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const metaTestFiles = new Set([
  "Tests/changelog-lint-streams.test.py",
  "Tests/ipc-idle-services-harness-lint.test.py",
  "Tests/qml-static-fixtures.test.py",
  "Tests/qml-static-imports.test.py",
  "Tests/qml-static-runtime-fixtures.test.py",
  "Tests/service-cohort-harness-lint.test.py",
  "Tests/unit-parent-settings-isolation.test.py",
  "Tests/qml-function-inventory.test.js",
  "Tests/qml-test-utils.test.js",
  "Tests/runner-completeness.test.js",
  "Tests/quickshell-regression.test.sh",
  "Tests/test-runner-categories.test.sh",
]);

// Reviewed indirect test references, not records of test execution.
const indirectTestEvidence = [
  ...["NGridView", "NListView"].flatMap(widget => [
    {
      source: `Widgets/${widget}.qml`,
      functions: [
        "positionViewAtIndex",
        "positionViewAtBeginning",
        "positionViewAtEnd",
        "forceLayout",
        "cancelFlick",
        "flick",
        "indexAt",
        "itemAt",
        "itemAtIndex",
      ],
      runner: "Tests/view-wrapper-guards.test.js",
      caseFile: "Tests/view-wrapper-guards.test.js",
      caseName: "testViewWrapperMethodArgumentsAndResults",
      proof: "Executable behavior coverage",
    },
    {
      source: `Widgets/${widget}.qml`,
      functions: ["incrementCurrentIndex", "decrementCurrentIndex"],
      runner: "Tests/grid-list-warnings.test.py",
      caseFile: "Tests/Qml/GridListWarningsHarness.qml",
      caseName: "test_index_boundaries",
      proof: "QML lifecycle integration",
    },
  ]),
  {
    source: "Commons/Settings.qml",
    functions: ["scheduleSave"],
    runner: "Tests/residual-singleton-owners.test.py",
    caseFile: "Tests/residual-singleton-owners.test.py",
    caseName: "runtime",
    proof: "QML lifecycle integration",
  },
  ...["TaskbarGrouped", "Workspace"].flatMap(widget => [
    {
      source: `Modules/Bar/Widgets/${widget}.qml`,
      functions: [
        "workspaceUrgencyKey",
        "displayedUrgentForWorkspace",
        "setDisplayedUrgency",
      ],
      runner: widget === "TaskbarGrouped"
        ? "Tests/taskbar-grouped-warnings.test.py"
        : "Tests/qml-runtime-guards.test.js",
      caseFile: widget === "TaskbarGrouped"
        ? "Tests/Qml/TaskbarGroupedHarness.qml"
        : "Tests/qml-runtime-guards.test.js",
      caseName: widget === "TaskbarGrouped"
        ? "test_urgency_cooldown_survives_rebuild"
        : "testWorkspaceUrgentBadgeHasCooldown",
      proof: "QML lifecycle integration",
    },
    {
      source: `Modules/Bar/Widgets/${widget}.qml`,
      functions: ["triggerUnifiedWave"],
      runner: "Tests/qml-runtime-guards.test.js",
      caseFile: "Tests/qml-runtime-guards.test.js",
      caseName: "testFocusedWorkspaceBurstOnlyRunsOnFocusChange",
      proof: "Executable behavior coverage",
    },
  ]),
  {
    source: "Modules/Bar/Widgets/Tray.qml",
    functions: ["bindTrayContext"],
    runner: "Tests/tray-widget-reload.test.py",
    caseFile: "Tests/tray-widget-reload.test.py",
    caseName: "runtime",
    proof: "QML lifecycle integration",
  },
  {
    source: "Modules/MainScreen/PopupMenuWindow.qml",
    functions: ["initializeTrayMenu", "hideContent"],
    runner: "Tests/popup-menu-window-warnings.test.py",
    caseFile: "Tests/popup-menu-window-warnings.test.py",
    caseName: "exerciseLifecycle",
    proof: "QML lifecycle integration",
  },
  {
    source: "Modules/Panels/WiFi/WiFiNetworksList.qml",
    functions: ["submitPassword", "cancelPassword"],
    runner: "Tests/wifi-networks-list-warnings.test.py",
    caseFile: "Tests/Qml/WiFiNetworksListWarningsHarness.qml",
    caseName: "assertPassword",
    proof: "QML lifecycle integration",
  },
];

function referenceKey(root, entry) {
  return `${path.relative(root, entry.file_path)}:${entry.name}`;
}

function readEvidenceCase(root, evidence) {
  assert.match(evidence.runner, /^Tests\/.*\.test\.(?:js|py|sh)$/, "evidence runner must be an executable test path");
  assert.ok(evidence.caseFile.startsWith("Tests/"), "evidence case must be a test path");
  const proofLevels = ["QML lifecycle integration", "Executable behavior coverage"];
  assert.ok(proofLevels.includes(evidence.proof), "evidence must distinguish proof level");
  const runner = fs.readFileSync(path.join(root, evidence.runner), "utf8");
  const caseSource = fs.readFileSync(path.join(root, evidence.caseFile), "utf8");
  if (evidence.runner !== evidence.caseFile) {
    assert.ok(runner.includes(evidence.caseFile), `runner must stage ${evidence.caseFile}`);
  }
  const declaration = new RegExp(
    `(?:\\bfunction\\s+${evidence.caseName}\\s*\\(|^def\\s+${evidence.caseName}\\s*\\()`,
    "m",
  );
  assert.match(caseSource, declaration, `missing evidence case ${evidence.caseFile}:${evidence.caseName}`);
}

function readEvidenceReferences(root, inventory, mappings) {
  const references = new Set();
  for (const evidence of mappings) {
    readEvidenceCase(root, evidence);
    const source = fs.readFileSync(path.join(root, evidence.source), "utf8");
    for (const name of evidence.functions) {
      const key = `${evidence.source}:${name}`;
      const declarations = inventory.filter(entry => referenceKey(root, entry) === key);
      assert.equal(declarations.length, 1, `source function must be uniquely inventoried: ${key}`);
      assert.match(source, new RegExp(`\\bfunction\\s+${name}\\s*\\(`), `missing source function ${key}`);
      references.add(key);
    }
  }
  return references;
}

function functionsWithoutEvidence(root, entries, references) {
  return entries.filter(entry => !references.has(referenceKey(root, entry)));
}

let sourceInventory;
function readSourceInventory() {
  if (sourceInventory) return sourceInventory;
  const functions = codeIndexJson("list", "--kind", "function");
  const unreferenced = codeIndexJson("untested");
  const references = readEvidenceReferences(repoRoot, functions, indirectTestEvidence);
  sourceInventory = {
    functions,
    unreferenced: functionsWithoutEvidence(repoRoot, unreferenced, references),
  };
  const accountedCount = unreferenced.length - sourceInventory.unreferenced.length;
  console.log(`indirect references: ${references.size} validated; ${accountedCount} graph gaps accounted`);
  for (const evidence of indirectTestEvidence) {
    console.log(
      `reference ${evidence.source} [${evidence.functions.join(", ")}] -> `
      + `${evidence.runner} ${evidence.caseFile}:${evidence.caseName} `
      + `(${evidence.proof}; execution not established by inventory)`,
    );
  }
  return sourceInventory;
}

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
  const inventory = readSourceInventory();
  const qmlFunctions = inventory.functions.filter(isQmlSourcePath);
  const uncoveredQmlFunctions = inventory.unreferenced.filter(isQmlSourcePath);

  assert.ok(
    qmlFunctions.length >= 1200,
    "QML source function inventory must stay broad enough to catch structural-reference regressions",
  );
  assert.deepEqual(uncoveredQmlFunctions.map(formatSymbol), [], "QML source functions must have code-index references or validated indirect test evidence");
}

function testQmlFunctionInventoryIncludesDeclarations() {
  const qmlFunctions = readSourceInventory().functions.filter(isQmlSourcePath);
  const indexedFunctions = new Set(qmlFunctions.map(formatSymbol));
  const missingDeclarations = qmlFunctionDeclarations()
    .filter(declaration => !indexedFunctions.has(formatSymbol(declaration)))
    .map(formatSymbol);

  assert.deepEqual(missingDeclarations, [], "code-index must inventory every QML function declaration");
}

function testNonTestSourceFunctionsStayStructurallyReferenced() {
  const uncoveredSourceFunctions = readSourceInventory().unreferenced
    .filter(entry => !isTestPath(entry))
    .map(formatSymbol);

  assert.deepEqual(uncoveredSourceFunctions, [], "non-test source functions must have code-index references or validated indirect test evidence");
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

function testExplicitEvidenceDiscovery() {
  assert.equal(typeof readEvidenceReferences, "function", "explicit mapping discovery must exist");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "noctalia-reference-fixture-"));
  const write = (file, text) => {
    fs.mkdirSync(path.dirname(path.join(directory, file)), { recursive: true });
    fs.writeFileSync(path.join(directory, file), text);
  };
  try {
    write("Widget.qml", "function scheduleSave() { timer.start(); }\nfunction untouched() {}\n");
    write("Other.qml", "function scheduleSave() {}\n");
    write("Tests/runner.test.py", 'def runtime(directory):\n    stage("Tests/Qml/Harness.qml", directory)\n');
    write("Tests/Qml/Harness.qml", "function test_deferred_persistence() { settings.volume = 17; compare(saved.volume, 17); }\n");
    const inventory = [
      { file_path: path.join(directory, "Widget.qml"), name: "scheduleSave", line_start: 1 },
      { file_path: path.join(directory, "Widget.qml"), name: "untouched", line_start: 2 },
      { file_path: path.join(directory, "Other.qml"), name: "scheduleSave", line_start: 1 },
    ];
    const mapping = {
      source: "Widget.qml",
      functions: ["scheduleSave"],
      runner: "Tests/runner.test.py",
      caseFile: "Tests/Qml/Harness.qml",
      caseName: "test_deferred_persistence",
      proof: "QML lifecycle integration",
    };
    const references = readEvidenceReferences(directory, inventory, [mapping]);
    assert.deepEqual([...references], ["Widget.qml:scheduleSave"]);
    assert.deepEqual(functionsWithoutEvidence(directory, inventory, references), inventory.slice(1));
    assert.throws(() => readEvidenceReferences(directory, inventory, [{ ...mapping, caseName: "test_removed" }]), /missing evidence case/);
    assert.throws(() => readEvidenceReferences(directory, inventory, [{ ...mapping, runner: "Tests/missing.test.py" }]), /ENOENT/);
    assert.throws(() => readEvidenceReferences(directory, inventory, [{ ...mapping, functions: ["removed"] }]), /source function/);
    write("Tests/runner.test.py", "def runtime(directory):\n    pass\n");
    assert.throws(() => readEvidenceReferences(directory, inventory, [mapping]), /runner must stage/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

const tests = [
  testExplicitEvidenceDiscovery,
  testQmlFunctionsStayStructurallyReferencedByTests,
  testQmlFunctionInventoryIncludesDeclarations,
  testNonTestSourceFunctionsStayStructurallyReferenced,
  testAllTestFilesAreNamedBySpecs,
  testNonMetaTestFilesAreNamedByFeatureSpecs,
  testMetaTestAllowlistStaysIntentional,
  testTestingSpecDistinguishesEvidenceCategories,
];

const selectedTests = process.argv.includes("--discovery-only") ? [testExplicitEvidenceDiscovery] : tests;

for (const test of selectedTests) {
  test();
  console.log(`ok ${test.name}`);
}
