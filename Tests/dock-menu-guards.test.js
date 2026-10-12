#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Dock/DockMenu.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function(
    "ctx",
    ...argNames,
    `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`,
  );
}

function createMenuContext() {
  const events = [];
  const later = [];
  const ctx = {
    events,
    later,
    items: [],
    visible: true,
    menuContentWidth: 0,
    toplevel: null,
    onAppClosed: null,
    Style: { marginS: 4, marginM: 8, fontSizeL: 20 },
    Settings: { data: { dock: { pinnedApps: [] } } },
    ToplevelManager: { toplevels: { values: [] } },
    I18n: { tr: (key) => key },
    Qt: { callLater: (callback) => later.push(callback) },
    textMeasure: {
      text: "",
      contentWidth: 0,
      forceLayout() {
        this.contentWidth = this.text.length * 10;
      },
    },
    requestClose() {
      events.push("request-close");
    },
  };
  ctx.root = ctx;
  const signatures = {
    calculateMenuWidth: [],
    initItems: [],
    normalizeAppId: ["appId"],
    getDesktopEntryId: ["appId"],
    isAppPinned: ["appId"],
    toggleAppPin: ["appId"],
    hide: [],
    getHoveredItem: ["mouseY"],
    handleFocus: [],
    handlePin: [],
    handleClose: [],
  };
  for (const [name, args] of Object.entries(signatures)) {
    const execute = qmlFunction(name, ...args);
    ctx[name] = (...values) => execute(ctx, ...values);
  }
  return ctx;
}

function testDockMenuWidthAndItems() {
  const ctx = createMenuContext();
  const actions = ["New window", "Private window"].map((name) => ({
    name,
    execute() {
      ctx.events.push(name);
    },
  }));
  ctx.DesktopEntries = {
    heuristicLookup(appId) {
      assert.equal(appId, "firefox");
      return { actions };
    },
    byId() {
      throw new Error("heuristic lookup should resolve Firefox");
    },
  };
  ctx.toplevel = {
    appId: "firefox",
    activate() {
      ctx.events.push("activate");
    },
    close() {
      ctx.events.push("close");
    },
  };
  ctx.ToplevelManager.toplevels.values = [ctx.toplevel];
  ctx.initItems();
  assert.deepEqual(
    ctx.items.map(({ icon, text }) => [icon, text]),
    [
      ["eye", "dock.menu.focus"],
      ["pin", "dock.menu.pin"],
      ["close", "dock.menu.close"],
      ["", "New window"],
      ["", "Private window"],
    ],
  );
  assert.equal(
    ctx.menuContentWidth,
    0,
    "measurement is deferred until publication",
  );
  assert.equal(ctx.later.length, 1);
  ctx.later.shift()();
  assert.equal(
    ctx.menuContentWidth,
    182,
    "margins, icon, spacing and measured text contribute",
  );
  for (const item of ctx.items.slice()) item.action();
  assert.deepEqual(ctx.events, [
    "activate",
    "request-close",
    "request-close",
    "close",
    "request-close",
    "New window",
    "Private window",
  ]);
  assert.deepEqual(ctx.Settings.data.dock.pinnedApps, ["firefox"]);

  ctx.ToplevelManager.toplevels.values = [];
  ctx.DesktopEntries = { byId: () => ({ actions }) };
  ctx.initItems();
  assert.deepEqual(
    ctx.items.map(({ icon, text }) => [icon, text]),
    [
      ["unpin", "dock.menu.unpin"],
      ["", "New window"],
      ["", "Private window"],
    ],
  );
  ctx.items[1].action();
  ctx.items[2].action();
  assert.deepEqual(ctx.events.slice(-2), ["New window", "Private window"]);
  ctx.DesktopEntries.byId = () => null;
  ctx.initItems();
  assert.equal(ctx.items.length, 1);
  ctx.toplevel = null;
  ctx.initItems();
  assert.deepEqual(
    ctx.items.map((item) => item.icon),
    ["pin"],
  );

  for (const items of [[], null, [null, {}]]) {
    ctx.items = items;
    ctx.calculateMenuWidth();
    assert.equal(ctx.menuContentWidth, 160);
  }
  ctx.items = [{ text: "abcdefghijklmnopqrst" }];
  ctx.calculateMenuWidth();
  assert.equal(
    ctx.menuContentWidth,
    208,
    "iconless items include only margins and text",
  );
}

function testDockMenuPinHelpers() {
  const ctx = createMenuContext();
  for (const invalid of [null, undefined, "", 42, {}])
    assert.equal(ctx.normalizeAppId(invalid), "");
  assert.equal(ctx.normalizeAppId(" Firefox "), "firefox");
  assert.equal(ctx.getDesktopEntryId(null), null);
  assert.equal(ctx.getDesktopEntryId("original"), "original");
  ctx.DesktopEntries = {
    heuristicLookup: () => ({ id: "Canonical.desktop" }),
    byId: () => ({ id: "Direct.desktop" }),
  };
  assert.equal(ctx.getDesktopEntryId("app"), "Canonical.desktop");
  ctx.DesktopEntries.heuristicLookup = () => null;
  assert.equal(ctx.getDesktopEntryId("app"), "Direct.desktop");
  ctx.DesktopEntries.heuristicLookup = () => {
    throw new Error("lookup unavailable");
  };
  assert.equal(ctx.getDesktopEntryId("app"), "Direct.desktop");
  ctx.DesktopEntries.byId = () => {
    throw new Error("entry unavailable");
  };
  assert.equal(ctx.getDesktopEntryId("original"), "original");
  ctx.Settings.data.dock.pinnedApps = undefined;
  assert.equal(ctx.isAppPinned("app"), false);
  assert.equal(ctx.isAppPinned(null), false);
  ctx.toggleAppPin(null);
  assert.equal(ctx.Settings.data.dock.pinnedApps, undefined);
  ctx.DesktopEntries.heuristicLookup = () => ({ id: "Canonical.desktop" });
  const original = ["OTHER.desktop"];
  ctx.Settings.data.dock.pinnedApps = original;
  ctx.toggleAppPin("app");
  assert.deepEqual(
    original,
    ["OTHER.desktop"],
    "pin updates must not mutate previous settings array",
  );
  assert.deepEqual(ctx.Settings.data.dock.pinnedApps, [
    "OTHER.desktop",
    "Canonical.desktop",
  ]);
  assert.equal(ctx.isAppPinned(" CANONICAL.DESKTOP "), true);
  const pinned = ctx.Settings.data.dock.pinnedApps;
  ctx.toggleAppPin("app");
  assert.deepEqual(ctx.Settings.data.dock.pinnedApps, ["OTHER.desktop"]);
  assert.deepEqual(pinned, ["OTHER.desktop", "Canonical.desktop"]);
}

function testDockMenuActionsAndHovering() {
  const ctx = createMenuContext();
  ctx.handleFocus();
  ctx.handlePin();
  ctx.items = [{}, {}];
  ctx.onAppClosed = () => ctx.events.push("refresh");
  const stale = {
    appId: "stale",
    close() {
      throw new Error("stale toplevel closed");
    },
  };
  ctx.toplevel = stale;
  ctx.handleClose();
  assert.deepEqual(ctx.events, [
    "request-close",
    "request-close",
    "request-close",
  ]);
  assert.equal(ctx.visible, false);
  assert.deepEqual(ctx.items, []);
  assert.deepEqual(ctx.later, []);
  ctx.toplevel = {
    close() {
      ctx.events.push("close");
    },
  };
  ctx.ToplevelManager.toplevels.values = [ctx.toplevel];
  ctx.visible = true;
  ctx.handleClose();
  assert.deepEqual(ctx.events.slice(-2), ["close", "request-close"]);
  assert.equal(ctx.visible, false);
  assert.equal(ctx.later.length, 1);
  ctx.later.shift()();
  assert.equal(ctx.events.at(-1), "refresh");
  ctx.onAppClosed = "not a callback";
  ctx.handleClose();
  assert.deepEqual(ctx.later, []);
}

function testDockMenuHoveredItemComputesBounds() {
  const ctx = createMenuContext();
  ctx.items = [{}, {}, {}];
  for (const [y, index] of [
    [7, -1],
    [8, 0],
    [39, 0],
    [40, 1],
    [103, 2],
    [104, -1],
  ]) {
    assert.equal(ctx.getHoveredItem(y), index);
  }
}

const tests = [
  testDockMenuWidthAndItems,
  testDockMenuPinHelpers,
  testDockMenuActionsAndHovering,
  testDockMenuHoveredItemComputesBounds,
];
for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
