#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Commons/Settings.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    debug: [],
    errors: [],
    warnings: [],
    d(...args) {
      this.debug.push(args);
    },
    e(...args) {
      this.errors.push(args);
    },
    w(...args) {
      this.warnings.push(args);
    },
  };
}

function testSettingsPreprocessPathExpandsHomeOnlyForStringPaths() {
  const preprocessPath = qmlFunction("preprocessPath", "path");
  const ctx = {
    Quickshell: {
      env(name) {
        assert.equal(name, "HOME");
        return "/home/osso";
      },
    },
  };

  assert.equal(preprocessPath(ctx, "~/Pictures"), "/home/osso/Pictures");
  assert.equal(preprocessPath(ctx, "~"), "/home/osso");
  assert.equal(preprocessPath(ctx, "/tmp/file"), "/tmp/file");
  assert.equal(preprocessPath(ctx, ""), "");
  assert.equal(preprocessPath(ctx, null), null);
}

function testSettingsSaveImmediateWritesFallbackOnlyWhenConfigured() {
  const saveImmediate = qmlFunction("saveImmediate");
  const writes = [];
  let savedSignals = 0;
  const ctx = {
    settingsFileView: {
      writeAdapter() {
        writes.push("primary");
      },
    },
    settingsFallbackFileView: {
      writeAdapter() {
        writes.push("fallback");
      },
    },
    Quickshell: {
      fallback: "",
      env(name) {
        assert.equal(name, "NOCTALIA_SETTINGS_FALLBACK");
        return this.fallback;
      },
    },
    root: {
      settingsSaved() {
        savedSignals += 1;
      },
    },
  };

  saveImmediate(ctx);
  ctx.Quickshell.fallback = "/tmp/settings.json";
  saveImmediate(ctx);

  assert.deepEqual(writes, ["primary", "primary", "fallback"]);
  assert.equal(savedSignals, 2);
}

function testSettingsGenerateDefaultSettingsWritesEncodedAdapter() {
  const generateDefaultSettings = qmlFunction("generateDefaultSettings");
  const logger = createLogger();
  const execs = [];
  const adapter = {
    settingsVersion: 42,
    bar: {
      widgets: {
        left: [],
        center: [],
        right: [],
      },
    },
  };
  const ctx = {
    adapter,
    Logger: logger,
    QtObj2JS: {
      qtObjectToPlainObject(value) {
        assert.equal(value, adapter);
        return { settingsVersion: value.settingsVersion, bar: value.bar };
      },
    },
    Qt: {
      btoa(value) {
        return Buffer.from(value, "utf8").toString("base64");
      },
    },
    Quickshell: {
      shellDir: "/repo",
      execDetached(command) {
        execs.push(command);
      },
    },
  };

  generateDefaultSettings(ctx);

  assert.equal(logger.debug.length, 1);
  assert.equal(logger.errors.length, 0);
  assert.equal(execs.length, 1);
  assert.deepEqual(execs[0].slice(0, 2), ["sh", "-c"]);
  assert.match(execs[0][2], /^echo "[A-Za-z0-9+/=]+" \| base64 -d > "\/repo\/Assets\/settings-default\.json"$/);
  const encoded = execs[0][2].match(/^echo "([^"]+)"/)[1];
  assert.deepEqual(JSON.parse(Buffer.from(encoded, "base64").toString("utf8")), {
    settingsVersion: 42,
    bar: {
      widgets: {
        left: [],
        center: [],
        right: [],
      },
    },
  });
}

function testSettingsRunVersionedMigrationsRunsOnlyNewerVersionsAndDestroysInstances() {
  const runVersionedMigrations = qmlFunction("runVersionedMigrations");
  const logger = createLogger();
  const events = [];
  const ctx = {
    adapter: {
      settingsVersion: 2,
    },
    root: {},
    Logger: logger,
    MigrationRegistry: {
      migrations: {
        1: {
          createObject() {
            throw new Error("old migrations should not run");
          },
        },
        3: {
          createObject(root) {
            assert.equal(root, ctx.root);
            return {
              migrate(adapter, migrationLogger) {
                assert.equal(adapter, ctx.adapter);
                assert.equal(migrationLogger, logger);
                events.push("migrate-3");
                return true;
              },
              destroy() {
                events.push("destroy-3");
              },
            };
          },
        },
        5: {
          createObject() {
            return {
              migrate() {
                events.push("migrate-5");
                return false;
              },
              destroy() {
                events.push("destroy-5");
              },
            };
          },
        },
        6: {
          createObject() {
            return {
              destroy() {
                events.push("destroy-6");
              },
            };
          },
        },
      },
    },
  };

  runVersionedMigrations(ctx);

  assert.deepEqual(events, ["migrate-3", "destroy-3", "migrate-5", "destroy-5", "destroy-6"]);
  assert.deepEqual(logger.errors, [
    ["Settings", "Migration to v5 failed"],
    ["Settings", "Invalid migration for v6"],
  ]);
}

function testSettingsUpgradeWidgetPrunesDeprecatedKeysAndAddsDefaults() {
  const upgradeWidget = qmlFunction("upgradeWidget", "widget");
  const ctx = {
    BarWidgetRegistry: {
      widgetMetadata: {
        Clock: {
          id: "Clock",
          allowUserSettings: true,
          format: "HH:mm",
          showSeconds: false,
        },
      },
    },
  };
  const widget = {
    id: "Clock",
    allowUserSettings: true,
    format: "h:mm a",
    stale: true,
  };

  const upgraded = upgradeWidget(ctx, widget);

  assert.equal(upgraded, true);
  assert.deepEqual(widget, {
    id: "Clock",
    allowUserSettings: true,
    format: "h:mm a",
    showSeconds: false,
  });

  assert.equal(upgradeWidget(ctx, widget), false);
}

function testSettingsUpgradeSettingsDataDefersUntilRegistryReady() {
  const upgradeSettingsData = qmlFunction("upgradeSettingsData");
  const logger = createLogger();
  let deferred = 0;
  const ctx = {
    Logger: logger,
    BarWidgetRegistry: {
      widgets: {},
    },
    Qt: {
      callLater(callback) {
        assert.equal(callback, ctx.upgradeSettingsData);
        deferred += 1;
      },
    },
    upgradeSettingsData() {},
  };

  upgradeSettingsData(ctx);

  assert.equal(deferred, 1);
  assert.deepEqual(logger.warnings, [["Settings", "BarWidgetRegistry not ready, deferring upgrade"]]);
}

function testSettingsUpgradeSettingsDataRemovesInvalidWidgetsAndKeepsControlCenter() {
  const upgradeSettingsData = qmlFunction("upgradeSettingsData");
  const logger = createLogger();
  const upgraded = [];
  const ctx = {
    Logger: logger,
    adapter: {
      bar: {
        widgets: {
          left: [{ id: "Invalid" }, { id: "Clock", stale: true }],
          center: [],
          right: [],
        },
      },
    },
    BarWidgetRegistry: {
      widgets: {
        Clock: {},
        ControlCenter: {},
      },
      widgetMetadata: {
        Clock: {
          allowUserSettings: true,
        },
      },
      hasWidget(id) {
        return id === "Clock" || id === "ControlCenter";
      },
    },
    upgradeWidget(widget) {
      upgraded.push(widget.id);
      widget.upgraded = true;
      return true;
    },
  };

  upgradeSettingsData(ctx);

  assert.deepEqual(ctx.adapter.bar.widgets, {
    left: [{ id: "Clock", stale: true, upgraded: true }],
    center: [],
    right: [{ id: "ControlCenter" }],
  });
  assert.deepEqual(upgraded, ["Clock"]);
  assert.deepEqual(logger.warnings, [
    ["Settings", "Deleted invalid widget Invalid"],
    ["Settings", "Added a ControlCenter widget to the right section"],
  ]);
  assert.equal(logger.debug.length, 1);
}

const tests = [
  testSettingsPreprocessPathExpandsHomeOnlyForStringPaths,
  testSettingsSaveImmediateWritesFallbackOnlyWhenConfigured,
  testSettingsGenerateDefaultSettingsWritesEncodedAdapter,
  testSettingsRunVersionedMigrationsRunsOnlyNewerVersionsAndDestroysInstances,
  testSettingsUpgradeWidgetPrunesDeprecatedKeysAndAddsDefaults,
  testSettingsUpgradeSettingsDataDefersUntilRegistryReady,
  testSettingsUpgradeSettingsDataRemovesInvalidWidgetsAndKeepsControlCenter,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
