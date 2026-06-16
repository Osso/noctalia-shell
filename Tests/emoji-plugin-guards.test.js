#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Launcher/Plugins/EmojiPlugin.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testEmojiPluginInitializationAndCategorySelection() {
  const init = qmlFunction("init");
  const selectCategory = qmlFunction("selectCategory", "category");
  const logs = [];
  let updates = 0;
  const ctx = {
    Logger: {
      i(scope, message) {
        logs.push([scope, message]);
      },
    },
    launcher: {
      updateResults() {
        updates++;
      },
    },
    selectedCategory: "recent",
  };

  init(ctx);
  selectCategory(ctx, "animals");

  assert.deepEqual(logs, [["EmojiPlugin", "Initialized"]]);
  assert.equal(ctx.selectedCategory, "animals");
  assert.equal(updates, 1);

  ctx.launcher = null;
  selectCategory(ctx, "food");
  assert.equal(ctx.selectedCategory, "food");
  assert.equal(updates, 1);
}

function testEmojiPluginCommandEntryPoints() {
  const handleCommand = qmlFunction("handleCommand", "searchText");
  const commands = qmlFunction("commands");
  const searches = [];
  const ctx = {
    I18n: {
      tr(key) {
        return `tr:${key}`;
      },
    },
    launcher: {
      setSearchText(text) {
        searches.push(text);
      },
    },
  };

  assert.equal(handleCommand(ctx, ">emoji smile"), true);
  assert.equal(handleCommand(ctx, "emoji smile"), false);

  const [command] = commands(ctx);
  assert.equal(command.name, ">emoji");
  assert.equal(command.description, "tr:plugins.emoji-search-description");
  assert.equal(command.icon, "face-smile");
  assert.equal(command.isImage, false);
  command.onActivate();
  assert.deepEqual(searches, [">emoji "]);
}

function testEmojiPluginResultsGuards() {
  const getResults = qmlFunction("getResults", "searchText");
  const smiles = [{ emoji: "🙂", name: "Slight Smile", keywords: ["smile"], category: "people" }];
  const animals = [{ emoji: "🐈", name: "Cat", keywords: ["pet"], category: "animals" }];
  const ctx = {
    I18n: {
      tr(key) {
        return `tr:${key}`;
      },
    },
    EmojiService: {
      loaded: false,
      getEmojisByCategory(category) {
        assert.equal(category, "animals");
        return animals;
      },
      search(query) {
        assert.equal(query, "smile");
        return smiles;
      },
    },
    formatEmojiEntry(emoji) {
      return { name: emoji.name, emojiChar: emoji.emoji };
    },
    selectedCategory: "animals",
    isBrowsingMode: false,
  };

  assert.deepEqual(getResults(ctx, "hello"), []);

  const [loading] = getResults(ctx, ">emoji");
  assert.equal(loading.name, "tr:plugins.emoji-loading");
  assert.equal(loading.description, "tr:plugins.emoji-loading-description");
  assert.equal(loading.icon, "view-refresh");
  assert.equal(loading.isImage, false);
  loading.onActivate();

  ctx.EmojiService.loaded = true;
  assert.deepEqual(getResults(ctx, ">emoji "), [{ name: "Cat", emojiChar: "🐈" }]);
  assert.equal(ctx.isBrowsingMode, true);

  assert.deepEqual(getResults(ctx, ">emoji smile"), [{ name: "Slight Smile", emojiChar: "🙂" }]);
  assert.equal(ctx.isBrowsingMode, false);
}

function testEmojiPluginFormatEntryAndActivation() {
  const formatEmojiEntry = qmlFunction("formatEmojiEntry", "emoji");
  const copied = [];
  let closed = 0;
  const ctx = {
    EmojiService: {
      copy(emojiChar) {
        copied.push(emojiChar);
      },
    },
    launcher: {
      close() {
        closed++;
      },
    },
  };

  const result = formatEmojiEntry(ctx, {
    emoji: "🚀",
    name: "Rocket",
    keywords: ["ship", "launch"],
    category: "travel",
  });

  assert.equal(result.name, "Rocket");
  assert.equal(result.description, "ship, launch • Category: travel");
  assert.equal(result.icon, null);
  assert.equal(result.isImage, false);
  assert.equal(result.emojiChar, "🚀");

  result.onActivate();
  assert.deepEqual(copied, ["🚀"]);
  assert.equal(closed, 1);
}

const tests = [
  testEmojiPluginInitializationAndCategorySelection,
  testEmojiPluginCommandEntryPoints,
  testEmojiPluginResultsGuards,
  testEmojiPluginFormatEntryAndActivation,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
