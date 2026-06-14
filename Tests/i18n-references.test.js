#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const repoRoot = path.resolve(__dirname, "..");
const translations = JSON.parse(fs.readFileSync(path.join(repoRoot, "Assets/Translations/en.json"), "utf8"));
const literalTranslationPattern = /I18n\.tr\(\s*["']([^"']+)["']/g;

function qmlFiles() {
  return execFileSync("rg", ["--files", "--glob", "*.qml"], {
    cwd: repoRoot,
    encoding: "utf8",
  }).trim().split("\n").filter(Boolean);
}

function lineAndColumn(source, index) {
  const prefix = source.slice(0, index);
  const lines = prefix.split("\n");
  return {
    line: lines.length,
    column: lines[lines.length - 1].length + 1,
  };
}

function hasTranslationKey(key) {
  let value = translations;
  for (const segment of key.split(".")) {
    if (value && typeof value === "object" && Object.prototype.hasOwnProperty.call(value, segment)) {
      value = value[segment];
      continue;
    }
    return false;
  }
  return typeof value === "string";
}

function isDynamicKeyPrefix(source, match) {
  const nextCharacter = source.slice(match.index + match[0].length).trimStart()[0];
  return nextCharacter === "+";
}

function testQmlLiteralTranslationReferencesExist() {
  const failures = [];
  let checkedReferences = 0;

  for (const file of qmlFiles()) {
    const source = fs.readFileSync(path.join(repoRoot, file), "utf8");
    let match;
    while ((match = literalTranslationPattern.exec(source)) !== null) {
      if (isDynamicKeyPrefix(source, match)) {
        continue;
      }

      checkedReferences++;
      const key = match[1];
      if (!hasTranslationKey(key)) {
        const location = lineAndColumn(source, match.index);
        failures.push(`${file}:${location.line}:${location.column} missing translation key: ${key}`);
      }
    }
  }

  assert.equal(failures.length, 0, failures.join("\n"));
  assert.ok(checkedReferences > 500, `expected broad literal translation reference coverage, got ${checkedReferences}`);
}

testQmlLiteralTranslationReferencesExist();
console.log("ok testQmlLiteralTranslationReferencesExist");
