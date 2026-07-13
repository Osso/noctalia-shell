pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "../../Helpers/BrightnessParsing.js" as BrightnessParsing
import qs.Commons

Singleton {
  id: root

  property var ddcMonitors: []
  readonly property var monitors: variants.instances
  property bool appleDisplayPresent: false
  property bool ddcDetectionPending: false
  property int ddcDetectionGeneration: 0

  function getMonitorForScreen(screen) {
    return monitors.find(m => m.modelData === screen);
  }

  // Signal emitted when a specific monitor's brightness changes, includes monitor context
  signal monitorBrightnessChanged(var monitor, real newBrightness)

  function getAvailableMethods() {
    var methods = [];
    if (Settings.data.brightness.enableDdcSupport && monitors.some(m => m.isDdc))
      methods.push("ddcutil");
    if (monitors.some(m => !m.isDdc))
      methods.push("internal");
    if (appleDisplayPresent)
      methods.push("apple");
    return methods;
  }

  // Global helpers for IPC and shortcuts
  function increaseBrightness() {
    monitors.forEach(m => m.increaseBrightness());
  }

  function decreaseBrightness() {
    monitors.forEach(m => m.decreaseBrightness());
  }

  function getDetectedDisplays() {
    return detectedDisplays;
  }

  function requestDdcDetection() {
    if (!Settings.data.brightness.enableDdcSupport) {
      return;
    }

    if (ddcProc.running) {
      ddcDetectionPending = true;
      return;
    }

    ddcDetectionPending = false;
    ddcDetectionGeneration += 1;
    ddcProc.generation = ddcDetectionGeneration;
    ddcProc.exitObserved = false;
    ddcProc.running = true;
  }

  function finishDdcDetection(generation, exitCode, output, errorOutput) {
    if (generation !== root.ddcDetectionGeneration || !Settings.data.brightness.enableDdcSupport) {
      return;
    }

    if (exitCode === 0) {
      const detectedMonitors = BrightnessParsing.parseDdcMonitors(output);
      if (root.hasMalformedDdcMonitor(detectedMonitors)) {
        Logger.w("Brightness", "Malformed ddcutil detection output");
      } else {
        detectedMonitors.forEach(monitor => {
                                   Logger.i("Brightness", "Detected DDC Monitor:", monitor.model, "on bus", monitor.busNum, "is DDC:", monitor.isDdc);
                                 });
        root.ddcMonitors = detectedMonitors.filter(monitor => monitor.isDdc);
      }
    } else {
      const failure = errorOutput.trim() || `ddcutil detection failed with exit ${exitCode}`;
      Logger.w("Brightness", failure);
    }
  }

  function hasMalformedDdcMonitor(detectedMonitors) {
    return detectedMonitors.some(monitor => monitor.isDdc && (monitor.model === "Unknown" || monitor.busNum === "Unknown"));
  }

  function restartPendingDdcDetection() {
    if (!root.ddcDetectionPending || !Settings.data.brightness.enableDdcSupport) {
      return;
    }

    root.ddcDetectionPending = false;
    root.requestDdcDetection();
  }

  function handleDdcStartFailure(generation, exitObserved) {
    if (!exitObserved) {
      finishDdcDetection(generation, -1, "", "ddcutil detection failed to start");
    }
  }

  reloadableId: "brightness"

  Component.onCompleted: {
    Logger.i("Brightness", "Service started");
    requestDdcDetection();
  }

  onMonitorsChanged: requestDdcDetection()

  Connections {
    target: Settings.data.brightness
    function onEnableDdcSupportChanged() {
      if (Settings.data.brightness.enableDdcSupport) {
        // Re-detect DDC monitors when enabled
        requestDdcDetection();
      } else {
        // Clear DDC monitors when disabled
        ddcDetectionGeneration += 1;
        ddcDetectionPending = false;
        ddcProc.running = false;
        ddcMonitors = [];
      }
    }
  }

  Variants {
    id: variants
    model: Quickshell.screens
    Monitor {}
  }

  // Check for Apple Display support
  Process {
    running: true
    command: ["sh", "-c", "which asdbctl >/dev/null 2>&1 && asdbctl get || echo ''"]
    stdout: StdioCollector {
      onStreamFinished: root.appleDisplayPresent = text.trim().length > 0
    }
  }

  // Detect DDC monitors
  Process {
    id: ddcProc
    property string output: ""
    property string errorOutput: ""
    property bool exitObserved: false
    property int generation: 0
    command: ["ddcutil", "detect", "--sleep-multiplier=0.5"]
    stdout: StdioCollector {
      onStreamFinished: ddcProc.output = text
    }
    stderr: StdioCollector {
      onStreamFinished: ddcProc.errorOutput = text
    }
    onExited: function (exitCode) {
      ddcProc.exitObserved = true;
      const output = ddcProc.output;
      const errorOutput = ddcProc.errorOutput;
      ddcProc.output = "";
      ddcProc.errorOutput = "";
      root.finishDdcDetection(ddcProc.generation, exitCode, output, errorOutput);
    }
    onRunningChanged: {
      if (!running) {
        root.handleDdcStartFailure(ddcProc.generation, exitObserved);
        exitObserved = false;
        root.restartPendingDdcDetection();
      }
    }
  }

  component Monitor: QtObject {
    id: monitor

    required property ShellScreen modelData
    readonly property string screenModel: modelData ? modelData.model : ""
    readonly property bool isDdc: Settings.data.brightness.enableDdcSupport && root.ddcMonitors.some(m => m.model === screenModel)
    readonly property string busNum: {
      const ddcMonitor = root.ddcMonitors.find(m => m.model === screenModel);
      return ddcMonitor ? ddcMonitor.busNum : "";
    }
    readonly property bool isAppleDisplay: root.appleDisplayPresent && screenModel.startsWith("StudioDisplay")
    readonly property string method: isAppleDisplay ? "apple" : (isDdc ? "ddcutil" : "internal")

    // Check if brightness control is available for this monitor
    readonly property bool brightnessControlAvailable: {
      if (isAppleDisplay)
      return true;
      if (isDdc)
      return true;
      // For internal displays, check if we have a brightness path
      return brightnessPath !== "";
    }

    property real brightness
    property real lastBrightness: 0
    property real queuedBrightness: NaN

    // For internal displays - store the backlight device path
    property string backlightDevice: ""
    property string brightnessPath: ""
    property string maxBrightnessPath: ""
    property int maxBrightness: 100
    property bool ignoreNextChange: false

    // Signal for brightness changes
    signal brightnessUpdated(real newBrightness)

    function publishBrightnessUpdate() {
      if (!BrightnessParsing.isValidBrightnessRatio(monitor.brightness)) {
        Logger.w("Brightness", "Skipping invalid brightness update for", monitor.modelData.name);
        return;
      }

      monitor.brightnessUpdated(monitor.brightness);
      root.monitorBrightnessChanged(monitor, monitor.brightness);
    }

    // Execute a system command to get the current brightness value directly
    readonly property Process refreshProc: Process {
      stdout: StdioCollector {
        onStreamFinished: {
          var dataText = text.trim();
          if (dataText === "") {
            return;
          }

          var lines = dataText.split("\n");
          if (lines.length >= 2) {
            var current = parseInt(lines[0].trim());
            var max = parseInt(lines[1].trim());
            if (!isNaN(current) && !isNaN(max) && max > 0) {
              var newBrightness = current / max;
              // Only update if it's actually different (avoid feedback loops)
              if (Math.abs(newBrightness - monitor.brightness) > 0.01) {
                // Update internal value to match system state
                monitor.brightness = newBrightness;
              monitor.publishBrightnessUpdate();
                //Logger.i("Brightness", "Refreshed brightness from system:", monitor.modelData.name, monitor.brightness)
              }
            }
          }
        }
      }
    }

    // Function to actively refresh the brightness from system
    function refreshBrightnessFromSystem() {
      if (!monitor.isDdc && !monitor.isAppleDisplay) {
        // For internal displays, query the system directly
        refreshProc.command = ["sh", "-c", "cat " + monitor.brightnessPath + " && " + "cat " + monitor.maxBrightnessPath];
        refreshProc.running = true;
      } else if (monitor.isDdc) {
        // For DDC displays, get the current value
        refreshProc.command = ["ddcutil", "-b", monitor.busNum, "getvcp", "10", "--brief"];
        refreshProc.running = true;
      } else if (monitor.isAppleDisplay) {
        // For Apple displays, get the current value
        refreshProc.command = ["asdbctl", "get"];
        refreshProc.running = true;
      }
    }

    // FileView to watch for external brightness changes (internal displays only)
    readonly property FileView brightnessWatcher: FileView {
      id: brightnessWatcher
      // Only set path for internal displays with a valid brightness path
      path: (!monitor.isDdc && !monitor.isAppleDisplay && monitor.brightnessPath !== "") ? monitor.brightnessPath : ""
      watchChanges: path !== ""
      onFileChanged: {
        // When a file change is detected, actively refresh from system
        // to ensure we get the most up-to-date value
        Qt.callLater(() => {
                       monitor.refreshBrightnessFromSystem();
                     });
      }
    }

    // Initialize brightness
    readonly property Process initProc: Process {
      stdout: StdioCollector {
        onStreamFinished: {
          var dataText = text.trim();
          if (dataText === "") {
            return;
          }

          //Logger.i("Brightness", "Raw brightness data for", monitor.modelData.name + ":", dataText)
          if (monitor.isAppleDisplay) {
            var appleBrightness = BrightnessParsing.parseAppleBrightness(dataText);
            if (appleBrightness) {
              monitor.brightness = appleBrightness.ratio;
              Logger.d("Brightness", "Apple display brightness:", monitor.brightness);
            }
          } else if (monitor.isDdc) {
            var ddcBrightness = BrightnessParsing.parseDdcBrightness(dataText);
            if (ddcBrightness) {
              monitor.brightness = ddcBrightness.ratio;
              Logger.d("Brightness", "DDC brightness:", ddcBrightness.current + "/" + ddcBrightness.max + " =", monitor.brightness);
            }
          } else {
            // Internal backlight - parse the response which includes device path
            var internalBrightness = BrightnessParsing.parseInternalBacklight(dataText);
            if (internalBrightness) {
              monitor.backlightDevice = internalBrightness.devicePath;
              monitor.brightnessPath = internalBrightness.brightnessPath;
              monitor.maxBrightnessPath = internalBrightness.maxBrightnessPath;
              monitor.maxBrightness = internalBrightness.max;
              monitor.brightness = internalBrightness.ratio;
              Logger.d("Brightness", "Internal brightness:", internalBrightness.current + "/" + internalBrightness.max + " =", monitor.brightness);
              Logger.d("Brightness", "Using backlight device:", monitor.backlightDevice);
            }
          }

          monitor.publishBrightnessUpdate();
        }
      }
    }

    readonly property real stepSize: Settings.data.brightness.brightnessStep / 100.0
    readonly property real minBrightnessValue: (Settings.data.brightness.enforceMinimum ? 0.01 : 0.0)

    // Timer for debouncing rapid changes
    readonly property Timer timer: Timer {
      interval: 100
      onTriggered: {
        if (!isNaN(monitor.queuedBrightness)) {
          monitor.setBrightness(monitor.queuedBrightness);
          monitor.queuedBrightness = NaN;
        }
      }
    }

    function setBrightnessDebounced(value) {
      monitor.queuedBrightness = value;
      timer.start();
    }

    function increaseBrightness() {
      const value = !isNaN(monitor.queuedBrightness) ? monitor.queuedBrightness : monitor.brightness;
      // Enforce minimum brightness if enabled
      if (Settings.data.brightness.enforceMinimum && value < minBrightnessValue) {
        setBrightnessDebounced(Math.max(stepSize, minBrightnessValue));
      } else {
        // Normal brightness increase
        setBrightnessDebounced(value + stepSize);
      }
    }

    function decreaseBrightness() {
      const value = !isNaN(monitor.queuedBrightness) ? monitor.queuedBrightness : monitor.brightness;
      setBrightnessDebounced(value - stepSize);
    }

    function setBrightness(value) {
      value = Math.max(minBrightnessValue, Math.min(1, value));
      var rounded = Math.round(value * 100);

      if (timer.running) {
        monitor.queuedBrightness = value;
        return;
      }

      // Update internal value and trigger UI feedback
      monitor.brightness = value;
      monitor.publishBrightnessUpdate();

      if (isAppleDisplay) {
        monitor.ignoreNextChange = true;
        Quickshell.execDetached(["asdbctl", "set", rounded]);
      } else if (isDdc) {
        monitor.ignoreNextChange = true;
        Quickshell.execDetached(["ddcutil", "-b", busNum, "setvcp", "10", rounded]);
      } else {
        monitor.ignoreNextChange = true;
        Quickshell.execDetached(["brightnessctl", "s", rounded + "%"]);
      }

      if (isDdc) {
        timer.restart();
      }
    }

    function initBrightness() {
      if (isAppleDisplay) {
        initProc.command = ["asdbctl", "get"];
      } else if (isDdc) {
        initProc.command = ["ddcutil", "-b", busNum, "getvcp", "10", "--brief"];
      } else {
        // Internal backlight - find the first available backlight device and get its info
        // This now returns: device_path, current_brightness, max_brightness (on separate lines)
        initProc.command = ["sh", "-c", "for dev in /sys/class/backlight/*; do " + "  if [ -f \"$dev/brightness\" ] && [ -f \"$dev/max_brightness\" ]; then " + "    echo \"$dev\"; " + "    cat \"$dev/brightness\"; " + "    cat \"$dev/max_brightness\"; " + "    break; " + "  fi; " + "done"];
      }
      initProc.running = true;
    }

    onBusNumChanged: initBrightness()
    Component.onCompleted: initBrightness()
  }
}
