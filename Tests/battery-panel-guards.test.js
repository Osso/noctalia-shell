#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Battery/BatteryPanel.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createSettings(widgets) {
  return {
    data: {
      bar: {
        widgets: {
          left: [],
          center: [],
          right: [],
          ...widgets,
        },
      },
    },
  };
}

function testBatteryPanelDevicePathPrefersRightSectionBatteryWidget() {
  const getBatteryDevicePath = qmlFunction("getBatteryDevicePath");
  const ctx = {
    Settings: createSettings({
      left: [{ id: "Battery", deviceNativePath: "/left/BAT0" }],
      right: [
        { id: "Clock", deviceNativePath: "/ignored" },
        { id: "Battery", deviceNativePath: "/right/BAT1" },
      ],
    }),
  };

  assert.equal(getBatteryDevicePath(ctx), "/right/BAT1");
}

function testBatteryPanelDevicePathFallsBackToLeftThenCenterSections() {
  const getBatteryDevicePath = qmlFunction("getBatteryDevicePath");

  assert.equal(getBatteryDevicePath({
    Settings: createSettings({
      left: [{ id: "Battery", deviceNativePath: "/left/BAT0" }],
      center: [{ id: "Battery", deviceNativePath: "/center/BAT0" }],
    }),
  }), "/left/BAT0");

  assert.equal(getBatteryDevicePath({
    Settings: createSettings({
      center: [{ id: "Battery", deviceNativePath: "/center/BAT0" }],
    }),
  }), "/center/BAT0");
}

function testBatteryPanelDevicePathIgnoresMissingOrNonBatteryWidgets() {
  const getBatteryDevicePath = qmlFunction("getBatteryDevicePath");
  const ctx = {
    Settings: createSettings({
      right: [
        { id: "Battery" },
        { id: "Clock", deviceNativePath: "/clock" },
      ],
      left: [{ id: "Tray", deviceNativePath: "/tray" }],
    }),
  };

  assert.equal(getBatteryDevicePath(ctx), "");
}

function testBatteryPanelDeviceNameRequiresReadyState() {
  const getDeviceName = qmlFunction("getDeviceName");

  assert.equal(getDeviceName({
    isReady: false,
    battery: { model: "Laptop Battery" },
    bluetoothDevice: { name: "Headphones" },
  }), "");
}

function testBatteryPanelDeviceNameSuppressesLaptopBatteryNames() {
  const getDeviceName = qmlFunction("getDeviceName");

  assert.equal(getDeviceName({
    isReady: true,
    battery: {
      isLaptopBattery: true,
      model: "Internal Battery",
    },
    bluetoothDevice: null,
  }), "");
}

function testBatteryPanelDeviceNamePrefersBluetoothThenBatteryModel() {
  const getDeviceName = qmlFunction("getDeviceName");

  assert.equal(getDeviceName({
    isReady: true,
    battery: {
      isLaptopBattery: false,
      model: "Mouse Battery",
    },
    bluetoothDevice: {
      name: "MX Master",
    },
  }), "MX Master");

  assert.equal(getDeviceName({
    isReady: true,
    battery: {
      isLaptopBattery: false,
      model: "UPS Battery",
    },
    bluetoothDevice: null,
  }), "UPS Battery");
}

function testBatteryPanelDeviceNameFallsBackToEmptyString() {
  const getDeviceName = qmlFunction("getDeviceName");

  assert.equal(getDeviceName({
    isReady: true,
    battery: {},
    bluetoothDevice: {},
  }), "");
}

const tests = [
  testBatteryPanelDevicePathPrefersRightSectionBatteryWidget,
  testBatteryPanelDevicePathFallsBackToLeftThenCenterSections,
  testBatteryPanelDevicePathIgnoresMissingOrNonBatteryWidgets,
  testBatteryPanelDeviceNameRequiresReadyState,
  testBatteryPanelDeviceNameSuppressesLaptopBatteryNames,
  testBatteryPanelDeviceNamePrefersBluetoothThenBatteryModel,
  testBatteryPanelDeviceNameFallsBackToEmptyString,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
