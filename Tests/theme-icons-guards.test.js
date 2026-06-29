#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Commons/ThemeIcons.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testThemeIconsResolveNamedIconsAndFailClosed() {
  const iconFromName = qmlFunction("iconFromName", "iconName", "fallbackName");
  const calls = [];
  const ctx = {
    Quickshell: {
      iconTheme: "test-theme",
    },
    ThemeIconResolver: {
      resolveIconPath(quickshell, iconName, fallbackName) {
        calls.push([quickshell.iconTheme, iconName, fallbackName]);
        return `/icons/${iconName || fallbackName}.svg`;
      },
    },
  };

  assert.equal(iconFromName(ctx, "firefox", "application-x-executable"), "/icons/firefox.svg");
  assert.deepEqual(calls, [["test-theme", "firefox", "application-x-executable"]]);

  ctx.ThemeIconResolver.resolveIconPath = () => {
    throw new Error("resolver failed");
  };
  assert.equal(iconFromName(ctx, "broken", "fallback"), "");
}

function testThemeIconsResolveDesktopEntryIconsAndFallbacks() {
  const iconForAppId = qmlFunction("iconForAppId", "appId", "fallbackName");
  const sanitizeDesktopEntryIcon = qmlFunction("sanitizeDesktopEntryIcon", "iconName", "fallbackName");
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
      heuristicLookup(appId) {
        return appId === "firefox.desktop" ? { icon: "firefox" } : null;
      },
      byId() {
        throw new Error("heuristic lookup should be preferred");
      },
    },
  };

  assert.equal(iconForAppId(ctx, "firefox.desktop", "fallback-icon"), "firefox:fallback-icon");
  assert.equal(iconForAppId(ctx, "", "fallback-icon"), "fallback-icon:fallback-icon");

  ctx.DesktopEntries.heuristicLookup = null;
  ctx.DesktopEntries.byId = appId => appId === "terminal.desktop" ? { icon: "utilities-terminal" } : null;
  assert.equal(iconForAppId(ctx, "terminal.desktop"), "utilities-terminal:application-x-executable");
  assert.equal(iconForAppId(ctx, "unknown.desktop", "fallback-icon"), "fallback-icon:fallback-icon");

  assert.deepEqual(calls, [
    ["firefox", "fallback-icon"],
    ["fallback-icon", "fallback-icon"],
    ["utilities-terminal", "application-x-executable"],
    ["fallback-icon", "fallback-icon"],
  ]);
}

function testThemeIconsRejectAbsoluteDesktopEntryIcons() {
  const sanitizeDesktopEntryIcon = qmlFunction("sanitizeDesktopEntryIcon", "iconName", "fallbackName");

  assert.equal(sanitizeDesktopEntryIcon({}, "/tmp/missing.svg", "fallback-icon"), "fallback-icon");
  assert.equal(sanitizeDesktopEntryIcon({}, "file:///tmp/missing.svg", "fallback-icon"), "fallback-icon");
  assert.equal(sanitizeDesktopEntryIcon({}, "firefox", "fallback-icon"), "firefox");
}

function testThemeIconsAppIdInputIsTyped() {
  assert.match(source, /function iconFromName\(iconName, fallbackName\)/, "iconFromName must type the required icon-name input while keeping fallback optional");
  assert.match(source, /function iconForAppId\(appId, fallbackName\)/, "iconForAppId must type the required app id input while keeping fallback optional");
}

function testThemeIconsFallbackWhenDesktopEntriesLookupFails() {
  const iconForAppId = qmlFunction("iconForAppId", "appId", "fallbackName");
  const sanitizeDesktopEntryIcon = qmlFunction("sanitizeDesktopEntryIcon", "iconName", "fallbackName");
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
        throw new Error("desktop database unavailable");
      },
      byId() {
        return null;
      },
    },
  };

  assert.equal(iconForAppId(ctx, "broken.desktop", "fallback-icon"), "fallback-icon:fallback-icon");
  assert.deepEqual(calls, [["fallback-icon", "fallback-icon"]]);
}

function testThemeIconsDistroLogoPathFailsClosed() {
  const distroLogoPath = qmlFunction("distroLogoPath");

  assert.equal(distroLogoPath({
    OSInfo: {
      distroIconPath: "/usr/share/pixmaps/arch.svg",
    },
  }), "/usr/share/pixmaps/arch.svg");

  assert.equal(distroLogoPath({
    OSInfo: {
      distroIconPath: "",
    },
  }), "");

  assert.equal(distroLogoPath({}), "");
}

const tests = [
  testThemeIconsResolveNamedIconsAndFailClosed,
  testThemeIconsResolveDesktopEntryIconsAndFallbacks,
  testThemeIconsRejectAbsoluteDesktopEntryIcons,
  testThemeIconsAppIdInputIsTyped,
  testThemeIconsFallbackWhenDesktopEntriesLookupFails,
  testThemeIconsDistroLogoPathFailsClosed,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
