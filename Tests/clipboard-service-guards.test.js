#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testClipboardServiceDependencyAndWatcherGuards() {
  const source = readQml("Services/Keyboard/ClipboardService.qml");
  const checkBody = extractFunctionBody(source, "checkCliphistAvailability");
  const startBody = extractFunctionBody(source, "startWatchers");
  const stopBody = extractFunctionBody(source, "stopWatchers");

  assert.match(checkBody, /if \(dependencyChecked\)\s+return;/, "checkCliphistAvailability must only run once");
  assert.match(checkBody, /dependencyCheckProcess\.command = \["which", "cliphist"\]/, "checkCliphistAvailability must probe cliphist");
  assert.match(checkBody, /dependencyCheckProcess\.running = true/, "checkCliphistAvailability must start the dependency process");
  assert.match(startBody, /if \(!root\.active \|\| !autoWatch \|\| watchersStarted \|\| !root\.cliphistAvailable\)\s+return;/, "startWatchers must require active clipboard history");
  assert.match(startBody, /watchersStarted = true/, "startWatchers must mark watchers started");
  assert.match(startBody, /watchText\.command = \["wl-paste", "--type", "text", "--watch", "cliphist", "store"\]/, "startWatchers must start text clipboard storage");
  assert.match(startBody, /watchImage\.command = \["wl-paste", "--type", "image", "--watch", "cliphist", "store"\]/, "startWatchers must start image clipboard storage");
  assert.match(stopBody, /if \(!watchersStarted\)\s+return;/, "stopWatchers must be idempotent");
  assert.match(stopBody, /watchText\.running = false[\s\S]*watchImage\.running = false[\s\S]*watchersStarted = false/, "stopWatchers must stop both watchers");
}

function testClipboardServiceListAndDecodeGuards() {
  const source = readQml("Services/Keyboard/ClipboardService.qml");
  const listBody = extractFunctionBody(source, "list");
  const decodeBody = extractFunctionBody(source, "decode");
  const dataUrlBody = extractFunctionBody(source, "decodeToDataUrl");
  const getImageBody = extractFunctionBody(source, "getImageData");
  const nextB64Body = extractFunctionBody(source, "_startNextB64");

  assert.match(listBody, /if \(!root\.active \|\| !root\.cliphistAvailable\)[\s\S]*return;/, "list must require active cliphist support");
  assert.match(listBody, /if \(listProc\.running\)\s+return;/, "list must avoid concurrent list processes");
  assert.match(listBody, /loading = true/, "list must expose loading state");
  assert.match(listBody, /const width = maxPreviewWidth \|\| 100/, "list must default preview width");
  assert.match(listBody, /listProc\.command = \["cliphist", "list", "-preview-width", String\(width\)\]/, "list must run cliphist list");
  assert.match(decodeBody, /if \(!root\.cliphistAvailable\)[\s\S]*if \(cb\)\s+cb\(""\)[\s\S]*return;/, "decode must fail closed when cliphist is unavailable");
  assert.match(decodeBody, /root\._decodeCallback = cb/, "decode must store callback for process completion");
  assert.match(decodeBody, /decodeProc\.command = \["cliphist", "decode", id\][\s\S]*decodeProc\.running = true/, "decode must start cliphist decode");
  assert.match(dataUrlBody, /if \(!root\.cliphistAvailable\)[\s\S]*if \(cb\)\s+cb\(""\)[\s\S]*return;/, "decodeToDataUrl must fail closed when cliphist is unavailable");
  assert.match(dataUrlBody, /if \(root\.imageDataById\[id\]\)[\s\S]*cb\(root\.imageDataById\[id\]\)[\s\S]*return;/, "decodeToDataUrl must return cached image data immediately");
  assert.match(dataUrlBody, /root\._b64Queue\.push\(\{[\s\S]*"id": id[\s\S]*"mime": mime \|\| "image\/\*"[\s\S]*"cb": cb/, "decodeToDataUrl must enqueue base64 decode jobs");
  assert.match(dataUrlBody, /if \(!decodeB64Proc\.running && root\._b64CurrentCb === null\)[\s\S]*_startNextB64\(\)/, "decodeToDataUrl must start idle base64 worker");
  assert.match(getImageBody, /if \(id === undefined\)[\s\S]*return null/, "getImageData must reject missing ids");
  assert.match(getImageBody, /return root\.imageDataById\[id\]/, "getImageData must return cached image data");
  assert.match(nextB64Body, /if \(root\._b64Queue\.length === 0 \|\| !root\.cliphistAvailable\)\s+return;/, "_startNextB64 must require queued jobs and cliphist");
  assert.match(nextB64Body, /const job = root\._b64Queue\.shift\(\)/, "_startNextB64 must consume one queued job");
  assert.match(nextB64Body, /root\._b64CurrentCb = job\.cb[\s\S]*root\._b64CurrentMime = job\.mime[\s\S]*root\._b64CurrentId = job\.id/, "_startNextB64 must expose current job state");
  assert.match(nextB64Body, /decodeB64Proc\.command = \["sh", "-lc", `cliphist decode \$\{job\.id\} \| base64 -w 0`\]/, "_startNextB64 must decode and base64 encode through the shell");
}

function testClipboardServiceMutationCommands() {
  const source = readQml("Services/Keyboard/ClipboardService.qml");
  const copyBody = extractFunctionBody(source, "copyToClipboard");
  const deleteBody = extractFunctionBody(source, "deleteById");
  const wipeBody = extractFunctionBody(source, "wipeAll");

  assert.match(copyBody, /if \(!root\.cliphistAvailable\)[\s\S]*return;/, "copyToClipboard must require cliphist");
  assert.match(copyBody, /copyProc\.command = \["sh", "-lc", `cliphist decode \$\{id\} \| wl-copy`\]/, "copyToClipboard must pipe decoded data to wl-copy");
  assert.match(copyBody, /copyProc\.running = true/, "copyToClipboard must start copy process");
  assert.match(deleteBody, /if \(!root\.cliphistAvailable\)[\s\S]*return;/, "deleteById must require cliphist");
  assert.match(deleteBody, /Quickshell\.execDetached\(\["cliphist", "delete", id\]\)/, "deleteById must invoke cliphist delete");
  assert.match(deleteBody, /revision\+\+[\s\S]*Qt\.callLater\(\(\) => list\(\)\)/, "deleteById must invalidate bindings and refresh list");
  assert.match(wipeBody, /if \(!root\.cliphistAvailable\)[\s\S]*return;/, "wipeAll must require cliphist");
  assert.match(wipeBody, /Quickshell\.execDetached\(\["cliphist", "wipe"\]\)/, "wipeAll must invoke cliphist wipe");
  assert.match(wipeBody, /revision\+\+[\s\S]*Qt\.callLater\(\(\) => list\(\)\)/, "wipeAll must invalidate bindings and refresh list");
}

const tests = [
  testClipboardServiceDependencyAndWatcherGuards,
  testClipboardServiceListAndDecodeGuards,
  testClipboardServiceMutationCommands,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
