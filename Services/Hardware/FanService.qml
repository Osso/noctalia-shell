pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

Singleton {
  id: root

  // Configuration
  property int sleepDuration: 5000

  // Public values - list of fan objects with rpm and label
  property var fans: []
  property bool available: fans.length > 0

  // Supported fan sensor names (hwmon drivers that expose fan_input)
  readonly property var supportedFanSensorNames: ["thinkpad", "dell_smm", "asus-ec-sensors", "nct6775", "it87", "coretemp"]

  // Internal state for hwmon detection
  property string fanHwmonPath: ""
  property bool sensorDetected: fanHwmonPath !== ""
  property string fanSensorName: ""
  property int maxFanSensors: 8
  property int pollingRefs: 0

  // Internal state for fan reading
  property var pendingFanReads: []
  property var pendingLabelReads: []
  property var collectedFans: []
  property var detectedFanIndices: []
  property var fanLabelCache: ({})

  Component.onCompleted: {
    Logger.i("FanService", "Service started with interval:", root.sleepDuration, "ms");
    fanHwmonDetector.checkNext();
  }

  // Timer for periodic updates
  Timer {
    id: updateTimer
    interval: root.sleepDuration
    repeat: true
    running: root.isPollingActive() && root.fanHwmonPath !== ""
    triggeredOnStart: true
    onTriggered: {
      root.readAllFans();
    }
  }

  // Detect hwmon path with fan sensors
  FileView {
    id: fanHwmonDetector
    property int currentIndex: 0
    printErrors: false

    function checkNext() {
      if (currentIndex >= 16) {
        Logger.w("FanService", "No supported fan sensor found");
        return;
      }

      fanHwmonDetector.path = `/sys/class/hwmon/hwmon${currentIndex}/name`;
      fanHwmonDetector.reload();
    }

    onLoaded: {
      const name = text().trim();
      if (root.supportedFanSensorNames.includes(name)) {
        // Check if this hwmon actually has fan inputs
        fanInputChecker.hwmonIndex = currentIndex;
        fanInputChecker.sensorName = name;
        fanInputChecker.path = `/sys/class/hwmon/hwmon${currentIndex}/fan1_input`;
        fanInputChecker.reload();
      } else {
        currentIndex++;
        Qt.callLater(() => checkNext());
      }
    }

    onLoadFailed: function(error) {
      currentIndex++;
      Qt.callLater(() => checkNext());
    }
  }

  // Verify the hwmon has fan inputs
  FileView {
    id: fanInputChecker
    property int hwmonIndex: 0
    property string sensorName: ""
    printErrors: false

    onLoaded: {
      // Found a valid fan input
      root.publishFanSensor(hwmonIndex, sensorName);
    }

    onLoadFailed: function(error) {
      // No fan inputs at this hwmon, continue searching
      fanHwmonDetector.currentIndex++;
      Qt.callLater(() => fanHwmonDetector.checkNext());
    }
  }

  function publishFanSensor(hwmonIndex, sensorName) {
    root.fanSensorName = sensorName;
    root.fanHwmonPath = `/sys/class/hwmon/hwmon${hwmonIndex}`;
    if (root.isPollingActive()) {
      root.readAllFans();
    }
    Logger.i("FanService", `Found ${root.fanSensorName} fan sensor at ${root.fanHwmonPath}`);
  }

  // Fan reader - reads individual fan files
  FileView {
    id: fanReader
    printErrors: false

    onLoaded: {
      const rpm = parseInt(text().trim()) || 0;
      const fanIndex = root.pendingFanReads.shift();

      if (rpm >= 0) {
        root.collectedFans.push({
          index: fanIndex,
          rpm: rpm,
          label: root.labelForFan(fanIndex)
        });
      }

      Qt.callLater(() => root.readNextFan());
    }

    onLoadFailed: function(error) {
      // No more fans at this index, we're done
      root.pendingFanReads = [];
      root.finalizeFanReading();
    }
  }

  // Label reader - reads fan labels if available
  FileView {
    id: labelReader
    property int fanIndex: 0
    printErrors: false

    onLoaded: {
      const label = text().trim();
      root.cacheFanLabel(fanIndex, label);
      root.readNextFanLabel();
    }

    onLoadFailed: function(error) {
      root.readNextFanLabel();
    }
  }

  function beginPolling() {
    pollingRefs++;
    root.readAllFans();
  }

  function endPolling() {
    pollingRefs = Math.max(0, pollingRefs - 1);
  }

  function isPollingActive() {
    return pollingRefs > 0;
  }

  function fanIndicesToRead() {
    if (root.detectedFanIndices.length > 0) {
      return root.detectedFanIndices.slice();
    }

    const indices = [];
    for (let i = 1; i <= root.maxFanSensors; i++) {
      indices.push(i);
    }
    return indices;
  }

  function rememberDetectedFanIndices(fans) {
    if (fans.length === 0) {
      return;
    }

    root.detectedFanIndices = fans.map(fan => fan.index).sort((a, b) => a - b);
  }

  function readAllFans() {
    if (root.fanHwmonPath === "") return;

    root.collectedFans = [];
    root.pendingFanReads = root.fanIndicesToRead();

    readNextFan();
  }

  function readNextFan() {
    if (root.pendingFanReads.length === 0) {
      finalizeFanReading();
      return;
    }

    const fanIndex = root.pendingFanReads[0]; // Peek, don't remove yet
    fanReader.path = `${root.fanHwmonPath}/fan${fanIndex}_input`;
    fanReader.reload();
  }

  function finalizeFanReading() {
    root.collectedFans.sort((a, b) => a.index - b.index);
    root.rememberDetectedFanIndices(root.collectedFans);
    root.pendingLabelReads = root.findMissingLabelIndices(root.collectedFans);
    root.publishFinalFans();

    if (root.pendingLabelReads.length > 0) {
      root.readNextFanLabel();
    }
  }

  function labelForFan(fanIndex) {
    return root.fanLabelCache[fanIndex] || `Fan ${fanIndex}`;
  }

  function findMissingLabelIndices(fans) {
    const missing = [];
    for (const fan of fans) {
      if (root.fanLabelCache[fan.index] === undefined) {
        missing.push(fan.index);
      }
    }
    return missing;
  }

  function cacheFanLabel(fanIndex, label) {
    if (!label) {
      return;
    }

    const labels = Object.assign({}, root.fanLabelCache);
    labels[fanIndex] = label;
    root.fanLabelCache = labels;
  }

  function applyCachedLabels(fans) {
    return fans.map(fan => Object.assign({}, fan, {
      label: root.labelForFan(fan.index)
    }));
  }

  function readNextFanLabel() {
    if (root.pendingLabelReads.length === 0) {
      root.publishFinalFans();
      return;
    }

    const fanIndex = root.pendingLabelReads.shift();
    labelReader.fanIndex = fanIndex;
    labelReader.path = `${root.fanHwmonPath}/fan${fanIndex}_label`;
    labelReader.reload();
  }

  function publishFinalFans() {
    root.fans = root.applyCachedLabels(root.collectedFans);
  }

  // Helper function to get average RPM
  function getAverageRpm() {
    if (fans.length === 0) return 0;
    let sum = 0;
    fans.forEach(f => sum += f.rpm);
    return Math.round(sum / fans.length);
  }

  // Helper function to get max RPM
  function getMaxRpm() {
    if (fans.length === 0) return 0;
    let max = 0;
    fans.forEach(f => { if (f.rpm > max) max = f.rpm; });
    return max;
  }

  // Helper to format RPM for display
  function formatRpm(rpm) {
    if (rpm < 1000) return rpm + "";
    return (rpm / 1000).toFixed(1) + "k";
  }
}
