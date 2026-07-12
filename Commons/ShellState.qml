pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "../Helpers/QtObj2JS.js" as QtObj2JS
import qs.Services.Power
import qs.Services.System
import qs.Services.UI

// Centralized shell state management for small cache files
Singleton {
  id: root

  property string stateFile: ""
  property bool isLoaded: false

  // State properties for different services
  readonly property alias data: adapter

  // Signals for state changes
  signal displayStateChanged
  signal notificationsStateChanged
  signal changelogStateChanged
  signal colorSchemesListChanged

  Component.onCompleted: initializeStateFile()

  Connections {
    target: Settings
    function onDirectoriesCreatedChanged() {
      root.initializeStateFile();
    }
  }

  function initializeStateFile() {
    if (!Settings.directoriesCreated || !Settings.cacheDir)
      return;
    root.stateFile = Settings.cacheDir + "shell-state.json";
    stateFileView.path = root.stateFile;
  }

  // FileView for shell state
  FileView {
    id: stateFileView
    printErrors: false
    watchChanges: false

    adapter: JsonAdapter {
      id: adapter

      // CompositorService: display scales
      property var display: ({})

      // NotificationService: notification state
      property var notificationsState: ({
                                          lastSeenTs: 0
                                        })

      // UpdateService: changelog state
      property var changelogState: ({
                                      lastSeenVersion: ""
                                    })

      // SchemeDownloader: color schemes list
      property var colorSchemesList: ({
                                        schemes: [],
                                        timestamp: 0
                                      })
    }

    onLoaded: root.handleStateLoaded()
    onLoadFailed: error => root.handleStateLoadFailed(error)
    onSaved: root.handleStateSaved()
    onSaveFailed: error => root.handleStateSaveFailed(error)
  }

  // Debounced save timer
  Timer {
    id: saveTimer
    interval: 500
    onTriggered: performSave()
  }

  Process {
    id: saveDirectoryProcess
    command: ["mkdir", "-p", Settings.cacheDir]
    property bool exitObserved: false
    onExited: function (exitCode) {
      saveDirectoryProcess.exitObserved = true;
      root.handleSaveDirectoryExit(exitCode);
    }
    onRunningChanged: {
      if (!running) {
        root.handleSaveDirectoryStartFailure(saveDirectoryProcess.exitObserved);
        saveDirectoryProcess.exitObserved = false;
      }
    }
  }

  property bool saveQueued: false
  property bool saveInProgress: false

  function handleStateLoaded() {
    isLoaded = true;
    Logger.d("ShellState", "Loaded state file");
  }

  function handleStateLoadFailed(error) {
    isLoaded = true;

    if (error === 2) {
      Logger.d("ShellState", "State file doesn't exist, will create on first write");
      return;
    }

    Logger.e("ShellState", "Failed to load state file:", error);
  }

  function save() {
    saveQueued = true;
    saveTimer.restart();
  }

  function performSave() {
    if (!saveQueued || !stateFile || saveDirectoryProcess.running || saveInProgress)
      return;
    saveDirectoryProcess.exitObserved = false;
    saveDirectoryProcess.running = true;
  }

  function handleSaveDirectoryStartFailure(exitObserved) {
    if (!exitObserved)
      Logger.e("ShellState", "Failed to start cache directory creation");
  }

  function handleSaveDirectoryExit(exitCode) {
    if (exitCode !== 0) {
      Logger.e("ShellState", "Failed to create cache directory, exit:", exitCode);
      return;
    }

    saveQueued = false;
    saveInProgress = true;
    try {
      stateFileView.writeAdapter();
    } catch (writeError) {
      saveInProgress = false;
      saveQueued = true;
      Logger.e("ShellState", "Failed to write state file:", writeError);
    }
  }

  function handleStateSaved() {
    saveInProgress = false;
    Logger.d("ShellState", "Saved state file");
    if (saveQueued)
      saveTimer.restart();
  }

  function handleStateSaveFailed(error) {
    saveInProgress = false;
    saveQueued = true;
    Logger.e("ShellState", "Failed to write state file:", error);
  }

  // Convenience functions for each service

  // Display state (CompositorService)
  function setDisplay(displayData) {
    adapter.display = displayData;
    save();
    displayStateChanged();
  }

  function getDisplay() {
    return adapter.display || {};
  }

  // Notifications state (NotificationService)
  function setNotificationsState(stateData) {
    adapter.notificationsState = stateData;
    save();
    notificationsStateChanged();
  }

  function getNotificationsState() {
    return adapter.notificationsState || {
      lastSeenTs: 0
    };
  }

  // Changelog state (UpdateService)
  function setChangelogState(stateData) {
    adapter.changelogState = stateData;
    save();
    changelogStateChanged();
  }

  function getChangelogState() {
    return adapter.changelogState || {
      lastSeenVersion: ""
    };
  }

  // Color schemes list (SchemeDownloader)
  function setColorSchemesList(listData) {
    adapter.colorSchemesList = listData;
    save();
    colorSchemesListChanged();
  }

  function getColorSchemesList() {
    return adapter.colorSchemesList || {
      schemes: [],
      timestamp: 0
    };
  }

  // -----------------------------------------------------
  function buildStateSnapshot() {
    try {
      const settingsData = QtObj2JS.qtObjectToPlainObject(Settings.data);
      const shellStateData = ShellState && ShellState.data ? QtObj2JS.qtObjectToPlainObject(ShellState.data) || {} : {};

      return {
        settings: settingsData,
        state: {
          doNotDisturb: NotificationService.doNotDisturb,
          noctaliaPerformanceMode: PowerProfileService.noctaliaPerformanceMode,
          barVisible: BarService.isVisible,
          wallpapers: WallpaperService.currentWallpapers || {},
          // -------------
          display: shellStateData.display || {},
          notificationsState: shellStateData.notificationsState || {},
          changelogState: shellStateData.changelogState || {},
          colorSchemesList: shellStateData.colorSchemesList || {}
        }
      };
    } catch (error) {
      Logger.e("Settings", "Failed to build state snapshot:", error);
      return null;
    }
  }
}
