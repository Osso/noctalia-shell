#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Keyboard/ClipboardService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  const args = argNames.join(", ");
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${args}) ${body}).call(ctx, ${args}); }`);
}

function testClipboardServiceDependencyAndWatcherGuards() {
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

function testClipboardServiceWatcherAndListCommandsExecute() {
  const startWatchers = qmlFunction("startWatchers");
  const stopWatchers = qmlFunction("stopWatchers");
  const list = qmlFunction("list", "maxPreviewWidth");
  const ctx = {
    root: null,
    active: true,
    autoWatch: true,
    watchersStarted: false,
    cliphistAvailable: true,
    loading: false,
    watchText: {},
    watchImage: {},
    listProc: { running: false },
  };
  ctx.root = ctx;

  startWatchers(ctx);
  assert.equal(ctx.watchersStarted, true, "startWatchers must mark watchers active");
  assert.deepEqual(ctx.watchText.command, ["wl-paste", "--type", "text", "--watch", "cliphist", "store"]);
  assert.deepEqual(ctx.watchImage.command, ["wl-paste", "--type", "image", "--watch", "cliphist", "store"]);
  assert.equal(ctx.watchText.running, true, "startWatchers must start text watcher");
  assert.equal(ctx.watchImage.running, true, "startWatchers must start image watcher");

  stopWatchers(ctx);
  assert.equal(ctx.watchersStarted, false, "stopWatchers must clear watcher state");
  assert.equal(ctx.watchText.running, false, "stopWatchers must stop text watcher");
  assert.equal(ctx.watchImage.running, false, "stopWatchers must stop image watcher");

  list(ctx, 240);
  assert.equal(ctx.loading, true, "list must mark clipboard history loading");
  assert.deepEqual(ctx.listProc.command, ["cliphist", "list", "-preview-width", "240"]);
  assert.equal(ctx.listProc.running, true, "list must start the list process");

  const blockedCtx = { ...ctx, active: false, loading: false, listProc: { running: false } };
  blockedCtx.root = blockedCtx;
  list(blockedCtx, 120);
  assert.equal(blockedCtx.loading, false, "list must not run when clipboard history is inactive");
  assert.equal(blockedCtx.listProc.command, undefined, "list must leave process command untouched when inactive");
}

function testClipboardServiceDecodeQueuesExecute() {
  const decode = qmlFunction("decode", "id", "cb");
  const decodeToDataUrl = qmlFunction("decodeToDataUrl", "id", "mime", "cb");
  const getImageData = qmlFunction("getImageData", "id");
  const startNextB64 = qmlFunction("_startNextB64");
  const unavailableCallbacks = [];
  const ctx = {
    root: null,
    cliphistAvailable: true,
    imageDataById: { "cached-id": "data:image/png;base64,cached" },
    _decodeCallback: null,
    _b64Queue: [],
    _b64CurrentCb: null,
    _b64CurrentMime: "",
    _b64CurrentId: "",
    decodeProc: {},
    decodeB64Proc: { running: false },
    _startNextB64() {
      startNextB64(ctx);
    },
  };
  ctx.root = ctx;

  decode({ ...ctx, root: { cliphistAvailable: false } }, "missing", value => unavailableCallbacks.push(value));
  assert.deepEqual(unavailableCallbacks, [""], "decode must call back with empty content when cliphist is unavailable");

  decode(ctx, "17", value => value);
  assert.equal(typeof ctx._decodeCallback, "function", "decode must store the callback");
  assert.deepEqual(ctx.decodeProc.command, ["cliphist", "decode", "17"]);
  assert.equal(ctx.decodeProc.running, true, "decode must start the decode process");

  assert.equal(getImageData(ctx, undefined), null, "getImageData must return null for undefined ids");
  assert.equal(getImageData(ctx, "cached-id"), "data:image/png;base64,cached", "getImageData must return cached image data");

  const cachedCallbacks = [];
  decodeToDataUrl(ctx, "cached-id", "image/png", value => cachedCallbacks.push(value));
  assert.deepEqual(cachedCallbacks, ["data:image/png;base64,cached"], "decodeToDataUrl must return cached data immediately");

  decodeToDataUrl(ctx, "new-id", "", value => value);
  assert.equal(ctx._b64CurrentId, "new-id", "decodeToDataUrl must start queued base64 work immediately when idle");
  assert.equal(ctx._b64CurrentMime, "image/*", "decodeToDataUrl must default missing mime types");
  assert.deepEqual(ctx.decodeB64Proc.command, ["sh", "-lc", "cliphist decode new-id | base64 -w 0"]);
  assert.equal(ctx.decodeB64Proc.running, true, "decodeToDataUrl must start the base64 process");
}

function testClipboardServiceMutationCommandsExecute() {
  const copyToClipboard = qmlFunction("copyToClipboard", "id");
  const deleteById = qmlFunction("deleteById", "id");
  const wipeAll = qmlFunction("wipeAll");
  const detachedCommands = [];
  const listCalls = [];
  const ctx = {
    root: null,
    cliphistAvailable: true,
    revision: 0,
    copyProc: {},
    list() {
      listCalls.push("list");
    },
    Quickshell: {
      execDetached(command) {
        detachedCommands.push(command);
      },
    },
    Qt: {
      callLater(callback) {
        callback();
      },
    },
  };
  ctx.root = ctx;

  copyToClipboard(ctx, "copy-id");
  assert.deepEqual(ctx.copyProc.command, ["sh", "-lc", "cliphist decode copy-id | wl-copy"]);
  assert.equal(ctx.copyProc.running, true, "copyToClipboard must start the copy process");

  deleteById(ctx, "delete-id");
  assert.deepEqual(detachedCommands[0], ["cliphist", "delete", "delete-id"]);
  assert.equal(ctx.revision, 1, "deleteById must bump revision");
  assert.deepEqual(listCalls, ["list"], "deleteById must refresh the list later");

  wipeAll(ctx);
  assert.deepEqual(detachedCommands[1], ["cliphist", "wipe"]);
  assert.equal(ctx.revision, 2, "wipeAll must bump revision");
  assert.deepEqual(listCalls, ["list", "list"], "wipeAll must refresh the list later");
}

const tests = [
  testClipboardServiceDependencyAndWatcherGuards,
  testClipboardServiceListAndDecodeGuards,
  testClipboardServiceMutationCommands,
  testClipboardServiceWatcherAndListCommandsExecute,
  testClipboardServiceDecodeQueuesExecute,
  testClipboardServiceMutationCommandsExecute,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
