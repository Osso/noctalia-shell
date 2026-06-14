#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const repoRoot = path.resolve(__dirname, "..");
const settings = JSON.parse(fs.readFileSync(path.join(repoRoot, "Assets/settings-default.json"), "utf8"));
const settingsReferencePattern = /Settings\.data((?:\.[A-Za-z_][A-Za-z0-9_]*)+)/g;

function qmlFiles() {
  return execFileSync("rg", ["--files", "--glob", "*.qml"], {
    cwd: repoRoot,
    encoding: "utf8",
  }).trim().split("\n").filter(Boolean);
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function lineAndColumn(source, index) {
  const prefix = source.slice(0, index);
  const lines = prefix.split("\n");
  return {
    line: lines.length,
    column: lines[lines.length - 1].length + 1,
  };
}

function validateSettingsReference(file, source, index, chain) {
  let value = settings;
  const accepted = [];

  for (const segment of chain) {
    if (isPlainObject(value) && Object.prototype.hasOwnProperty.call(value, segment)) {
      value = value[segment];
      accepted.push(segment);
      continue;
    }

    if (isPlainObject(value)) {
      const location = lineAndColumn(source, index);
      return `${file}:${location.line}:${location.column} missing Settings.data.${chain.join(".")} at ${segment} after ${accepted.join(".") || "<root>"}`;
    }

    return null;
  }

  return null;
}

function testQmlSettingsReferencesExistInDefaults() {
  const failures = [];
  let checkedReferences = 0;

  for (const file of qmlFiles()) {
    if (file === "Commons/Settings.qml") {
      continue;
    }

    const source = fs.readFileSync(path.join(repoRoot, file), "utf8");
    let match;
    while ((match = settingsReferencePattern.exec(source)) !== null) {
      checkedReferences++;
      const chain = match[1].slice(1).split(".");
      const failure = validateSettingsReference(file, source, match.index, chain);
      if (failure) {
        failures.push(failure);
      }
    }
  }

  assert.equal(failures.length, 0, failures.join("\n"));
  assert.ok(checkedReferences > 200, `expected broad Settings.data coverage, got ${checkedReferences}`);
}

testQmlSettingsReferencesExistInDefaults();
console.log("ok testQmlSettingsReferencesExistInDefaults");
