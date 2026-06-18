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
  const shellQuote = qmlFunction("shellQuote", "value");
  const clientConfigPathExpression = qmlFunction("clientConfigPathExpression", "configPath", "suffix");
  const buildClientDetectionScript = qmlFunction("buildClientDetectionScript", "clients", "requireThemesFolder");
  const ctx = {
    root: null,
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
    shellQuote(value) {
      return shellQuote(ctx, value);
    },
    clientConfigPathExpression(configPath, suffix) {
      return clientConfigPathExpression(ctx, configPath, suffix);
    },
    buildClientDetectionScript(clients, requireThemesFolder) {
      return buildClientDetectionScript(ctx, clients, requireThemesFolder);
    },
  };
  ctx.root = ctx;

  detectDiscordClient(ctx);

  assert.deepEqual(ctx.discordDetector.command.slice(0, 2), ["sh", "-c"]);
  assert.match(ctx.discordDetector.command[2], /"\$HOME"\/'\.config\/vesktop\/themes'/);
  assert.match(ctx.discordDetector.command[2], /"\$HOME"\/'\.config\/discord'/);
  assert.match(ctx.discordDetector.command[2], /printf '%s\\n' 'vesktop'/);
  assert.match(ctx.discordDetector.command[2], /printf '%s\\n' 'discord'/);
  assert.equal(ctx.discordDetector.running, true);
}

function testProgramCheckerDetectCodeClientBuildsDirectoryProbe() {
  const detectCodeClient = qmlFunction("detectCodeClient");
  const shellQuote = qmlFunction("shellQuote", "value");
  const clientConfigPathExpression = qmlFunction("clientConfigPathExpression", "configPath", "suffix");
  const buildClientDetectionScript = qmlFunction("buildClientDetectionScript", "clients", "requireThemesFolder");
  const ctx = {
    root: null,
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
    shellQuote(value) {
      return shellQuote(ctx, value);
    },
    clientConfigPathExpression(configPath, suffix) {
      return clientConfigPathExpression(ctx, configPath, suffix);
    },
    buildClientDetectionScript(clients, requireThemesFolder) {
      return buildClientDetectionScript(ctx, clients, requireThemesFolder);
    },
  };
  ctx.root = ctx;

  detectCodeClient(ctx);

  assert.deepEqual(ctx.codeDetector.command.slice(0, 2), ["sh", "-c"]);
  assert.match(ctx.codeDetector.command[2], /"\$HOME"\/'\.config\/Code'/);
  assert.match(ctx.codeDetector.command[2], /"\$HOME"\/'\.config\/VSCodium'/);
  assert.match(ctx.codeDetector.command[2], /printf '%s\\n' 'code'/);
  assert.equal(ctx.codeDetector.running, true);
}

function testProgramCheckerParsesDetectedClientOutput() {
  const parseDetectedClients = qmlFunction("parseDetectedClients", "rawOutput", "clients");
  const clients = [
    { name: "vesktop", configPath: "~/.config/vesktop" },
    { name: "discord", configPath: "~/.config/discord" },
    { name: "code", configPath: "~/.config/Code" },
  ];

  assert.match(source, /function parseDetectedClients\(rawOutput, clients\)/, "parseDetectedClients must type detector stdout input");
  assert.deepEqual(parseDetectedClients({}, " vesktop\nmissing\tcode vesktop ", clients), [clients[0], clients[2]]);
  assert.deepEqual(parseDetectedClients({}, "   \n\t", clients), []);
}

function testProgramCheckerHandlesShellSensitiveClientFixtures() {
  assert.match(source, /function shellQuote\(value\)/, "ProgramChecker must shell-quote dynamic detector values");
  assert.match(source, /function clientConfigPathExpression\(configPath, suffix\)/, "ProgramChecker must build quoted client config path expressions");
  assert.match(source, /function buildClientDetectionScript\(clients, requireThemesFolder\)/, "ProgramChecker must build client detector scripts through a shared helper");

  const detectDiscordClient = qmlFunction("detectDiscordClient");
  const detectCodeClient = qmlFunction("detectCodeClient");
  const shellQuote = qmlFunction("shellQuote", "value");
  const clientConfigPathExpression = qmlFunction("clientConfigPathExpression", "configPath", "suffix");
  const buildClientDetectionScript = qmlFunction("buildClientDetectionScript", "clients", "requireThemesFolder");
  const parseDetectedClients = qmlFunction("parseDetectedClients", "rawOutput", "clients");
  const clients = [
    { name: "weird client", configPath: "~/.config/weird client's app", requiresThemesFolder: true },
    { name: "semi;client", configPath: "~/.config/semi;path", requiresThemesFolder: false },
  ];
  const discordCtx = {
    root: null,
    TemplateRegistry: {
      discordClients: clients,
    },
    discordDetector: {
      command: [],
      running: false,
    },
    shellQuote(value) {
      return shellQuote(discordCtx, value);
    },
    clientConfigPathExpression(configPath, suffix) {
      return clientConfigPathExpression(discordCtx, configPath, suffix);
    },
    buildClientDetectionScript(clientList, requireThemesFolder) {
      return buildClientDetectionScript(discordCtx, clientList, requireThemesFolder);
    },
  };
  const codeCtx = {
    root: null,
    TemplateRegistry: {
      codeClients: clients,
    },
    codeDetector: {
      command: [],
      running: false,
    },
    shellQuote(value) {
      return shellQuote(codeCtx, value);
    },
    clientConfigPathExpression(configPath, suffix) {
      return clientConfigPathExpression(codeCtx, configPath, suffix);
    },
    buildClientDetectionScript(clientList, requireThemesFolder) {
      return buildClientDetectionScript(codeCtx, clientList, requireThemesFolder);
    },
  };
  discordCtx.root = discordCtx;
  codeCtx.root = codeCtx;

  assert.equal(shellQuote({}, "client's; name"), "'client'\\''s; name'");
  assert.equal(clientConfigPathExpression({ root: { shellQuote: value => shellQuote({}, value) } }, "~/.config/app dir", "/themes"), "\"$HOME\"/'.config/app dir/themes'");

  detectDiscordClient(discordCtx);
  detectCodeClient(codeCtx);

  assert.doesNotMatch(discordCtx.discordDetector.command[2], /\$HOME\/\.config\/weird client's app/, "raw apostrophes must not be interpolated into shell script");
  assert.match(discordCtx.discordDetector.command[2], /"\$HOME"\/'\.config\/weird client'\\''s app\/themes'/, "theme paths must quote the path suffix safely while preserving HOME expansion");
  assert.match(discordCtx.discordDetector.command[2], /printf '%s\\n' 'weird client'/, "detected names with spaces must be emitted as single lines");
  assert.match(discordCtx.discordDetector.command[2], /"\$HOME"\/'\.config\/semi;path'/, "shell metacharacters in paths must be quoted");
  assert.match(codeCtx.codeDetector.command[2], /"\$HOME"\/'\.config\/weird client'\\''s app'/, "code client paths must quote the path suffix safely while preserving HOME expansion");
  assert.deepEqual(parseDetectedClients({}, "weird client\nsemi;client\nunknown\n", clients), clients);
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

function testProgramCheckerHandlesCheckerExit() {
  const handleCheckerExit = qmlFunction("handleCheckerExit", "exitCode");
  const calls = [];
  const ctx = {
    kittyAvailable: false,
    ghosttyAvailable: true,
    completedChecks: 0,
    totalChecks: 2,
    checker: {
      currentProperty: "kittyAvailable",
      running: true,
    },
    checkNextProgram() {
      calls.push("next");
    },
    detectDiscordClient() {
      calls.push("discord");
    },
    detectCodeClient() {
      calls.push("code");
    },
    checksCompleted() {
      calls.push("completed");
    },
  };
  ctx.root = ctx;

  assert.match(source, /function handleCheckerExit\(exitCode\)/, "handleCheckerExit must type the process exit code");
  handleCheckerExit(ctx, 0);
  assert.equal(ctx.kittyAvailable, true);
  assert.equal(ctx.checker.running, false);
  assert.equal(ctx.completedChecks, 1);
  assert.deepEqual(calls, ["next"]);

  ctx.checker.currentProperty = "ghosttyAvailable";
  handleCheckerExit(ctx, 1);
  assert.equal(ctx.ghosttyAvailable, false);
  assert.equal(ctx.completedChecks, 2);
  assert.deepEqual(calls, ["next", "discord", "code", "completed"]);
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
  testProgramCheckerParsesDetectedClientOutput,
  testProgramCheckerHandlesShellSensitiveClientFixtures,
  testProgramCheckerQueueAdvancesOneProgramAtATime,
  testProgramCheckerCheckAllProgramsResetsQueue,
  testProgramCheckerCheckProgramGuardsUnknownProperties,
  testProgramCheckerHandlesCheckerExit,
  testProgramCheckerDiscordDetectionDebugLogs,
  testProgramCheckerProbeProgramListStaysAligned,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
