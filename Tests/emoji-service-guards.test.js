#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const serviceSource = readQml("Services/Keyboard/EmojiService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(serviceSource, functionName);
  const args = argNames.join(", ");
  return new Function(
    "ctx",
    ...argNames,
    `with (ctx) { return (function(${args}) ${body}).call(ctx, ${args}); }`,
  );
}

function testEmojiServiceSearchAndPopularResults() {
  const source = readQml("Services/Keyboard/EmojiService.qml");
  const searchBody = extractFunctionBody(source, "search");
  const popularBody = extractFunctionBody(source, "_getPopularEmojis");

  assert.match(searchBody, /if \(!loaded\)[\s\S]*return \[\]/, "search must fail closed before emoji data loads");
  assert.match(searchBody, /if \(!query \|\| query\.trim\(\) === ""\)[\s\S]*return _getPopularEmojis\(50\)/, "search must return popular results for blank queries");
  assert.match(searchBody, /const terms = query\.toLowerCase\(\)\.split\(" "\)\.filter\(t => t\)/, "search must split normalized search terms");
  assert.match(searchBody, /emoji\.emoji\.toLowerCase\(\)\.includes\(term\)/, "search must match emoji glyph text");
  assert.match(searchBody, /emoji\.name\.toLowerCase\(\)\.includes\(term\)/, "search must match emoji names");
  assert.match(searchBody, /emoji\.keywords\.some\(kw => kw\.toLowerCase\(\)\.includes\(term\)\)/, "search must match emoji keywords");
  assert.match(searchBody, /emoji\.category\.toLowerCase\(\)\.includes\(term\)/, "search must match emoji categories");
  assert.match(searchBody, /if \(!emojiMatch && !nameMatch && !keywordMatch && !categoryMatch\)[\s\S]*return false/, "search must require every query term to match some field");
  assert.match(popularBody, /usageCount: usageCounts\[emoji\.emoji\] \|\| 0/, "popular results must read per-emoji usage counts");
  assert.match(popularBody, /return item\.usageCount > 0/, "popular results must exclude unused emoji");
  assert.match(popularBody, /return b\.usageCount - a\.usageCount/, "popular results must sort high usage first");
  assert.match(popularBody, /return a\.emoji\.name\.localeCompare\(b\.emoji\.name\)/, "popular results must sort ties by name");
  assert.match(popularBody, /return emojisWithUsage\.slice\(0, limit\)\.map\(function \(item\)[\s\S]*return item\.emoji/, "popular results must return limited emoji objects");
}

function testEmojiServiceCategoriesAndUsage() {
  const source = readQml("Services/Keyboard/EmojiService.qml");
  const categoriesBody = extractFunctionBody(source, "getCategoriesWithCounts");
  const byCategoryBody = extractFunctionBody(source, "getEmojisByCategory");
  const recordBody = extractFunctionBody(source, "recordUsage");

  assert.match(categoriesBody, /if \(!loaded\)[\s\S]*return \[\]/, "getCategoriesWithCounts must fail closed before load");
  assert.match(categoriesBody, /var category = emoji\.category \|\| "other"/, "getCategoriesWithCounts must bucket missing categories under other");
  assert.match(categoriesBody, /categoryCounts\[category\]\+\+/, "getCategoriesWithCounts must count each category");
  assert.match(categoriesBody, /categories\.push\(\{[\s\S]*name: cat[\s\S]*count: categoryCounts\[cat\]/, "getCategoriesWithCounts must expose names and counts");
  assert.match(byCategoryBody, /if \(!loaded\)[\s\S]*return \[\]/, "getEmojisByCategory must fail closed before load");
  assert.match(byCategoryBody, /if \(category === "recent"\)[\s\S]*return _getPopularEmojis\(25\)/, "getEmojisByCategory must use popular emoji for recent");
  assert.match(byCategoryBody, /return emoji\.category === category/, "getEmojisByCategory must filter by exact category");
  assert.match(recordBody, /if \(emojiChar\)/, "recordUsage must ignore empty emoji values");
  assert.match(recordBody, /const currentCount = usageCounts\[emojiChar\] \|\| 0/, "recordUsage must default missing usage to zero");
  assert.match(recordBody, /usageCounts\[emojiChar\] = currentCount \+ 1/, "recordUsage must increment usage");
  assert.match(recordBody, /_saveUsageData\(\)/, "recordUsage must schedule persistence");
}

function testEmojiServiceFileLoadingAndFinalization() {
  const source = readQml("Services/Keyboard/EmojiService.qml");
  const ensureBody = extractFunctionBody(source, "_ensureUsageFileExists");
  const loadBody = extractFunctionBody(source, "_loadEmojis");
  const completeBody = extractFunctionBody(source, "_onLoadComplete");
  const finalizeBody = extractFunctionBody(source, "_finalizeEmojis");

  assert.match(ensureBody, /mkdir -p "\$\(dirname "\$\{root\.usageFilePath\}"\)" && echo '\{\}' > "\$\{root\.usageFilePath\}"/, "_ensureUsageFileExists must create a default usage file");
  assert.match(loadBody, /_pendingLoads = 2/, "_loadEmojis must wait for user and built-in files");
  assert.match(loadBody, /userEmojiFile\.reload\(\)/, "_loadEmojis must reload user emoji data");
  assert.match(loadBody, /builtinEmojiFile\.reload\(\)/, "_loadEmojis must reload built-in emoji data");
  assert.match(completeBody, /_pendingLoads--/, "_onLoadComplete must decrement pending load count");
  assert.match(completeBody, /if \(_pendingLoads <= 0\)[\s\S]*_finalizeEmojis\(\)/, "_onLoadComplete must finalize after all loads finish");
  assert.match(finalizeBody, /const emojiMap = new Map\(\)/, "_finalizeEmojis must deduplicate with a map");
  assert.match(finalizeBody, /for \(const emoji of _builtinEmojiData\)[\s\S]*emojiMap\.set\(emoji\.emoji, emoji\)/, "_finalizeEmojis must load built-ins first");
  assert.match(finalizeBody, /for \(const emoji of _userEmojiData\)[\s\S]*emojiMap\.set\(emoji\.emoji, emoji\)/, "_finalizeEmojis must allow user emoji overrides");
  assert.match(finalizeBody, /emojis = Array\.from\(emojiMap\.values\(\)\)/, "_finalizeEmojis must publish merged emoji data");
  assert.match(finalizeBody, /loaded = true/, "_finalizeEmojis must mark service loaded");
}

function testEmojiServiceUsagePersistenceAndClipboard() {
  const source = readQml("Services/Keyboard/EmojiService.qml");
  const loadUsageBody = extractFunctionBody(source, "_loadUsageData");
  const saveUsageBody = extractFunctionBody(source, "_saveUsageData");
  const doSaveBody = extractFunctionBody(source, "_doSaveUsageData");
  const copyBody = extractFunctionBody(source, "copy");

  assert.match(loadUsageBody, /usageFile\.reload\(\)/, "_loadUsageData must reload persisted usage data");
  assert.match(saveUsageBody, /saveTimer\.restart\(\)/, "_saveUsageData must debounce writes");
  assert.match(doSaveBody, /const content = JSON\.stringify\(root\.usageCounts\)/, "_doSaveUsageData must serialize usage counts");
  assert.match(doSaveBody, /Quickshell\.execDetached\(\["sh", "-c", `mkdir -p "\$\(dirname "\$\{root\.usageFilePath\}"\)" && echo '\$\{content\}' > "\$\{root\.usageFilePath\}"`\]\)/, "_doSaveUsageData must create the directory and write JSON");
  assert.match(doSaveBody, /Logger\.e\("EmojiService", "Failed to save usage data: " \+ e\.message\)/, "_doSaveUsageData must log save errors");
  assert.match(copyBody, /if \(emojiChar\)/, "copy must ignore empty emoji values");
  assert.match(copyBody, /recordUsage\(emojiChar\)/, "copy must record usage before copying");
  assert.match(copyBody, /echo -n "\$\{emojiChar\}" \| wl-copy/, "copy must write the emoji to wl-copy");
}

function testEmojiServiceSearchExecutesMatchingAndPopularFallback() {
  const search = qmlFunction("search", "query");
  const getPopularEmojis = qmlFunction("_getPopularEmojis", "limit");
  const ctx = {
    loaded: true,
    usageCounts: { "fire": 4, "grin": 2 },
    emojis: [
      { emoji: "grin", name: "grinning face", keywords: ["happy", "smile"], category: "people" },
      { emoji: "fire", name: "fire", keywords: ["hot", "lit"], category: "symbols" },
      { emoji: "seed", name: "seedling", keywords: ["plant", "garden"], category: "nature" },
    ],
    _getPopularEmojis(limit) {
      return getPopularEmojis(ctx, limit);
    },
  };

  assert.deepEqual(search({ ...ctx, loaded: false }, "fire"), [], "search must fail closed while unloaded");
  assert.deepEqual(
    search(ctx, ""),
    [ctx.emojis[1], ctx.emojis[0]],
    "blank search must return popular emojis by usage",
  );
  assert.deepEqual(
    search(ctx, "hot symbols"),
    [ctx.emojis[1]],
    "search must require every term to match a field",
  );
  assert.deepEqual(search(ctx, "garden"), [ctx.emojis[2]], "search must match keywords");
  assert.deepEqual(search(ctx, "missing"), [], "search must omit nonmatching emojis");
}

function testEmojiServiceCategoryAndUsageHelpersExecute() {
  const getCategoriesWithCounts = qmlFunction("getCategoriesWithCounts");
  const getEmojisByCategory = qmlFunction("getEmojisByCategory", "category");
  const recordUsage = qmlFunction("recordUsage", "emojiChar");
  const saveCalls = [];
  const ctx = {
    loaded: true,
    usageCounts: { grin: 1 },
    emojis: [
      { emoji: "grin", name: "grinning face", keywords: [], category: "people" },
      { emoji: "smile", name: "smiling face", keywords: [], category: "people" },
      { emoji: "question", name: "question", keywords: [] },
    ],
    _getPopularEmojis(limit) {
      return this.emojis.slice(0, limit);
    },
    _saveUsageData() {
      saveCalls.push({ ...this.usageCounts });
    },
  };

  assert.deepEqual(
    getCategoriesWithCounts({ ...ctx, loaded: false }),
    [],
    "categories must fail closed while unloaded",
  );
  assert.deepEqual(getCategoriesWithCounts(ctx), [
    { name: "people", count: 2 },
    { name: "other", count: 1 },
  ]);
  assert.deepEqual(getEmojisByCategory(ctx, "people"), [ctx.emojis[0], ctx.emojis[1]]);
  assert.deepEqual(
    getEmojisByCategory(ctx, "recent"),
    ctx.emojis,
    "recent category must use popular emoji fallback",
  );

  recordUsage(ctx, "grin");
  recordUsage(ctx, "fire");
  recordUsage(ctx, "");
  assert.deepEqual(
    ctx.usageCounts,
    { grin: 2, fire: 1 },
    "recordUsage must increment existing and new emoji counts",
  );
  assert.equal(saveCalls.length, 2, "recordUsage must save only nonempty emoji usage");
}

const tests = [
  testEmojiServiceSearchAndPopularResults,
  testEmojiServiceCategoriesAndUsage,
  testEmojiServiceFileLoadingAndFinalization,
  testEmojiServiceUsagePersistenceAndClipboard,
  testEmojiServiceSearchExecutesMatchingAndPopularFallback,
  testEmojiServiceCategoryAndUsageHelpersExecute,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
