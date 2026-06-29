#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/UI/PanelService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testPanelRegistrationGuards() {
  const registerPanelBody = extractFunctionBody(source, "registerPanel");
  const registerPanelLoaderBody = extractFunctionBody(source, "registerPanelLoader");
  const registerPopupBody = extractFunctionBody(source, "registerPopupMenuWindow");

  assert.match(registerPanelBody, /registeredPanels\[panel\.objectName\] = panel/, "registerPanel must store panels by objectName");
  assert.match(registerPanelLoaderBody, /panelLoaders\[panelKey\] = loader/, "registerPanelLoader must store panel loaders by panel key");
  assert.match(registerPanelBody, /Logger\.d\("PanelService", "Registered panel:", panel\.objectName\)/, "registerPanel must log registered panel names");
  assert.match(registerPopupBody, /if \(!screen \|\| !window\)[\s\S]*return/, "registerPopupMenuWindow must ignore missing screen or window");
  assert.match(registerPopupBody, /var key = screen\.name[\s\S]*popupMenuWindows\[key\] = window/, "registerPopupMenuWindow must store windows by screen name");
  assert.match(registerPopupBody, /popupMenuWindowRegistered\(screen\)/, "registerPopupMenuWindow must emit registration signal");
}

function testPanelLookupGuards() {
  const getPopupBody = extractFunctionBody(source, "getPopupMenuWindow");
  const getPanelBody = extractFunctionBody(source, "getPanel");
  const loadPanelBody = extractFunctionBody(source, "loadPanel");
  const hasPanelBody = extractFunctionBody(source, "hasPanel");

  assert.match(getPopupBody, /if \(!screen\)[\s\S]*return null/, "getPopupMenuWindow must return null without a screen");
  assert.match(getPopupBody, /return popupMenuWindows\[screen\.name\] \|\| null/, "getPopupMenuWindow must fall back to null for unknown screens");
  assert.match(getPanelBody, /if \(!screen\)[\s\S]*for \(var key in registeredPanels\)[\s\S]*key\.startsWith\(name \+ "-"\)[\s\S]*return registeredPanels\[key\]/, "getPanel must fall back to first matching panel when screen is missing");
  assert.match(getPanelBody, /var panelKey = `\$\{name\}-\$\{screen\.name\}`/, "getPanel must include screen name in panel keys");
  assert.match(getPanelBody, /if \(registeredPanels\[panelKey\]\)[\s\S]*return registeredPanels\[panelKey\]/, "getPanel must return already registered screen panel");
  assert.match(getPanelBody, /return loadPanel\(panelKey\)/, "getPanel must load registered lazy panels on demand");
  assert.match(loadPanelBody, /const loader = panelLoaders\[panelKey\]/, "loadPanel must look up registered panel loaders");
  assert.match(loadPanelBody, /loader\.active = true[\s\S]*return loader\.item \|\| registeredPanels\[panelKey\] \|\| null/, "loadPanel must activate loaders and return loaded panel items");
  assert.match(loadPanelBody, /Logger\.w\("PanelService", "Panel not found:", panelKey\)[\s\S]*return null/, "loadPanel must log and fail closed for missing panel keys");
  assert.match(hasPanelBody, /return name in registeredPanels/, "hasPanel must query registered panel keys");
}

function testLazyPanelLookupExecutes() {
  const registerPanelLoader = qmlFunction("registerPanelLoader", "panelKey", "loader");
  const getPanel = qmlFunction("getPanel", "name", "screen");
  const hasPanel = qmlFunction("hasPanel", "name");
  const loadedPanel = { objectName: "clockPanel-eDP-1" };
  const loader = { active: false, item: loadedPanel };
  const ctx = {
    registeredPanels: {},
    panelLoaders: {},
    Logger: { d() {}, w() {} },
    loadPanel(panelKey) {
      const targetLoader = this.panelLoaders[panelKey];
      if (!targetLoader) {
        this.Logger.w("PanelService", "Panel not found:", panelKey);
        return null;
      }
      targetLoader.active = true;
      return targetLoader.item || this.registeredPanels[panelKey] || null;
    },
  };

  registerPanelLoader(ctx, "clockPanel-eDP-1", loader);

  assert.equal(hasPanel(ctx, "clockPanel-eDP-1"), true);
  assert.equal(getPanel(ctx, "clockPanel", { name: "eDP-1" }), loadedPanel);
  assert.equal(loader.active, true);
}

function testPanelMultiScreenPopupAndPanelLookupsExecute() {
  const registerPanel = qmlFunction("registerPanel", "panel");
  const registerPopupMenuWindow = qmlFunction("registerPopupMenuWindow", "screen", "window");
  const getPopupMenuWindow = qmlFunction("getPopupMenuWindow", "screen");
  const getPanel = qmlFunction("getPanel", "name", "screen");
  const hasPanel = qmlFunction("hasPanel", "name");
  const popupSignals = [];
  const leftScreen = { name: "eDP-1" };
  const rightScreen = { name: "HDMI-A-1" };
  const leftPanel = { objectName: "launcher-eDP-1" };
  const rightPanel = { objectName: "launcher-HDMI-A-1" };
  const leftWindow = { id: "left-window" };
  const rightWindow = { id: "right-window" };
  const ctx = {
    registeredPanels: {},
    panelLoaders: {},
    popupMenuWindows: {},
    Logger: {
      d() {},
      w() {},
    },
    loadPanel(panelKey) {
      const loader = this.panelLoaders[panelKey];
      if (!loader) {
        this.Logger.w("PanelService", "Panel not found:", panelKey);
        return null;
      }
      loader.active = true;
      return loader.item || this.registeredPanels[panelKey] || null;
    },
    popupMenuWindowRegistered(screen) {
      popupSignals.push(screen.name);
    },
  };

  registerPanel(ctx, leftPanel);
  registerPanel(ctx, rightPanel);
  registerPopupMenuWindow(ctx, leftScreen, leftWindow);
  registerPopupMenuWindow(ctx, rightScreen, rightWindow);
  registerPopupMenuWindow(ctx, null, { id: "missing-screen" });
  registerPopupMenuWindow(ctx, { name: "DP-1" }, null);

  assert.equal(getPanel(ctx, "launcher", leftScreen), leftPanel);
  assert.equal(getPanel(ctx, "launcher", rightScreen), rightPanel);
  assert.equal(getPanel(ctx, "launcher", null), leftPanel);
  assert.equal(getPanel(ctx, "launcher", { name: "DP-1" }), null);
  assert.equal(hasPanel(ctx, "launcher-eDP-1"), true);
  assert.equal(hasPanel(ctx, "launcher-DP-1"), false);
  assert.equal(getPopupMenuWindow(ctx, leftScreen), leftWindow);
  assert.equal(getPopupMenuWindow(ctx, rightScreen), rightWindow);
  assert.equal(getPopupMenuWindow(ctx, { name: "DP-1" }), null);
  assert.equal(getPopupMenuWindow(ctx, null), null);
  assert.deepEqual(popupSignals, ["eDP-1", "HDMI-A-1"]);
}

function testPanelOpenCloseGuards() {
  const willOpenBody = extractFunctionBody(source, "willOpenPanel");
  const closedBody = extractFunctionBody(source, "closedPanel");

  assert.match(willOpenBody, /if \(openedPanel && openedPanel !== panel\)[\s\S]*openedPanel\.close\(\)/, "willOpenPanel must close a different open panel");
  assert.match(willOpenBody, /openedPanel = panel[\s\S]*willOpen\(\)/, "willOpenPanel must set openedPanel before emitting");
  assert.match(closedBody, /if \(openedPanel && openedPanel === panel\)[\s\S]*openedPanel = null/, "closedPanel must clear only the active panel");
  assert.match(closedBody, /didClose\(\)/, "closedPanel must emit didClose");
}

function testPanelOpenClosesDifferentActivePanelBeforeSignal() {
  const willOpenPanel = qmlFunction("willOpenPanel", "panel");
  const events = [];
  const previousPanel = {
    close() {
      events.push("close-previous");
    },
  };
  const nextPanel = {
    close() {
      events.push("close-next");
    },
  };
  const ctx = {
    openedPanel: previousPanel,
    willOpen() {
      events.push(`will-open:${this.openedPanel === nextPanel}`);
    },
  };

  willOpenPanel(ctx, nextPanel);

  assert.equal(ctx.openedPanel, nextPanel);
  assert.deepEqual(events, ["close-previous", "will-open:true"]);
}

function testPanelCloseClearsOnlyActivePanelBeforeSignal() {
  const closedPanel = qmlFunction("closedPanel", "panel");
  const activePanel = {};
  const otherPanel = {};
  const events = [];
  const ctx = {
    openedPanel: activePanel,
    didClose() {
      events.push(this.openedPanel === null ? "closed-empty" : "closed-kept");
    },
  };

  closedPanel(ctx, otherPanel);
  assert.equal(ctx.openedPanel, activePanel);
  assert.deepEqual(events, ["closed-kept"]);

  closedPanel(ctx, activePanel);
  assert.equal(ctx.openedPanel, null);
  assert.deepEqual(events, ["closed-kept", "closed-empty"]);
}

const tests = [
  testPanelRegistrationGuards,
  testPanelLookupGuards,
  testLazyPanelLookupExecutes,
  testPanelMultiScreenPopupAndPanelLookupsExecute,
  testPanelOpenCloseGuards,
  testPanelOpenClosesDifferentActivePanelBeforeSignal,
  testPanelCloseClearsOnlyActivePanelBeforeSignal,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
