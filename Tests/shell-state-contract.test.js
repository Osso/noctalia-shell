#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const shellStateSource = fs.readFileSync(path.join(repoRoot, "Commons/ShellState.qml"), "utf8");

const expectedStateKeys = [
  "display",
  "notificationsState",
  "changelogState",
  "colorSchemesList",
];

function extractJsonAdapterBody(source) {
  const adapterStart = source.indexOf("adapter: JsonAdapter {");
  assert.notEqual(adapterStart, -1, "ShellState must define a JsonAdapter");

  const startIndex = source.indexOf("{", adapterStart);
  let depth = 0;
  for (let index = startIndex; index < source.length; index++) {
    const char = source[index];
    if (char === "{") {
      depth++;
    } else if (char === "}") {
      depth--;
      if (depth === 0) {
        return source.slice(startIndex, index + 1);
      }
    }
  }

  throw new Error("unterminated ShellState JsonAdapter");
}

function extractAdapterKeys(adapterBody) {
  return [...adapterBody.matchAll(/property var (\w+):/g)].map(match => match[1]);
}

function assertContains(source, pattern, message) {
  assert.match(source, pattern, message);
}

function testShellStateAdapterContract() {
  const adapterBody = extractJsonAdapterBody(shellStateSource);
  const adapterKeys = extractAdapterKeys(adapterBody);

  assert.deepEqual(adapterKeys.sort(), [...expectedStateKeys].sort());

  assertContains(adapterBody, /notificationsState:[\s\S]*lastSeenTs:\s*0/, "notificationsState must default lastSeenTs");
  assertContains(adapterBody, /changelogState:[\s\S]*lastSeenVersion:\s*""/, "changelogState must default lastSeenVersion");
  assertContains(adapterBody, /colorSchemesList:[\s\S]*schemes:\s*\[\],[\s\S]*timestamp:\s*0/, "colorSchemesList must default schemes and timestamp");

  for (const key of expectedStateKeys) {
    assertContains(shellStateSource, new RegExp(`adapter\\.${key}\\b`), `${key} must be read or written through adapter`);
  }

  assertContains(shellStateSource, /function setDisplay\(displayData\)/, "display setter missing");
  assertContains(shellStateSource, /function getDisplay\(\)/, "display getter missing");
  assertContains(shellStateSource, /function setNotificationsState\(stateData\)/, "notifications setter missing");
  assertContains(shellStateSource, /function getNotificationsState\(\)/, "notifications getter missing");
  assertContains(shellStateSource, /function setChangelogState\(stateData\)/, "changelog setter missing");
  assertContains(shellStateSource, /function getChangelogState\(\)/, "changelog getter missing");
  assertContains(shellStateSource, /function setColorSchemesList\(listData\)/, "color schemes setter missing");
  assertContains(shellStateSource, /function getColorSchemesList\(\)/, "color schemes getter missing");
}

testShellStateAdapterContract();
console.log("ok testShellStateAdapterContract");
