#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/UI/ToastService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { const fn = function(${argNames.join(", ")}) ${body}; return fn.apply(ctx, Array.prototype.slice.call(arguments, 1)); }`);
}

function createContext() {
  const notifications = [];
  return {
    notifications,
    notify(...args) {
      notifications.push(args);
    },
  };
}

function testToastServiceShowNoticeForwardsMessageIconTypeAndDefaultDuration() {
  const showNotice = qmlFunction("showNotice", "message", "description = \"\"", "icon = \"\"", "duration = 3000");
  const ctx = createContext();

  showNotice(ctx, "Title", "Body", "info-icon");

  assert.deepEqual(ctx.notifications, [["Title", "Body", "info-icon", "notice", 3000]]);
}

function testToastServiceShowWarningUsesWarningTypeAndEmptyIcon() {
  const showWarning = qmlFunction("showWarning", "message", "description = \"\"", "duration = 4000");
  const ctx = createContext();

  showWarning(ctx, "Careful", "Something happened", 12000);

  assert.deepEqual(ctx.notifications, [["Careful", "Something happened", "", "warning", 12000]]);
}

function testToastServiceShowErrorUsesErrorTypeAndDefaultDuration() {
  const showError = qmlFunction("showError", "message", "description = \"\"", "duration = 6000");
  const ctx = createContext();

  showError(ctx, "Failed", "Something broke");

  assert.deepEqual(ctx.notifications, [["Failed", "Something broke", "", "error", 6000]]);
}

const tests = [
  testToastServiceShowNoticeForwardsMessageIconTypeAndDefaultDuration,
  testToastServiceShowWarningUsesWarningTypeAndEmptyIcon,
  testToastServiceShowErrorUsesErrorTypeAndDefaultDuration,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
