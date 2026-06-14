#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const defaultSettings = JSON.parse(fs.readFileSync(path.join(repoRoot, "Assets/settings-default.json"), "utf8"));

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

function configuredWidgetIds(sections) {
  return Object.values(sections)
    .flat()
    .map(widget => widget.id);
}

function configuredCardIds(cards) {
  return cards.map(card => card.id);
}

function switchCaseIdsAfter(source, precedingMarker, switchExpression) {
  const markerStart = source.indexOf(precedingMarker);
  assert.notEqual(markerStart, -1, `missing marker before switch: ${precedingMarker}`);

  const switchStart = source.indexOf(`switch (${switchExpression})`, markerStart);
  assert.notEqual(switchStart, -1, `missing switch for ${switchExpression} after ${precedingMarker}`);

  const blockStart = source.indexOf("{", switchStart);
  let depth = 0;

  for (let index = blockStart; index < source.length; index++) {
    const char = source[index];

    if (char === "{") {
      depth++;
    } else if (char === "}") {
      depth--;
      if (depth === 0) {
        const block = source.slice(blockStart, index + 1);
        return Array.from(block.matchAll(/case "([^"]+)":/g), match => match[1]);
      }
    }
  }

  throw new Error(`unterminated switch for ${switchExpression}`);
}

function quotedIds(source) {
  return new Set(Array.from(source.matchAll(/"([a-z][a-z0-9-]*-card)"/g), match => match[1]));
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

function testDefaultBarWidgetsExistInRegistry() {
  const source = readQml("Services/UI/BarWidgetRegistry.qml");
  const widgetKeys = new Set(keysFromPairs(extractTopLevelStringPairs(extractPropertyObjectBody(source, "widgets"))));
  const configuredIds = configuredWidgetIds(defaultSettings.bar.widgets);

  assert.equal(configuredIds.length, 12);
  for (const widgetId of configuredIds) {
    assert.ok(widgetKeys.has(widgetId), `default bar widget is missing from BarWidgetRegistry: ${widgetId}`);
  }
}

function testDefaultControlCenterShortcutsExistInRegistry() {
  const source = readQml("Services/UI/ControlCenterWidgetRegistry.qml");
  const widgetKeys = new Set(keysFromPairs(extractTopLevelStringPairs(extractPropertyObjectBody(source, "widgets"))));
  const configuredIds = configuredWidgetIds(defaultSettings.controlCenter.shortcuts);

  assert.equal(configuredIds.length, 8);
  for (const widgetId of configuredIds) {
    assert.ok(widgetKeys.has(widgetId), `default control center shortcut is missing from ControlCenterWidgetRegistry: ${widgetId}`);
  }
}

function testDefaultControlCenterCardsAreLoadable() {
  const source = readQml("Modules/Panels/ControlCenter/ControlCenterPanel.qml");
  const loadableIds = new Set(switchCaseIdsAfter(source, "sourceComponent:", "modelData.id"));
  const sizedIds = new Set(switchCaseIdsAfter(source, "Layout.preferredHeight:", "modelData.id"));
  const configuredIds = configuredCardIds(defaultSettings.controlCenter.cards);

  assert.equal(configuredIds.length, 5);
  for (const cardId of configuredIds) {
    assert.ok(loadableIds.has(cardId), `default control center card is missing from ControlCenterPanel loader: ${cardId}`);
    assert.ok(sizedIds.has(cardId), `default control center card is missing from ControlCenterPanel height switch: ${cardId}`);
  }
}

function testDefaultCalendarCardsAreLoadableOrMigrated() {
  const panelSource = readQml("Modules/Panels/Clock/ClockPanel.qml");
  const migrationSource = readQml("Commons/Migrations/Migration26.qml");
  const loadableIds = new Set(switchCaseIdsAfter(panelSource, "sourceComponent:", "modelData.id"));
  const migrationIds = quotedIds(migrationSource);
  const configuredIds = configuredCardIds(defaultSettings.calendar.cards);

  assert.equal(configuredIds.length, 4);
  for (const cardId of configuredIds) {
    assert.ok(
      loadableIds.has(cardId) || migrationIds.has(cardId),
      `default calendar card is neither loadable nor covered by Migration26: ${cardId}`,
    );
  }
  assert.ok(loadableIds.has("calendar-header-card"), "ClockPanel must load Migration26 calendar-header-card");
  assert.ok(loadableIds.has("calendar-month-card"), "ClockPanel must load Migration26 calendar-month-card");
  assert.ok(migrationIds.has("banner-card"), "Migration26 must handle legacy banner-card");
  assert.ok(migrationIds.has("calendar-card"), "Migration26 must handle legacy calendar-card");
}

const tests = [
  testBarWidgetRegistryMetadata,
  testControlCenterWidgetRegistryMetadata,
  testDefaultBarWidgetsExistInRegistry,
  testDefaultControlCenterShortcutsExistInRegistry,
  testDefaultControlCenterCardsAreLoadable,
  testDefaultCalendarCardsAreLoadableOrMigrated,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
