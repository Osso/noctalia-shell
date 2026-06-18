#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/Tray.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    warnings: [],
    w(...args) {
      this.warnings.push(args);
    },
  };
}

function testTrayWidgetWildcardMatchHandlesEscapedRulesAndCase() {
  const wildCardMatch = qmlFunction("wildCardMatch", "str", "rule");
  const ctx = { Logger: createLogger() };

  assert.match(source, /function wildCardMatch\(str, rule\)/, "wildCardMatch must type string inputs");
  assert.equal(wildCardMatch(ctx, "Bluetooth Manager", "bluetooth*"), true);
  assert.equal(wildCardMatch(ctx, "org.kde.StatusNotifierItem-1", "org.kde.*-1"), true);
  assert.equal(wildCardMatch(ctx, "literal.plus", "literal.plus"), true);
  assert.equal(wildCardMatch(ctx, "literalXplus", "literal.plus"), false);
  assert.equal(wildCardMatch(ctx, "", "*"), false);
  assert.equal(wildCardMatch(ctx, "Network", ""), false);
  assert.deepEqual(ctx.Logger.warnings, []);
}

function testTrayWidgetFilteringShowsAllInlineWhenDrawerDisabled() {
  const performUpdate = qmlFunction("_performFilteredItemsUpdate");
  const network = { tooltipTitle: "Network" };
  const bluetooth = { name: "Bluetooth" };
  const hidden = { id: "Hidden App" };
  const ctx = {
    SystemTray: {
      items: {
        values: [network, null, bluetooth, hidden],
      },
    },
    root: null,
    blacklist: ["Hidden*"],
    drawerEnabled: false,
    pinned: [],
    filteredItems: [],
    dropdownItems: [],
    wildCardMatch(str, rule) {
      return qmlFunction("wildCardMatch", "str", "rule")({ Logger: createLogger() }, str, rule);
    },
  };
  ctx.root = ctx;

  performUpdate(ctx);

  assert.deepEqual(ctx.filteredItems, [network, bluetooth]);
  assert.deepEqual(ctx.dropdownItems, []);
}

function testTrayWidgetFilteringSplitsPinnedAndDropdownItems() {
  const performUpdate = qmlFunction("_performFilteredItemsUpdate");
  const network = { tooltipTitle: "Network" };
  const bluetooth = { name: "Bluetooth" };
  const updates = { id: "Updater" };
  const ctx = {
    SystemTray: {
      items: {
        values: [network, bluetooth, updates],
      },
    },
    root: null,
    blacklist: [],
    drawerEnabled: true,
    pinned: ["Blue*", "Network"],
    filteredItems: [],
    dropdownItems: [],
    wildCardMatch(str, rule) {
      return qmlFunction("wildCardMatch", "str", "rule")({ Logger: createLogger() }, str, rule);
    },
  };
  ctx.root = ctx;

  performUpdate(ctx);

  assert.deepEqual(ctx.filteredItems, [network, bluetooth]);
  assert.deepEqual(ctx.dropdownItems, [updates]);

  ctx.pinned = [];
  performUpdate(ctx);

  assert.deepEqual(ctx.filteredItems, []);
  assert.deepEqual(ctx.dropdownItems, [network, bluetooth, updates]);
}

function testTrayWidgetUpdateFilteredItemsRestartsDebounceTimer() {
  const updateFilteredItems = qmlFunction("updateFilteredItems");
  let restarts = 0;
  const ctx = {
    updateDebounceTimer: {
      restart() {
        restarts += 1;
      },
    },
  };

  updateFilteredItems(ctx);

  assert.equal(restarts, 1);
}

function testTrayWidgetToggleDrawerHidesTooltipClosesMenuAndDelegatesPanel() {
  const toggleDrawer = qmlFunction("toggleDrawer", "button");
  const events = [];
  const screen = { name: "HDMI-A-1" };
  const ctx = {
    TooltipService: {
      hideImmediately() {
        events.push("hide-tooltip");
      },
    },
    popupMenuWindow: {
      visible: true,
      close() {
        events.push("close-menu");
      },
    },
    PanelService: {
      getPanel(name, panelScreen) {
        assert.equal(name, "trayDrawerPanel");
        assert.equal(panelScreen, screen);
        return {
          widgetSection: "",
          widgetIndex: -1,
          toggle(item) {
            events.push(["toggle", item]);
            this.toggledWith = item;
          },
        };
      },
    },
    root: null,
    screen,
    section: "right",
    sectionWidgetIndex: 2,
  };
  ctx.root = ctx;

  toggleDrawer(ctx, { id: "button" });

  assert.equal(events[0], "hide-tooltip");
  assert.equal(events[1], "close-menu");
  assert.deepEqual(events[2], ["toggle", ctx]);
}

const tests = [
  testTrayWidgetWildcardMatchHandlesEscapedRulesAndCase,
  testTrayWidgetFilteringShowsAllInlineWhenDrawerDisabled,
  testTrayWidgetFilteringSplitsPinnedAndDropdownItems,
  testTrayWidgetUpdateFilteredItemsRestartsDebounceTimer,
  testTrayWidgetToggleDrawerHidesTooltipClosesMenuAndDelegatesPanel,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
