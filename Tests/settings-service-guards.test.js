#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Commons/Settings.qml");
const settingsDataSource = readQml("Commons/SettingsData.qml");
const settingsDefaultsSource = readQml("Helpers/SettingsDefaults.js");
const defaultSettings = JSON.parse(readQml("Assets/settings-default.json"));

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    debug: [],
    errors: [],
    info: [],
    warnings: [],
    d(...args) {
      this.debug.push(args);
    },
    e(...args) {
      this.errors.push(args);
    },
    i(...args) {
      this.info.push(args);
    },
    w(...args) {
      this.warnings.push(args);
    },
  };
}

function createBootstrapContext(overrides = {}) {
  const failures = [];
  const ctx = {
    PreparingDirectories: 0,
    Validating: 1,
    CreatingDefaults: 2,
    Snapshotting: 3,
    Hydrating: 4,
    Ready: 5,
    Error: 6,
    Settings: {
      PreparingDirectories: 0,
      Validating: 1,
      CreatingDefaults: 2,
      Snapshotting: 3,
      Hydrating: 4,
      Ready: 5,
      Error: 6,
    },
    Logger: createLogger(),
    FileViewError: {
      FileNotFound: 2,
    },
    root: {
      PreparingDirectories: 0,
      Validating: 1,
      CreatingDefaults: 2,
      Snapshotting: 3,
      Hydrating: 4,
      Ready: 5,
      Error: 6,
      bootstrapState: 0,
      directoriesCreated: false,
      loadGeneration: 0,
      errorMessage: "",
      validatedSettingsText: "{\"settingsVersion\":26}",
      validatedSettingsData: null,
      pendingSavedSettingsText: "",
      persistedSettingsText: "{\"settingsVersion\":26}",
      saveInProgress: false,
      saveQueued: false,
      watcherChangeQueued: false,
      verifyingSave: false,
      verifyingSnapshot: false,
      isLoaded: false,
      settingsLoadFailed(message) {
        failures.push(message);
      },
    },
    directoryCreationProcess: { running: false },
    saveTimer: {
      stops: 0,
      stop() {
        this.stops += 1;
      },
    },
    Quickshell: { env() { return ""; } },
    Qt: {
      callLater() {},
    },
    QtObj2JS: {
      qtObjectToPlainObject(value) {
        return { settingsVersion: value.settingsVersion };
      },
    },
    settingsLoadedCount: 0,
    settingsSavedCount: 0,
    settingsLoaded() {
      this.settingsLoadedCount += 1;
    },
    runVersionedMigrations() {
      return true;
    },
    upgradeSettingsData() {},
    adapter: { settingsVersion: 0 },
    settingsVersion: 26,
    ...overrides,
  };
  ctx.root.settingsLoaded = () => {
    ctx.settingsLoadedCount += 1;
  };
  ctx.root.settingsSaved = () => {
    ctx.settingsSavedCount += 1;
  };
  ctx.root.beginBootstrap = () => qmlFunction("beginBootstrap")(ctx);
  ctx.root.beginValidation = () => qmlFunction("beginValidation")(ctx);
  ctx.root.failBootstrap = message => qmlFunction("failBootstrap", "message")(ctx, message);
  ctx.root.sortSettingsValue = value => qmlFunction("sortSettingsValue", "value")(ctx, value);
  ctx.root.canonicalizeSettingsValue = value => qmlFunction("canonicalizeSettingsValue", "value")(ctx, value);
  ctx.root.canonicalizeSettingsText = rawText => qmlFunction("canonicalizeSettingsText", "rawText")(ctx, rawText);
  ctx.root.byteArraysEqual = (left, right) => qmlFunction("byteArraysEqual", "left", "right")(ctx, left, right);
  ctx.failures = failures;
  return ctx;
}

function testSettingsBootstrapStartsWithDirectoryProcessOnly() {
  const beginBootstrap = qmlFunction("beginBootstrap");
  const ctx = createBootstrapContext();

  beginBootstrap(ctx);

  assert.equal(ctx.root.bootstrapState, ctx.PreparingDirectories);
  assert.equal(ctx.root.directoriesCreated, false);
  assert.equal(ctx.directoryCreationProcess.running, true);
}

function testSettingsDirectorySuccessBeginsNewValidationGeneration() {
  const handleDirectoryCreationExit = qmlFunction("handleDirectoryCreationExit", "exitCode");
  const ctx = createBootstrapContext();

  handleDirectoryCreationExit(ctx, 0);

  assert.equal(ctx.root.directoriesCreated, true);
  assert.equal(ctx.root.loadGeneration, 1);
  assert.equal(ctx.root.bootstrapState, ctx.Validating);
}

function testSettingsCorruptJsonFailsWithoutWritingOrHydrating() {
  const handleValidationLoaded = qmlFunction("handleValidationLoaded", "generation", "rawText", "rawData");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 3;
  ctx.root.bootstrapState = ctx.Validating;

  handleValidationLoaded(ctx, 3, "{ broken", Buffer.from("{ broken"));

  assert.equal(ctx.root.bootstrapState, ctx.Error);
  assert.match(ctx.root.errorMessage, /Invalid settings JSON/);
  assert.equal(ctx.root.isLoaded, false);
  assert.deepEqual(ctx.failures, [ctx.root.errorMessage]);
}

function testSettingsValidJsonAdvancesToSnapshotOfExactBytes() {
  const handleValidationLoaded = qmlFunction("handleValidationLoaded", "generation", "rawText", "rawData");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 4;
  ctx.root.bootstrapState = ctx.Validating;

  const rawData = Buffer.from("{\"settingsVersion\":26}");
  handleValidationLoaded(ctx, 4, "{\"settingsVersion\":26}", rawData);

  assert.equal(ctx.root.bootstrapState, ctx.Snapshotting);
  assert.equal(ctx.root.validatedSettingsText, "{\"settingsVersion\":26}");
  assert.equal(ctx.root.validatedSettingsData, rawData);
  assert.equal(ctx.root.errorMessage, "");
}

function testSettingsSnapshotSaveRequiresByteExactReadBackBeforeHydration() {
  const handleSnapshotSaved = qmlFunction("handleSnapshotSaved", "generation");
  const handleSnapshotVerificationLoaded = qmlFunction("handleSnapshotVerificationLoaded", "generation", "rawData");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 4;
  ctx.root.bootstrapState = ctx.Snapshotting;
  ctx.root.validatedSettingsData = Buffer.from("{\"settingsVersion\":26}");

  handleSnapshotSaved(ctx, 3);
  assert.equal(ctx.root.verifyingSnapshot, false);

  handleSnapshotSaved(ctx, 4);
  assert.equal(ctx.root.verifyingSnapshot, true);
  assert.equal(ctx.root.bootstrapState, ctx.Snapshotting);

  handleSnapshotVerificationLoaded(ctx, 4, Buffer.from(ctx.root.validatedSettingsData));
  assert.equal(ctx.root.verifyingSnapshot, false);
  assert.equal(ctx.root.bootstrapState, ctx.Hydrating);

  const mismatch = createBootstrapContext();
  mismatch.root.loadGeneration = 4;
  mismatch.root.bootstrapState = mismatch.Snapshotting;
  mismatch.root.verifyingSnapshot = true;
  mismatch.root.validatedSettingsData = Buffer.from("expected");
  handleSnapshotVerificationLoaded(mismatch, 4, Buffer.from("different"));
  assert.equal(mismatch.root.bootstrapState, mismatch.Error);
}

function testSettingsStaleValidationCallbackCannotChangeState() {
  const handleValidationLoaded = qmlFunction("handleValidationLoaded", "generation", "rawText", "rawData");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 8;
  ctx.root.bootstrapState = ctx.Validating;

  handleValidationLoaded(ctx, 7, "{ broken", Buffer.from("{ broken"));

  assert.equal(ctx.root.bootstrapState, ctx.Validating);
  assert.equal(ctx.root.errorMessage, "");
}

function testSettingsMissingFileCreatesDefaultsOnlyBeforeFirstSuccessfulLoad() {
  const handleValidationLoadFailure = qmlFunction("handleValidationLoadFailure", "generation", "error");
  const firstRun = createBootstrapContext();
  firstRun.root.loadGeneration = 2;
  firstRun.root.bootstrapState = firstRun.Validating;

  handleValidationLoadFailure(firstRun, 2, 2);

  assert.equal(firstRun.root.bootstrapState, firstRun.CreatingDefaults);
  assert.equal(firstRun.root.shouldOpenSetupWizard, true);

  const laterRun = createBootstrapContext();
  laterRun.root.loadGeneration = 3;
  laterRun.root.bootstrapState = laterRun.Validating;
  laterRun.root.hasLoadedOnce = true;

  handleValidationLoadFailure(laterRun, 3, 2);

  assert.equal(laterRun.root.bootstrapState, laterRun.Error);
  assert.match(laterRun.root.errorMessage, /Failed to load settings/);
}

function testSettingsDefaultsSaveRevalidatesCurrentGeneration() {
  const handleDefaultsSaved = qmlFunction("handleDefaultsSaved", "generation");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 6;
  ctx.root.bootstrapState = ctx.CreatingDefaults;

  handleDefaultsSaved(ctx, 6);

  assert.equal(ctx.root.loadGeneration, 7);
  assert.equal(ctx.root.bootstrapState, ctx.Validating);
}

function testSettingsBootstrapFailureIgnoresStaleGeneration() {
  const handleBootstrapFailure = qmlFunction("handleBootstrapFailure", "generation", "message");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 5;
  ctx.root.bootstrapState = ctx.Hydrating;

  handleBootstrapFailure(ctx, 4, "stale failure");
  assert.equal(ctx.root.bootstrapState, ctx.Hydrating);

  handleBootstrapFailure(ctx, 5, "current failure");
  assert.equal(ctx.root.bootstrapState, ctx.Error);
  assert.equal(ctx.root.errorMessage, "current failure");
}

function testSettingsHydrationCompletesReadyState() {
  const handleHydrationLoaded = qmlFunction("handleHydrationLoaded", "generation");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 2;
  ctx.root.bootstrapState = ctx.Hydrating;

  handleHydrationLoaded(ctx, 2);

  assert.equal(ctx.root.bootstrapState, ctx.Ready);
  assert.equal(ctx.root.isLoaded, true);
  assert.equal(ctx.settingsLoadedCount, 1);
  assert.equal(ctx.adapter.settingsVersion, 26);
}

function testSettingsOwnWriteFileContentDoesNotUnloadShell() {
  const handleReadyFileLoaded = qmlFunction("handleReadyFileLoaded", "generation", "rawText");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 5;
  ctx.root.bootstrapState = ctx.Ready;
  ctx.root.isLoaded = true;
  ctx.adapter.settingsVersion = 26;

  handleReadyFileLoaded(ctx, 5, "{\"settingsVersion\":26}");

  assert.equal(ctx.root.isLoaded, true);
  assert.equal(ctx.root.loadGeneration, 5);
  assert.equal(ctx.root.bootstrapState, ctx.Ready);
}

function testSettingsPendingWriteContentDoesNotUnloadShellDuringQueuedSave() {
  const handleReadyFileLoaded = qmlFunction("handleReadyFileLoaded", "generation", "rawText");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 5;
  ctx.root.bootstrapState = ctx.Ready;
  ctx.root.isLoaded = true;
  ctx.root.saveInProgress = true;
  ctx.root.pendingSavedSettingsText = "{\"settingsVersion\":26}";
  ctx.adapter.settingsVersion = 27;

  handleReadyFileLoaded(ctx, 5, "{\"settingsVersion\":25}");

  assert.equal(ctx.root.bootstrapState, ctx.Ready);
  assert.equal(ctx.root.loadGeneration, 5);
}

function testSettingsDivergentFileContentUnloadsShellAndRevalidates() {
  const handleReadyFileLoaded = qmlFunction("handleReadyFileLoaded", "generation", "rawText");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 5;
  ctx.root.bootstrapState = ctx.Ready;
  ctx.root.isLoaded = true;
  ctx.adapter.settingsVersion = 26;

  handleReadyFileLoaded(ctx, 5, "{\"settingsVersion\":99}");

  assert.equal(ctx.root.isLoaded, false);
  assert.equal(ctx.root.loadGeneration, 6);
  assert.equal(ctx.root.bootstrapState, ctx.Validating);
  assert.equal(ctx.saveTimer.stops, 1);
}

function testSettingsErrorRetryIsReadOnlyAndStartsNewGeneration() {
  const retryBootstrap = qmlFunction("retryBootstrap");
  const ctx = createBootstrapContext();
  ctx.root.directoriesCreated = true;
  ctx.root.bootstrapState = ctx.Error;
  ctx.root.errorMessage = "bad file";
  ctx.root.loadGeneration = 9;

  retryBootstrap(ctx);

  assert.equal(ctx.root.errorMessage, "");
  assert.equal(ctx.root.loadGeneration, 10);
  assert.equal(ctx.root.bootstrapState, ctx.Validating);
}

function testSettingsWatcherQueuesOwnedSaveChangesBeforeReading() {
  assert.match(source, /id:\s*settingsWatcherLoader[\s\S]*?blockLoading:\s*true[\s\S]*?blockAllReads:\s*true/);
  assert.match(source, /onFileChanged:\s*\{\s*if \(root\.saveInProgress\) \{\s*root\.watcherChangeQueued = true;\s*return;\s*\}\s*reload\(\);\s*root\.handleReadyFileLoaded\(generation,\s*text\(\)\);\s*\}/);
  assert.match(source, /onLoadFailed:\s*function \(error\) \{\s*if \(root\.saveInProgress\) \{\s*root\.watcherChangeQueued = true;\s*return;\s*\}/);
}

function testSettingsQueuedWatcherChangeRevalidatesExternalContent() {
  const processQueuedWatcherChange = qmlFunction("processQueuedWatcherChange");
  const handleReadyFileLoaded = qmlFunction("handleReadyFileLoaded", "generation", "rawText");
  const ctx = createBootstrapContext();
  let reloads = 0;
  ctx.root.loadGeneration = 5;
  ctx.root.bootstrapState = ctx.Ready;
  ctx.root.isLoaded = true;
  ctx.adapter.settingsVersion = 26;
  ctx.settingsWatcherLoader = {
    item: {
      reload() {
        reloads += 1;
      },
      text() {
        return '{"settingsVersion":99}';
      },
    },
  };
  ctx.root.handleReadyFileLoaded = (generation, rawText) => handleReadyFileLoaded(ctx, generation, rawText);

  processQueuedWatcherChange(ctx);

  assert.equal(reloads, 1);
  assert.equal(ctx.root.bootstrapState, ctx.Validating);
  assert.equal(ctx.root.loadGeneration, 6);
  assert.equal(ctx.root.isLoaded, false);
}

function testSettingsBootstrapUsesSnapshotHydrationAndWriteOnlyPersistence() {
  assert.match(source, /Loader\s*\{\s*id:\s*validationFileLoader/);
  assert.match(source, /Loader\s*\{\s*id:\s*snapshotWriterLoader/);
  assert.match(source, /setData\(root\.validatedSettingsData\)/);
  assert.match(source, /Loader\s*\{\s*id:\s*hydrationFileLoader[\s\S]*?path:\s*root\.settingsSnapshotFile/);
  assert.match(source, /Loader\s*\{\s*id:\s*settingsWriterLoader[\s\S]*?preload:\s*false/);
  assert.match(source, /Loader\s*\{\s*id:\s*settingsWatcherLoader/);
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

function testSettingsNoOpSaveCompletesWithoutStartingWriter() {
  const saveImmediate = qmlFunction("saveImmediate");
  let savedSignals = 0;
  const ctx = {
    adapter: { settingsVersion: 26 },
    QtObj2JS: {
      qtObjectToPlainObject() {
        return { settingsVersion: 26 };
      },
    },
    settingsFileView: {
      writeAdapter() {
        throw new Error("no-op save must not start writer");
      },
    },
    root: {
      canonicalizeSettingsValue(value) {
        return JSON.stringify(value);
      },
      persistedSettingsText: "{\"settingsVersion\":26}",
      saveInProgress: false,
      saveQueued: false,
      settingsSaved() {
        savedSignals += 1;
      },
    },
  };

  saveImmediate(ctx);

  assert.equal(ctx.root.saveInProgress, false);
  assert.equal(savedSignals, 1);
}

function testSettingsSaveImmediateQueuesOverlappingRequestWithoutReplacingSnapshot() {
  const saveImmediate = qmlFunction("saveImmediate");
  const writes = [];
  let savedSignals = 0;
  const adapter = { settingsVersion: 26 };
  const ctx = {
    adapter,
    QtObj2JS: {
      qtObjectToPlainObject(value) {
        assert.equal(value, adapter);
        return { settingsVersion: value.settingsVersion };
      },
    },
    settingsFileView: {
      writeAdapter() {
        writes.push("primary");
      },
    },
    root: {
      canonicalizeSettingsValue(value) {
        return JSON.stringify(value);
      },
      pendingSavedSettingsText: "",
      saveInProgress: false,
      saveQueued: false,
      settingsSaved() {
        savedSignals += 1;
      },
    },
  };

  saveImmediate(ctx);
  ctx.adapter.settingsVersion = 27;
  saveImmediate(ctx);

  assert.deepEqual(writes, ["primary"]);
  assert.equal(ctx.root.pendingSavedSettingsText, "{\"settingsVersion\":26}");
  assert.equal(ctx.root.saveInProgress, true);
  assert.equal(ctx.root.saveQueued, true);
  assert.equal(savedSignals, 0);
}

function testSettingsCanonicalizationIgnoresObjectKeyOrder() {
  const canonicalizeSettingsText = qmlFunction("canonicalizeSettingsText", "rawText");
  const ctx = createBootstrapContext();

  const left = canonicalizeSettingsText(ctx, '{"bar":{"position":"top","widgets":[]},"settingsVersion":26}');
  const right = canonicalizeSettingsText(ctx, '{"settingsVersion":26,"bar":{"widgets":[],"position":"top"}}');

  assert.equal(left, right);
}

function testSettingsCanonicalizationPreservesProtoKey() {
  const canonicalizeSettingsText = qmlFunction("canonicalizeSettingsText", "rawText");
  const ctx = createBootstrapContext();

  const canonical = canonicalizeSettingsText(ctx, '{"__proto__":{"enabled":true},"settingsVersion":26}');

  const parsed = JSON.parse(canonical);
  assert.equal(Object.hasOwn(parsed, "__proto__"), true);
  assert.deepEqual(parsed["__proto__"], { enabled: true });
  assert.equal(parsed.settingsVersion, 26);
}

function testSettingsDefaultLocationIsNotPersistedAtAdapterRoot() {
  const defaultLocationMatch = settingsDefaultsSource.match(/var defaultLocation = "([^"]+)";/);

  assert.ok(defaultLocationMatch, "shared default location constant must exist");
  assert.doesNotMatch(settingsDataSource, /^\s*(?:required\s+)?property\s+string\s+defaultLocation\b/m);
  assert.match(settingsDataSource, /property string name: SettingsDefaults\.defaultLocation/);
  assert.match(source, /readonly property string defaultLocation: SettingsDefaults\.defaultLocation/);
  assert.equal(defaultSettings.location.name, defaultLocationMatch[1]);
  assert.equal(Object.hasOwn(defaultSettings, "defaultLocation"), false);
}

function testSettingsSavedSignalWaitsForVerifiedPrimaryContent() {
  const handleSettingsSaved = qmlFunction("handleSettingsSaved", "generation", "serializedText");
  const handleSaveVerificationLoaded = qmlFunction("handleSaveVerificationLoaded", "generation", "rawText");
  const ctx = createBootstrapContext();
  ctx.root.loadGeneration = 4;
  ctx.root.bootstrapState = ctx.Ready;
  ctx.root.saveInProgress = true;
  ctx.root.watcherChangeQueued = true;
  ctx.root.pendingSavedSettingsText = "{\"settingsVersion\":999}";
  let watcherChecks = 0;
  ctx.root.processQueuedWatcherChange = () => {
    watcherChecks += 1;
  };

  handleSettingsSaved(ctx, 4, "{\n  \"settingsVersion\": 26\n}");
  assert.equal(ctx.root.pendingSavedSettingsText, "{\"settingsVersion\":26}");
  assert.equal(ctx.root.verifyingSave, true);
  assert.equal(ctx.settingsSavedCount, 0);

  handleSaveVerificationLoaded(ctx, 4, "{\"settingsVersion\":26}");
  assert.equal(ctx.root.verifyingSave, false);
  assert.equal(ctx.root.saveInProgress, false);
  assert.equal(ctx.root.watcherChangeQueued, false);
  assert.equal(watcherChecks, 1);
  assert.equal(ctx.settingsSavedCount, 1);
}

function testSettingsErrorStateIsStableUntilExplicitRetry() {
  assert.doesNotMatch(source, /running:\s*root\.bootstrapState\s*===\s*root\.Error/);
  assert.doesNotMatch(source, /NOCTALIA_SETTINGS_FALLBACK/);
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

function testSettingsRunMigrationExecutesAndDestroysOneMigration() {
  const runMigration = qmlFunction("runMigration", "version", "migrationComponent");
  const events = [];
  const ctx = {
    adapter: {},
    root: {},
    Logger: createLogger(),
  };
  const component = {
    createObject(root) {
      assert.equal(root, ctx.root);
      return {
        migrate(adapter) {
          assert.equal(adapter, ctx.adapter);
          events.push("migrate");
          return true;
        },
        destroy() {
          events.push("destroy");
        },
      };
    },
  };

  assert.equal(runMigration(ctx, 3, component), true);
  assert.deepEqual(events, ["migrate", "destroy"]);
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
  ctx.runMigration = (version, migrationComponent) => qmlFunction("runMigration", "version", "migrationComponent")(ctx, version, migrationComponent);

  const migrationsSucceeded = runVersionedMigrations(ctx);

  assert.equal(migrationsSucceeded, false);
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
  testSettingsBootstrapStartsWithDirectoryProcessOnly,
  testSettingsDirectorySuccessBeginsNewValidationGeneration,
  testSettingsCorruptJsonFailsWithoutWritingOrHydrating,
  testSettingsValidJsonAdvancesToSnapshotOfExactBytes,
  testSettingsSnapshotSaveRequiresByteExactReadBackBeforeHydration,
  testSettingsStaleValidationCallbackCannotChangeState,
  testSettingsMissingFileCreatesDefaultsOnlyBeforeFirstSuccessfulLoad,
  testSettingsDefaultsSaveRevalidatesCurrentGeneration,
  testSettingsBootstrapFailureIgnoresStaleGeneration,
  testSettingsHydrationCompletesReadyState,
  testSettingsOwnWriteFileContentDoesNotUnloadShell,
  testSettingsPendingWriteContentDoesNotUnloadShellDuringQueuedSave,
  testSettingsDivergentFileContentUnloadsShellAndRevalidates,
  testSettingsErrorRetryIsReadOnlyAndStartsNewGeneration,
  testSettingsWatcherQueuesOwnedSaveChangesBeforeReading,
  testSettingsQueuedWatcherChangeRevalidatesExternalContent,
  testSettingsBootstrapUsesSnapshotHydrationAndWriteOnlyPersistence,
  testSettingsPreprocessPathExpandsHomeOnlyForStringPaths,
  testSettingsNoOpSaveCompletesWithoutStartingWriter,
  testSettingsSaveImmediateQueuesOverlappingRequestWithoutReplacingSnapshot,
  testSettingsCanonicalizationIgnoresObjectKeyOrder,
  testSettingsCanonicalizationPreservesProtoKey,
  testSettingsDefaultLocationIsNotPersistedAtAdapterRoot,
  testSettingsSavedSignalWaitsForVerifiedPrimaryContent,
  testSettingsErrorStateIsStableUntilExplicitRetry,
  testSettingsGenerateDefaultSettingsWritesEncodedAdapter,
  testSettingsRunMigrationExecutesAndDestroysOneMigration,
  testSettingsRunVersionedMigrationsRunsOnlyNewerVersionsAndDestroysInstances,
  testSettingsUpgradeWidgetPrunesDeprecatedKeysAndAddsDefaults,
  testSettingsUpgradeSettingsDataDefersUntilRegistryReady,
  testSettingsUpgradeSettingsDataRemovesInvalidWidgetsAndKeepsControlCenter,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
