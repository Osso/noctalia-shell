#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testBackgroundAvoidsIdleTransitionShader() {
  const source = readQml("Modules/Background/Background.qml");

  assert.match(source, /readonly property bool shaderActive: transitioning \|\| nextWallpaper\.source !== ""/, "background shader must be active only during transition work");
  assert.match(source, /active: root\.shaderActive/, "shader loader must unload while wallpaper is idle");
  assert.match(source, /visible: !root\.shaderActive && currentWallpaper\.source !== ""/, "current wallpaper image must render directly while idle");
}

function testBackgroundSetsDecodeSizeBeforeSource() {
  const source = readQml("Modules/Background/Background.qml");
  const setImmediateBody = extractFunctionBody(source, "setWallpaperImmediate");
  const setTransitionBody = extractFunctionBody(source, "setWallpaperWithTransition");
  const prepareBody = extractFunctionBody(source, "prepareWallpaperImage");

  assert.match(source, /readonly property size targetDecodeSize: calculateTargetDecodeSize\(\)/, "background must precompute decode size from monitor dimensions");
  assert.match(source, /sourceSize: root\.targetDecodeSize/, "current wallpaper must request decode size before source assignment");
  assert.match(source, /sourceSize: root\.targetDecodeSize/, "next wallpaper must request decode size before source assignment");
  assert.match(prepareBody, /image\.sourceSize = root\.targetDecodeSize[\s\S]*image\.source = source/, "wallpaper preparation must set sourceSize before source");
  assert.match(setImmediateBody, /prepareWallpaperImage\(currentWallpaper, source\)/, "immediate wallpaper changes must use sourceSize-before-source helper");
  assert.match(setTransitionBody, /prepareWallpaperImage\(nextWallpaper, source\)/, "transition wallpaper changes must use sourceSize-before-source helper");
}

function testBackgroundHelperFunctionsExist() {
  const source = readQml("Modules/Background/Background.qml");

  assert.match(source, /function calculateTargetDecodeSize\(\)/, "background must expose target decode size helper");
  assert.match(source, /function imageFillMode\(\)/, "background must map wallpaper fill settings to Image fill modes");
  assert.match(source, /function prepareWallpaperImage\(image, source\)/, "background must centralize sourceSize-before-source assignment");
}

const tests = [
  testBackgroundAvoidsIdleTransitionShader,
  testBackgroundSetsDecodeSizeBeforeSource,
  testBackgroundHelperFunctionsExist,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
