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
    fanDetectorProcess.running = true;
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

  function buildFanDetectionScript() {
    const names = root.supportedFanSensorNames.join(" ");
    return [
      "for name_path in /sys/class/hwmon/hwmon*/name; do",
      "  [ -r \"$name_path\" ] || continue",
      '  dir="${name_path%/name}"',
      "  sensor=$(cat \"$name_path\" 2>/dev/null || true)",
      `  case " ${names} " in`,
      '    *" $sensor "*)',
      '      [ -r "$dir/fan1_input" ] || continue',
      '      printf \'hwmon\\t%s\\t%s\\n\' "${dir##*/hwmon}" "$sensor"',
      '      for input in "$dir"/fan*_input; do',
      '        [ -r "$input" ] || continue',
      '        base="${input##*/fan}"',
      '        idx="${base%_input}"',
      '        label=""',
      '        if [ -r "$dir/fan${idx}_label" ]; then',
      '          label=$(cat "$dir/fan${idx}_label" 2>/dev/null || true)',
      '        fi',
      '        printf \'fan\\t%s\\t%s\\n\' "$idx" "$label"',
      '      done',
      '      exit 0',
      '      ;;',
      "  esac",
      "done",
      "exit 1"
    ].join("\n");
  }

  function parseFanDetectionOutput(output) {
    const lines = output.trim().split(/\r?\n/).filter(row => row.trim().length > 0);
    if (lines.length === 0) {
      return null;
    }

    const sensor = root.parseFanDetectionHeader(lines[0]);
    if (!sensor) {
      return null;
    }

    const fans = root.parseDetectedFanLines(lines.slice(1));
    return {
      hwmonIndex: sensor.hwmonIndex,
      sensorName: sensor.sensorName,
      fanIndices: fans.indices,
      fanLabels: fans.labels
    };
  }

  function parseFanDetectionHeader(line) {
    const header = line.split("\t");
    if (header.length < 3 || header[0] !== "hwmon") {
      return null;
    }

    const hwmonIndex = parseInt(header[1], 10);
    const sensorName = header[2].trim();
    if (isNaN(hwmonIndex) || sensorName === "") {
      return null;
    }

    return {
      hwmonIndex: hwmonIndex,
      sensorName: sensorName
    };
  }

  function parseDetectedFanLines(lines) {
    const indices = [];
    const labels = ({});
    for (const line of lines) {
      const parts = line.split("\t");
      if (parts.length < 2 || parts[0] !== "fan") {
        continue;
      }

      const fanIndex = parseInt(parts[1], 10);
      if (isNaN(fanIndex)) {
        continue;
      }

      indices.push(fanIndex);
      labels[fanIndex] = (parts[2] || "").trim() || null;
    }

    return {
      indices: indices.sort((a, b) => a - b),
      labels: labels
    };
  }

  // Detect hwmon path with fan sensors in one operation. Repeated FileView path
  // changes during startup can leave dropped operations behind in Quickshell.
  Process {
    id: fanDetectorProcess
    running: false
    command: ["sh", "-c", root.buildFanDetectionScript()]
    stdout: StdioCollector {
      onStreamFinished: {
        const detected = root.parseFanDetectionOutput(text);
        if (detected) {
          root.publishFanSensor(detected.hwmonIndex, detected.sensorName, detected.fanIndices, detected.fanLabels);
        }
      }
    }
    onExited: function(exitCode, exitStatus) {
      if (exitCode !== 0 && root.fanHwmonPath === "") {
        Logger.w("FanService", "No supported fan sensor found");
      }
    }
  }

  function publishFanSensor(hwmonIndex, sensorName, fanIndices, fanLabels) {
    root.fanSensorName = sensorName;
    root.detectedFanIndices = fanIndices && fanIndices.length > 0 ? fanIndices.slice().sort((a, b) => a - b) : [1];
    root.fanLabelCache = Object.assign({}, fanLabels || {});
    root.fanHwmonPath = `/sys/class/hwmon/hwmon${hwmonIndex}`;
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
      root.cacheFanLabel(fanIndex, "");
      root.readNextFanLabel();
    }
  }

  function beginPolling() {
    pollingRefs++;
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
    root.loadFanInput(fanIndex);
  }

  function loadFanInput(fanIndex) {
    const nextPath = `${root.fanHwmonPath}/fan${fanIndex}_input`;
    if (fanReader.path === nextPath) {
      fanReader.reload();
      return;
    }

    fanReader.path = nextPath;
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
    const labels = Object.assign({}, root.fanLabelCache);
    labels[fanIndex] = label || null;
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
    root.loadFanLabel(fanIndex);
  }

  function loadFanLabel(fanIndex) {
    const nextPath = `${root.fanHwmonPath}/fan${fanIndex}_label`;
    labelReader.fanIndex = fanIndex;
    if (labelReader.path === nextPath) {
      labelReader.reload();
      return;
    }

    labelReader.path = nextPath;
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
