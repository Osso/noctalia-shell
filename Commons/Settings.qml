pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "../Helpers/QtObj2JS.js" as QtObj2JS
import qs.Commons
import qs.Commons.Migrations
import qs.Modules.OSD
import qs.Services.UI

Singleton {
  id: root

  enum BootstrapState {
    PreparingDirectories,
    Validating,
    CreatingDefaults,
    Snapshotting,
    Hydrating,
    Ready,
    Error
  }

  property bool isLoaded: false
  property bool directoriesCreated: false
  property bool shouldOpenSetupWizard: false
  property bool hasLoadedOnce: false
  property int bootstrapState: Settings.PreparingDirectories
  property int loadGeneration: 0
  property string errorMessage: ""
  property string lastLoggedError: ""
  property string validatedSettingsText: ""
  property var validatedSettingsData: null
  property string pendingSavedSettingsText: ""
  property string persistedSettingsText: ""
  property bool saveInProgress: false
  property bool saveQueued: false
  property bool verifyingSave: false
  property bool verifyingSnapshot: false
  readonly property bool ready: bootstrapState === Settings.Ready
  readonly property var settingsFileView: settingsWriterLoader.item

  /*
  Shell directories.
  - Default config directory: ~/.config/noctalia
  - Default cache directory: ~/.cache/noctalia
  */
  readonly property alias data: adapter  // Used to access via Settings.data.xxx.yyy
  readonly property int settingsVersion: 26
  readonly property bool isDebug: Quickshell.env("NOCTALIA_DEBUG") === "1"
  readonly property string shellName: "noctalia"
  readonly property string configDir: Quickshell.env("NOCTALIA_CONFIG_DIR") || (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/" + shellName + "/"
  readonly property string cacheDir: Quickshell.env("NOCTALIA_CACHE_DIR") || (Quickshell.env("XDG_CACHE_HOME") || Quickshell.env("HOME") + "/.cache") + "/" + shellName + "/"
  readonly property string cacheDirImages: cacheDir + "images/"
  readonly property string cacheDirImagesWallpapers: cacheDir + "images/wallpapers/"
  readonly property string cacheDirImagesNotifications: cacheDir + "images/notifications/"
  readonly property string settingsFile: Quickshell.env("NOCTALIA_SETTINGS_FILE") || (configDir + "settings.json")
  readonly property string settingsSnapshotFile: cacheDir + "settings-bootstrap.json"
  readonly property string defaultLocation: "Tokyo"
  readonly property string defaultAvatar: Quickshell.env("HOME") + "/.face"
  readonly property string defaultVideosDirectory: Quickshell.env("HOME") + "/Videos"
  readonly property string defaultWallpapersDirectory: Quickshell.env("HOME") + "/Pictures/Wallpapers"

  // Signal emitted when settings are loaded after startupcale changes
  signal settingsLoaded
  signal settingsSaved
  signal settingsLoadFailed(string message)

  Component.onCompleted: {
    if (isDebug) {
      generateDefaultSettings();
    }

    adapter.general.avatarImage = defaultAvatar;
    adapter.screenRecorder.directory = defaultVideosDirectory;
    adapter.wallpaper.directory = defaultWallpapersDirectory;
    adapter.ui.fontDefault = Qt.application.font.family;
    adapter.ui.fontFixed = "monospace";
    beginBootstrap();
  }

  Process {
    id: directoryCreationProcess
    running: false
    command: ["mkdir", "-p", configDir, cacheDir, cacheDirImagesWallpapers, cacheDirImagesNotifications]
    onExited: function (exitCode) {
      root.handleDirectoryCreationExit(exitCode);
    }
  }

  Timer {
    id: saveTimer
    running: false
    interval: 500
    onTriggered: root.saveImmediate()
  }

  Loader {
    id: validationFileLoader
    active: root.bootstrapState === root.Validating

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsFile
      printErrors: false
      watchChanges: false
      Component.onCompleted: generation = root.loadGeneration
      onLoaded: root.handleValidationLoaded(generation, text(), data())
      onLoadFailed: function (error) {
        root.handleValidationLoadFailure(generation, error);
      }
    }
  }

  Loader {
    id: defaultsWriterLoader
    active: root.bootstrapState === root.CreatingDefaults

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsFile
      adapter: adapter
      preload: false
      printErrors: false
      watchChanges: false
      Component.onCompleted: {
        generation = root.loadGeneration;
        writeAdapter();
      }
      onSaved: root.handleDefaultsSaved(generation)
      onSaveFailed: function (error) {
        root.handleBootstrapFailure(generation, `Failed to create settings: ${error}`);
      }
    }
  }

  Loader {
    id: snapshotWriterLoader
    active: root.bootstrapState === root.Snapshotting

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsSnapshotFile
      preload: false
      printErrors: false
      watchChanges: false
      Component.onCompleted: {
        generation = root.loadGeneration;
        setData(root.validatedSettingsData);
      }
      onSaved: root.handleSnapshotSaved(generation)
      onSaveFailed: function (error) {
        root.handleBootstrapFailure(generation, `Failed to snapshot settings: ${error}`);
      }
    }
  }

  Loader {
    id: snapshotVerificationLoader
    active: root.verifyingSnapshot

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsSnapshotFile
      printErrors: false
      watchChanges: false
      Component.onCompleted: generation = root.loadGeneration
      onLoaded: root.handleSnapshotVerificationLoaded(generation, data())
      onLoadFailed: function (error) {
        root.handleBootstrapFailure(generation, `Failed to verify settings snapshot: ${error}`);
      }
    }
  }

  Loader {
    id: hydrationFileLoader
    active: root.bootstrapState === root.Hydrating

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsSnapshotFile
      adapter: adapter
      printErrors: false
      watchChanges: false
      Component.onCompleted: generation = root.loadGeneration
      onLoaded: root.handleHydrationLoaded(generation)
      onLoadFailed: function (error) {
        root.handleBootstrapFailure(generation, `Failed to hydrate settings: ${error}`);
      }
    }
  }

  Loader {
    id: settingsWatcherLoader
    active: root.bootstrapState === root.Ready

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsFile
      preload: false
      blockLoading: true
      blockAllReads: true
      printErrors: false
      watchChanges: true
      Component.onCompleted: generation = root.loadGeneration
      onFileChanged: {
        reload();
        root.handleReadyFileLoaded(generation, text());
      }
      onLoadFailed: function (error) {
        root.handleBootstrapFailure(generation, `Failed to read changed settings: ${error}`);
      }
    }
  }

  Loader {
    id: saveVerificationLoader
    active: root.verifyingSave

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsFile
      printErrors: false
      watchChanges: false
      Component.onCompleted: generation = root.loadGeneration
      onLoaded: root.handleSaveVerificationLoaded(generation, text())
      onLoadFailed: function (error) {
        root.handleBootstrapFailure(generation, `Failed to verify settings save: ${error}`);
      }
    }
  }

  Loader {
    id: settingsWriterLoader
    active: root.bootstrapState === root.Ready

    sourceComponent: FileView {
      property int generation: 0
      path: root.settingsFile
      adapter: adapter
      preload: false
      printErrors: false
      watchChanges: false
      Component.onCompleted: generation = root.loadGeneration
      onAdapterUpdated: saveTimer.start()
      onSaved: root.handleSettingsSaved(generation)
      onSaveFailed: function (error) {
        root.handleBootstrapFailure(generation, `Failed to save settings: ${error}`);
      }
    }
  }

  SettingsData {
    id: adapter
    settingsVersion: root.settingsVersion
    defaultLocation: root.defaultLocation
  }

  // -----------------------------------------------------
  // Settings bootstrap state machine
  function beginBootstrap() {
    root.bootstrapState = root.PreparingDirectories;
    root.isLoaded = false;
    if (!directoryCreationProcess.running) {
      directoryCreationProcess.running = true;
    }
  }

  function handleDirectoryCreationExit(exitCode) {
    if (exitCode !== 0) {
      root.failBootstrap(`Failed to create settings directories (mkdir exit ${exitCode})`);
      return;
    }

    root.directoriesCreated = true;
    root.beginValidation();
  }

  function beginValidation() {
    saveTimer.stop();
    root.saveInProgress = false;
    root.saveQueued = false;
    root.verifyingSave = false;
    root.pendingSavedSettingsText = "";
    root.isLoaded = false;
    root.errorMessage = "";
    root.validatedSettingsText = "";
    root.validatedSettingsData = null;
    root.loadGeneration += 1;
    root.bootstrapState = root.Validating;
  }

  function handleValidationLoaded(generation, rawText, rawData) {
    if (generation !== root.loadGeneration || root.bootstrapState !== root.Validating) {
      return;
    }

    try {
      const parsedSettings = JSON.parse(rawText);
      if (!parsedSettings || Array.isArray(parsedSettings) || typeof parsedSettings !== "object") {
        throw new Error("settings root must be a JSON object");
      }
    } catch (error) {
      root.failBootstrap(`Invalid settings JSON: ${error}`);
      return;
    }

    root.errorMessage = "";
    root.validatedSettingsText = rawText;
    root.validatedSettingsData = rawData;
    root.bootstrapState = root.Snapshotting;
  }

  function handleSnapshotSaved(generation) {
    if (generation !== root.loadGeneration || root.bootstrapState !== root.Snapshotting) {
      return;
    }

    root.verifyingSnapshot = true;
  }

  function handleSnapshotVerificationLoaded(generation, rawData) {
    if (generation !== root.loadGeneration || !root.verifyingSnapshot) {
      return;
    }

    if (!root.byteArraysEqual(rawData, root.validatedSettingsData)) {
      root.failBootstrap("Settings snapshot verification failed");
      return;
    }

    root.verifyingSnapshot = false;
    root.bootstrapState = root.Hydrating;
  }

  function handleValidationLoadFailure(generation, error) {
    if (generation !== root.loadGeneration || root.bootstrapState !== root.Validating) {
      return;
    }

    const errorText = String(error);
    const missing = error === FileViewError.FileNotFound || errorText.includes("No such file");
    if (missing && !root.hasLoadedOnce) {
      root.shouldOpenSetupWizard = true;
      root.bootstrapState = root.CreatingDefaults;
      return;
    }

    root.failBootstrap(`Failed to load settings: ${errorText}`);
  }

  function handleDefaultsSaved(generation) {
    if (generation !== root.loadGeneration || root.bootstrapState !== root.CreatingDefaults) {
      return;
    }

    root.beginValidation();
  }

  function handleHydrationLoaded(generation) {
    if (generation !== root.loadGeneration || root.bootstrapState !== root.Hydrating) {
      return;
    }

    Logger.i("Settings", "Settings loaded");
    try {
      if (!runVersionedMigrations()) {
        root.failBootstrap("Settings migration failed");
        return;
      }
      upgradeSettingsData();
    } catch (error) {
      root.failBootstrap(`Failed to upgrade settings: ${error}`);
      return;
    }
    root.isLoaded = true;
    root.hasLoadedOnce = true;
    root.persistedSettingsText = JSON.stringify(JSON.parse(root.validatedSettingsText));
    root.bootstrapState = root.Ready;
    root.settingsLoaded();
    adapter.settingsVersion = settingsVersion;

    const loadedSettingsText = JSON.stringify(JSON.parse(root.validatedSettingsText));
    const hydratedSettingsText = JSON.stringify(QtObj2JS.qtObjectToPlainObject(adapter));
    if (loadedSettingsText !== hydratedSettingsText) {
      Qt.callLater(root.saveImmediate);
    }
  }

  function handleSettingsSaved(generation) {
    if (generation !== root.loadGeneration || root.bootstrapState !== root.Ready || !root.saveInProgress) {
      return;
    }

    root.verifyingSave = true;
  }

  function handleSaveVerificationLoaded(generation, rawText) {
    if (generation !== root.loadGeneration || !root.verifyingSave) {
      return;
    }

    let savedSettingsText = "";
    try {
      savedSettingsText = JSON.stringify(JSON.parse(rawText));
    } catch (error) {
      root.failBootstrap(`Saved settings are invalid JSON: ${error}`);
      return;
    }

    if (savedSettingsText !== root.pendingSavedSettingsText) {
      root.failBootstrap("Settings save verification failed");
      return;
    }

    const shouldSaveAgain = root.saveQueued;
    root.persistedSettingsText = savedSettingsText;
    root.verifyingSave = false;
    root.saveInProgress = false;
    root.saveQueued = false;
    root.pendingSavedSettingsText = "";
    root.settingsSaved();
    if (shouldSaveAgain) {
      Qt.callLater(root.saveImmediate);
    }
  }

  function handleReadyFileLoaded(generation, rawText) {
    if (generation !== root.loadGeneration || root.bootstrapState !== root.Ready) {
      return;
    }

    let currentSettingsText = "";
    try {
      currentSettingsText = JSON.stringify(JSON.parse(rawText));
    } catch (error) {
      root.beginValidation();
      return;
    }

    const adapterSettingsText = JSON.stringify(QtObj2JS.qtObjectToPlainObject(adapter));
    if (currentSettingsText === root.pendingSavedSettingsText || currentSettingsText === adapterSettingsText) {
      return;
    }
    if (currentSettingsText !== adapterSettingsText) {
      root.beginValidation();
    }
  }

  function handleBootstrapFailure(generation, message) {
    if (generation !== root.loadGeneration) {
      return;
    }

    root.failBootstrap(message);
  }

  function failBootstrap(message) {
    saveTimer.stop();
    root.saveInProgress = false;
    root.saveQueued = false;
    root.verifyingSave = false;
    root.verifyingSnapshot = false;
    root.pendingSavedSettingsText = "";
    root.isLoaded = false;
    root.errorMessage = String(message);
    root.bootstrapState = root.Error;
    if (root.lastLoggedError !== root.errorMessage) {
      Logger.e("Settings", root.errorMessage);
      root.lastLoggedError = root.errorMessage;
    }
    root.settingsLoadFailed(root.errorMessage);
  }

  function byteArraysEqual(left, right) {
    if (left === right) {
      return true;
    }
    if (!left || !right || left.byteLength !== right.byteLength) {
      return false;
    }

    const leftBytes = new Uint8Array(left);
    const rightBytes = new Uint8Array(right);
    for (let index = 0; index < leftBytes.length; index++) {
      if (leftBytes[index] !== rightBytes[index]) {
        return false;
      }
    }
    return true;
  }

  function retryBootstrap() {
    root.errorMessage = "";
    if (!root.directoriesCreated) {
      root.beginBootstrap();
      return;
    }

    root.beginValidation();
  }

  // Function to preprocess paths by expanding "~" to user's home directory
  function preprocessPath(path) {
    if (typeof path !== "string" || path === "") {
      return path;
    }

    // Expand "~" to user's home directory
    if (path.startsWith("~/")) {
      return Quickshell.env("HOME") + path.substring(1);
    } else if (path === "~") {
      return Quickshell.env("HOME");
    }

    return path;
  }

  // -----------------------------------------------------
  // Public function to trigger immediate settings saving
  function saveImmediate() {
    if (!settingsFileView) {
      return;
    }
    if (root.saveInProgress) {
      root.saveQueued = true;
      return;
    }

    const settingsText = JSON.stringify(QtObj2JS.qtObjectToPlainObject(adapter));
    if (settingsText === root.persistedSettingsText) {
      root.settingsSaved();
      return;
    }

    root.pendingSavedSettingsText = settingsText;
    root.saveInProgress = true;
    settingsFileView.writeAdapter();
  }

  // -----------------------------------------------------
  // Generate default settings at the root of the repo
  function generateDefaultSettings() {
    try {
      Logger.d("Settings", "Generating settings-default.json");

      // Prepare a clean JSON
      var plainAdapter = QtObj2JS.qtObjectToPlainObject(adapter);
      var jsonData = JSON.stringify(plainAdapter, null, 2);

      var defaultPath = Quickshell.shellDir + "/Assets/settings-default.json";

      // Encode transfer it has base64 to avoid any escaping issue
      var base64Data = Qt.btoa(jsonData);
      Quickshell.execDetached(["sh", "-c", `echo "${base64Data}" | base64 -d > "${defaultPath}"`]);
    } catch (error) {
      Logger.e("Settings", "Failed to generate default settings file: " + error);
    }
  }

  // -----------------------------------------------------
  // Run versioned migrations using MigrationRegistry
  function runMigration(version, migrationComponent) {
    let migration = null;
    try {
      migration = migrationComponent.createObject(root);
      if (!migration || typeof migration.migrate !== "function") {
        Logger.e("Settings", "Invalid migration for v" + version);
        return false;
      }

      if (!migration.migrate(adapter, Logger)) {
        Logger.e("Settings", "Migration to v" + version + " failed");
        return false;
      }
      return true;
    } catch (error) {
      Logger.e("Settings", `Migration to v${version} threw: ${error}`);
      return false;
    } finally {
      if (migration) {
        migration.destroy();
      }
    }
  }

  function runVersionedMigrations() {
    const currentVersion = adapter.settingsVersion;
    const migrations = MigrationRegistry.migrations;
    const versions = Object.keys(migrations).map(v => parseInt(v)).sort((a, b) => a - b);
    let allSucceeded = true;

    for (var i = 0; i < versions.length; i++) {
      const version = versions[i];
      if (currentVersion < version && !runMigration(version, migrations[version])) {
        allSucceeded = false;
      }
    }

    return allSucceeded;
  }

  // -----------------------------------------------------
  // Function to clean up deprecated user/custom bar widgets settings
  function upgradeWidget(widget) {
    // Backup the widget definition before altering
    const widgetBefore = JSON.stringify(widget);

    // Get all existing custom settings keys
    const keys = Object.keys(BarWidgetRegistry.widgetMetadata[widget.id]);

    // Delete deprecated user settings from the wiget
    for (const k of Object.keys(widget)) {
      if (k === "id" || k === "allowUserSettings") {
        continue;
      }
      if (!keys.includes(k)) {
        delete widget[k];
      }
    }

    // Inject missing default setting (metaData) from BarWidgetRegistry
    for (var i = 0; i < keys.length; i++) {
      const k = keys[i];
      if (k === "id" || k === "allowUserSettings") {
        continue;
      }

      if (widget[k] === undefined) {
        widget[k] = BarWidgetRegistry.widgetMetadata[widget.id][k];
      }
    }

    // Compare settings, to detect if something has been upgraded
    const widgetAfter = JSON.stringify(widget);
    return (widgetAfter !== widgetBefore);
  }

  // -----------------------------------------------------
  // If the settings structure has changed, ensure
  // backward compatibility by upgrading the settings
  function upgradeSettingsData() {
    // Wait for BarWidgetRegistry to be ready
    if (!BarWidgetRegistry.widgets || Object.keys(BarWidgetRegistry.widgets).length === 0) {
      Logger.w("Settings", "BarWidgetRegistry not ready, deferring upgrade");
      Qt.callLater(upgradeSettingsData);
      return;
    }

    const sections = ["left", "center", "right"];

    // -----------------
    // 1. remove any non existing widget type
    var removedWidget = false;
    for (var s = 0; s < sections.length; s++) {
      const sectionName = sections[s];
      const widgets = adapter.bar.widgets[sectionName];
      // Iterate backward through the widgets array, so it does not break when removing a widget
      for (var i = widgets.length - 1; i >= 0; i--) {
        var widget = widgets[i];
        if (!BarWidgetRegistry.hasWidget(widget.id)) {
          Logger.w(`Settings`, `Deleted invalid widget ${widget.id}`);
          widgets.splice(i, 1);
          removedWidget = true;
        }
      }
    }

    // -----------------
    // 2. upgrade user widget settings
    for (var s = 0; s < sections.length; s++) {
      const sectionName = sections[s];
      for (var i = 0; i < adapter.bar.widgets[sectionName].length; i++) {
        var widget = adapter.bar.widgets[sectionName][i];

        // Check if widget registry supports user settings, if it does not, then there is nothing to do
        const reg = BarWidgetRegistry.widgetMetadata[widget.id];
        if ((reg === undefined) || (reg.allowUserSettings === undefined) || !reg.allowUserSettings) {
          continue;
        }

        if (upgradeWidget(widget)) {
          Logger.d("Settings", `Upgraded ${widget.id} widget:`, JSON.stringify(widget));
        }
      }
    }

    // -----------------
    // 3. safety check
    // if a widget was deleted, ensure we still have a control center
    if (removedWidget) {
      var gotControlCenter = false;
      for (var s = 0; s < sections.length; s++) {
        const sectionName = sections[s];
        for (var i = 0; i < adapter.bar.widgets[sectionName].length; i++) {
          var widget = adapter.bar.widgets[sectionName][i];
          if (widget.id === "ControlCenter") {
            gotControlCenter = true;
            break;
          }
        }
      }

      if (!gotControlCenter) {
        //const obj = JSON.parse('{"id": "ControlCenter"}');
        adapter.bar.widgets["right"].push(({
                                             "id": "ControlCenter"
                                           }));
        Logger.w("Settings", "Added a ControlCenter widget to the right section");
      }
    }
  }
}
