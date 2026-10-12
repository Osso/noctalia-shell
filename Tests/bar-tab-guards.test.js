#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/Tabs/BarTab.qml");

function executeProduction(name, parameters, environment) {
  return new Function(
    ...Object.keys(environment),
    `return function (${parameters.join(", ")}) ${extractFunctionBody(source, name)};`,
  )(...Object.values(environment));
}

function widgetSettings(widgets) {
  return { data: { bar: { widgets } } };
}

function testBarTabAddWidgetGuards() {
  const widgets = { left: [{ id: "Clock" }], center: [], right: [] };
  const metadata = {
    allowUserSettings: true,
    icon: "terminal",
    command: "never-run",
  };
  const add = executeProduction(
    "_addWidgetToSection",
    ["widgetId", "section"],
    {
      Settings: widgetSettings(widgets),
      BarWidgetRegistry: {
        widgetHasUserSettings: (id) => id !== "Clock",
        widgetMetadata: { CustomButton: metadata, Clock: { icon: "ignored" } },
      },
    },
  );

  add("CustomButton", "center");
  add("Clock", "right");
  add("MissingMetadata", "center");
  assert.deepEqual(widgets, {
    left: [{ id: "Clock" }],
    center: [
      { id: "CustomButton", icon: "terminal", command: "never-run" },
      { id: "MissingMetadata" },
    ],
    right: [{ id: "Clock" }],
  });
  assert.deepEqual(metadata, {
    allowUserSettings: true,
    icon: "terminal",
    command: "never-run",
  });
}

function testBarTabRemoveAndReorderGuards() {
  const original = [{ id: "Clock" }, { id: "ControlCenter" }, { id: "Tray" }];
  const widgets = { left: original, center: [{ id: "Spacer" }], right: [] };
  const warnings = [];
  const environment = {
    Settings: widgetSettings(widgets),
    BarService: {
      lookupWidget: (id) =>
        Object.values(widgets)
          .flat()
          .find((widget) => widget.id === id),
    },
    ToastService: { showWarning: (...args) => warnings.push(args) },
    I18n: { tr: (key) => `translated:${key}` },
  };
  const remove = executeProduction(
    "_removeWidgetFromSection",
    ["section", "index"],
    environment,
  );
  const reorder = executeProduction(
    "_reorderWidgetInSection",
    ["section", "fromIndex", "toIndex"],
    environment,
  );

  for (const index of [-1, original.length]) {
    remove("left", index);
    assert.strictEqual(widgets.left, original);
    for (const [from, to] of [
      [index, 0],
      [0, index],
    ]) {
      reorder("left", from, to);
      assert.strictEqual(widgets.left, original);
    }
  }
  assert.deepEqual(warnings, []);

  reorder("left", 2, 0);
  assert.deepEqual(widgets.left, [
    { id: "Tray" },
    { id: "Clock" },
    { id: "ControlCenter" },
  ]);
  assert.deepEqual(original, [
    { id: "Clock" },
    { id: "ControlCenter" },
    { id: "Tray" },
  ]);
  const reordered = widgets.left;
  reorder("left", 0, 2);
  assert.deepEqual(widgets.left, original);
  assert.deepEqual(reordered, [
    { id: "Tray" },
    { id: "Clock" },
    { id: "ControlCenter" },
  ]);

  const beforeRemoval = widgets.left;
  remove("left", 0);
  assert.deepEqual(widgets.left, [{ id: "ControlCenter" }, { id: "Tray" }]);
  assert.deepEqual(beforeRemoval, original);
  assert.deepEqual(warnings, []);

  widgets.right = [{ id: "ControlCenter" }];
  remove("left", 0);
  assert.deepEqual(widgets.left, [{ id: "Tray" }]);
  assert.deepEqual(warnings, []);
  remove("right", 0);
  assert.deepEqual(widgets.right, []);
  assert.deepEqual(widgets.center, [{ id: "Spacer" }]);
  assert.deepEqual(warnings, [
    [
      "translated:toast.missing-control-center.label",
      "translated:toast.missing-control-center.description",
      12000,
    ],
  ]);
}

function testBarTabUpdateAndMoveGuards() {
  const widgets = {
    left: [{ id: "Clock", format: "old" }, { id: "Tray" }],
    center: [{ id: "Spacer" }],
    right: [{ id: "ControlCenter" }],
  };
  const environment = { Settings: widgetSettings(widgets) };
  const update = executeProduction(
    "_updateWidgetSettingsInSection",
    ["section", "index", "settings"],
    environment,
  );
  const move = executeProduction(
    "_moveWidgetBetweenSections",
    ["fromSection", "index", "toSection"],
    environment,
  );
  const settings = { id: "Clock", format: "HH:mm" };
  update("left", 0, settings);
  assert.deepEqual(widgets.left, [settings, { id: "Tray" }]);
  assert.strictEqual(widgets.left[0], settings);
  assert.deepEqual(widgets.center, [{ id: "Spacer" }]);

  const originalSource = widgets.left;
  const originalTarget = widgets.center;
  for (const index of [-1, originalSource.length]) {
    move("left", index, "center");
    assert.strictEqual(widgets.left, originalSource);
    assert.strictEqual(widgets.center, originalTarget);
  }
  move("left", 0, "center");
  assert.deepEqual(widgets.left, [{ id: "Tray" }]);
  assert.deepEqual(widgets.center, [{ id: "Spacer" }, settings]);
  assert.strictEqual(widgets.center[1], settings);
  assert.deepEqual(originalSource, [settings, { id: "Tray" }]);
  assert.deepEqual(originalTarget, [{ id: "Spacer" }]);
  assert.deepEqual(widgets.right, [{ id: "ControlCenter" }]);
}

function testBarTabAvailableWidgetModelGuards() {
  const instances = [
    { widgetId: "Clock", section: "left" },
    { widgetId: "Tray", section: "center" },
    { widgetId: "Clock", section: "left" },
    { widgetId: "Clock", section: "center" },
    { widgetId: "Clock", section: "right" },
    { widgetId: "Clock", section: "unknown" },
  ];
  const locations = executeProduction("getWidgetLocations", ["widgetId"], {
    BarService: { getAllRegisteredWidgets: () => instances },
  });
  const unavailableLocations = executeProduction(
    "getWidgetLocations",
    ["widgetId"],
    {
      BarService: null,
    },
  );
  assert.deepEqual(unavailableLocations("Clock"), []);
  assert.equal(locations("Clock"), "LCR");
  assert.equal(locations("Tray"), "C");
  assert.equal(locations("Missing"), "");

  let entries = ["Tray", "Clock", "CustomButton"];
  const widgetChoices = {
    rows: [{ key: "obsolete", name: "obsolete", badgeLocations: "R" }],
    clear() {
      this.rows = [];
    },
    append(row) {
      this.rows.push(row);
    },
  };
  const refresh = executeProduction("updateAvailableWidgetsModel", [], {
    widgetChoices,
    BarWidgetRegistry: { getAvailableWidgets: () => entries },
    getWidgetLocations: locations,
  });
  refresh();
  assert.deepEqual(widgetChoices.rows, [
    { key: "Tray", name: "Tray", badgeLocations: "C" },
    { key: "Clock", name: "Clock", badgeLocations: "LCR" },
    { key: "CustomButton", name: "CustomButton", badgeLocations: "" },
  ]);
  instances.splice(0, instances.length, {
    widgetId: "Clock",
    section: "right",
  });
  entries = ["Clock"];
  refresh();
  assert.deepEqual(widgetChoices.rows, [
    { key: "Clock", name: "Clock", badgeLocations: "R" },
  ]);
  entries = [];
  refresh();
  assert.deepEqual(widgetChoices.rows, []);
}

const tests = [
  testBarTabAddWidgetGuards,
  testBarTabRemoveAndReorderGuards,
  testBarTabUpdateAndMoveGuards,
  testBarTabAvailableWidgetModelGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
