#!/usr/bin/env node

const assert = require("assert/strict");
const {
  extractComponentBlocks,
  extractFunctionBody,
  extractHandlerBlock,
  findComponentBlock,
  readQml,
} = require("./qml-test-utils");

const source = readQml("Widgets/NSearchableComboBox.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function(
    "ctx",
    ...argNames,
    `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`,
  );
}

function createListModel(items = []) {
  return {
    items: [...items],
    get count() {
      return this.items.length;
    },
    get(index) {
      return this.items[index];
    },
    append(item) {
      this.items.push(item);
    },
    clear() {
      this.items = [];
    },
  };
}

function createContext({
  modelItems = [],
  filteredItems = [],
  searchText = "",
  Fuzzysort,
} = {}) {
  const ctx = {
    model: createListModel(modelItems),
    filteredModel: createListModel(filteredItems),
    searchText,
  };
  ctx.root = ctx;

  if (Fuzzysort) {
    ctx.Fuzzysort = Fuzzysort;
  }

  return ctx;
}

function testSearchableComboBoxFindIndexByKeyReturnsFirstMatchAndMissingSentinel() {
  const findIndexByKey = qmlFunction("findIndexByKey", "key");
  const ctx = createContext({
    modelItems: [
      { key: "wifi", name: "Wi-Fi" },
      { key: "bt", name: "Bluetooth" },
      { key: "wifi", name: "Duplicate Wi-Fi" },
    ],
  });

  assert.equal(findIndexByKey(ctx, "wifi"), 0);
  assert.equal(findIndexByKey(ctx, "bt"), 1);
  assert.equal(findIndexByKey(ctx, "missing"), -1);
}

function testSearchableComboBoxFindIndexByKeyInFilteredUsesFilteredModelOnly() {
  const findIndexByKeyInFiltered = qmlFunction(
    "findIndexByKeyInFiltered",
    "key",
  );
  const ctx = createContext({
    modelItems: [{ key: "wifi", name: "Wi-Fi" }],
    filteredItems: [
      { key: "audio", name: "Audio" },
      { key: "display", name: "Display" },
    ],
  });

  assert.equal(findIndexByKeyInFiltered(ctx, "display"), 1);
  assert.equal(findIndexByKeyInFiltered(ctx, "wifi"), -1);
}

function testSearchableComboBoxKeyLookupKeepsDistinctStringKeys() {
  const ctx = createContext({
    modelItems: [
      { key: "01", name: "First" },
      { key: "1", name: "Second" },
    ],
    filteredItems: [
      { key: "1", name: "Second" },
      { key: "01", name: "First" },
    ],
  });
  assert.equal(qmlFunction("findIndexByKey", "key")(ctx, "01"), 0);
  assert.equal(qmlFunction("findIndexByKeyInFiltered", "key")(ctx, "01"), 1);
  assert.equal(qmlFunction("findIndexByKey", "key")(ctx, 1), -1);
}

function testSearchableComboBoxFilterModelClearsAndReturnsForMissingOrEmptyModel() {
  const filterModel = qmlFunction("filterModel");
  const ctx = createContext({
    filteredItems: [{ key: "stale", name: "Stale" }],
  });

  ctx.model = null;
  filterModel(ctx);
  assert.deepEqual(ctx.filteredModel.items, []);

  ctx.filteredModel.append({ key: "stale", name: "Stale" });
  ctx.model = createListModel([]);
  filterModel(ctx);
  assert.deepEqual(ctx.filteredModel.items, []);
}

function testSearchableComboBoxFilterModelCopiesAllItemsForBlankSearch() {
  const filterModel = qmlFunction("filterModel");
  const ctx = createContext({
    searchText: "  ",
    filteredItems: [{ key: "stale", name: "Stale" }],
    modelItems: [
      { key: "wifi", name: "Wi-Fi" },
      { key: "display", name: "Display" },
    ],
  });

  filterModel(ctx);

  assert.deepEqual(ctx.filteredModel.items, [
    { key: "wifi", name: "Wi-Fi" },
    { key: "display", name: "Display" },
  ]);
}

function testSearchableComboBoxFilterModelFallsBackToCaseInsensitiveNameSearch() {
  const filterModel = qmlFunction("filterModel");
  const ctx = createContext({
    searchText: "wi",
    modelItems: [
      { key: "display", name: "Display" },
      { key: "wifi", name: "Wi-Fi" },
      { key: "wireguard", name: "WireGuard" },
    ],
  });

  filterModel(ctx);

  assert.deepEqual(ctx.filteredModel.items, [
    { key: "wifi", name: "Wi-Fi" },
    { key: "wireguard", name: "WireGuard" },
  ]);
}

function testSearchableComboBoxFilterModelUsesFuzzyResultOrdering() {
  const filterModel = qmlFunction("filterModel");
  const fuzzyCalls = [];
  const ctx = createContext({
    searchText: "net",
    modelItems: [
      { key: "network", name: "Network" },
      { key: "ethernet", name: "Ethernet" },
    ],
    Fuzzysort: {
      go(searchText, items, options) {
        fuzzyCalls.push({ searchText, items, options });
        return [{ obj: items[1] }, { obj: items[0] }];
      },
    },
  });

  filterModel(ctx);

  assert.equal(fuzzyCalls.length, 1);
  assert.equal(fuzzyCalls[0].searchText, "net");
  assert.deepEqual(fuzzyCalls[0].options, {
    key: "name",
    threshold: -1000,
    limit: 50,
  });
  assert.deepEqual(ctx.filteredModel.items, [
    { key: "ethernet", name: "Ethernet" },
    { key: "network", name: "Network" },
  ]);
}

function evaluateBinding(block, property, ctx) {
  const match = block.match(new RegExp(`^\\s*${property}:\\s*(.+)$`, "m"));
  assert.ok(match, `missing ${property} binding`);
  return new Function("ctx", `with (ctx) { return (${match[1]}); }`)(ctx);
}

function executeHandler(block, handler, ctx) {
  const declaration = extractHandlerBlock(block, handler);
  const body = declaration.slice(declaration.indexOf("{"));
  return new Function(
    "ctx",
    `with (ctx) { return (function() ${body}).call(ctx); }`,
  )(ctx);
}

function testSearchableComboBoxDefaultDelegateSelectsOwnRolesAndBadges() {
  const inlineComponents = source.replace(/component (\w+): \w+\s*\{/g, "$1 {");
  const option = extractComponentBlocks(inlineComponents, "SearchOption")[0];
  const badge = extractComponentBlocks(inlineComponents, "Badge")[0];
  const defaults = findComponentBlock(
    source,
    "Component",
    "id: defaultDelegate",
  );
  const selected = [];
  const owner = createContext({
    filteredItems: [{ key: "display", name: "Display" }],
  });
  owner.selected = (key) => selected.push(key);
  owner.findIndexByKeyInFiltered = (key) =>
    qmlFunction("findIndexByKeyInFiltered", "key")(owner, key);
  let closes = 0;
  const combo = {
    currentIndex: -1,
    popup: {
      close() {
        closes++;
      },
    },
  };
  const view = { width: 320, currentIndex: -1 };
  const ownerScope = { root: owner, combo, listView: view };
  const delegateRoot = {
    widgetOwner: evaluateBinding(defaults, "widgetOwner", ownerScope),
    parentComboBox: evaluateBinding(defaults, "parentComboBox", ownerScope),
    ownerView: evaluateBinding(defaults, "ownerView", ownerScope),
    ListView: { view },
    index: 0,
    key: "display",
    name: "Display",
    hovered: false,
    model: { badgeLocations: ["DP-1", "HDMI-A-1"] },
  };
  const scope = { delegateRoot };
  assert.equal(evaluateBinding(option, "width", scope), 320);
  assert.equal(
    evaluateBinding(extractComponentBlocks(option, "NText")[0], "text", scope),
    "Display",
  );
  executeHandler(option, "onHoveredChanged", scope);
  assert.equal(view.currentIndex, -1);
  delegateRoot.hovered = true;
  executeHandler(option, "onHoveredChanged", scope);
  assert.equal(view.currentIndex, 0);
  assert.equal(evaluateBinding(option, "highlighted", scope), true);
  executeHandler(option, "onClicked", scope);
  assert.deepEqual(selected, ["display"]);
  assert.equal(combo.currentIndex, 0);
  assert.equal(closes, 1);
  const repeater = extractComponentBlocks(option, "Repeater")[0];
  const badges = evaluateBinding(repeater, "model", scope);
  const text = extractComponentBlocks(badge, "NText")[0];
  assert.deepEqual(
    badges.map((modelData) =>
      evaluateBinding(text, "text", {
        badgeDelegate: { modelData },
      }),
    ),
    ["DP-1", "HDMI-A-1"],
  );
  delegateRoot.model = {};
  assert.deepEqual(evaluateBinding(repeater, "model", scope), []);
}

function testSearchableComboBoxCurrentSelectionHelpersExecute() {
  const filteredKeyAt = qmlFunction("filteredKeyAt", "index");
  const activateCurrentSelection = qmlFunction("activateCurrentSelection");
  const selectedKeys = [];
  const ctx = createContext({
    filteredItems: [
      { key: "wifi", name: "Wi-Fi" },
      { key: "display", name: "Display" },
    ],
  });
  ctx.combo = { currentIndex: 1 };
  ctx.filteredKeyAt = (index) => filteredKeyAt(ctx, index);
  ctx.selected = (key) => selectedKeys.push(key);

  assert.equal(filteredKeyAt(ctx, -1), "");
  assert.equal(filteredKeyAt(ctx, 2), "");
  assert.equal(filteredKeyAt(ctx, 1), "display");

  activateCurrentSelection(ctx);
  assert.deepEqual(selectedKeys, ["display"]);

  ctx.combo.currentIndex = -1;
  activateCurrentSelection(ctx);
  assert.deepEqual(selectedKeys, ["display"]);
}

function testSearchableComboBoxCurrentKeySyncExecutes() {
  const syncCurrentIndexToCurrentKey = qmlFunction(
    "syncCurrentIndexToCurrentKey",
  );
  const ctx = createContext({
    filteredItems: [
      { key: "audio", name: "Audio" },
      { key: "network", name: "Network" },
    ],
  });
  ctx.currentKey = "network";
  ctx.combo = { currentIndex: -1 };
  ctx.findIndexByKeyInFiltered = (key) =>
    qmlFunction("findIndexByKeyInFiltered", "key")(ctx, key);

  syncCurrentIndexToCurrentKey(ctx);
  assert.equal(ctx.combo.currentIndex, 1);

  ctx.currentKey = "missing";
  syncCurrentIndexToCurrentKey(ctx);
  assert.equal(ctx.combo.currentIndex, -1);
}

function testSearchableComboBoxPopupOpenFiltersAndFocusesSearch() {
  const handlePopupOpened = qmlFunction("handlePopupOpened");
  const events = [];
  const ctx = createContext();
  ctx.filterModel = () => events.push("filter");
  ctx.searchInput = {
    inputItem: {
      forceActiveFocus() {
        events.push("focus");
      },
    },
  };
  ctx.Qt = {
    callLater(callback) {
      events.push("scheduled");
      callback();
    },
  };

  handlePopupOpened(ctx);
  assert.deepEqual(events, ["filter", "scheduled", "focus"]);

  events.length = 0;
  ctx.searchInput = null;
  handlePopupOpened(ctx);
  assert.deepEqual(events, ["filter", "scheduled"]);
}

const tests = [
  testSearchableComboBoxFindIndexByKeyReturnsFirstMatchAndMissingSentinel,
  testSearchableComboBoxFindIndexByKeyInFilteredUsesFilteredModelOnly,
  testSearchableComboBoxKeyLookupKeepsDistinctStringKeys,
  testSearchableComboBoxFilterModelClearsAndReturnsForMissingOrEmptyModel,
  testSearchableComboBoxFilterModelCopiesAllItemsForBlankSearch,
  testSearchableComboBoxFilterModelFallsBackToCaseInsensitiveNameSearch,
  testSearchableComboBoxFilterModelUsesFuzzyResultOrdering,
  testSearchableComboBoxDefaultDelegateSelectsOwnRolesAndBadges,
  testSearchableComboBoxCurrentSelectionHelpersExecute,
  testSearchableComboBoxCurrentKeySyncExecutes,
  testSearchableComboBoxPopupOpenFiltersAndFocusesSearch,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
