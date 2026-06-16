#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/Battery.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBatteryWidgetFindBatteryDeviceUsesNativePathAndFallback() {
  const findBatteryDevice = qmlFunction("findBatteryDevice", "nativePath");
  const displayDevice = { nativePath: "/display", percentage: 0.5 };
  const batteryDevice = { nativePath: "/battery/BAT1", type: "Battery", percentage: 0.82 };
  const linePowerDevice = { nativePath: "/battery/AC", type: "LinePower", percentage: 1 };
  const noPercentDevice = { nativePath: "/battery/empty", type: "Battery" };
  const ctx = {
    UPower: {
      displayDevice,
      devices: {
        values: [linePowerDevice, noPercentDevice, batteryDevice],
      },
    },
    UPowerDeviceType: {
      LinePower: "LinePower",
    },
  };

  assert.equal(findBatteryDevice(ctx, "/battery/BAT1"), batteryDevice);
  assert.equal(findBatteryDevice(ctx, "/battery/AC"), displayDevice);
  assert.equal(findBatteryDevice(ctx, "/battery/missing"), displayDevice);
  assert.equal(findBatteryDevice(ctx, ""), displayDevice);
}

function testBatteryWidgetFindBluetoothDeviceExtractsCaseInsensitiveMac() {
  const findBluetoothDevice = qmlFunction("findBluetoothDevice", "nativePath");
  const headphones = { address: "AA:BB:CC:DD:EE:FF", name: "Headphones" };
  const mouse = { address: "11:22:33:44:55:66", name: "Mouse" };
  const ctx = {
    BluetoothService: {
      devices: {
        values: [headphones, mouse],
      },
    },
  };

  assert.equal(findBluetoothDevice(ctx, "/dev/bluetooth/aa:bb:cc:dd:ee:ff"), headphones);
  assert.equal(findBluetoothDevice(ctx, "prefix 11:22:33:44:55:66 suffix"), mouse);
  assert.equal(findBluetoothDevice(ctx, "/dev/bluetooth/not-a-mac"), null);
  assert.equal(findBluetoothDevice({ BluetoothService: {} }, "/dev/bluetooth/aa:bb:cc:dd:ee:ff"), null);
}

function testBatteryWidgetMaybeNotifyWarnsOnceAndResetsAfterRecovery() {
  const maybeNotify = qmlFunction("maybeNotify", "currentPercent", "isCharging");
  const toasts = [];
  const ctx = {
    hasNotifiedLowBattery: false,
    warningThreshold: 20,
    I18n: {
      tr(key, params) {
        return params ? `${key}:${params.percent}` : key;
      },
    },
    ToastService: {
      showWarning(title, message) {
        toasts.push([title, message]);
      },
    },
  };

  maybeNotify(ctx, 19.6, false);
  maybeNotify(ctx, 18, false);

  assert.equal(ctx.hasNotifiedLowBattery, true);
  assert.deepEqual(toasts, [["toast.battery.low", "toast.battery.low-desc:20"]]);

  maybeNotify(ctx, 24, false);
  assert.equal(ctx.hasNotifiedLowBattery, true);

  maybeNotify(ctx, 26, false);
  assert.equal(ctx.hasNotifiedLowBattery, false);

  maybeNotify(ctx, 15, true);
  assert.equal(ctx.hasNotifiedLowBattery, false);
  assert.equal(toasts.length, 1);
}

function testBatteryWidgetGetCurrentPercentPrefersBluetoothBattery() {
  const getCurrentPercent = qmlFunction("getCurrentPercent");

  assert.equal(getCurrentPercent({
    hasBluetoothBattery: true,
    bluetoothDevice: { battery: 0.43 },
    battery: { percentage: 0.88 },
  }), 43);

  assert.equal(getCurrentPercent({
    hasBluetoothBattery: false,
    bluetoothDevice: { battery: 0.43 },
    battery: { percentage: 0.88 },
  }), 88);

  assert.equal(getCurrentPercent({
    hasBluetoothBattery: false,
    bluetoothDevice: null,
    battery: null,
  }), 0);
}

const tests = [
  testBatteryWidgetFindBatteryDeviceUsesNativePathAndFallback,
  testBatteryWidgetFindBluetoothDeviceExtractsCaseInsensitiveMac,
  testBatteryWidgetMaybeNotifyWarnsOnceAndResetsAfterRecovery,
  testBatteryWidgetGetCurrentPercentPrefersBluetoothBattery,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
