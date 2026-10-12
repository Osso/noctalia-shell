import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.System

ShellRoot {
  id: harness
  property int phase: 0
  property int ticks: 0
  property int completions: 0
  property int previousCompletions: 0

  Connections {
    target: ProgramCheckerService
    function onChecksCompleted() {
      harness.completions++;
    }
  }

  FileView {
    id: scenario
    path: "/state/scenario"
    blockLoading: true
    blockWrites: true
  }

  function require(condition, message) {
    if (!condition)
      throw new Error(message);
  }

  function clientsEqual(discord, code) {
    const discordNames = ProgramCheckerService.availableDiscordClients.map(client => client.name);
    const codeNames = ProgramCheckerService.availableCodeClients.map(client => client.name);
    return JSON.stringify(discordNames) === JSON.stringify(discord) && JSON.stringify(codeNames) === JSON.stringify(code);
  }

  function detectWithMode(mode) {
    scenario.setText(mode);
    harness.require(scenario.text() === mode, "write private scenario");
    ProgramCheckerService.detectDiscordClient();
    ProgramCheckerService.detectCodeClient();
  }

  function checkAvailability() {
    for (const propertyName of Object.keys(ProgramCheckerService.programsToCheck)) {
      const expected = propertyName === "kittyAvailable" || propertyName === "niriAvailable";
      harness.require(ProgramCheckerService[propertyName] === expected, propertyName);
    }
    const before = ProgramCheckerService.completedChecks;
    const warnings = Logger.warnings.length;
    ProgramCheckerService.checkProgram("unknownAvailable");
    harness.require(ProgramCheckerService.completedChecks === before, "unknown check must not advance queue");
    harness.require(Logger.warnings.length === warnings + 1 && Logger.warnings[warnings].includes("unknownAvailable"), "unknown property warning");
  }

  function advance() {
    harness.ticks++;
    harness.require(harness.ticks < 200, "timed out awaiting real process exits");
    const detected = harness.clientsEqual(["vesktop", "discord"], ["code", "vscodium"]);
    const empty = harness.clientsEqual([], []);
    if (harness.phase === 0 && detected && ProgramCheckerService.completedChecks === ProgramCheckerService.totalChecks) {
      harness.checkAvailability();
      harness.detectWithMode("error");
      harness.phase = 1;
    } else if (harness.phase === 1 && empty) {
      // Nonzero exit with plausible stdout clears prior detections.
      harness.detectWithMode("success");
      harness.phase = 2;
    } else if (harness.phase === 2 && detected) {
      harness.detectWithMode("none");
      harness.phase = 3;
    } else if (harness.phase === 3 && empty) {
      // Successful empty stdout also clears prior detections.
      scenario.setText("success");
      harness.require(scenario.text() === "success", "write restart scenario");
      harness.previousCompletions = harness.completions;
      ProgramCheckerService.checkAllPrograms();
      harness.phase = 4;
    } else if (harness.phase === 4 && detected && harness.completions === harness.previousCompletions + 1) {
      harness.require(ProgramCheckerService.completedChecks === ProgramCheckerService.totalChecks, "rerun queue completed");
      harness.checkAvailability();
      console.log("PROGRAM_CHECKER_PASS: 7 cases: availability, unknown property, collector output, deduplication, nonzero exit, empty output, rerun completion");
      Qt.quit();
    }
  }

  Timer {
    interval: 20
    running: true
    repeat: true
    onTriggered: {
      try {
        harness.advance();
      } catch (error) {
        console.error("PROGRAM_CHECKER_FAIL:", error.message);
        Qt.quit();
      }
    }
  }
}
