#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Extras/TrayMenu.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    warnings: [],
    w(scope, message) {
      this.warnings.push([scope, message]);
    },
  };
}

function createSettings(widgets) {
  let saveCalls = 0;
  return {
    data: {
      bar: {
        widgets,
      },
    },
    saveImmediate() {
      saveCalls += 1;
    },
    get saveCalls() {
      return saveCalls;
    },
  };
}

function testTrayMenuShowAtGuardsMissingAnchorAndWaitsForMenuChildren() {
  const showAt = qmlFunction("showAt", "item", "x", "y");
  const logger = createLogger();
  const laterCalls = [];
  const ctx = {
    Logger: logger,
    opener: {
      children: {
        values: [],
      },
    },
    Qt: {
      callLater(callback) {
        laterCalls.push(callback);
      },
    },
    showAt(item, x, y) {
      laterCalls.push(["retry", item, x, y]);
    },
    anchorItem: null,
    visible: false,
  };
  const anchor = { id: "tray-anchor" };

  showAt(ctx, null, 10, 20);
  showAt(ctx, anchor, 10, 20);
  laterCalls[0]();

  assert.deepEqual(logger.warnings, [["TrayMenu", "anchorItem is undefined, won't show menu."]]);
  assert.deepEqual(laterCalls[1], ["retry", anchor, 10, 20]);
  assert.equal(ctx.anchorItem, null);
  assert.equal(ctx.visible, false);
}

function testTrayMenuShowAtPositionsAndUpdatesAnchor() {
  const showAt = qmlFunction("showAt", "item", "x", "y");
  let focused = 0;
  let anchorUpdates = 0;
  const anchor = { id: "tray-anchor" };
  const ctx = {
    Logger: createLogger(),
    opener: {
      children: {
        values: [{}],
      },
    },
    Qt: {
      callLater(callback) {
        callback();
      },
    },
    root: {
      anchor: {
        updateAnchor() {
          anchorUpdates += 1;
        },
      },
    },
    forceActiveFocus() {
      focused += 1;
    },
    anchorItem: null,
    anchorX: 0,
    anchorY: 0,
    visible: false,
  };

  showAt(ctx, anchor, 12, 34);

  assert.equal(ctx.anchorItem, anchor);
  assert.equal(ctx.anchorX, 12);
  assert.equal(ctx.anchorY, 34);
  assert.equal(ctx.visible, true);
  assert.equal(focused, 1);
  assert.equal(anchorUpdates, 1);
}

function testTrayMenuHideMenuDestroysNestedSubmenus() {
  const hideMenu = qmlFunction("hideMenu");
  const calls = [];
  const childWithSubMenu = {
    subMenu: {
      hideMenu() {
        calls.push("hide");
      },
      destroy() {
        calls.push("destroy");
      },
    },
  };
  const ctx = {
    visible: true,
    columnLayout: {
      children: [
        null,
        {},
        childWithSubMenu,
      ],
    },
  };

  hideMenu(ctx);

  assert.equal(ctx.visible, false);
  assert.deepEqual(calls, ["hide", "destroy"]);
  assert.equal(childWithSubMenu.subMenu, null);
}

function testTrayMenuAddToPinnedValidatesAndPersistsTrayWidget() {
  const addToPinned = qmlFunction("addToPinned");
  const logger = createLogger();
  const settings = createSettings({
    right: [{ id: "Tray", pinned: ["Network"] }],
  });
  let panelClosed = 0;
  const screen = { name: "HDMI-A-1" };
  const ctx = {
    Logger: logger,
    Settings: settings,
    PanelService: {
      getPanel(name, panelScreen) {
        assert.equal(name, "trayDrawerPanel");
        assert.equal(panelScreen, screen);
        return {
          close() {
            panelClosed += 1;
          },
        };
      },
    },
    trayItem: { tooltipTitle: "Bluetooth", name: "Ignored", id: "ignored" },
    widgetSection: "right",
    widgetIndex: 0,
    screen,
  };

  addToPinned(ctx);

  assert.deepEqual(settings.data.bar.widgets.right[0], {
    id: "Tray",
    pinned: ["Network", "Bluetooth"],
  });
  assert.equal(settings.saveCalls, 1);
  assert.equal(panelClosed, 1);
  assert.deepEqual(logger.warnings, []);
}

function testTrayMenuAddToPinnedRejectsInvalidInputs() {
  const addToPinned = qmlFunction("addToPinned");
  const logger = createLogger();
  const settings = createSettings({
    right: [{ id: "Tray", pinned: [] }],
  });
  const ctx = {
    Logger: logger,
    Settings: settings,
    PanelService: {
      getPanel() {
        throw new Error("panel lookup should not run");
      },
    },
    trayItem: null,
    widgetSection: "right",
    widgetIndex: 0,
    screen: {},
  };

  addToPinned(ctx);
  ctx.trayItem = {};
  addToPinned(ctx);
  ctx.trayItem = { id: "Network" };
  ctx.widgetIndex = 99;
  addToPinned(ctx);
  ctx.widgetIndex = 0;
  settings.data.bar.widgets.right[0] = { id: "Clock" };
  addToPinned(ctx);

  assert.deepEqual(logger.warnings, [
    ["TrayMenu", "Cannot pin: missing tray item or widget info"],
    ["TrayMenu", "Cannot pin: tray item has no name"],
    ["TrayMenu", "Cannot pin: invalid widget index"],
    ["TrayMenu", "Cannot pin: widget is not a Tray widget"],
  ]);
  assert.equal(settings.saveCalls, 0);
}

function testTrayMenuRemoveFromPinnedFiltersItemAndSaves() {
  const removeFromPinned = qmlFunction("removeFromPinned");
  const settings = createSettings({
    left: [{ id: "Tray", pinned: ["Network", "Bluetooth", "Network"] }],
  });
  const ctx = {
    Logger: createLogger(),
    Settings: settings,
    trayItem: { name: "Network" },
    widgetSection: "left",
    widgetIndex: 0,
  };

  removeFromPinned(ctx);

  assert.deepEqual(settings.data.bar.widgets.left[0], {
    id: "Tray",
    pinned: ["Bluetooth"],
  });
  assert.equal(settings.saveCalls, 1);
}

const tests = [
  testTrayMenuShowAtGuardsMissingAnchorAndWaitsForMenuChildren,
  testTrayMenuShowAtPositionsAndUpdatesAnchor,
  testTrayMenuHideMenuDestroysNestedSubmenus,
  testTrayMenuAddToPinnedValidatesAndPersistsTrayWidget,
  testTrayMenuAddToPinnedRejectsInvalidInputs,
  testTrayMenuRemoveFromPinnedFiltersItemAndSaves,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
