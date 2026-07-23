pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

/**
 * ProcessService - Fetches and maintains a list of running processes
 * Uses ps command to get process information sorted by CPU or memory usage
 */
Singleton {
  id: root

  // Configuration
  property int updateInterval: 3000
  property int processLimit: 20
  property string sortBy: "cpu" // "cpu", "memory", "name", "pid"
  property bool sortDescending: true

  // Reference counting for lazy updates
  property int refCount: 0
  property bool isActive: refCount > 0

  // Process list data
  property var processes: []
  property int processCount: 0
  property int threadCount: 0

  // System summary
  property real totalCpuUsage: 0
  property real totalMemoryUsage: 0

  function addRef() {
    refCount++;
    if (refCount === 1) {
      Logger.d("ProcessService", "Activated - starting process monitoring");
      updateProcesses();
    }
  }

  function removeRef() {
    refCount = Math.max(0, refCount - 1);
    if (refCount === 0) {
      Logger.d("ProcessService", "Deactivated - stopping process monitoring");
    }
  }

  function setSortBy(newSort) {
    if (sortBy !== newSort) {
      sortBy = newSort;
      applySorting();
    }
  }

  function toggleSortDirection() {
    sortDescending = !sortDescending;
    applySorting();
  }

  function updateProcesses() {
    if (!isActive) return;
    psProcess.running = true;
  }

  function killProcess(pid) {
    if (pid > 0) {
      Logger.i("ProcessService", "Killing process:", pid);
      killProcessCmd.command = ["kill", pid.toString()];
      killProcessCmd.running = true;
    }
  }

  function forceKillProcess(pid) {
    if (pid > 0) {
      Logger.i("ProcessService", "Force killing process:", pid);
      killProcessCmd.command = ["kill", "-9", pid.toString()];
      killProcessCmd.running = true;
    }
  }

  // Format CPU usage for display
  function formatCpu(cpu) {
    return cpu.toFixed(1) + "%";
  }

  // Format memory for display
  function formatMemory(memKB) {
    if (memKB < 1024) {
      return memKB.toFixed(0) + " KB";
    } else if (memKB < 1024 * 1024) {
      return (memKB / 1024).toFixed(1) + " MB";
    } else {
      return (memKB / (1024 * 1024)).toFixed(2) + " GB";
    }
  }

  // Get icon name based on process command
  function getProcessIcon(command) {
    const cmd = command.toLowerCase();
    if (cmd.includes("firefox") || cmd.includes("chrome") || cmd.includes("chromium") || cmd.includes("brave")) {
      return "web";
    }
    if (cmd.includes("code") || cmd.includes("nvim") || cmd.includes("vim") || cmd.includes("emacs")) {
      return "code";
    }
    if (cmd.includes("kitty") || cmd.includes("wezterm") || cmd.includes("alacritty") || cmd.includes("terminal") || cmd.includes("konsole")) {
      return "terminal";
    }
    if (cmd.includes("spotify") || cmd.includes("music") || cmd.includes("rhythmbox") || cmd.includes("clementine")) {
      return "music";
    }
    if (cmd.includes("vlc") || cmd.includes("mpv") || cmd.includes("totem") || cmd.includes("video")) {
      return "video";
    }
    if (cmd.includes("discord") || cmd.includes("slack") || cmd.includes("telegram") || cmd.includes("signal")) {
      return "chat";
    }
    if (cmd.includes("steam") || cmd.includes("game")) {
      return "gamepad";
    }
    if (cmd.includes("docker") || cmd.includes("containerd") || cmd.includes("podman")) {
      return "docker";
    }
    if (cmd.includes("systemd") || cmd.includes("dbus") || cmd.includes("polkit")) {
      return "settings";
    }
    if (cmd.includes("kworker") || cmd.includes("kthread") || cmd.includes("migration")) {
      return "cpu";
    }
    return "process";
  }

  // Internal: Parse consecutive /proc snapshots and update process list
  property var allProcesses: []
  property var previousProcessSamples: ({})
  property real previousSampleTime: 0

  function parseProcessOutput(text) {
    if (!text) return;

    let snapshot;
    try {
      snapshot = JSON.parse(text);
    } catch (error) {
      Logger.w("ProcessService", "Invalid process snapshot:", error);
      return;
    }
    if (!snapshot || !Array.isArray(snapshot.processes)) return;

    const sampleInterval = snapshot.sampleTime - previousSampleTime;
    const newSamples = {};
    const newProcesses = [];
    let totalCpu = 0;
    let totalMem = 0;

    for (const processData of snapshot.processes) {
      const pid = processData.pid || 0;
      if (pid <= 0) continue;

      const previous = previousProcessSamples[pid];
      const sameProcess = previous && previous.startTime === processData.startTime;
      const cpuTimeDelta = sameProcess ? processData.cpuTime - previous.cpuTime : 0;
      const cpu = sampleInterval > 0 ? Math.max(0, cpuTimeDelta / sampleInterval * 100) : 0;
      const command = processData.command || "";
      const memPercent = processData.memoryPercent || 0;
      const rssKB = processData.memoryKB || 0;
      let cmdName = command;

      if (cmdName.startsWith('[')) {
        cmdName = cmdName.split(']')[0].replace('[', '').split('/')[0];
      } else {
        const firstArg = command.split(' ')[0];
        cmdName = firstArg.split('/').pop();
      }

      newSamples[pid] = {
        cpuTime: processData.cpuTime,
        startTime: processData.startTime
      };
      newProcesses.push({
        pid: pid,
        cpu: cpu,
        memoryPercent: memPercent,
        memoryKB: rssKB,
        command: cmdName,
        fullCommand: command,
        displayName: cmdName.length > 25 ? cmdName.substring(0, 25) + "…" : cmdName
      });

      totalCpu += cpu;
      totalMem += memPercent;
    }

    previousProcessSamples = newSamples;
    previousSampleTime = snapshot.sampleTime;
    allProcesses = newProcesses;
    processCount = newProcesses.length;
    totalCpuUsage = Math.min(totalCpu, 100);
    totalMemoryUsage = Math.min(totalMem, 100);

    applySorting();
  }

  function applySorting() {
    if (!allProcesses || allProcesses.length === 0) return;

    const sorted = allProcesses.slice();
    sorted.sort((a, b) => {
      let valueA, valueB;

      switch (sortBy) {
        case "cpu":
          valueA = a.cpu || 0;
          valueB = b.cpu || 0;
          break;
        case "memory":
          valueA = a.memoryKB || 0;
          valueB = b.memoryKB || 0;
          break;
        case "name":
          valueA = (a.command || "").toLowerCase();
          valueB = (b.command || "").toLowerCase();
          return sortDescending ? valueB.localeCompare(valueA) : valueA.localeCompare(valueB);
        case "pid":
          valueA = a.pid || 0;
          valueB = b.pid || 0;
          break;
        default:
          return 0;
      }

      return sortDescending ? (valueB - valueA) : (valueA - valueB);
    });

    // Force new array reference for QML binding update
    processes = sorted.slice(0, processLimit);
  }

  // Timer for periodic updates
  Timer {
    id: updateTimer
    interval: root.updateInterval
    running: root.isActive
    repeat: true
    triggeredOnStart: true
    onTriggered: root.updateProcesses()
  }

  Component.onCompleted: {
    Logger.d("ProcessService", "Component completed");
  }

  // Process to fetch cumulative CPU and memory counters from /proc
  Process {
    id: psProcess
    command: ["python3", Quickshell.shellDir + "/Bin/process-stats.py"]
    running: false

    stdout: StdioCollector {
      onStreamFinished: root.parseProcessOutput(text)
    }

    onExited: exitCode => {
      if (exitCode !== 0) {
        Logger.w("ProcessService", "ps command failed with exit code:", exitCode);
      }
    }
  }

  // Process to kill a process
  Process {
    id: killProcessCmd
    command: ["kill", "0"]
    running: false

    onExited: exitCode => {
      if (exitCode === 0) {
        // Refresh the list after killing
        Qt.callLater(() => root.updateProcesses());
      } else {
        Logger.w("ProcessService", "Failed to kill process, exit code:", exitCode);
      }
    }
  }
}
