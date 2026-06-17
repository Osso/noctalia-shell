#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testWallhavenUrlSignaturesAreTyped() {
  const source = readQml("Services/UI/WallhavenService.qml");

  assert.match(source, /function getWallpaperUrl\(wallpaper\): string/, "getWallpaperUrl must declare string output");
  assert.match(source, /function search\(query: string, page: int\)/, "search must type query and page inputs");
  assert.match(source, /function getThumbnailUrl\(wallpaper, size: string\): string/, "getThumbnailUrl must type the size input and declare string output");
}

function testWallhavenSearchQueryGuards() {
  const source = readQml("Services/UI/WallhavenService.qml");
  const searchBody = extractFunctionBody(source, "search");

  assert.match(searchBody, /if \(fetching\)[\s\S]*return/, "search must ignore duplicate requests while fetching");
  assert.match(searchBody, /if \(initialSearchScheduled\)[\s\S]*initialSearchScheduled = false/, "search must clear scheduled initial search state");
  assert.match(searchBody, /fetching = true[\s\S]*lastError = ""[\s\S]*currentQuery = query \|\| ""[\s\S]*currentPage = page \|\| 1/, "search must reset public request state");
  assert.match(searchBody, /params\.push\("q=" \+ encodeURIComponent\(currentQuery\)\)/, "search must encode query text");
  assert.match(searchBody, /params\.push\("categories=" \+ categories\)[\s\S]*params\.push\("purity=" \+ purity\)[\s\S]*params\.push\("sorting=" \+ sorting\)[\s\S]*params\.push\("order=" \+ order\)/, "search must include base Wallhaven filters");
  assert.match(searchBody, /if \(sorting === "toplist"\)[\s\S]*params\.push\("topRange=" \+ topRange\)/, "search must include topRange only for toplist sorting");
  assert.match(searchBody, /if \(sorting === "random" && seed\)[\s\S]*params\.push\("seed=" \+ seed\)/, "search must include seed only for random sorting");
  assert.match(searchBody, /params\.push\("page=" \+ currentPage\)[\s\S]*url \+= "\?" \+ params\.join\("&"\)/, "search must include page and join query params");
  assert.match(searchBody, /xhr\.open\("GET", url\)[\s\S]*xhr\.send\(\)/, "search must issue a GET request");
}

function testWallhavenSearchResponseGuards() {
  const source = readQml("Services/UI/WallhavenService.qml");
  const searchBody = extractFunctionBody(source, "search");

  assert.match(searchBody, /if \(xhr\.readyState === XMLHttpRequest\.DONE\)[\s\S]*fetching = false/, "search must clear fetching only after request completion");
  assert.match(searchBody, /if \(xhr\.status === 200\)[\s\S]*var response = JSON\.parse\(xhr\.responseText\)/, "search must parse successful JSON responses");
  assert.match(searchBody, /if \(response\.data && Array\.isArray\(response\.data\)\)[\s\S]*currentResults = response\.data[\s\S]*currentMeta = response\.meta \|\| \{\}[\s\S]*lastPage = currentMeta\.last_page \|\| 1/, "search must publish valid result and metadata state");
  assert.match(searchBody, /if \(currentMeta\.seed\)[\s\S]*seed = currentMeta\.seed/, "search must retain random search seed from metadata");
  assert.match(searchBody, /searchCompleted\(currentResults, currentMeta\)/, "search must emit successful result state");
  assert.match(searchBody, /var errorMsg = "Invalid API response"[\s\S]*lastError = errorMsg[\s\S]*searchFailed\(errorMsg\)/, "search must fail closed on invalid API shape");
  assert.match(searchBody, /"Failed to parse API response: " \+ e\.toString\(\)[\s\S]*searchFailed\(errorMsg\)/, "search must report parse failures");
  assert.match(searchBody, /xhr\.status === 429[\s\S]*"Rate limit exceeded \(45 requests\/minute\)"[\s\S]*searchFailed\(errorMsg\)/, "search must map Wallhaven rate limit responses");
  assert.match(searchBody, /"API error: " \+ xhr\.status[\s\S]*searchFailed\(errorMsg\)/, "search must report non-200 API errors");
}

function runSearchFixture({ status, responseText }) {
  const source = readQml("Services/UI/WallhavenService.qml");
  const search = new Function("ctx", "query", "page", `with (ctx) { return (function(query, page) ${extractFunctionBody(source, "search")}).call(ctx, query, page); }`);
  const requests = [];
  function XMLHttpRequest() {
    this.readyState = 0;
    this.status = status;
    this.responseText = responseText;
    this.open = (method, url) => {
      requests.push({ method, url });
    };
    this.send = () => {
      this.readyState = XMLHttpRequest.DONE;
      this.onreadystatechange();
    };
  }
  XMLHttpRequest.DONE = 4;
  const completed = [];
  const failed = [];
  const ctx = {
    apiBaseUrl: "https://wallhaven.test/api/v1",
    fetching: false,
    initialSearchScheduled: true,
    currentResults: [],
    currentMeta: {},
    currentQuery: "",
    currentPage: 0,
    lastPage: 0,
    lastError: "",
    categories: "111",
    purity: "100",
    sorting: "random",
    order: "desc",
    topRange: "1M",
    seed: "old-seed",
    minResolution: "1920x1080",
    resolutions: "1920x1080",
    ratios: "16x9",
    colors: "336699",
    XMLHttpRequest,
    Logger: {
      d() {},
      e() {},
      w() {},
    },
    searchCompleted(results, meta) {
      completed.push({ results, meta });
    },
    searchFailed(error) {
      failed.push(error);
    },
  };

  search(ctx, "space cats", 2);

  return { ctx, completed, failed, requests };
}

function testWallhavenSearchHandlesConcreteSuccessFixture() {
  const response = {
    data: [
      { id: "abc123", path: "https://wallhaven.test/wallpaper.jpg" },
    ],
    meta: {
      last_page: 3,
      seed: "new-seed",
    },
  };
  const { ctx, completed, failed, requests } = runSearchFixture({
    status: 200,
    responseText: JSON.stringify(response),
  });

  assert.equal(ctx.fetching, false);
  assert.equal(ctx.initialSearchScheduled, false);
  assert.equal(ctx.currentQuery, "space cats");
  assert.equal(ctx.currentPage, 2);
  assert.equal(ctx.lastPage, 3);
  assert.equal(ctx.seed, "new-seed");
  assert.deepEqual(ctx.currentResults, response.data);
  assert.deepEqual(ctx.currentMeta, response.meta);
  assert.deepEqual(completed, [{ results: response.data, meta: response.meta }]);
  assert.deepEqual(failed, []);
  assert.equal(requests[0].method, "GET");
  assert.match(requests[0].url, /^https:\/\/wallhaven\.test\/api\/v1\/search\?/);
  assert.match(requests[0].url, /q=space%20cats/);
  assert.match(requests[0].url, /sorting=random/);
  assert.match(requests[0].url, /seed=old-seed/);
  assert.match(requests[0].url, /page=2/);
}

function testWallhavenSearchHandlesConcreteErrorFixtures() {
  const invalidShape = runSearchFixture({
    status: 200,
    responseText: JSON.stringify({ data: { not: "an array" } }),
  });
  assert.equal(invalidShape.ctx.lastError, "Invalid API response");
  assert.deepEqual(invalidShape.failed, ["Invalid API response"]);

  const parseFailure = runSearchFixture({
    status: 200,
    responseText: "{",
  });
  assert.match(parseFailure.ctx.lastError, /^Failed to parse API response:/);
  assert.equal(parseFailure.failed[0], parseFailure.ctx.lastError);

  const rateLimit = runSearchFixture({
    status: 429,
    responseText: "",
  });
  assert.equal(rateLimit.ctx.lastError, "Rate limit exceeded (45 requests/minute)");
  assert.deepEqual(rateLimit.failed, ["Rate limit exceeded (45 requests/minute)"]);

  const serverError = runSearchFixture({
    status: 500,
    responseText: "",
  });
  assert.equal(serverError.ctx.lastError, "API error: 500");
  assert.deepEqual(serverError.failed, ["API error: 500"]);
}

function testWallhavenUrlHelpers() {
  const source = readQml("Services/UI/WallhavenService.qml");
  const wallpaperBody = extractFunctionBody(source, "getWallpaperUrl");
  const thumbnailBody = extractFunctionBody(source, "getThumbnailUrl");

  assert.match(wallpaperBody, /if \(wallpaper\.path\)[\s\S]*return wallpaper\.path/, "getWallpaperUrl must prefer API-provided path");
  assert.match(wallpaperBody, /var idPrefix = wallpaper\.id\.substring\(0, 2\)[\s\S]*"https:\/\/w\.wallhaven\.cc\/full\/" \+ idPrefix \+ "\/wallhaven-" \+ wallpaper\.id \+ "\.jpg"/, "getWallpaperUrl must construct full image fallback from id prefix");
  assert.match(wallpaperBody, /return ""/, "getWallpaperUrl must fail closed without path or id");
  assert.match(thumbnailBody, /if \(wallpaper\.thumbs && wallpaper\.thumbs\[size\]\)[\s\S]*return wallpaper\.thumbs\[size\]/, "getThumbnailUrl must prefer API-provided thumbnail size");
  assert.match(thumbnailBody, /var sizeMap = \{[\s\S]*"small": "small"[\s\S]*"large": "lg"[\s\S]*"original": "orig"[\s\S]*var sizePath = sizeMap\[size\] \|\| "lg"/, "getThumbnailUrl must map known sizes and default to large");
  assert.match(thumbnailBody, /"https:\/\/th\.wallhaven\.cc\/" \+ sizePath \+ "\/" \+ idPrefix \+ "\/" \+ wallpaper\.id \+ "\.jpg"/, "getThumbnailUrl must construct thumbnail fallback from id prefix");
}

function testWallhavenDownloadAndPagingGuards() {
  const source = readQml("Services/UI/WallhavenService.qml");
  const downloadBody = extractFunctionBody(source, "downloadWallpaper");
  const resetBody = extractFunctionBody(source, "reset");
  const nextBody = extractFunctionBody(source, "nextPage");
  const previousBody = extractFunctionBody(source, "previousPage");

  assert.match(downloadBody, /var url = getWallpaperUrl\(wallpaper\)[\s\S]*if \(!url\)[\s\S]*callback\(false, ""\)[\s\S]*return/, "downloadWallpaper must fail callback when no wallpaper URL exists");
  assert.match(downloadBody, /var wallpaperDir = Settings\.preprocessPath\(Settings\.data\.wallpaper\.directory\)[\s\S]*wallpaperDir = Settings\.defaultWallpapersDirectory/, "downloadWallpaper must resolve configured directory with default fallback");
  assert.match(downloadBody, /if \(!wallpaperDir\.endsWith\("\/"\)\)[\s\S]*wallpaperDir \+= "\/"/, "downloadWallpaper must normalize directory slash");
  assert.match(downloadBody, /var localPath = wallpaperDir \+ "wallhaven_" \+ wallpaperId \+ "\.jpg"/, "downloadWallpaper must build stable local path");
  assert.match(downloadBody, /downloadProcess\.exited\.connect\(function \(exitCode\)[\s\S]*if \(exitCode === 0\)[\s\S]*wallpaperDownloaded\(wallpaperId, localPath\)[\s\S]*callback\(true, localPath\)[\s\S]*callback\(false, ""\)[\s\S]*downloadProcess\.destroy\(\)/, "downloadWallpaper must emit and cleanup for success or failure");
  assert.match(resetBody, /currentResults = \[\][\s\S]*currentMeta = \{\}[\s\S]*currentQuery = ""[\s\S]*currentPage = 1[\s\S]*lastPage = 1[\s\S]*seed = ""[\s\S]*lastError = ""/, "reset must clear search state");
  assert.match(nextBody, /if \(currentPage < lastPage && !fetching\)[\s\S]*search\(currentQuery, currentPage \+ 1\)/, "nextPage must advance only inside bounds and while idle");
  assert.match(previousBody, /if \(currentPage > 1 && !fetching\)[\s\S]*search\(currentQuery, currentPage - 1\)/, "previousPage must go back only inside bounds and while idle");
}

const tests = [
  testWallhavenUrlSignaturesAreTyped,
  testWallhavenSearchQueryGuards,
  testWallhavenSearchResponseGuards,
  testWallhavenSearchHandlesConcreteSuccessFixture,
  testWallhavenSearchHandlesConcreteErrorFixtures,
  testWallhavenUrlHelpers,
  testWallhavenDownloadAndPagingGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
