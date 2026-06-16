#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Toast/ToastScreen.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createBaseContext(messageQueue = []) {
  return {
    messageQueue,
    maxQueueSize: 3,
    isShowingToast: false,
    replaceOnNew: false,
    processCalls: 0,
    Logger: {
      d() {},
    },
    processQueue() {
      this.processCalls += 1;
    },
  };
}

function testEnqueueToastQueuesAndProcessesNewToast() {
  const enqueueToast = qmlFunction("enqueueToast", "toastData");
  const ctx = createBaseContext();
  const toast = { type: "notice", message: "Saved", description: "Done\nnow" };

  enqueueToast(ctx, toast);

  assert.deepEqual(ctx.messageQueue, [toast]);
  assert.equal(ctx.processCalls, 1);
}

function testEnqueueToastDropsOldestWhenQueueIsFull() {
  const enqueueToast = qmlFunction("enqueueToast", "toastData");
  const oldest = { message: "oldest" };
  const newer = { message: "newer" };
  const newest = { message: "newest" };
  const ctx = createBaseContext([oldest, newer]);
  ctx.maxQueueSize = 2;

  enqueueToast(ctx, newest);

  assert.deepEqual(ctx.messageQueue, [newer, newest]);
  assert.equal(ctx.processCalls, 1);
}

function testEnqueueToastReplacesVisibleToastAndRestartsSwitchTimer() {
  const enqueueToast = qmlFunction("enqueueToast", "toastData");
  const replacement = { message: "latest", description: null, type: "warning" };
  const ctx = createBaseContext([{ message: "queued" }]);
  ctx.replaceOnNew = true;
  ctx.isShowingToast = true;
  ctx.hideStops = 0;
  ctx.hideCalls = 0;
  ctx.restartCalls = 0;
  ctx.hideTimer = {
    stop() {
      ctx.hideStops += 1;
    },
  };
  ctx.windowLoader = {
    item: {
      hideToast() {
        ctx.hideCalls += 1;
      },
    },
  };
  ctx.quickSwitchTimer = {
    restart() {
      ctx.restartCalls += 1;
    },
  };

  enqueueToast(ctx, replacement);

  assert.deepEqual(ctx.messageQueue, [replacement]);
  assert.equal(ctx.isShowingToast, false);
  assert.equal(ctx.processCalls, 0);
  assert.equal(ctx.hideStops, 1);
  assert.equal(ctx.hideCalls, 1);
  assert.equal(ctx.restartCalls, 1);
}

function testProcessQueueIgnoresEmptyOrVisibleToast() {
  const processQueue = qmlFunction("processQueue");
  const emptyCtx = {
    messageQueue: [],
    isShowingToast: false,
    windowLoader: { pendingToast: null, active: false },
  };
  const visibleCtx = {
    messageQueue: [{ message: "queued" }],
    isShowingToast: true,
    windowLoader: { pendingToast: null, active: false },
  };

  processQueue(emptyCtx);
  processQueue(visibleCtx);

  assert.equal(emptyCtx.windowLoader.active, false);
  assert.equal(visibleCtx.windowLoader.active, false);
  assert.deepEqual(visibleCtx.messageQueue, [{ message: "queued" }]);
}

function testProcessQueueActivatesLoaderWithNextToast() {
  const processQueue = qmlFunction("processQueue");
  const first = { message: "first" };
  const second = { message: "second" };
  const ctx = {
    messageQueue: [first, second],
    isShowingToast: false,
    windowLoader: { pendingToast: null, active: false },
  };

  processQueue(ctx);

  assert.equal(ctx.isShowingToast, true);
  assert.equal(ctx.windowLoader.pendingToast, first);
  assert.equal(ctx.windowLoader.active, true);
  assert.deepEqual(ctx.messageQueue, [second]);
}

const tests = [
  testEnqueueToastQueuesAndProcessesNewToast,
  testEnqueueToastDropsOldestWhenQueueIsFull,
  testEnqueueToastReplacesVisibleToastAndRestartsSwitchTimer,
  testProcessQueueIgnoresEmptyOrVisibleToast,
  testProcessQueueActivatesLoaderWithNextToast,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
