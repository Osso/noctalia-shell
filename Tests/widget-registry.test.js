#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function extractPropertyObjectBody(source, propertyName) {
  const marker = `property var ${propertyName}: ({`;
  const markerIndex = source.indexOf(marker);
  assert.notEqual(markerIndex, -1, `missing property object: ${propertyName}`);

  const startIndex = source.indexOf("{", markerIndex);
  let depth = 0;
  let quote = null;
  let escaped = false;

  for (let index = startIndex; index < source.length; index++) {
    const char = source[index];

    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === quote) {
        quote = null;
      }
      continue;
    }

    if (char === "\"" || char === "'") {
      quote = char;
      continue;
    }

    if (char === "{") {
      depth++;
    } else if (char === "}") {
      depth--;
      if (depth === 0) {
        return source.slice(startIndex, index + 1);
      }
    }
  }

  throw new Error(`unterminated property object: ${propertyName}`);
}

function extractTopLevelStringPairs(objectBody) {
  const pairs = [];
  let depth = 0;
  let quote = null;
  let escaped = false;
  let token = "";
  let collectingToken = false;
  let pendingKey = null;
  let expectingValue = false;
  let valueToken = "";

  for (let index = 0; index < objectBody.length; index++) {
    const char = objectBody[index];

    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === quote) {
        quote = null;

        if (collectingToken && depth === 1) {
          if (expectingValue && pendingKey !== null) {
            pairs.push([pendingKey, token]);
            pendingKey = null;
            expectingValue = false;
          } else if (pendingKey === null) {
            pendingKey = token;
          }
        }

        collectingToken = false;
      } else if (collectingToken) {
        token += char;
      }
      continue;
    }

    if (char === "\"" || char === "'") {
      quote = char;
      collectingToken = depth === 1;
      token = "";
      continue;
    }

    if (char === "{") {
      depth++;
      continue;
    }

    if (char === "}") {
      if (depth === 1 && pendingKey !== null) {
        pairs.push([pendingKey, valueToken.trim() || null]);
        pendingKey = null;
        expectingValue = false;
        valueToken = "";
      }
      depth--;
      continue;
    }

    if (depth === 1 && pendingKey !== null && char === ":") {
      expectingValue = true;
      valueToken = "";
      continue;
    }

    if (depth === 1 && char === "," && pendingKey !== null) {
      pairs.push([pendingKey, valueToken.trim() || null]);
      pendingKey = null;
      expectingValue = false;
      valueToken = "";
      continue;
    }

    if (depth === 1 && expectingValue) {
      valueToken += char;
    }
  }

  return pairs;
}

function extractComponentNames(source) {
  return [...source.matchAll(/property Component (\w+)Component:/g)].map(match => match[1]);
}

function keysFromPairs(pairs) {
  return pairs.map(([key]) => key);
}

function assertSameMembers(actual, expected, message) {
  assert.deepEqual([...actual].sort(), [...expected].sort(), message);
}

function testBarWidgetRegistryMetadata() {
  const source = readQml("Services/UI/BarWidgetRegistry.qml");
  const widgetPairs = extractTopLevelStringPairs(extractPropertyObjectBody(source, "widgets"));
  const widgetKeys = keysFromPairs(widgetPairs);
  const componentNames = extractComponentNames(source);
  const settingsKeys = keysFromPairs(extractTopLevelStringPairs(extractPropertyObjectBody(source, "widgetSettingsMap")));
  const metadataKeys = keysFromPairs(extractTopLevelStringPairs(extractPropertyObjectBody(source, "widgetMetadata")));

  assert.equal(widgetKeys.length, 30);
  assert.equal(new Set(widgetKeys).size, widgetKeys.length, "bar widget ids must be unique");
  assertSameMembers(
    widgetPairs.map(([, component]) => component.replace(/Component$/, "")),
    componentNames,
    "bar widgets must reference declared components",
  );
  assertSameMembers(settingsKeys, metadataKeys, "bar settings and metadata must cover the same widgets");
  assert.ok(widgetKeys.includes("Brightness"));
  assert.ok(widgetKeys.includes("LockKeys"));
  assert.ok(widgetKeys.includes("VPN"));
  assert.ok(metadataKeys.includes("CustomButton"));
}

function testControlCenterWidgetRegistryMetadata() {
  const source = readQml("Services/UI/ControlCenterWidgetRegistry.qml");
  const widgetPairs = extractTopLevelStringPairs(extractPropertyObjectBody(source, "widgets"));
  const widgetKeys = keysFromPairs(widgetPairs);
  const componentNames = extractComponentNames(source);
  const metadataKeys = keysFromPairs(extractTopLevelStringPairs(extractPropertyObjectBody(source, "widgetMetadata")));

  assert.equal(widgetKeys.length, 10);
  assert.equal(new Set(widgetKeys).size, widgetKeys.length, "control center widget ids must be unique");
  assertSameMembers(
    widgetPairs.map(([, component]) => component.replace(/Component$/, "")),
    componentNames,
    "control center widgets must reference declared components",
  );
  assert.deepEqual(metadataKeys, ["CustomButton"]);
  assert.ok(widgetKeys.includes("Notifications"));
  assert.ok(widgetKeys.includes("WallpaperSelector"));
}

const tests = [
  testBarWidgetRegistryMetadata,
  testControlCenterWidgetRegistryMetadata,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
