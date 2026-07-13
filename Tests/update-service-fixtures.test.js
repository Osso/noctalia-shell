#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Noctalia/UpdateService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createContext() {
  const requests = [];
  class FakeXMLHttpRequest {
    static DONE = 4;

    constructor() {
      this.readyState = 0;
      this.status = 0;
      this.statusText = "";
      this.responseText = "";
      this.onreadystatechange = null;
      requests.push(this);
    }

    open(method, url) {
      this.method = method;
      this.url = url;
    }

    send() {
      this.sent = true;
    }

    complete({ status, statusText = "", responseText = "" }) {
      this.status = status;
      this.statusText = statusText;
      this.responseText = responseText;
      this.readyState = FakeXMLHttpRequest.DONE;
      this.onreadystatechange();
    }
  }

  const ctx = {
    XMLHttpRequest: FakeXMLHttpRequest,
    Logger: { d() {}, e() {} },
    I18n: { tr(key) { return key; } },
    developmentSuffix: "-git",
    upgradeLogBaseUrl: "https://example.invalid/upgrade",
    changelogLastSeenVersion: "",
    upgradeLogRequestGeneration: 0,
    releaseHighlights: [],
    fetchError: "old error",
    opened: 0,
    openWhenReady() { this.opened += 1; },
  };
  ctx.root = ctx;
  ctx.isVersionLine = text => qmlFunction("isVersionLine", "text")(ctx, text);
  ctx.cleanEntry = text => qmlFunction("cleanEntry", "text")(ctx, text);
  ctx.isIgnoredEntry = text => qmlFunction("isIgnoredEntry", "text")(ctx, text);
  ctx.parseReleaseNotes = body => qmlFunction("parseReleaseNotes", "body")(ctx, body);
  ctx.requests = requests;
  return ctx;
}

function fetch(ctx, from = "v4.0.0", to = "v5.0.0") {
  qmlFunction("fetchUpgradeLog", "fromVersion", "toVersion")(ctx, from, to);
  return ctx.requests.at(-1);
}

function testSuccessfulUpgradeLogResponsePublishesPlainTextEntries() {
  const ctx = createContext();
  const request = fetch(ctx);

  assert.equal(request.method, "GET");
  assert.equal(request.url, "https://example.invalid/upgrade/v4.0.0/v5.0.0");
  assert.equal(request.sent, true);

  request.complete({ status: 200, responseText: "A\r\nB\n" });

  assert.deepEqual(ctx.releaseHighlights, [{ version: "v5.0.0", date: "", entries: ["A", "B"] }]);
  assert.equal(ctx.fetchError, "");
  assert.equal(ctx.opened, 1);
}

function testUpgradeLogHttpAndTransportFailuresFailClosed() {
  for (const status of [0, 403, 500]) {
    const ctx = createContext();
    fetch(ctx).complete({ status, statusText: "failed", responseText: "ignored" });

    assert.deepEqual(ctx.releaseHighlights, []);
    assert.equal(ctx.fetchError, "changelog.error.fetch-failed");
    assert.equal(ctx.opened, 1);
  }
}

function testUpgradeLogBodiesRemainPlainText() {
  const empty = createContext();
  fetch(empty).complete({ status: 200, responseText: "" });
  assert.deepEqual(empty.releaseHighlights[0].entries, []);

  const markup = createContext();
  fetch(markup).complete({ status: 200, responseText: "<html>not structured release data</html>" });
  assert.deepEqual(markup.releaseHighlights[0].entries, ["<html>not structured release data</html>"]);
}

function testStaleUpgradeLogCompletionCannotOverwriteNewerResponse() {
  const ctx = createContext();
  const older = fetch(ctx, "v3.0.0", "v4.0.0");
  const newer = fetch(ctx, "v4.0.0", "v5.0.0");

  newer.complete({ status: 200, responseText: "new release" });
  older.complete({ status: 403, statusText: "stale failure" });

  assert.deepEqual(ctx.releaseHighlights, [{ version: "v5.0.0", date: "", entries: ["new release"] }]);
  assert.equal(ctx.fetchError, "");
  assert.equal(ctx.opened, 1, "stale completion must not reopen or overwrite popup state");
}

function testChangelogPanelWaitsForScreenAndRegistration() {
  const openWhenReady = qmlFunction("openWhenReady");
  const later = [];
  let panelLookups = 0;
  const ctx = {
    popupScheduled: true,
    changelogCurrentVersion: "v5.0.0",
    lastShownVersion: "",
    Quickshell: { screens: [] },
    PanelService: { getPanel() { panelLookups += 1; return null; } },
    Qt: { callLater(callback) { later.push(callback); } },
  };
  ctx.root = ctx;
  ctx.openWhenReady = () => openWhenReady(ctx);

  openWhenReady(ctx);
  assert.equal(later.length, 1);
  assert.equal(panelLookups, 0, "panel lookup must wait until a screen exists");
  assert.equal(ctx.popupScheduled, true);

  ctx.Quickshell.screens = [{ name: "screen" }];
  later.shift()();
  assert.equal(panelLookups, 1);
  assert.equal(later.length, 1, "missing panel must schedule another attempt");
  assert.equal(ctx.popupScheduled, true);

  let opened = 0;
  ctx.PanelService.getPanel = (name, screen) => {
    assert.equal(name, "changelogPanel");
    assert.equal(screen, ctx.Quickshell.screens[0]);
    return { open() { opened += 1; } };
  };
  later.shift()();
  assert.equal(opened, 1);
  assert.equal(ctx.popupScheduled, false);
  assert.equal(ctx.lastShownVersion, "v5.0.0");
}

function testChangelogStateLoadFailureStillReplaysDeferredShow() {
  const loadChangelogState = qmlFunction("loadChangelogState");
  const later = [];
  let shown = 0;
  let reads = 0;
  let loggedErrors = 0;
  const ctx = {
    changelogLastSeenVersion: "existing",
    changelogStateLoaded: false,
    pendingShowRequest: true,
    ShellState: { getChangelogState() { reads += 1; throw new Error("read failed"); } },
    Logger: { d() {}, e() { loggedErrors += 1; } },
    Qt: { callLater(callback) { later.push(callback); } },
    showLatestChangelog() { shown += 1; },
  };
  ctx.root = ctx;

  loadChangelogState(ctx);
  assert.equal(reads, 1);
  assert.equal(loggedErrors, 1);
  assert.equal(ctx.changelogLastSeenVersion, "existing", "load failure must preserve the in-memory value");
  assert.equal(ctx.changelogStateLoaded, true);
  assert.equal(ctx.pendingShowRequest, false);
  assert.equal(later.length, 1);
  later.shift()();
  assert.equal(shown, 1);

  const noPendingLater = [];
  let unexpectedShows = 0;
  const noPending = {
    changelogLastSeenVersion: "",
    changelogStateLoaded: false,
    pendingShowRequest: false,
    ShellState: { getChangelogState() { return { lastSeenVersion: "v5.0.0" }; } },
    Logger: { d() {}, e() {} },
    Qt: { callLater(callback) { noPendingLater.push(callback); } },
    showLatestChangelog() { unexpectedShows += 1; },
  };
  noPending.root = noPending;
  loadChangelogState(noPending);
  assert.equal(noPendingLater.length, 0, "load without a deferred request must not schedule replay");
  assert.equal(unexpectedShows, 0);
}

for (const test of [
  testSuccessfulUpgradeLogResponsePublishesPlainTextEntries,
  testUpgradeLogHttpAndTransportFailuresFailClosed,
  testUpgradeLogBodiesRemainPlainText,
  testStaleUpgradeLogCompletionCannotOverwriteNewerResponse,
  testChangelogPanelWaitsForScreenAndRegistration,
  testChangelogStateLoadFailureStillReplaysDeferredShow,
]) {
  test();
  console.log(`ok ${test.name}`);
}
