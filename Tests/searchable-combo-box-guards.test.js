#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Widgets/NSearchableComboBox.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
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

function createContext({ modelItems = [], filteredItems = [], searchText = "", Fuzzysort } = {}) {
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
  const findIndexByKeyInFiltered = qmlFunction("findIndexByKeyInFiltered", "key");
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

function testSearchableComboBoxKeyLookupInputsAreTyped() {
  assert.match(source, /function findIndexByKey\(key\)/, "findIndexByKey must type the key input");
  assert.match(source, /function findIndexByKeyInFiltered\(key\)/, "findIndexByKeyInFiltered must type the key input");
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

function testSearchableComboBoxDefaultDelegateRolesAreTyped() {
  const defaultDelegate = /Component\s*\{[\s\S]*?id:\s*defaultDelegate[\s\S]*?ItemDelegate\s*\{/;
  const typedItemRoles = /required\s+property\s+int\s+index[\s\S]*?required\s+property\s+string\s+key[\s\S]*?required\s+property\s+string\s+name/;
  const typedRoleUsage = /root\.selected\(key\)[\s\S]*?findIndexByKeyInFiltered\(key\)[\s\S]*?text:\s*delegateRoot\.name/;
  const typedBadgeText = /Repeater\s*\{[\s\S]*?delegate:\s*Item\s*\{[\s\S]*?required\s+property\s+string\s+modelData[\s\S]*?text:\s*modelData/;

  assert.match(source, defaultDelegate, "default delegate must be present");
  assert.match(source, typedItemRoles, "default delegate must type key/name/index roles");
  assert.match(source, typedRoleUsage, "default delegate must use typed roles for selection and label text");
  assert.match(source, typedBadgeText, "default delegate must type badge modelData");
}

function testSearchableComboBoxCurrentSelectionHelpersExecute() {
  assert.match(source, /function filteredKeyAt\(index\)/, "filteredKeyAt must type index input");
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
  ctx.filteredKeyAt = index => filteredKeyAt(ctx, index);
  ctx.selected = key => selectedKeys.push(key);

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
  const syncCurrentIndexToCurrentKey = qmlFunction("syncCurrentIndexToCurrentKey");
  const ctx = createContext({
    filteredItems: [
      { key: "audio", name: "Audio" },
      { key: "network", name: "Network" },
    ],
  });
  ctx.currentKey = "network";
  ctx.combo = { currentIndex: -1 };
  ctx.findIndexByKeyInFiltered = key => qmlFunction("findIndexByKeyInFiltered", "key")(ctx, key);

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
  testSearchableComboBoxKeyLookupInputsAreTyped,
  testSearchableComboBoxFilterModelClearsAndReturnsForMissingOrEmptyModel,
  testSearchableComboBoxFilterModelCopiesAllItemsForBlankSearch,
  testSearchableComboBoxFilterModelFallsBackToCaseInsensitiveNameSearch,
  testSearchableComboBoxFilterModelUsesFuzzyResultOrdering,
  testSearchableComboBoxDefaultDelegateRolesAreTyped,
  testSearchableComboBoxCurrentSelectionHelpersExecute,
  testSearchableComboBoxCurrentKeySyncExecutes,
  testSearchableComboBoxPopupOpenFiltersAndFocusesSearch,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
