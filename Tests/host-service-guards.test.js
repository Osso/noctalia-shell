#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/System/HostService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBuildCandidatesRejectsBlankAndPathLikeNames() {
  const buildCandidates = qmlFunction("buildCandidates", "name");
  const ctx = {};

  assert.deepEqual(buildCandidates(ctx, ""), []);
  assert.deepEqual(buildCandidates(ctx, "   "), []);
  assert.deepEqual(buildCandidates(ctx, "../escape"), []);
  assert.deepEqual(buildCandidates(ctx, ".hidden"), []);
}

function testBuildCandidatesIncludesKnownLogoSearchRoots() {
  const buildCandidates = qmlFunction("buildCandidates", "name");
  const ctx = {};

  const candidates = buildCandidates(ctx, "nixos-logo");

  assert.equal(candidates[0], "/usr/share/pixmaps/nixos-logo.svg");
  assert.equal(candidates[1], "/usr/share/pixmaps/nixos-logo.png");
  assert.ok(candidates.includes("/usr/share/icons/hicolor/scalable/apps/nixos-logo.svg"));
  assert.ok(candidates.includes("/usr/share/icons/hicolor/48x48/apps/nixos-logo.png"));
  assert.ok(candidates.includes("/run/current-system/sw/share/icons/hicolor/scalable/apps/nixos-logo.svg"));
  assert.ok(candidates.includes("/run/current-system/sw/share/icons/hicolor/48x48/apps/nixos-logo.png"));
  assert.ok(candidates.includes("/usr/share/icons/nixos-logo.svg"));
  assert.ok(candidates.includes("/usr/share/icons/nixos-logo/nixos-logo.png"));
  assert.ok(candidates.includes("/usr/share/icons/nixos-logo/apps/nixos-logo.svg"));
}

function testResolveLogoSkipsInvalidNames() {
  const resolveLogo = qmlFunction("resolveLogo", "name");
  const ctx = {
    buildCandidates: qmlFunction("buildCandidates", "name"),
    probe: {
      command: [],
      running: false,
    },
  };

  resolveLogo(ctx, "../escape");

  assert.deepEqual(ctx.probe.command, []);
  assert.equal(ctx.probe.running, false);
}

function testResolveLogoBuildsShellProbeForCandidates() {
  const resolveLogo = qmlFunction("resolveLogo", "name");
  const ctx = {
    buildCandidates() {
      return ["/usr/share/pixmaps/os.svg", "/usr/share/pixmaps/os.png"];
    },
    probe: {
      command: [],
      running: false,
    },
  };

  resolveLogo(ctx, "os");

  assert.deepEqual(ctx.probe.command, [
    "sh",
    "-c",
    'if [ -f "/usr/share/pixmaps/os.svg" ]; then echo "/usr/share/pixmaps/os.svg"; exit 0; fi; if [ -f "/usr/share/pixmaps/os.png" ]; then echo "/usr/share/pixmaps/os.png"; exit 0; fi; exit 1',
  ]);
  assert.equal(ctx.probe.running, true);
}

function testParseOsReleaseExtractsReadinessAndLogo() {
  const parseOsRelease = qmlFunction("parseOsRelease", "rawText");

  assert.match(source, /function parseOsRelease\(rawText: string\)/, "parseOsRelease must type raw os-release input");
  assert.deepEqual(parseOsRelease({}, [
    'NAME="NixOS"',
    'PRETTY_NAME="NixOS 26.05 (Warbler)"',
    'ID=nixos',
    'LOGO=nixos-logo',
  ].join("\n")), {
    osPretty: "NixOS 26.05 (Warbler)",
    isNixOS: true,
    logoName: "nixos-logo",
    isReady: true,
  });
  assert.deepEqual(parseOsRelease({}, [
    'NAME="Arch Linux"',
    "ID=arch",
  ].join("\n")), {
    osPretty: "Arch Linux",
    isNixOS: false,
    logoName: "",
    isReady: true,
  });
}

function testHandleLogoProbeExitAssignsLogoUrl() {
  const handleLogoProbeExit = qmlFunction("handleLogoProbeExit", "exitCode");
  const messages = [];
  const ctx = {
    osLogo: "old",
    probe: {
      stdout: {
        text: " /usr/share/pixmaps/os.svg \n",
      },
    },
    Logger: {
      d(...args) {
        messages.push(["d", ...args]);
      },
      w(...args) {
        messages.push(["w", ...args]);
      },
    },
  };

  assert.match(source, /function handleLogoProbeExit\(exitCode: int\)/, "handleLogoProbeExit must type probe exit code");
  handleLogoProbeExit(ctx, 0);
  assert.equal(ctx.osLogo, "file:///usr/share/pixmaps/os.svg");
  assert.deepEqual(messages, [["d", "HostService", "Found", "file:///usr/share/pixmaps/os.svg"]]);

  messages.length = 0;
  ctx.probe.stdout.text = "";
  handleLogoProbeExit(ctx, 1);
  assert.equal(ctx.osLogo, "");
  assert.deepEqual(messages, [["w", "HostService", "None logo found"]]);
}

function testResolveDisplayNamePrecedence() {
  const resolveDisplayName = qmlFunction("resolveDisplayName", "explicitRealName", "resolvedRealName", "userName");

  assert.match(source, /function resolveDisplayName\(explicitRealName: string, resolvedRealName: string, userName: string\)/, "resolveDisplayName must type all display-name inputs");
  assert.equal(resolveDisplayName({}, "Alessio", "Ignored", "osso"), "Alessio");
  assert.equal(resolveDisplayName({}, "", "Resolved Name", "osso"), "Resolved Name");
  assert.equal(resolveDisplayName({}, "", "", "osso"), "Osso");
  assert.equal(resolveDisplayName({}, "", "", ""), "User");
}

const tests = [
  testBuildCandidatesRejectsBlankAndPathLikeNames,
  testBuildCandidatesIncludesKnownLogoSearchRoots,
  testResolveLogoSkipsInvalidNames,
  testResolveLogoBuildsShellProbeForCandidates,
  testParseOsReleaseExtractsReadinessAndLogo,
  testHandleLogoProbeExitAssignsLogoUrl,
  testResolveDisplayNamePrecedence,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
