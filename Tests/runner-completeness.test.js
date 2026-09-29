#!/usr/bin/env node

const assert = require("assert/strict");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function testUnitRunnerDiscoversEveryJavaScriptTest() {
  const runner = fs.readFileSync(path.join(repoRoot, "run-tests.sh"), "utf8");

  assert.match(runner, /rg --files Tests --glob '\*\.test\.js'/);
  assert.match(runner, /LC_ALL=C sort/);
}

function testUnitRunnerFailsWhenJavaScriptDiscoveryFails() {
  const fakeBin = fs.mkdtempSync(path.join(os.tmpdir(), "noctalia-test-runner-"));
  const fakeSort = path.join(fakeBin, "sort");
  fs.writeFileSync(fakeSort, "#!/bin/sh\nexit 42\n", { mode: 0o755 });

  try {
    const result = spawnSync(path.join(repoRoot, "run-tests.sh"), ["unit"], {
      cwd: repoRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        PATH: `${fakeBin}:${process.env.PATH}`,
      },
    });

    assert.notEqual(result.status, 0, "unit runner must fail when JavaScript discovery pipeline fails");
    assert.match(result.stderr, /Failed to discover JavaScript tests/);
    assert.doesNotMatch(result.stdout, /EVIDENCE PASS deterministic-unit/);
    assert.doesNotMatch(result.stdout, /EVIDENCE START structural-reference/);
  } finally {
    fs.rmSync(fakeBin, { recursive: true, force: true });
  }
}

function runStructuralWithFakeIndex(indexFails) {
  const fakeBin = fs.mkdtempSync(path.join(os.tmpdir(), "noctalia-structural-runner-"));
  const state = path.join(fakeBin, "index-state");
  const calls = path.join(fakeBin, "test-calls");
  fs.writeFileSync(state, "stale\n");
  fs.writeFileSync(calls, "");
  fs.writeFileSync(path.join(fakeBin, "code-index"), `#!/bin/sh
case "$1" in
  index)
    [ "$#" -eq 2 ] && [ "$2" = "$repo_root" ] || exit 23
    if [ "$TEST_INDEX_FAIL" = 1 ]; then
      echo 'index refresh failed' >&2
      exit 42
    fi
    printf 'fresh\\n' > "$TEST_INDEX_STATE"
    ;;
  list) cat "$TEST_INDEX_STATE" ;;
  *) exit 24 ;;
esac
`, { mode: 0o755 });
  fs.writeFileSync(path.join(fakeBin, "node"), `#!/bin/sh
[ "$(code-index list)" = fresh ] || { echo 'stale graph' >&2; exit 25; }
printf '%s\\n' "$(basename "$1")" >> "$TEST_NODE_CALLS"
`, { mode: 0o755 });

  try {
    const result = spawnSync(path.join(repoRoot, "run-tests.sh"), ["structural"], {
      cwd: repoRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        PATH: `${fakeBin}:${process.env.PATH}`,
        TEST_INDEX_FAIL: indexFails ? "1" : "0",
        TEST_INDEX_STATE: state,
        TEST_NODE_CALLS: calls,
      },
    });
    return { result, calls: fs.readFileSync(calls, "utf8").trim().split("\n").filter(Boolean) };
  } finally {
    fs.rmSync(fakeBin, { recursive: true, force: true });
  }
}

function testStructuralRunnerRefreshesBeforeQueryingInventory() {
  const { result, calls } = runStructuralWithFakeIndex(false);

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(calls, ["qml-function-inventory.test.js", "source-coverage.test.js"]);
  assert.match(result.stdout, /EVIDENCE PASS structural-reference/);
}

function testStructuralRunnerStopsWhenIndexRefreshFails() {
  const { result, calls } = runStructuralWithFakeIndex(true);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /index refresh failed/);
  assert.deepEqual(calls, []);
  assert.doesNotMatch(result.stdout, /EVIDENCE PASS structural-reference/);
  assert.match(result.stderr, /EVIDENCE FAIL structural-reference/);
}

for (const test of [
  testUnitRunnerDiscoversEveryJavaScriptTest,
  testUnitRunnerFailsWhenJavaScriptDiscoveryFails,
  testStructuralRunnerRefreshesBeforeQueryingInventory,
  testStructuralRunnerStopsWhenIndexRefreshFails,
]) {
  test();
  console.log(`ok ${test.name}`);
}
