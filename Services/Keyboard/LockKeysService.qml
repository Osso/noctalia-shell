pragma Singleton

import Qt.labs.folderlistmodel
import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

Singleton {
  id: root

  property bool capsLockOn: false
  property bool numLockOn: false
  property bool scrollLockOn: false

  signal capsLockChanged(bool active)
  signal numLockChanged(bool active)
  signal scrollLockChanged(bool active)

  // Flag to track if this is the initial check to avoid OSD triggers
  property bool initialCheckDone: false

  readonly property int pollIntervalMs: 3000
  readonly property var lockKeyConfigs: [{
      "key": "caps",
      "label": "Caps Lock",
      "suffix": "::capslock"
    }, {
      "key": "num",
      "label": "Num Lock",
      "suffix": "::numlock"
    }, {
      "key": "scroll",
      "label": "Scroll Lock",
      "suffix": "::scrolllock"
    }]

  property string capsBrightnessPath: ""
  property string numBrightnessPath: ""
  property string scrollBrightnessPath: ""
  property int pendingInitialReads: 0

  function refreshAllStates() {
    if (!initialCheckDone) {
      pendingInitialReads = (capsBrightnessPath ? 1 : 0) + (numBrightnessPath ? 1 : 0) + (scrollBrightnessPath ? 1 : 0);
    }

    if (capsBrightnessPath) {
      capsBrightnessFile.reload();
    }
    if (numBrightnessPath) {
      numBrightnessFile.reload();
    }
    if (scrollBrightnessPath) {
      scrollBrightnessFile.reload();
    }

    if (!capsBrightnessPath) {
      applyState("caps", false);
    }
    if (!numBrightnessPath) {
      applyState("num", false);
    }
    if (!scrollBrightnessPath) {
      applyState("scroll", false);
    }

    if (!initialCheckDone && pendingInitialReads === 0) {
      initialCheckDone = true;
    }
  }

  function applyState(key, active) {
    if (key === "caps") {
      if (capsLockOn !== active) {
        capsLockOn = active;
        if (initialCheckDone) {
          capsLockChanged(active);
        }
        Logger.i("LockKeysService", "Caps Lock:", active);
      }
    } else if (key === "num") {
      if (numLockOn !== active) {
        numLockOn = active;
        if (initialCheckDone) {
          numLockChanged(active);
        }
        Logger.i("LockKeysService", "Num Lock:", active);
      }
    } else if (key === "scroll") {
      if (scrollLockOn !== active) {
        scrollLockOn = active;
        if (initialCheckDone) {
          scrollLockChanged(active);
        }
        Logger.i("LockKeysService", "Scroll Lock:", active);
      }
    }
  }

  FolderListModel {
    id: ledDirectory
    folder: "file:///sys/class/leds"
    showDirs: true
    showFiles: false
    showDotAndDotDot: false

    onStatusChanged: {
      if (status !== FolderListModel.Ready) {
        return;
      }

      var capsPath = "";
      var numPath = "";
      var scrollPath = "";
      for (var i = 0; i < ledDirectory.count; i++) {
        var fileName = ledDirectory.get(i, "fileName");
        if (!capsPath && fileName.endsWith("::capslock")) {
          capsPath = "/sys/class/leds/" + fileName + "/brightness";
        } else if (!numPath && fileName.endsWith("::numlock")) {
          numPath = "/sys/class/leds/" + fileName + "/brightness";
        } else if (!scrollPath && fileName.endsWith("::scrolllock")) {
          scrollPath = "/sys/class/leds/" + fileName + "/brightness";
        }
      }

      capsBrightnessPath = capsPath;
      numBrightnessPath = numPath;
      scrollBrightnessPath = scrollPath;
      refreshAllStates();
    }
  }

  FileView {
    id: capsBrightnessFile
    path: capsBrightnessPath
    printErrors: false
    onLoaded: {
      applyState("caps", text().trim() === "1");
      if (!initialCheckDone) {
        pendingInitialReads--;
        if (pendingInitialReads <= 0) {
          initialCheckDone = true;
        }
      }
    }
  }

  FileView {
    id: numBrightnessFile
    path: numBrightnessPath
    printErrors: false
    onLoaded: {
      applyState("num", text().trim() === "1");
      if (!initialCheckDone) {
        pendingInitialReads--;
        if (pendingInitialReads <= 0) {
          initialCheckDone = true;
        }
      }
    }
  }

  FileView {
    id: scrollBrightnessFile
    path: scrollBrightnessPath
    printErrors: false
    onLoaded: {
      applyState("scroll", text().trim() === "1");
      if (!initialCheckDone) {
        pendingInitialReads--;
        if (pendingInitialReads <= 0) {
          initialCheckDone = true;
        }
      }
    }
  }

  Timer {
    id: pollTimer
    interval: pollIntervalMs
    running: true
    repeat: true
    onTriggered: refreshAllStates()
  }

  Component.onCompleted: {
    Logger.i("LockKeysService", "Service started, performing initial state check.");
  }
}
