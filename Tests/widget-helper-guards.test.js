#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const mediaMiniSource = readQml("Modules/Bar/Widgets/MediaMini.qml");
const notificationHistorySource = readQml("Modules/Bar/Widgets/NotificationHistory.qml");
const barBackgroundSource = readQml("Modules/MainScreen/Backgrounds/BarBackground.qml");
const panelBackgroundSource = readQml("Modules/MainScreen/Backgrounds/PanelBackground.qml");
const comboBoxSource = readQml("Widgets/NComboBox.qml");
const bluetoothDevicesSource = readQml("Modules/Panels/Bluetooth/BluetoothDevicesList.qml");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testMediaMiniTitleFormatsArtistFirst() {
  const getTitle = qmlFunction(mediaMiniSource, "getTitle");

  assert.equal(getTitle({
    showArtistFirst: true,
    MediaService: {
      trackArtist: "Sylvaine",
      trackTitle: "Mono No Aware",
    },
  }), "Sylvaine - Mono No Aware");
  assert.equal(getTitle({
    showArtistFirst: true,
    MediaService: {
      trackArtist: "",
      trackTitle: "Mono No Aware",
    },
  }), "Mono No Aware");
}

function testMediaMiniTitleFormatsTitleFirst() {
  const getTitle = qmlFunction(mediaMiniSource, "getTitle");

  assert.equal(getTitle({
    showArtistFirst: false,
    MediaService: {
      trackArtist: "Sylvaine",
      trackTitle: "Mono No Aware",
    },
  }), "Mono No Aware - Sylvaine");
  assert.equal(getTitle({
    showArtistFirst: false,
    MediaService: {
      trackArtist: "",
      trackTitle: "Mono No Aware",
    },
  }), "Mono No Aware");
}

function testNotificationHistoryUnreadCountHandlesDatesAndNumbers() {
  const computeUnreadCount = qmlFunction(notificationHistorySource, "computeUnreadCount");
  const rows = [
    { timestamp: new Date(1700000000000) },
    { timestamp: 1700000000500 },
    { timestamp: 1699999999999 },
  ];

  assert.equal(computeUnreadCount({
    NotificationService: {
      lastSeenTs: 1700000000000,
      historyList: {
        count: rows.length,
        get(index) {
          return rows[index];
        },
      },
    },
  }), 1);
}

function testBackgroundCornerRadiusMapsFlatCornersToZero() {
  const barGetCornerRadius = qmlFunction(barBackgroundSource, "getCornerRadius", "cornerState");
  const panelGetCornerRadius = qmlFunction(panelBackgroundSource, "getCornerRadius", "cornerState");

  assert.equal(barGetCornerRadius({ effectiveRadius: 8 }, -1), 0);
  assert.equal(barGetCornerRadius({ effectiveRadius: 8 }, 0), 8);
  assert.equal(panelGetCornerRadius({ effectiveRadius: 12 }, -1), 0);
  assert.equal(panelGetCornerRadius({ effectiveRadius: 12 }, 2), 12);
}

function testComboBoxItemCountSupportsCountedModelsArraysAndMissingModels() {
  const itemCount = qmlFunction(comboBoxSource, "itemCount");

  assert.equal(itemCount({ root: { model: null } }), 0);
  assert.equal(itemCount({ root: { model: { count: 4 } } }), 4);
  assert.equal(itemCount({ root: { model: ["one", "two", "three"] } }), 3);
  assert.equal(itemCount({ root: { model: { length: 8 } } }), 0);
}

function createComboBoxContext(model) {
  const itemCount = qmlFunction(comboBoxSource, "itemCount");
  const getItem = qmlFunction(comboBoxSource, "getItem", "index");
  const ctx = { root: { model } };
  ctx.itemCount = () => itemCount(ctx);
  ctx.getItem = index => getItem(ctx, index);
  return ctx;
}

function testComboBoxGetItemSupportsModelGetArraysAndMissingModels() {
  const getItem = qmlFunction(comboBoxSource, "getItem", "index");
  const rows = [{ key: "one" }, { key: "two" }];
  const listModel = {
    get(index) {
      return rows[index];
    },
  };

  assert.match(comboBoxSource, /function getItem\(index\)/, "getItem must type the model index input");
  assert.deepEqual(getItem(createComboBoxContext(listModel), 1), { key: "two" });
  assert.deepEqual(getItem(createComboBoxContext(rows), 0), { key: "one" });
  assert.equal(getItem(createComboBoxContext(null), 0), null);
  assert.equal(getItem(createComboBoxContext({ length: 2 }), 0), null);
}

function testComboBoxFindIndexByKeyFindsFirstMatchAndMissingSentinel() {
  const findIndexByKey = qmlFunction(comboBoxSource, "findIndexByKey", "key");
  const ctx = createComboBoxContext([
    { key: "alpha" },
    { key: "beta" },
    { key: "alpha" },
  ]);

  assert.match(comboBoxSource, /function findIndexByKey\(key\)/, "findIndexByKey must type the key input");
  assert.equal(findIndexByKey(ctx, "alpha"), 0);
  assert.equal(findIndexByKey(ctx, "beta"), 1);
  assert.equal(findIndexByKey(ctx, "missing"), -1);
}

function createComboBoxSelectionContext(items) {
  const selectedKeys = [];
  const ctx = createComboBoxContext(items);
  ctx.root = ctx;
  ctx.model = items;
  ctx.getItem = index => qmlFunction(comboBoxSource, "getItem", "index")(ctx, index);
  ctx.selectItem = (itemIndex, parentComboBox) => qmlFunction(comboBoxSource, "selectItem", "itemIndex", "parentComboBox")(ctx, itemIndex, parentComboBox);
  ctx.shouldDelayDelegateClick = listView => qmlFunction(comboBoxSource, "shouldDelayDelegateClick", "listView")(ctx, listView);
  ctx.selected = key => selectedKeys.push(key);
  return { ctx, selectedKeys };
}

function createParentComboBox() {
  const closeCalls = [];
  return {
    currentIndex: -1,
    popup: {
      close() {
        closeCalls.push("close");
      },
    },
    closeCalls,
  };
}

function testComboBoxActivationEmitsCurrentItemKey() {
  const activateCurrentIndex = qmlFunction(comboBoxSource, "activateCurrentIndex", "index");
  const { ctx, selectedKeys } = createComboBoxSelectionContext([
    { key: "alpha" },
    { name: "missing-key" },
    { key: "gamma" },
  ]);

  activateCurrentIndex(ctx, 2);
  activateCurrentIndex(ctx, 1);
  activateCurrentIndex(ctx, 99);

  assert.deepEqual(selectedKeys, ["gamma"]);
}

function testComboBoxDelegateClickSelectsAndClosesPopup() {
  const handleDelegateClick = qmlFunction(comboBoxSource, "handleDelegateClick", "itemIndex", "parentComboBox", "listView", "clickRetryTimer", "delegate");
  const { ctx, selectedKeys } = createComboBoxSelectionContext([
    { key: "alpha" },
    { key: "beta" },
  ]);
  const parentComboBox = createParentComboBox();

  handleDelegateClick(ctx, 1, parentComboBox, { flicking: false, moving: false }, null, { pendingClick: false });

  assert.deepEqual(selectedKeys, ["beta"]);
  assert.equal(parentComboBox.currentIndex, 1);
  assert.deepEqual(parentComboBox.closeCalls, ["close"]);
}

function testComboBoxDelegateClickDefersWhileListIsMoving() {
  const handleDelegateClick = qmlFunction(comboBoxSource, "handleDelegateClick", "itemIndex", "parentComboBox", "listView", "clickRetryTimer", "delegate");
  const { ctx, selectedKeys } = createComboBoxSelectionContext([{ key: "alpha" }]);
  const cancelCalls = [];
  const timerCalls = [];
  const delegate = { pendingClick: false };

  handleDelegateClick(ctx, 0, createParentComboBox(), {
    flicking: true,
    moving: false,
    cancelFlick() {
      cancelCalls.push("cancel");
    },
  }, {
    start() {
      timerCalls.push("start");
    },
  }, delegate);

  assert.deepEqual(selectedKeys, []);
  assert.equal(delegate.pendingClick, true);
  assert.deepEqual(cancelCalls, ["cancel"]);
  assert.deepEqual(timerCalls, ["start"]);
}

function testComboBoxPendingClickRetrySelectsAndClearsPendingFlag() {
  const retryPendingClick = qmlFunction(comboBoxSource, "retryPendingClick", "itemIndex", "parentComboBox", "listView", "clickRetryTimer", "delegate");
  const { ctx, selectedKeys } = createComboBoxSelectionContext([{ key: "alpha" }]);
  const parentComboBox = createParentComboBox();
  const delegate = { pendingClick: true };
  const timerCalls = [];

  retryPendingClick(ctx, 0, parentComboBox, { flicking: true, moving: false }, {
    restart() {
      timerCalls.push("restart");
    },
  }, delegate);
  retryPendingClick(ctx, 0, parentComboBox, { flicking: false, moving: false }, {
    restart() {
      timerCalls.push("unexpected");
    },
  }, delegate);
  retryPendingClick(ctx, 0, parentComboBox, { flicking: false, moving: false }, {
    restart() {
      timerCalls.push("unexpected");
    },
  }, delegate);

  assert.deepEqual(selectedKeys, ["alpha"]);
  assert.equal(parentComboBox.currentIndex, 0);
  assert.deepEqual(parentComboBox.closeCalls, ["close"]);
  assert.deepEqual(timerCalls, ["restart"]);
  assert.equal(delegate.pendingClick, false);
}

function testBluetoothDeviceContentColorReflectsTransientAndBlockedState() {
  const getContentColor = qmlFunction(bluetoothDevicesSource, "getContentColor", "defaultColor");
  const Color = {
    mPrimary: "primary",
    mError: "error",
  };

  assert.equal(getContentColor({
    Color,
    devicePairing: true,
    deviceConnecting: false,
    deviceBlocked: true,
  }, "default"), "primary");
  assert.equal(getContentColor({
    Color,
    devicePairing: false,
    deviceConnecting: true,
    deviceBlocked: false,
  }, "default"), "primary");
  assert.equal(getContentColor({
    Color,
    devicePairing: false,
    deviceConnecting: false,
    deviceBlocked: true,
  }, "default"), "error");
  assert.equal(getContentColor({
    Color,
    devicePairing: false,
    deviceConnecting: false,
    deviceBlocked: false,
  }, "default"), "default");
}

const tests = [
  testMediaMiniTitleFormatsArtistFirst,
  testMediaMiniTitleFormatsTitleFirst,
  testNotificationHistoryUnreadCountHandlesDatesAndNumbers,
  testBackgroundCornerRadiusMapsFlatCornersToZero,
  testComboBoxItemCountSupportsCountedModelsArraysAndMissingModels,
  testComboBoxGetItemSupportsModelGetArraysAndMissingModels,
  testComboBoxFindIndexByKeyFindsFirstMatchAndMissingSentinel,
  testComboBoxActivationEmitsCurrentItemKey,
  testComboBoxDelegateClickSelectsAndClosesPopup,
  testComboBoxDelegateClickDefersWhileListIsMoving,
  testComboBoxPendingClickRetrySelectsAndClearsPendingFlag,
  testBluetoothDeviceContentColorReflectsTransientAndBlockedState,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
