#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/System/HostService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createOsReleaseContext() {
  const ctx = {};
  ctx.root = ctx;
  ctx.decodeDoubleQuotedOsReleaseValue = value => qmlFunction("decodeDoubleQuotedOsReleaseValue", "value")(ctx, value);
  ctx.decodeUnquotedOsReleaseValue = value => qmlFunction("decodeUnquotedOsReleaseValue", "value")(ctx, value);
  ctx.decodeOsReleaseValue = rawValue => qmlFunction("decodeOsReleaseValue", "rawValue")(ctx, rawValue);
  return ctx;
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
  const ctx = createOsReleaseContext();

  assert.match(source, /function parseOsRelease\(rawText\)/, "parseOsRelease must type raw os-release input");
  assert.deepEqual(parseOsRelease(ctx, [
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
  assert.deepEqual(parseOsRelease(ctx, [
    'NAME="Arch Linux"',
    "ID=arch",
  ].join("\n")), {
    osPretty: "Arch Linux",
    isNixOS: false,
    logoName: "",
    isReady: true,
  });
}

function testDecodeOsReleaseValueHandlesShellStyleQuotes() {
  const decodeOsReleaseValue = qmlFunction("decodeOsReleaseValue", "rawValue");
  const ctx = createOsReleaseContext();

  assert.equal(decodeOsReleaseValue(ctx, '"Arch Linux"'), "Arch Linux");
  assert.equal(decodeOsReleaseValue(ctx, "'Arch Linux'"), "Arch Linux");
  assert.equal(decodeOsReleaseValue(ctx, '"Arch\\"Custom"'), 'Arch"Custom');
  assert.equal(decodeOsReleaseValue(ctx, '"Arch\\qLinux"'), "Arch\\qLinux");
  assert.equal(decodeOsReleaseValue(ctx, "Arch\\ Linux"), "Arch Linux");
  assert.equal(decodeOsReleaseValue(ctx, "Arch\\ "), "Arch ");
}

function testDecodeOsReleaseValueRejectsMalformedQuotes() {
  const decodeOsReleaseValue = qmlFunction("decodeOsReleaseValue", "rawValue");
  const ctx = createOsReleaseContext();

  assert.throws(() => decodeOsReleaseValue(ctx, '"Arch"junk"'), /malformed/i);
  assert.throws(() => decodeOsReleaseValue(ctx, '"Arch\\"'), /unterminated/i);
  assert.throws(() => decodeOsReleaseValue(ctx, "'Arch'junk'"), /malformed/i);
}

function testParseOsReleaseRejectsMalformedMetadata() {
  const parseOsRelease = qmlFunction("parseOsRelease", "rawText");
  const ctx = createOsReleaseContext();

  assert.throws(() => parseOsRelease(ctx, ""), /missing NAME and ID/i);
  assert.throws(() => parseOsRelease(ctx, "COMMENT=not-host-metadata"), /missing NAME and ID/i);
  assert.throws(() => parseOsRelease(ctx, 'NAME="   "\nID="   "'), /missing NAME and ID/i);
  assert.throws(() => parseOsRelease(ctx, 'NAME="Arch Linux\nID=arch'), /unterminated/i);
  assert.throws(() => parseOsRelease(ctx, "NAME=Arch Linux\nID=arch"), /malformed/i);
  assert.throws(() => parseOsRelease(ctx, 'NAME="Arch Linux"\nID=arch\nBROKEN'), /malformed/i);
}

function testParseOsReleasePreservesEmbeddedEquals() {
  const parseOsRelease = qmlFunction("parseOsRelease", "rawText");
  const parsed = parseOsRelease(createOsReleaseContext(), 'NAME="Arch=Custom"\nID=arch');

  assert.equal(parsed.osPretty, "Arch=Custom");
  assert.equal(parsed.isReady, true);

  const trailingSpace = parseOsRelease(createOsReleaseContext(), "NAME=Arch\\ \nID=arch");
  assert.equal(trailingSpace.osPretty, "Arch", "identity normalization may trim decoded trailing space after preserving valid input syntax");
}

function testHandleOsInfoLoadFailureRecordsTerminalState() {
  const handleOsInfoLoadFailure = qmlFunction("handleOsInfoLoadFailure", "error");
  const warnings = [];
  const ctx = {
    isReady: false,
    osInfoLoadFailed: false,
    osInfoError: "",
    Logger: {
      w(...args) {
        warnings.push(args.join(" "));
      },
    },
  };
  ctx.root = ctx;

  handleOsInfoLoadFailure(ctx, "permission denied");

  assert.equal(ctx.isReady, false, "failed host metadata must not report ready");
  assert.equal(ctx.osInfoLoadFailed, true, "failed host metadata must expose terminal failure");
  assert.equal(ctx.osInfoError, "permission denied", "failed host metadata must preserve error context");
  assert.match(warnings.at(-1), /permission denied/, "failed host metadata must log error context");
}

function testApplyOsReleaseRecoversAfterLoadFailure() {
  const handleOsInfoLoadFailure = qmlFunction("handleOsInfoLoadFailure", "error");
  const applyOsRelease = qmlFunction("applyOsRelease", "rawText");
  const ctx = {
    isReady: false,
    isNixOS: false,
    osPretty: "",
    osInfoLoadFailed: false,
    osInfoError: "",
    Logger: { i() {}, w() {} },
    parseOsRelease(rawText) {
      return qmlFunction("parseOsRelease", "rawText")(ctx, rawText);
    },
    resolveLogo() {},
  };
  ctx.root = ctx;
  ctx.decodeDoubleQuotedOsReleaseValue = value => qmlFunction("decodeDoubleQuotedOsReleaseValue", "value")(ctx, value);
  ctx.decodeUnquotedOsReleaseValue = value => qmlFunction("decodeUnquotedOsReleaseValue", "value")(ctx, value);
  ctx.decodeOsReleaseValue = rawValue => qmlFunction("decodeOsReleaseValue", "rawValue")(ctx, rawValue);

  handleOsInfoLoadFailure(ctx, "temporary failure");
  applyOsRelease(ctx, 'NAME="Arch Linux"\nID=arch');

  assert.equal(ctx.isReady, true, "successful retry must restore host readiness");
  assert.equal(ctx.isNixOS, false);
  assert.equal(ctx.osPretty, "Arch Linux");
  assert.equal(ctx.osInfoLoadFailed, false, "successful retry must clear terminal failure");
  assert.equal(ctx.osInfoError, "", "successful retry must clear stale error context");
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

  assert.match(source, /function handleLogoProbeExit\(exitCode\)/, "handleLogoProbeExit must type probe exit code");
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

  assert.match(source, /function resolveDisplayName\(explicitRealName, resolvedRealName, userName\)/, "resolveDisplayName must type all display-name inputs");
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
  testDecodeOsReleaseValueHandlesShellStyleQuotes,
  testDecodeOsReleaseValueRejectsMalformedQuotes,
  testParseOsReleaseRejectsMalformedMetadata,
  testParseOsReleasePreservesEmbeddedEquals,
  testHandleOsInfoLoadFailureRecordsTerminalState,
  testApplyOsReleaseRecoversAfterLoadFailure,
  testHandleLogoProbeExitAssignsLogoUrl,
  testResolveDisplayNamePrecedence,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
