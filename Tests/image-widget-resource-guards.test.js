#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const roundedSource = readQml("Widgets/NImageRounded.qml");
const cachedSource = readQml("Widgets/NImageCached.qml");

function qmlFunction(source, functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testRoundedImageResourceGuards() {
  const shouldLoadBody = extractFunctionBody(roundedSource, "shouldLoadImage");
  const decodeBody = extractFunctionBody(roundedSource, "targetDecodeSize");

  assert.match(shouldLoadBody, /if \(!visible \|\| showFallback\)[\s\S]*return false;[\s\S]*return imagePath !== "" && width > 0 && height > 0/, "NImageRounded must load image resources only while visible with size and source");
  assert.match(decodeBody, /Math\.ceil\(width \* scale\)[\s\S]*Math\.ceil\(height \* scale\)/, "NImageRounded must derive decode size from rendered size");
  assert.match(roundedSource, /source: root\.shouldLoadImage\(\) \? root\.imagePath : ""/, "NImageRounded must clear Image source when hidden or fallback-only");
  assert.match(roundedSource, /mipmap: false/, "NImageRounded must avoid mipmap allocation for small rounded images");
  assert.match(roundedSource, /Loader \{[\s\S]*active: root\.shouldLoadImage\(\)[\s\S]*sourceComponent: roundedShaderComponent/, "NImageRounded must instantiate rounded shader only while image resources are needed");
}

function testCachedImageResourceGuards() {
  const shouldLoadBody = extractFunctionBody(cachedSource, "shouldLoadImage");
  const cacheBody = extractFunctionBody(cachedSource, "shouldCacheCurrentImage");

  assert.match(shouldLoadBody, /if \(!visible\)[\s\S]*return false;[\s\S]*return imagePath !== "" && width > 0 && height > 0/, "NImageCached must load images only while visible with size and source");
  assert.match(cacheBody, /if \(!visible \|\| !Window\.window \|\| !Window\.window\.visible\)[\s\S]*return false;[\s\S]*const originalIsReady = source === imagePath && status === Image\.Ready[\s\S]*const cacheTargetExists = imageHash !== "" && cachePath !== ""[\s\S]*return originalIsReady && cacheTargetExists/, "NImageCached must cache only visible ready originals in a visible window");
  assert.match(cachedSource, /function refreshImageSource\(\)/, "NImageCached must centralize source transitions");
  assert.match(cachedSource, /source = ""/, "NImageCached must clear source when not loadable");
  assert.match(cachedSource, /sourceSize\.width: root\.shouldLoadImage\(\) \? maxCacheDimension : 0/, "NImageCached must avoid hidden thumbnail decode targets");
  assert.match(cachedSource, /if \(shouldCacheCurrentImage\(\)\) \{[\s\S]*grabToImage/, "NImageCached must guard grabToImage behind cache eligibility");
}

function testRoundedImageGuardExecution() {
  const shouldLoadImage = qmlFunction(roundedSource, "shouldLoadImage");
  const targetDecodeSize = qmlFunction(roundedSource, "targetDecodeSize");
  const ctx = {
    visible: true,
    showFallback: false,
    imagePath: "file:///tmp/avatar.png",
    width: 32,
    height: 24,
    Screen: { devicePixelRatio: 2 },
  };

  assert.equal(shouldLoadImage(ctx), true);
  ctx.visible = false;
  assert.equal(shouldLoadImage(ctx), false);
  ctx.visible = true;
  ctx.showFallback = true;
  assert.equal(shouldLoadImage(ctx), false);
  ctx.showFallback = false;
  assert.deepEqual(targetDecodeSize(ctx), { width: 64, height: 48 });
}

function testCachedImageGuardExecution() {
  const shouldLoadImage = qmlFunction(cachedSource, "shouldLoadImage");
  const shouldCacheCurrentImage = qmlFunction(cachedSource, "shouldCacheCurrentImage");
  const ctx = {
    visible: true,
    imagePath: "file:///tmp/wall.png",
    width: 120,
    height: 90,
    source: "file:///tmp/wall.png",
    status: 1,
    Image: { Ready: 1 },
    imageHash: "abc123",
    cachePath: "/tmp/cache.png",
    Window: { window: { visible: true } },
  };

  assert.equal(shouldLoadImage(ctx), true);
  assert.equal(shouldCacheCurrentImage(ctx), true);
  ctx.visible = false;
  assert.equal(shouldLoadImage(ctx), false);
  assert.equal(shouldCacheCurrentImage(ctx), false);
}

const tests = [
  testRoundedImageResourceGuards,
  testCachedImageResourceGuards,
  testRoundedImageGuardExecution,
  testCachedImageGuardExecution,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
