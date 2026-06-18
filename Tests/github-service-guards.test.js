#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const serviceSource = readQml("Services/Noctalia/GitHubService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(serviceSource, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testGitHubServiceCacheAndFetchLifecycle() {
  const source = readQml("Services/Noctalia/GitHubService.qml");
  const initBody = extractFunctionBody(source, "init");
  const loadBody = extractFunctionBody(source, "loadFromCache");
  const fetchBody = extractFunctionBody(source, "fetchFromGitHub");
  const saveBody = extractFunctionBody(source, "saveData");
  const checkBody = extractFunctionBody(source, "checkAndSaveData");
  const resetBody = extractFunctionBody(source, "resetCache");

  assert.match(initBody, /Logger\.i\("GitHub", "Service started"\)/, "init must log service startup");
  assert.match(initBody, /loadFromCache\(\)/, "init must hydrate cached GitHub data");
  assert.match(loadBody, /const now = Time\.timestamp/, "loadFromCache must compare against current time");
  assert.match(loadBody, /if \(!data\.timestamp \|\| \(now >= data\.timestamp \+ githubUpdateFrequency\)\)/, "loadFromCache must detect missing or expired cache");
  assert.match(loadBody, /if \(data\.version\)[\s\S]*root\.latestVersion = data\.version/, "loadFromCache must publish cached version");
  assert.match(loadBody, /if \(data\.contributors\)[\s\S]*root\.contributors = data\.contributors/, "loadFromCache must publish cached contributors");
  assert.match(loadBody, /if \(needsRefetch\)[\s\S]*fetchFromGitHub\(\)/, "loadFromCache must refresh stale cache");
  assert.match(fetchBody, /if \(isFetchingData\)[\s\S]*return;/, "fetchFromGitHub must avoid concurrent fetches");
  assert.match(fetchBody, /isFetchingData = true[\s\S]*versionProcess\.running = true[\s\S]*contributorsProcess\.running = true/, "fetchFromGitHub must start both GitHub requests");
  assert.match(saveBody, /data\.timestamp = Time\.timestamp/, "saveData must stamp cached data");
  assert.match(saveBody, /Quickshell\.execDetached\(\["mkdir", "-p", Settings\.cacheDir\]\)/, "saveData must ensure cache directory exists");
  assert.match(saveBody, /Qt\.callLater\(\(\) =>[\s\S]*githubDataFileView\.writeAdapter\(\)/, "saveData must defer FileView writes");
  assert.match(checkBody, /if \(!versionProcess\.running && !contributorsProcess\.running\)[\s\S]*root\.isFetchingData = false[\s\S]*root\.saveData\(\)/, "checkAndSaveData must save only after both requests finish");
  assert.match(resetBody, /data\.version = I18n\.tr\("system\.unknown-version"\)/, "resetCache must clear cached version");
  assert.match(resetBody, /data\.contributors = \[\][\s\S]*data\.timestamp = 0[\s\S]*fetchFromGitHub\(\)/, "resetCache must clear cached contributors and refetch");
}

function testGitHubServiceMetadataPersistence() {
  const source = readQml("Services/Noctalia/GitHubService.qml");
  const loadMetadataBody = extractFunctionBody(source, "loadCacheMetadata");
  const saveMetadataBody = extractFunctionBody(source, "saveCacheMetadata");

  assert.match(loadMetadataBody, /command: \["cat", "\$\{metadataPath\}"\]/, "loadCacheMetadata must read metadata from disk");
  assert.match(loadMetadataBody, /StdioCollector \{\}/, "loadCacheMetadata must attach stdout collection");
  assert.match(loadMetadataBody, /if \(text && text\.trim\(\)\)[\s\S]*cacheMetadata = JSON\.parse\(text\)/, "loadCacheMetadata must parse non-empty metadata JSON");
  assert.match(loadMetadataBody, /for \(var username in cacheMetadata\)[\s\S]*cachedCircularAvatars\[username\] = "file:\/\/" \+ entry\.cached_path/, "loadCacheMetadata must populate circular avatar paths");
  assert.match(loadMetadataBody, /metadataLoaded = true/, "loadCacheMetadata must mark metadata loaded");
  assert.match(loadMetadataBody, /catch \(e\)[\s\S]*cacheMetadata = \{\}[\s\S]*metadataLoaded = true/, "loadCacheMetadata must recover from parse failures");
  assert.match(loadMetadataBody, /loadProcess\.exited\.connect\(function \(exitCode\)[\s\S]*if \(exitCode !== 0\)[\s\S]*cacheMetadata = \{\}[\s\S]*metadataLoaded = true/, "loadCacheMetadata must initialize empty metadata when file reads fail");
  assert.match(loadMetadataBody, /loadProcess\.running = true/, "loadCacheMetadata must start the read process");
  assert.match(saveMetadataBody, /Quickshell\.execDetached\(\["mkdir", "-p", avatarCacheDir\]\)/, "saveCacheMetadata must ensure avatar cache directory exists");
  assert.match(saveMetadataBody, /var jsonContent = JSON\.stringify\(cacheMetadata, null, 2\)/, "saveCacheMetadata must serialize metadata prettily");
  assert.match(saveMetadataBody, /var base64Content = Qt\.btoa\(jsonContent\)/, "saveCacheMetadata must base64 encode metadata before shell write");
  assert.match(saveMetadataBody, /base64 -d > '\$\{metadataPath\}'/, "saveCacheMetadata must decode into the metadata path");
  assert.match(saveMetadataBody, /saveProcess\.exited\.connect\(function \(exitCode\)[\s\S]*saveProcess\.destroy\(\)/, "saveCacheMetadata must clean up the process");
  assert.match(saveMetadataBody, /saveProcess\.running = true/, "saveCacheMetadata must start the save process");
}

function testGitHubServiceAvatarQueueing() {
  const source = readQml("Services/Noctalia/GitHubService.qml");
  const body = extractFunctionBody(source, "cacheTopContributorAvatars");

  assert.match(body, /if \(contributors\.length === 0\)\s+return;/, "cacheTopContributorAvatars must ignore empty contributor lists");
  assert.match(body, /avatarsCached = true/, "cacheTopContributorAvatars must mark contributor set as processed");
  assert.match(body, /Quickshell\.execDetached\(\["mkdir", "-p", avatarCacheDir\]\)/, "cacheTopContributorAvatars must ensure cache directory exists");
  assert.match(body, /avatarQueue = \[\]/, "cacheTopContributorAvatars must rebuild the queue");
  assert.match(body, /for \(var i = 0; i < Math\.min\(contributors\.length, 20\); i\+\+\)/, "cacheTopContributorAvatars must only process the top 20 contributors");
  assert.match(body, /var circularPath = avatarCacheDir \+ username \+ "_circular\.png"/, "cacheTopContributorAvatars must derive circular avatar paths");
  assert.match(body, /if \(!cacheMetadata\[username\]\)[\s\S]*needsProcessing = true[\s\S]*reason = "new user"/, "cacheTopContributorAvatars must queue new users");
  assert.match(body, /else if \(cacheMetadata\[username\]\.avatar_url !== avatarUrl\)[\s\S]*needsProcessing = true[\s\S]*reason = "avatar URL changed"/, "cacheTopContributorAvatars must queue changed avatar URLs");
  assert.match(body, /cachedCircularAvatars\[username\] = "file:\/\/" \+ circularPath/, "cacheTopContributorAvatars must reuse existing cached avatars");
  assert.match(body, /avatarQueue\.push\(\{[\s\S]*username: username[\s\S]*avatarUrl: avatarUrl[\s\S]*circularPath: circularPath/, "cacheTopContributorAvatars must queue avatar work items");
  assert.match(body, /for \(var cachedUsername in cacheMetadata\)[\s\S]*if \(!currentTop20\[cachedUsername\]\)/, "cacheTopContributorAvatars must find removed top contributors");
  assert.match(body, /Quickshell\.execDetached\(\["rm", "-f", pathToDelete\]\)/, "cacheTopContributorAvatars must delete stale circular avatar files");
  assert.match(body, /delete cacheMetadata\[cachedUsername\][\s\S]*delete cachedCircularAvatars\[cachedUsername\]/, "cacheTopContributorAvatars must remove stale metadata and avatar entries");
  assert.match(body, /if \(removedUsers\.length > 0\)[\s\S]*saveCacheMetadata\(\)/, "cacheTopContributorAvatars must save metadata after cleanup");
  assert.match(body, /if \(avatarQueue\.length > 0\)[\s\S]*processNextAvatar\(\)[\s\S]*else[\s\S]*cachedCircularAvatarsChanged\(\)/, "cacheTopContributorAvatars must process queued work or notify reused cache");
}

function testGitHubServiceAvatarProcessing() {
  const source = readQml("Services/Noctalia/GitHubService.qml");
  const nextBody = extractFunctionBody(source, "processNextAvatar");
  const downloadBody = extractFunctionBody(source, "downloadAvatar");
  const renderBody = extractFunctionBody(source, "renderCircularAvatar");

  assert.match(nextBody, /if \(avatarQueue\.length === 0 \|\| isProcessingAvatars\)\s+return;/, "processNextAvatar must avoid empty or concurrent work");
  assert.match(nextBody, /isProcessingAvatars = true[\s\S]*var item = avatarQueue\.shift\(\)/, "processNextAvatar must claim and dequeue one item");
  assert.match(nextBody, /var tempPath = avatarCacheDir \+ item\.username \+ "_temp\.png"/, "processNextAvatar must use a temp avatar path");
  assert.match(nextBody, /downloadAvatar\(item\.avatarUrl, tempPath, function \(success\)/, "processNextAvatar must download the original avatar");
  assert.match(nextBody, /if \(success\)[\s\S]*renderCircularAvatar\(tempPath, item\.circularPath, item\.username, item\.avatarUrl\)/, "processNextAvatar must render successful downloads");
  assert.match(nextBody, /else[\s\S]*isProcessingAvatars = false[\s\S]*processNextAvatar\(\)/, "processNextAvatar must continue after failed downloads");
  assert.match(downloadBody, /curl -L -s -o '\$\{destPath\}' '\$\{url\}' \|\| wget -q -O '\$\{destPath\}' '\$\{url\}'/, "downloadAvatar must use curl with wget fallback");
  assert.match(downloadBody, /callback\(exitCode === 0\)[\s\S]*downloadProcess\.destroy\(\)/, "downloadAvatar must report success and clean up");
  assert.match(downloadBody, /downloadProcess\.running = true/, "downloadAvatar must start the process");
  assert.match(renderBody, /command: \["magick", "\$\{inputPath\}", "-resize", "256x256\^"/, "renderCircularAvatar must use ImageMagick resize pipeline");
  assert.match(renderBody, /var success = exitCode === 0/, "renderCircularAvatar must check process success");
  assert.match(renderBody, /cacheMetadata\[username\] = \{[\s\S]*avatar_url: avatarUrl[\s\S]*cached_path: outputPath[\s\S]*cached_at: Date\.now\(\)/, "renderCircularAvatar must update metadata on success");
  assert.match(renderBody, /cachedCircularAvatars\[username\] = "file:\/\/" \+ outputPath[\s\S]*cachedCircularAvatarsChanged\(\)[\s\S]*saveCacheMetadata\(\)/, "renderCircularAvatar must publish and persist rendered avatars");
  assert.match(renderBody, /Quickshell\.execDetached\(\["rm", "-f", inputPath\]\)/, "renderCircularAvatar must remove temp input files");
  assert.match(renderBody, /isProcessingAvatars = false[\s\S]*processNextAvatar\(\)[\s\S]*convertProcess\.destroy\(\)/, "renderCircularAvatar must release the worker and continue queue processing");
  assert.match(renderBody, /convertProcess\.running = true/, "renderCircularAvatar must start the conversion process");
}

function testGitHubServiceParsesVersionAndContributorResponses() {
  const parseVersionResponse = qmlFunction("parseVersionResponse", "rawResponse");
  const parseContributorsResponse = qmlFunction("parseContributorsResponse", "rawResponse");
  const contributors = [
    { login: "alessio", contributions: 12 },
    { login: "osso", contributions: 3 },
  ];

  assert.match(serviceSource, /function parseVersionResponse\(rawResponse\)/, "parseVersionResponse must type raw GitHub response input");
  assert.match(serviceSource, /function parseContributorsResponse\(rawResponse\)/, "parseContributorsResponse must type raw GitHub response input");
  assert.deepEqual(parseVersionResponse({}, JSON.stringify({ tag_name: "v1.2.3" })), {
    version: "v1.2.3",
    warning: "",
  });
  assert.deepEqual(parseVersionResponse({}, JSON.stringify({ message: "rate limited" })), {
    version: "",
    warning: "rate limited",
  });
  assert.deepEqual(parseVersionResponse({}, ""), {
    version: "",
    warning: "Empty response from GitHub API",
  });
  assert.deepEqual(parseContributorsResponse({}, JSON.stringify(contributors)), {
    contributors,
    warning: "",
  });
  assert.deepEqual(parseContributorsResponse({}, JSON.stringify({ message: "bad shape" })), {
    contributors: [],
    warning: "Unexpected contributors response shape",
  });
  assert.deepEqual(parseContributorsResponse({}, ""), {
    contributors: [],
    warning: "Empty response from GitHub API for contributors",
  });
}

const tests = [
  testGitHubServiceCacheAndFetchLifecycle,
  testGitHubServiceMetadataPersistence,
  testGitHubServiceAvatarQueueing,
  testGitHubServiceAvatarProcessing,
  testGitHubServiceParsesVersionAndContributorResponses,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
