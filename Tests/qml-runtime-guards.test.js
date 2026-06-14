#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function extractFunctionBody(source, functionName) {
  const marker = `function ${functionName}(`;
  const markerIndex = source.indexOf(marker);
  assert.notEqual(markerIndex, -1, `missing function: ${functionName}`);

  const blockStart = source.indexOf("{", markerIndex);
  let depth = 0;

  for (let index = blockStart; index < source.length; index++) {
    const char = source[index];

    if (char === "{") {
      depth++;
    } else if (char === "}") {
      depth--;
      if (depth === 0) {
        return source.slice(blockStart, index + 1);
      }
    }
  }

  throw new Error(`unterminated function: ${functionName}`);
}

function testOsdBrightnessHandlerRejectsInvalidValues() {
  const source = readQml("Modules/OSD/OSD.qml");
  const body = extractFunctionBody(source, "onBrightnessChanged");

  assert.match(body, /BrightnessParsing\.isValidBrightnessRatio\(newBrightness\)/);
  assert.match(body, /return;/);
  assert.match(body, /root\.currentBrightness = newBrightness/);
}

const tests = [
  testOsdBrightnessHandlerRejectsInvalidValues,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
