#!/usr/bin/env node

const assert = require("assert/strict");
const vm = require("vm");
const {
  readQml,
  extractFunctionBody,
  extractHandlerBlock,
  findComponentBlock,
} = require("./qml-test-utils");

const source = readQml("Services/Theming/ColorSchemeService.qml");
const plain = value => JSON.parse(JSON.stringify(value));

// Execute the service's JS with isolated QML boundary objects. No disk writes,
// processes, Settings singleton, or desktop surfaces are created.
function createService() {
  const effects = { commands: [], notices: [], errors: [], paths: [], palettes: [] };
  const root = {
    schemes: [],
    scanning: false,
    schemesDirectory: "/bundled",
    downloadedSchemesDirectory: "/isolated/colorschemes",
    colorsJsonFilePath: "/isolated/colors.json",
  };
  const settings = {
    colorSchemes: { darkMode: true, useWallpaperColors: false, predefinedScheme: "", generateTemplatesForPredefined: true },
    templates: { terminal: true },
  };
  const schemeReader = {};
  Object.defineProperty(schemeReader, "path", {
    set: value => effects.paths.push(value),
  });
  const context = vm.createContext({
    root,
    Settings: { data: settings },
    Logger: { d() {}, i() {}, e() {} },
    Quickshell: { execDetached: command => effects.commands.push(plain(command)) },
    ToastService: {
      showNotice: (...args) => effects.notices.push(args),
      showError: (...args) => effects.errors.push(args),
    },
    I18n: { tr: key => key },
    AppThemeService: { generateFromPredefinedScheme: data => effects.palettes.push(plain(data)) },
    findProcess: { running: false },
    schemeReader,
    out: { mPrimary: "#000000", mSurface: "#111111" },
    colorsWriter: { writeAdapter() { effects.saved = true; } },
  });
  // QML root functions can resolve their own properties and functions directly.
  for (const name of Object.keys(root)) {
    Object.defineProperty(context, name, {
      get: () => root[name],
      set: value => { root[name] = value; },
      configurable: true,
    });
  }
  const functions = {
    init: [], loadColorSchemes: [], getBasename: ["path"],
    resolveSchemePath: ["nameOrPath"], applyScheme: ["nameOrPath"],
    setPredefinedScheme: ["schemeName"], hasEnabledTemplates: [], writeColorsToDisk: ["obj"],
    onDarkModeChanged: [],
  };
  for (const [name, args] of Object.entries(functions)) {
    root[name] = vm.runInContext(`(function(${args.join(",")}) ${extractFunctionBody(source, name)})`, context);
    context[name] = root[name];
  }
  function handler(component, marker, name, args = []) {
    const block = extractHandlerBlock(findComponentBlock(source, component, marker), name);
    return vm.runInContext(`(function(${args.join(",")}) ${block.slice(block.indexOf("{"))})`, context);
  }
  return {
    root, settings, effects, context,
    exited: handler("Process", "id: findProcess", "onExited", ["exitCode"]),
    loaded: handler("FileView", "id: schemeReader", "onLoaded"),
  };
}

function testDiscoveryAndLookup() {
  const { root, context, effects, settings, exited } = createService();
  root.init();
  assert.equal(root.scanning, true);
  assert.deepEqual(plain(root.schemes), []);
  assert.deepEqual(effects.commands, [["mkdir", "-p", "/isolated/colorschemes"]]);
  assert.deepEqual(plain(context.findProcess.command), ["find", "/bundled", "/isolated/colorschemes", "-name", "*.json", "-type", "f"]);
  assert.equal(context.findProcess.running, true);
  settings.colorSchemes.predefinedScheme = "/isolated/colorschemes/Tokyo-Night/Tokyo-Night.json";
  context.stdout = { text: "/bundled/Zebra/Zebra.json\n/isolated/colorschemes/Tokyo-Night/Tokyo-Night.json\n/bundled/Amber.json\n" };
  exited(0);
  assert.deepEqual(plain(root.schemes), ["/bundled/Amber.json", "/isolated/colorschemes/Tokyo-Night/Tokyo-Night.json", "/bundled/Zebra/Zebra.json"]);
  assert.equal(root.scanning, false);
  assert.equal(settings.colorSchemes.predefinedScheme, "Tokyo Night");
  assert.deepEqual(effects.paths, ["", "/isolated/colorschemes/Tokyo-Night/Tokyo-Night.json"]);
  assert.equal(root.resolveSchemePath("Tokyo Night"), "/isolated/colorschemes/Tokyo-Night/Tokyo-Night.json");
  assert.equal(root.resolveSchemePath("Noctalia (default)"), "/bundled/Noctalia-default/Noctalia-default.json");
  assert.equal(root.resolveSchemePath("Rose Pine"), "/bundled/Rosepine/Rosepine.json");
  assert.equal(root.resolveSchemePath("/explicit/theme.json"), "/explicit/theme.json");
  assert.equal(root.resolveSchemePath(""), "");
  exited(1);
  assert.deepEqual(plain(root.schemes), []);
  assert.equal(root.scanning, false);
}

function testSelectionAndDarkMode() {
  const { root, settings, effects } = createService();
  root.schemes = ["/bundled/Rosepine/Rosepine.json"];
  root.setPredefinedScheme("Rose Pine");
  assert.equal(settings.colorSchemes.predefinedScheme, "Rose Pine");
  assert.deepEqual(effects.paths, ["", "/bundled/Rosepine/Rosepine.json"]);
  assert.deepEqual(effects.notices[0], ["Color Scheme", "Set to Rose Pine", "settings-color-scheme"]);
  root.setPredefinedScheme("Missing");
  assert.equal(settings.colorSchemes.predefinedScheme, "Rose Pine");
  assert.deepEqual(effects.errors, [["Color Scheme", "Scheme 'Missing' not found!"]]);
  root.onDarkModeChanged();
  assert.equal(effects.paths.length, 4);
  assert.deepEqual(effects.notices[1], ["toast.dark-mode.dark-mode", "toast.dark-mode.enabled", "dark-mode"]);
  settings.colorSchemes.useWallpaperColors = true;
  root.onDarkModeChanged();
  assert.equal(effects.paths.length, 4);
}

function testLoadedVariantsAndWriting() {
  const { settings, context, effects, loaded } = createService();
  const data = { dark: { primary: "#123456" }, light: { mPrimary: "#abcdef" } };
  context.text = () => JSON.stringify(data);
  context.path = "/bundled/Rosepine/Rosepine.json";
  loaded();
  assert.equal(context.out.mPrimary, "#123456");
  assert.equal(context.out.mSurface, "#111111");
  assert.equal(context.colorsWriter.path, "/isolated/colors.json");
  assert.equal(effects.saved, true);
  assert.deepEqual(effects.palettes, [data]);
  settings.colorSchemes.darkMode = false;
  settings.templates.terminal = false;
  loaded();
  assert.equal(context.out.mPrimary, "#abcdef");
  assert.equal(effects.palettes.length, 1);
}

for (const test of [testDiscoveryAndLookup, testSelectionAndDarkMode, testLoadedVariantsAndWriting]) {
  test();
  console.log(`ok ${test.name}`);
}
