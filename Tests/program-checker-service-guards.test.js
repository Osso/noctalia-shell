#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/System/ProgramCheckerService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function logger() {
  const messages = [];
  return {
    messages,
    d(...args) {
      messages.push(["d", ...args]);
    },
    w(...args) {
      messages.push(["w", ...args]);
    },
  };
}

function testProgramCheckerDetectDiscordClientBuildsDirectoryProbe() {
  const detectDiscordClient = qmlFunction("detectDiscordClient");
  const ctx = {
    TemplateRegistry: {
      discordClients: [
        { name: "vesktop", configPath: "~/.config/vesktop", requiresThemesFolder: true },
        { name: "discord", configPath: "~/.config/discord", requiresThemesFolder: false },
      ],
    },
    discordDetector: {
      command: [],
      running: false,
    },
  };

  detectDiscordClient(ctx);

  assert.deepEqual(ctx.discordDetector.command.slice(0, 2), ["sh", "-c"]);
  assert.match(ctx.discordDetector.command[2], /\$HOME\/\.config\/vesktop\/themes/);
  assert.match(ctx.discordDetector.command[2], /\$HOME\/\.config\/discord"/);
  assert.match(ctx.discordDetector.command[2], /available_clients="\$available_clients vesktop"/);
  assert.match(ctx.discordDetector.command[2], /echo "\$available_clients"/);
  assert.equal(ctx.discordDetector.running, true);
}

function testProgramCheckerDetectCodeClientBuildsDirectoryProbe() {
  const detectCodeClient = qmlFunction("detectCodeClient");
  const ctx = {
    TemplateRegistry: {
      codeClients: [
        { name: "code", configPath: "~/.config/Code" },
        { name: "vscodium", configPath: "~/.config/VSCodium" },
      ],
    },
    codeDetector: {
      command: [],
      running: false,
    },
  };

  detectCodeClient(ctx);

  assert.deepEqual(ctx.codeDetector.command.slice(0, 2), ["sh", "-c"]);
  assert.match(ctx.codeDetector.command[2], /\$HOME\/\.config\/Code/);
  assert.match(ctx.codeDetector.command[2], /\$HOME\/\.config\/VSCodium/);
  assert.match(ctx.codeDetector.command[2], /available_clients="\$available_clients code"/);
  assert.equal(ctx.codeDetector.running, true);
}

function testProgramCheckerQueueAdvancesOneProgramAtATime() {
  const checkNextProgram = qmlFunction("checkNextProgram");
  const ctx = {
    currentCheckIndex: 0,
    checkQueue: ["kittyAvailable", "ghosttyAvailable"],
    programsToCheck: {
      kittyAvailable: ["which", "kitty"],
      ghosttyAvailable: ["which", "ghostty"],
    },
    checker: {
      currentProperty: "",
      command: [],
      running: false,
    },
  };

  checkNextProgram(ctx);
  assert.equal(ctx.checker.currentProperty, "kittyAvailable");
  assert.deepEqual(ctx.checker.command, ["which", "kitty"]);
  assert.equal(ctx.checker.running, true);
  assert.equal(ctx.currentCheckIndex, 1);

  checkNextProgram(ctx);
  assert.equal(ctx.checker.currentProperty, "ghosttyAvailable");
  assert.deepEqual(ctx.checker.command, ["which", "ghostty"]);
  assert.equal(ctx.currentCheckIndex, 2);

  ctx.checker.running = false;
  checkNextProgram(ctx);
  assert.equal(ctx.checker.running, false);
  assert.equal(ctx.currentCheckIndex, 2);
}

function testProgramCheckerCheckAllProgramsResetsQueue() {
  const checkAllPrograms = qmlFunction("checkAllPrograms");
  const started = [];
  const ctx = {
    completedChecks: 7,
    currentCheckIndex: 4,
    checkQueue: [],
    programsToCheck: {
      kittyAvailable: ["which", "kitty"],
      ghosttyAvailable: ["which", "ghostty"],
    },
    checkNextProgram() {
      started.push(this.checkQueue[this.currentCheckIndex]);
      this.currentCheckIndex++;
    },
  };

  checkAllPrograms(ctx);

  assert.equal(ctx.completedChecks, 0);
  assert.equal(ctx.currentCheckIndex, 1);
  assert.deepEqual(ctx.checkQueue, ["kittyAvailable", "ghosttyAvailable"]);
  assert.deepEqual(started, ["kittyAvailable"]);
}

function testProgramCheckerCheckProgramGuardsUnknownProperties() {
  const checkProgram = qmlFunction("checkProgram", "programProperty");
  const log = logger();
  const ctx = {
    Logger: log,
    programsToCheck: {
      kittyAvailable: ["which", "kitty"],
    },
    checker: {
      currentProperty: "",
      command: [],
      running: false,
    },
  };

  checkProgram(ctx, "missingAvailable");
  assert.deepEqual(log.messages, [["w", "ProgramChecker", "Unknown program property:", "missingAvailable"]]);
  assert.equal(ctx.checker.running, false);

  checkProgram(ctx, "kittyAvailable");
  assert.equal(ctx.checker.currentProperty, "kittyAvailable");
  assert.deepEqual(ctx.checker.command, ["which", "kitty"]);
  assert.equal(ctx.checker.running, true);
}

function testProgramCheckerDiscordDetectionDebugLogs() {
  const testDiscordDetection = qmlFunction("testDiscordDetection");
  const log = logger();
  let detections = 0;
  const ctx = {
    Logger: log,
    Quickshell: {
      env(name) {
        assert.equal(name, "HOME");
        return "/home/alessio";
      },
    },
    TemplateRegistry: {
      discordClients: [
        { name: "vesktop", configPath: "~/.config/vesktop" },
        { name: "discord", configPath: "~/.config/discord" },
      ],
    },
    detectDiscordClient() {
      detections++;
    },
  };

  testDiscordDetection(ctx);

  assert.deepEqual(log.messages, [
    ["d", "ProgramChecker", "Testing Discord detection..."],
    ["d", "ProgramChecker", "HOME:", "/home/alessio"],
    ["d", "ProgramChecker", "Checking:", "/home/alessio/.config/vesktop"],
    ["d", "ProgramChecker", "Checking:", "/home/alessio/.config/discord"],
  ]);
  assert.equal(detections, 1);
}

function testProgramCheckerProbeProgramListStaysAligned() {
  const propertyNames = [...source.matchAll(/"([^"]+)Available": \[/g)].map(match => match[1]);
  const servicePrograms = propertyNames.map(name => name
    .replace(/([a-z0-9])([A-Z])/g, "$1-$2")
    .toLowerCase());
  const probesSource = fs.readFileSync(path.join(__dirname, "..", "Bin/dev/service-probes.sh"), "utf8");
  const expectedBlock = probesSource.match(/local expected_programs=\(\n([\s\S]*?)\n    \)/);
  assert.notEqual(expectedBlock, null, "service-probes.sh must keep an expected_programs block");
  const probePrograms = expectedBlock[1]
    .split("\n")
    .map(line => line.trim())
    .filter(Boolean)
    .sort();

  assert.deepEqual(probePrograms, servicePrograms.filter(program => !["emacs", "telegram", "vicinae"].includes(program)).sort(), "service probe expected programs must match ProgramCheckerService programs except intentionally optional desktop/client checks");
}

const tests = [
  testProgramCheckerDetectDiscordClientBuildsDirectoryProbe,
  testProgramCheckerDetectCodeClientBuildsDirectoryProbe,
  testProgramCheckerQueueAdvancesOneProgramAtATime,
  testProgramCheckerCheckAllProgramsResetsQueue,
  testProgramCheckerCheckProgramGuardsUnknownProperties,
  testProgramCheckerDiscordDetectionDebugLogs,
  testProgramCheckerProbeProgramListStaysAligned,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
