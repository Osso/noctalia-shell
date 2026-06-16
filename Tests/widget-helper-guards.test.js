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
  testBluetoothDeviceContentColorReflectsTransientAndBlockedState,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
