#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testColorSchemeInitializationAndLoadingGuards() {
  const source = readQml("Services/Theming/ColorSchemeService.qml");
  const initBody = extractFunctionBody(source, "init");
  const loadBody = extractFunctionBody(source, "loadColorSchemes");

  assert.match(initBody, /Logger\.i\("ColorScheme", "Service started"\)/, "init must log service startup");
  assert.match(initBody, /loadColorSchemes\(\)/, "init must trigger color scheme discovery");
  assert.match(loadBody, /Logger\.d\("ColorScheme", "Load colorScheme"\)/, "loadColorSchemes must log discovery");
  assert.match(loadBody, /scanning = true[\s\S]*schemes = \[\]/, "loadColorSchemes must reset scan state");
  assert.match(loadBody, /Quickshell\.execDetached\(\["mkdir", "-p", downloadedSchemesDirectory\]\)/, "loadColorSchemes must ensure downloaded scheme directory exists");
  assert.match(loadBody, /findProcess\.command = \["find", schemesDirectory, downloadedSchemesDirectory, "-name", "\*\.json", "-type", "f"\]/, "loadColorSchemes must scan preinstalled and downloaded schemes");
  assert.match(loadBody, /findProcess\.running = true/, "loadColorSchemes must start the finder process");
}

function testColorSchemePathResolutionGuards() {
  const source = readQml("Services/Theming/ColorSchemeService.qml");
  const basenameBody = extractFunctionBody(source, "getBasename");
  const resolveBody = extractFunctionBody(source, "resolveSchemePath");

  assert.match(basenameBody, /if \(!path\)\s+return ""/, "getBasename must handle empty paths");
  assert.match(basenameBody, /var filename = chunks\[chunks\.length - 1\][\s\S]*var schemeName = filename\.replace\("\.json", ""\)/, "getBasename must strip directories and json extension");
  assert.match(basenameBody, /schemeName === "Noctalia-default"[\s\S]*return "Noctalia \(default\)"/, "getBasename must normalize Noctalia default name");
  assert.match(basenameBody, /schemeName === "Noctalia-legacy"[\s\S]*return "Noctalia \(legacy\)"/, "getBasename must normalize Noctalia legacy name");
  assert.match(basenameBody, /schemeName === "Tokyo-Night"[\s\S]*return "Tokyo Night"/, "getBasename must normalize Tokyo Night name");
  assert.match(basenameBody, /schemeName === "Rosepine"[\s\S]*return "Rose Pine"/, "getBasename must normalize Rose Pine name");
  assert.match(resolveBody, /if \(!nameOrPath\)\s+return ""/, "resolveSchemePath must handle empty input");
  assert.match(resolveBody, /if \(nameOrPath\.indexOf\("\/"\) !== -1\)[\s\S]*return nameOrPath/, "resolveSchemePath must preserve explicit paths");
  assert.match(resolveBody, /schemeName === "Noctalia \(default\)"[\s\S]*schemeName = "Noctalia-default"/, "resolveSchemePath must map display names to directory names");
  assert.match(resolveBody, /schemeName === "Tokyo Night"[\s\S]*schemeName = "Tokyo-Night"/, "resolveSchemePath must map Tokyo Night display name");
  assert.match(resolveBody, /var preinstalledPath = schemesDirectory \+ "\/" \+ schemeName \+ "\/" \+ schemeName \+ "\.json"/, "resolveSchemePath must build preinstalled path fallback");
  assert.match(resolveBody, /var downloadedPath = downloadedSchemesDirectory \+ "\/" \+ schemeName \+ "\/" \+ schemeName \+ "\.json"/, "resolveSchemePath must build downloaded path candidate");
  assert.match(resolveBody, /for \(var i = 0; i < schemes\.length; i\+\+\)[\s\S]*return schemes\[i\]/, "resolveSchemePath must prefer loaded scheme paths");
  assert.match(resolveBody, /return preinstalledPath/, "resolveSchemePath must fall back to preinstalled path");
}

function testColorSchemeApplyAndSelectionGuards() {
  const source = readQml("Services/Theming/ColorSchemeService.qml");
  const applyBody = extractFunctionBody(source, "applyScheme");
  const setBody = extractFunctionBody(source, "setPredefinedScheme");
  const templateBody = extractFunctionBody(source, "hasEnabledTemplates");

  assert.match(applyBody, /var filePath = resolveSchemePath\(nameOrPath\)/, "applyScheme must resolve display names or paths");
  assert.match(applyBody, /schemeReader\.path = ""[\s\S]*schemeReader\.path = filePath/, "applyScheme must bounce FileView path to force reload");
  assert.match(setBody, /Logger\.i\("ColorScheme", "Attempting to set predefined scheme to:", schemeName\)/, "setPredefinedScheme must log requested scheme");
  assert.match(setBody, /var resolvedPath = resolveSchemePath\(schemeName\)[\s\S]*var basename = getBasename\(schemeName\)/, "setPredefinedScheme must resolve path and display basename");
  assert.match(setBody, /for \(var i = 0; i < schemes\.length; i\+\+\)[\s\S]*if \(getBasename\(schemes\[i\]\) === basename\)/, "setPredefinedScheme must verify loaded schemes by basename");
  assert.match(setBody, /Settings\.data\.colorSchemes\.predefinedScheme = basename[\s\S]*applyScheme\(schemeName\)/, "setPredefinedScheme must persist and apply valid schemes");
  assert.match(setBody, /ToastService\.showNotice\("Color Scheme", `Set to \$\{basename\}`, "settings-color-scheme"\)/, "setPredefinedScheme must toast successful scheme changes");
  assert.match(setBody, /Logger\.e\("ColorScheme", "Scheme not found:", schemeName\)[\s\S]*ToastService\.showError\("Color Scheme", `Scheme '\$\{basename\}' not found!`\)/, "setPredefinedScheme must report missing schemes");
  assert.match(templateBody, /const templates = Settings\.data\.templates/, "hasEnabledTemplates must inspect template settings");
  assert.match(templateBody, /for \(const key in templates\)[\s\S]*if \(templates\[key\]\)[\s\S]*return true/, "hasEnabledTemplates must detect any enabled template");
  assert.match(templateBody, /return false/, "hasEnabledTemplates must return false when no template is enabled");
}

function testColorSchemeWriteGuards() {
  const source = readQml("Services/Theming/ColorSchemeService.qml");
  const writeBody = extractFunctionBody(source, "writeColorsToDisk");

  assert.match(writeBody, /function pick\(o, a, b, fallback\)[\s\S]*return \(o && \(o\[a\] \|\| o\[b\]\)\) \|\| fallback/, "writeColorsToDisk must support material and plain key names with fallbacks");
  const palettePairs = [
    ["mPrimary", "primary"],
    ["mOnPrimary", "onPrimary"],
    ["mSecondary", "secondary"],
    ["mOnSecondary", "onSecondary"],
    ["mTertiary", "tertiary"],
    ["mOnTertiary", "onTertiary"],
    ["mError", "error"],
    ["mOnError", "onError"],
    ["mSurface", "surface"],
    ["mOnSurface", "onSurface"],
    ["mSurfaceVariant", "surfaceVariant"],
    ["mOnSurfaceVariant", "onSurfaceVariant"],
    ["mOutline", "outline"],
    ["mShadow", "shadow"],
    ["mHover", "hover"],
    ["mOnHover", "onHover"],
  ];

  for (const [materialKey, plainKey] of palettePairs) {
    const pattern = new RegExp(`out\\.${materialKey} = pick\\(obj, "${materialKey}", "${plainKey}", out\\.${materialKey}\\)`);
    assert.match(writeBody, pattern, `writeColorsToDisk must persist ${materialKey}`);
  }

  assert.match(writeBody, /colorsWriter\.path = ""[\s\S]*colorsWriter\.path = colorsJsonFilePath[\s\S]*colorsWriter\.writeAdapter\(\)/, "writeColorsToDisk must force colors.json rewrite");
}

const tests = [
  testColorSchemeInitializationAndLoadingGuards,
  testColorSchemePathResolutionGuards,
  testColorSchemeApplyAndSelectionGuards,
  testColorSchemeWriteGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
