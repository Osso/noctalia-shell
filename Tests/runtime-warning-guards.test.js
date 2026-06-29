#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const cavaSource = readQml("Services/Media/CavaService.qml");
const themeIconsSource = readQml("Commons/ThemeIcons.qml");
const processPanelSource = readQml("Modules/Panels/Process/ProcessPanel.qml");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testCavaDoesNotSpawnWhenUnavailable() {
  const canRunCava = qmlFunction(cavaSource, "canRunCava");
  const ctx = {
    ProgramCheckerService: { cavaAvailable: false },
    BarService: { hasAudioVisualizer: true },
    PanelService: { lockScreen: null, openedPanel: null },
  };

  assert.match(cavaSource, /import qs\.Services\.System/, "CavaService must import ProgramCheckerService availability state");
  assert.match(cavaSource, /property bool shouldRun: canRunCava\(\)/, "CavaService should delegate process start gating to canRunCava");
  assert.equal(canRunCava(ctx), false, "cava must not spawn when the binary is unavailable");

  ctx.ProgramCheckerService.cavaAvailable = true;
  assert.equal(canRunCava(ctx), true, "cava may run when available and a visualizer consumer exists");
}

function testThemeIconsRejectUnsafeDesktopEntryIconPaths() {
  const sanitizeDesktopEntryIcon = qmlFunction(themeIconsSource, "sanitizeDesktopEntryIcon", "iconName", "fallbackName");
  const iconForAppId = qmlFunction(themeIconsSource, "iconForAppId", "appId", "fallbackName");
  const calls = [];
  const ctx = {
    sanitizeDesktopEntryIcon(iconName, fallbackName) {
      return sanitizeDesktopEntryIcon(ctx, iconName, fallbackName);
    },
    iconFromName(iconName, fallbackName) {
      calls.push([iconName, fallbackName]);
      return `${iconName}:${fallbackName}`;
    },
    DesktopEntries: {
      heuristicLookup() {
        return { icon: "/home/osso/.local/share/JetBrains/Toolbox/missing.desktop.icon.svg" };
      },
    },
  };

  assert.equal(sanitizeDesktopEntryIcon(ctx, "/tmp/missing.svg", "fallback-icon"), "fallback-icon");
  assert.equal(sanitizeDesktopEntryIcon(ctx, "file:///tmp/missing.svg", "fallback-icon"), "fallback-icon");
  assert.equal(sanitizeDesktopEntryIcon(ctx, "org.mozilla.firefox", "fallback-icon"), "org.mozilla.firefox");
  assert.equal(iconForAppId(ctx, "jetbrains-rustrover.desktop", "fallback-icon"), "fallback-icon:fallback-icon");
  assert.deepEqual(calls, [["fallback-icon", "fallback-icon"]]);
}

function testProcessPanelUsesDefinedWarningColor() {
  assert.doesNotMatch(processPanelSource, /Color\.mWarning/, "ProcessPanel must not reference undefined Color.mWarning");
  assert.match(processPanelSource, /if \(processCpu > 20\)\s+return Color\.mTertiary;/, "ProcessPanel CPU warning state must use defined tertiary color");
}

const tests = [
  testCavaDoesNotSpawnWhenUnavailable,
  testThemeIconsRejectUnsafeDesktopEntryIconPaths,
  testProcessPanelUsesDefinedWarningColor,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
