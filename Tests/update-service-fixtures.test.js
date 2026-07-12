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

for (const test of [
  testSuccessfulUpgradeLogResponsePublishesPlainTextEntries,
  testUpgradeLogHttpAndTransportFailuresFailClosed,
  testUpgradeLogBodiesRemainPlainText,
  testStaleUpgradeLogCompletionCannotOverwriteNewerResponse,
]) {
  test();
  console.log(`ok ${test.name}`);
}
