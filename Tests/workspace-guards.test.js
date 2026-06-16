#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Bar/Widgets/Workspace.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function listModel(items = []) {
  return {
    items: [...items],
    get count() {
      return this.items.length;
    },
    get(index) {
      return this.items[index];
    },
    clear() {
      this.items = [];
    },
    append(item) {
      this.items.push(item);
    },
  };
}

function testWorkspaceDimensionsRespectLabelsAndActivity() {
  const getWorkspaceWidth = qmlFunction("getWorkspaceWidth", "ws");
  const getWorkspaceHeight = qmlFunction("getWorkspaceHeight", "ws");
  const ctx = {
    Style: { capsuleHeight: 20 },
    root: null,
    baseDimensionRatio: 1,
    characterCount: 4,
    labelMode: "none",
  };
  ctx.root = ctx;

  assert.equal(getWorkspaceWidth(ctx, { idx: 2, isActive: false }), 20);
  assert.equal(getWorkspaceHeight(ctx, { idx: 2, isActive: true }), 44);

  ctx.labelMode = "name";
  assert.equal(getWorkspaceWidth(ctx, { idx: 2, name: "mailbox", isActive: false }), 44);

  ctx.labelMode = "index+name";
  assert.equal(getWorkspaceWidth(ctx, { idx: 2, name: "mailbox", isActive: false }), 60);
}

function testWorkspaceAggregateDimensionsIncludeSpacingAndPadding() {
  const computeWidth = qmlFunction("computeWidth");
  const computeHeight = qmlFunction("computeHeight");
  const ctx = {
    localWorkspaces: listModel([{ w: 10, h: 3 }, { w: 14, h: 7 }]),
    spacingBetweenPills: 5,
    horizontalPadding: 2,
    getWorkspaceWidth: ws => ws.w,
    getWorkspaceHeight: ws => ws.h,
  };

  assert.equal(computeWidth(ctx), 33);
  assert.equal(computeHeight(ctx), 19);
}

function testWorkspaceFocusedIndexAndSwitchingGuards() {
  const getFocusedLocalIndex = qmlFunction("getFocusedLocalIndex");
  const switchByOffset = qmlFunction("switchByOffset", "offset");
  const switched = [];
  const ctx = {
    localWorkspaces: listModel([{ idx: 1 }, { idx: 2, isFocused: true }, { idx: 3 }]),
    getFocusedLocalIndex: () => getFocusedLocalIndex(ctx),
    CompositorService: {
      switchToWorkspace: ws => switched.push(ws.idx),
    },
  };

  assert.equal(getFocusedLocalIndex(ctx), 1);
  switchByOffset(ctx, 1);
  assert.deepEqual(switched, [3]);

  switchByOffset(ctx, -3);
  assert.deepEqual(switched, [3, 3]);

  ctx.localWorkspaces = listModel([]);
  switchByOffset(ctx, 1);
  assert.deepEqual(switched, [3, 3]);
}

function testWorkspaceRefreshFiltersByScreenAndOccupancy() {
  const refreshWorkspaces = qmlFunction("refreshWorkspaces");
  let focusUpdates = 0;
  const ctx = {
    followFocusedScreen: false,
    hideUnoccupied: true,
    screen: { name: "DP-1" },
    localWorkspaces: listModel(),
    workspaceRepeaterHorizontal: {},
    workspaceRepeaterVertical: {},
    updateWorkspaceFocus: () => focusUpdates++,
    CompositorService: {
      workspaces: listModel([
        { idx: 1, output: "DP-1", isOccupied: true },
        { idx: 2, output: "DP-1", isOccupied: false, isFocused: false },
        { idx: 3, output: "HDMI-A-1", isOccupied: true, isFocused: true },
      ]),
    },
  };

  refreshWorkspaces(ctx);
  assert.deepEqual(ctx.localWorkspaces.items.map(ws => ws.idx), [1]);
  assert.equal(ctx.workspaceRepeaterHorizontal.model, ctx.localWorkspaces);
  assert.equal(ctx.workspaceRepeaterVertical.model, ctx.localWorkspaces);
  assert.equal(focusUpdates, 1);

  ctx.followFocusedScreen = true;
  refreshWorkspaces(ctx);
  assert.deepEqual(ctx.localWorkspaces.items.map(ws => ws.idx), [3]);
}

const tests = [
  testWorkspaceDimensionsRespectLabelsAndActivity,
  testWorkspaceAggregateDimensionsIncludeSpacingAndPadding,
  testWorkspaceFocusedIndexAndSwitchingGuards,
  testWorkspaceRefreshFiltersByScreenAndOccupancy,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
