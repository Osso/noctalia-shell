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
  testWallhavenUrlHelpers,
  testWallhavenDownloadAndPagingGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
