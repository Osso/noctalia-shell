pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

Singleton {
  id: root

  // Configuration
  property int sleepDuration: 3000

  // Public values - list of fan objects with rpm and label
  property list<var> fans: []
  property bool available: fans.length > 0

  // Supported fan sensor names (hwmon drivers that expose fan_input)
  readonly property var supportedFanSensorNames: ["thinkpad", "dell_smm", "asus-ec-sensors", "nct6775", "it87", "coretemp"]

  // Internal state for hwmon detection
  property string fanHwmonPath: ""
  property string fanSensorName: ""
  property int maxFanSensors: 8

  // Internal state for fan reading
  property var pendingFanReads: []
  property var collectedFans: []

  Component.onCompleted: {
    Logger.i("FanService", "Service started with interval:", root.sleepDuration, "ms");
    fanHwmonDetector.checkNext();
  }

  // Timer for periodic updates
  Timer {
    id: updateTimer
    interval: root.sleepDuration
    repeat: true
    running: root.fanHwmonPath !== ""
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
      root.fanSensorName = sensorName;
      root.fanHwmonPath = `/sys/class/hwmon/hwmon${hwmonIndex}`;
      Logger.i("FanService", `Found ${root.fanSensorName} fan sensor at ${root.fanHwmonPath}`);
    }

    onLoadFailed: function(error) {
      // No fan inputs at this hwmon, continue searching
      fanHwmonDetector.currentIndex++;
      Qt.callLater(() => fanHwmonDetector.checkNext());
    }
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
          label: `Fan ${fanIndex}`
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
    printErrors: false

    onLoaded: {
      const label = text().trim();
      if (label && root.collectedFans.length > 0) {
        const lastFan = root.collectedFans[root.collectedFans.length - 1];
        lastFan.label = label;
      }
    }
  }

  function readAllFans() {
    if (root.fanHwmonPath === "") return;

    root.collectedFans = [];
    root.pendingFanReads = [];

    // Queue fan indices to read
    for (let i = 1; i <= root.maxFanSensors; i++) {
      root.pendingFanReads.push(i);
    }

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
    // Sort by index and update the public property
    root.collectedFans.sort((a, b) => a.index - b.index);

    // Try to read labels for each fan
    root.collectedFans.forEach((fan, idx) => {
      const labelPath = `${root.fanHwmonPath}/fan${fan.index}_label`;
      // Attempt to read label (async, will update if found)
      labelReader.path = labelPath;
      labelReader.reload();
    });

    root.fans = root.collectedFans;
  }

  // Helper function to get average RPM
  function getAverageRpm(): int {
    if (fans.length === 0) return 0;
    let sum = 0;
    fans.forEach(f => sum += f.rpm);
    return Math.round(sum / fans.length);
  }

  // Helper function to get max RPM
  function getMaxRpm(): int {
    if (fans.length === 0) return 0;
    let max = 0;
    fans.forEach(f => { if (f.rpm > max) max = f.rpm; });
    return max;
  }

  // Helper to format RPM for display
  function formatRpm(rpm: int): string {
    if (rpm < 1000) return rpm + "";
    return (rpm / 1000).toFixed(1) + "k";
  }
}
