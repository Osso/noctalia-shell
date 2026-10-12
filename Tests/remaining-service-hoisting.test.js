#!/usr/bin/env node
const assert = require("assert/strict");
const fs = require("fs");
const { extractFunctionBody, extractHandlerBlock, findComponentBlock, readQml } = require("./qml-test-utils");

function bindFunctions(source, ctx, declarations) {
  ctx.root = ctx;
  for (const [name, args] of Object.entries(declarations)) {
    const body = extractFunctionBody(source, name);
    const execute = new Function("ctx", ...args, `with (ctx) { return (function(${args.join(",")}) ${body}).call(ctx, ${args.join(",")}); }`);
    ctx[name] = (...values) => execute(ctx, ...values);
  }
  return ctx;
}

function testWallhaven() {
  const requests = [];
  const processes = [];
  class FakeRequest {
    static DONE = 4;
    constructor() { requests.push(this); }
    open(method, url) { this.method = method; this.url = url; }
    send() { this.sent = true; }
    complete(status, responseText) {
      this.status = status;
      this.responseText = responseText;
      this.readyState = FakeRequest.DONE;
      this.onreadystatechange();
    }
  }
  const completed = [];
  const failed = [];
  const downloads = [];
  const ctx = bindFunctions(readQml("Services/UI/WallhavenService.qml"), {
    XMLHttpRequest: FakeRequest,
    Logger: { d() {}, e() {}, w() {}, i() {} },
    fetching: false, initialSearchScheduled: true, currentResults: [], currentMeta: {},
    lastError: "old", currentQuery: "", currentPage: 1, lastPage: 1,
    apiBaseUrl: "https://fixture.invalid", categories: "111", purity: "100",
    sorting: "random", order: "desc", topRange: "1M", seed: "fixed",
    minResolution: "1920x1080", resolutions: "", ratios: "16x9", colors: "aabbcc",
    searchCompleted(results, meta) { completed.push({ results, meta }); },
    searchFailed(error) { failed.push(error); },
    wallpaperDownloaded(id, path) { downloads.push([id, path]); },
    Settings: { data: { wallpaper: { directory: "/private/pictures" } }, preprocessPath(path) { return path; } },
    Qt: { createQmlObject() {
      const process = { destroyed: false, running: false, exited: { connect(callback) { process.finish = callback; } }, destroy() { this.destroyed = true; } };
      processes.push(process);
      return process;
    } },
  }, { search: ["query", "page"], nextPage: [], previousPage: [], reset: [],
    getWallpaperUrl: ["wallpaper"], getThumbnailUrl: ["wallpaper", "size"], downloadWallpaper: ["wallpaper", "callback"] });
  ctx.search("sky & sea", 1);
  assert.equal(ctx.initialSearchScheduled, false);
  assert.equal(ctx.fetching, true);
  assert.match(requests[0].url, /q=sky%20%26%20sea/);
  assert.match(requests[0].url, /seed=fixed/);
  ctx.search("blocked", 9);
  assert.equal(requests.length, 1);
  requests[0].complete(200, JSON.stringify({ data: [{ id: "ab1" }, { id: "cd2" }], meta: { last_page: 3, seed: "next" } }));
  assert.deepEqual(ctx.currentResults, [{ id: "ab1" }, { id: "cd2" }]);
  assert.equal(completed.length, 1);
  assert.equal(ctx.seed, "next");
  assert.equal(ctx.fetching, false);
  ctx.nextPage();
  assert.equal(ctx.currentPage, 2);
  requests.at(-1).complete(200, '{"data":[],"meta":{"last_page":3}}');
  ctx.previousPage();
  assert.equal(ctx.currentPage, 1);
  requests.at(-1).complete(200, '{"data":[],"meta":{"last_page":3}}');
  for (const [status, body, message] of [
    [200, '{}', "Invalid API response"], [200, '{', "Failed to parse API response:"],
    [429, '', "Rate limit exceeded"], [0, '', "API error: 0"], [503, '', "API error: 503"],
  ]) {
    ctx.search("failure", 1);
    requests.at(-1).complete(status, body);
    assert.ok(ctx.lastError.startsWith(message), ctx.lastError);
    assert.equal(failed.at(-1), ctx.lastError);
    assert.equal(ctx.fetching, false);
  }
  assert.equal(ctx.getWallpaperUrl({ path: "explicit" }), "explicit");
  assert.equal(ctx.getWallpaperUrl({ id: "ab1" }), "https://w.wallhaven.cc/full/ab/wallhaven-ab1.jpg");
  assert.equal(ctx.getWallpaperUrl({}), "");
  for (const [size, folder] of [["small", "small"], ["large", "lg"], ["original", "orig"], ["unknown", "lg"]]) {
    assert.equal(ctx.getThumbnailUrl({ id: "cd2" }, size), `https://th.wallhaven.cc/${folder}/cd/cd2.jpg`);
  }
  assert.equal(ctx.getThumbnailUrl({ thumbs: { small: "direct" } }, "small"), "direct");
  assert.equal(ctx.getThumbnailUrl({}, "small"), "");
  const callbacks = [];
  ctx.downloadWallpaper({ id: "ab1" }, (...args) => callbacks.push(args));
  ctx.downloadWallpaper({ id: "cd2" }, (...args) => callbacks.push(args));
  assert.equal(callbacks.length, 0);
  assert.equal(processes[0].running, true);
  processes[1].finish(1);
  processes[0].finish(0);
  assert.deepEqual(callbacks, [[false, ""], [true, "/private/pictures/wallhaven_ab1.jpg"]]);
  assert.deepEqual(downloads, [["ab1", "/private/pictures/wallhaven_ab1.jpg"]]);
  assert.ok(processes.every(process => process.destroyed));
  ctx.reset();
  assert.deepEqual(ctx.currentResults, []);
  assert.deepEqual(ctx.currentMeta, {});
  assert.equal(ctx.seed, "");
  assert.equal(ctx.currentPage, 1);
}

function testEmoji() {
  const source = readQml("Services/Keyboard/EmojiService.qml");
  const queued = [];
  const ctx = bindFunctions(source, {
    loaded: false, emojis: [], usageCounts: {}, _userEmojiData: [], _builtinEmojiData: [], _pendingLoads: 0,
    userEmojiFile: { reload() {} }, builtinEmojiFile: { reload() {} },
    Qt: { callLater(callback) { queued.push(callback); } },
    _ensureUsageFileExists() { throw new Error("unexpected host command"); },
  }, { getCategoriesWithCounts: [], _loadEmojis: [], _onLoadComplete: [], _finalizeEmojis: [] });
  assert.deepEqual(ctx.getCategoriesWithCounts(), []);
  function load(id, content, failure = false) {
    const block = findComponentBlock(source, "FileView", `id: ${id}`);
    if (failure) {
      const handler = extractHandlerBlock(block, "onLoadFailed");
      const callback = handler.slice(handler.indexOf("function"));
      new Function("ctx", `with (ctx) { (${callback}).call(ctx, "fixture failure"); }`)(ctx);
    } else {
      const handler = extractHandlerBlock(block, "onLoaded");
      const body = handler.slice(handler.indexOf("{"));
      new Function("ctx", "text", `with (ctx) { (function() ${body}).call(ctx); }`)(ctx, () => content);
    }
  }
  const builtin = [{ emoji: "a", category: "animals" }, { emoji: "b", category: "animals" }, { emoji: "c" }];
  const user = [{ emoji: "a", category: "custom" }, { emoji: "d", category: "custom" }];
  ctx._loadEmojis();
  load("userEmojiFile", JSON.stringify(user));
  assert.equal(ctx.loaded, false);
  assert.equal(ctx._pendingLoads, 1);
  load("builtinEmojiFile", JSON.stringify(builtin));
  assert.equal(ctx.loaded, true);
  assert.deepEqual(ctx.getCategoriesWithCounts(), [{ name: "custom", count: 2 }, { name: "animals", count: 1 }, { name: "other", count: 1 }]);
  for (const content of ["{", "{}", ""]) {
    ctx._loadEmojis();
    load("builtinEmojiFile", JSON.stringify(builtin));
    load("userEmojiFile", content);
    assert.deepEqual(ctx.getCategoriesWithCounts(), [{ name: "animals", count: 2 }, { name: "other", count: 1 }]);
  }
  ctx._loadEmojis();
  load("builtinEmojiFile", "", true);
  load("userEmojiFile", JSON.stringify(user));
  assert.deepEqual(ctx.getCategoriesWithCounts(), [{ name: "custom", count: 2 }]);
}

function testUpdate() {
  const ctx = bindFunctions(readQml("Services/Noctalia/UpdateService.qml"), {}, {
    normalizeVersion: ["version"], parseVersionParts: ["version"], compareVersions: ["a", "b"], parseReleaseNotes: ["body"],
  });
  for (const [a, b, expected] of [["v3.5.0", "3.5", 0], ["v3.5.2", "v3.5.10", -1], ["v3.10.1", "v3.9.9", 1], ["", "v1", -1]]) {
    assert.equal(ctx.compareVersions(a, b), expected);
  }
  assert.deepEqual(ctx.parseReleaseNotes("first\r\nsecond\n\nthird\n \n"), ["first", "second", "", "third"]);
  assert.deepEqual(ctx.parseReleaseNotes(""), []);
}

for (const path of ["/home/osso/.config/noctalia/settings.json", "/syncthing", "/run/user"]) {
  assert.equal(fs.existsSync(path), false, `host path exposed: ${path}`);
}
assert.ok(process.env.HOME.startsWith("/tmp/noctalia-remaining-services-"));
const tests = { WallhavenService: testWallhaven, EmojiService: testEmoji, UpdateService: testUpdate };
for (const [name, test] of Object.entries(tests)) {
  if (process.argv[2] && process.argv[2] !== name) continue;
  test();
  console.log(`PASS ${name}`);
}
