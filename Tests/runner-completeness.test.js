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

for (const test of [
  testUnitRunnerDiscoversEveryJavaScriptTest,
  testUnitRunnerFailsWhenJavaScriptDiscoveryFails,
]) {
  test();
  console.log(`ok ${test.name}`);
}
