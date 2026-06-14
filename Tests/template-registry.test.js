#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const registryPath = path.join(repoRoot, "Services/Theming/TemplateRegistry.qml");
const settingsPath = path.join(repoRoot, "Assets/settings-default.json");
const templatesRoot = path.join(repoRoot, "Assets/MatugenTemplates");

function readRegistry() {
  return fs.readFileSync(registryPath, "utf8");
}

function extractStringProperty(source, propertyName) {
  const pattern = new RegExp(`"${propertyName}"\\s*:\\s*"([^"]+)"`, "g");
  return [...source.matchAll(pattern)].map(match => match[1]);
}

function extractTemplateIds(source) {
  return new Set(extractStringProperty(source, "id"));
}

function assertTemplateFileExists(relativePath) {
  const templatePath = path.join(templatesRoot, relativePath);
  assert.ok(fs.existsSync(templatePath), `missing Matugen template: ${relativePath}`);
  assert.ok(fs.statSync(templatePath).size > 0, `empty Matugen template: ${relativePath}`);
}

function testTemplateRegistryAssetsExist() {
  const registry = readRegistry();

  for (const matugenPath of extractStringProperty(registry, "matugenPath")) {
    assertTemplateFileExists(matugenPath);
  }

  for (const input of extractStringProperty(registry, "input")) {
    assertTemplateFileExists(input);
  }
}

function testTemplateSettingsHaveRegistryEntries() {
  const registryIds = extractTemplateIds(readRegistry());
  const settings = JSON.parse(fs.readFileSync(settingsPath, "utf8"));

  for (const templateKey of Object.keys(settings.templates)) {
    if (templateKey === "enableUserTemplates") {
      continue;
    }

    assert.ok(registryIds.has(templateKey), `settings template is missing from TemplateRegistry: ${templateKey}`);
  }
}

testTemplateRegistryAssetsExist();
console.log("ok testTemplateRegistryAssetsExist");
testTemplateSettingsHaveRegistryEntries();
console.log("ok testTemplateSettingsHaveRegistryEntries");
