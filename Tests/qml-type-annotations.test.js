#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assertPropertyType(relativePath, propertyName, expectedType) {
  const source = readQml(relativePath);
  const declaration = new RegExp(`\\bproperty\\s+${expectedType}\\s+${propertyName}\\b`);

  assert.match(source, declaration, `${relativePath} must declare ${propertyName} as ${expectedType}`);
}

function testSliderCutoutColorsAreTyped() {
  const sliderFiles = [
    "Widgets/NSlider.qml",
    "Widgets/NColorSlider.qml",
    "Widgets/NValueSlider.qml",
  ];

  for (const sliderFile of sliderFiles) {
    assertPropertyType(sliderFile, "cutoutColor", "color");
  }
}

const tests = [
  testSliderCutoutColorsAreTyped,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
