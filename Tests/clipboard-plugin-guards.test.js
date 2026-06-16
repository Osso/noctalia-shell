#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testClipboardPluginCommandAndLifecycleGuards() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ClipboardPlugin.qml");
  const initBody = extractFunctionBody(source, "init");
  const handleBody = extractFunctionBody(source, "handleCommand");
  const commandsBody = extractFunctionBody(source, "commands");

  assert.match(initBody, /Logger\.i\("ClipboardPlugin", "Initialized"\)/, "init must log startup");
  assert.match(initBody, /if \(ClipboardService\.active\)[\s\S]*ClipboardService\.list\(100\)/, "init must preload clipboard data when active");
  assert.match(handleBody, /return searchText\.startsWith\(">clip"\)/, "handleCommand must claim >clip commands");
  assert.match(commandsBody, /"name": ">clip"[\s\S]*I18n\.tr\("plugins\.clipboard-search-description"\)[\s\S]*launcher\.setSearchText\(">clip "\)/, "commands must expose clipboard search command");
  assert.match(commandsBody, /"name": ">clip clear"[\s\S]*I18n\.tr\("plugins\.clipboard-clear-description"\)[\s\S]*ClipboardService\.wipeAll\(\)[\s\S]*launcher\.close\(\)/, "commands must expose clipboard clear command");
}

function testClipboardPluginResultStateGuards() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ClipboardPlugin.qml");
  const resultsBody = extractFunctionBody(source, "getResults");

  assert.match(resultsBody, /if \(!searchText\.startsWith\(">clip"\)\)[\s\S]*return \[\];/, "getResults must ignore non-clipboard commands");
  assert.match(resultsBody, /lastSearchText = searchText[\s\S]*const query = searchText\.slice\(5\)\.trim\(\)/, "getResults must remember search text and trim >clip query");
  assert.match(resultsBody, /if \(!ClipboardService\.active\)[\s\S]*I18n\.tr\("plugins\.clipboard-history-disabled"\)[\s\S]*I18n\.tr\("plugins\.clipboard-history-disabled-description"\)/, "getResults must show disabled state when service is inactive");
  assert.match(resultsBody, /if \(query === "clear"\)[\s\S]*I18n\.tr\("plugins\.clipboard-clear-history"\)[\s\S]*ClipboardService\.wipeAll\(\)[\s\S]*launcher\.close\(\)/, "getResults must handle the clear command");
  assert.match(resultsBody, /if \(ClipboardService\.loading \|\| isWaitingForData\)[\s\S]*I18n\.tr\("plugins\.clipboard-loading"\)/, "getResults must show loading state");
  assert.match(resultsBody, /const items = ClipboardService\.items \|\| \[\]/, "getResults must tolerate missing service items");
  assert.match(resultsBody, /if \(items\.count === 0 && !ClipboardService\.loading\)[\s\S]*isWaitingForData = true[\s\S]*ClipboardService\.list\(100\)/, "getResults must request data when the model is empty");
  assert.match(resultsBody, /const searchTerm = query\.toLowerCase\(\)/, "getResults must search case-insensitively");
  assert.match(resultsBody, /items\.forEach\(function \(item\)[\s\S]*const preview = \(item\.preview \|\| ""\)\.toLowerCase\(\)/, "getResults must iterate clipboard items using lower-case previews");
  assert.match(resultsBody, /if \(searchTerm && preview\.indexOf\(searchTerm\) === -1\)[\s\S]*return;/, "getResults must skip non-matching items");
  assert.match(resultsBody, /if \(item\.isImage\)[\s\S]*entry = formatImageEntry\(item\)[\s\S]*else[\s\S]*entry = formatTextEntry\(item\)/, "getResults must format image and text entries separately");
  assert.match(resultsBody, /entry\.onActivate = function \(\) \{[\s\S]*ClipboardService\.copyToClipboard\(item\.id\)[\s\S]*launcher\.close\(\)/, "getResults must copy selected items and close launcher");
  assert.match(resultsBody, /if \(results\.length === 0\)[\s\S]*searchTerm \? "No matching clipboard items" : "Clipboard is empty"/, "getResults must show empty or no-match state");
}

function testClipboardPluginFormattingGuards() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ClipboardPlugin.qml");
  const imageBody = extractFunctionBody(source, "formatImageEntry");
  const textBody = extractFunctionBody(source, "formatTextEntry");
  const metaBody = extractFunctionBody(source, "parseImageMeta");
  const getImageBody = extractFunctionBody(source, "getImageForItem");

  assert.match(imageBody, /const meta = parseImageMeta\(item\.preview\)/, "formatImageEntry must parse preview metadata");
  assert.match(imageBody, /"name": meta \? `Image \$\{meta\.w\}[\s\S]*\$\{meta\.h\}` : "Image"/, "formatImageEntry must include dimensions when metadata exists");
  assert.match(imageBody, /"description": meta \? `\$\{meta\.fmt\}[\s\S]*\$\{meta\.size\}` : item\.mime \|\| "Image data"/, "formatImageEntry must describe parsed or fallback image data");
  assert.match(imageBody, /"isImage": true[\s\S]*"imageWidth": meta \? meta\.w : 0[\s\S]*"imageHeight": meta \? meta\.h : 0/, "formatImageEntry must expose image dimensions");
  assert.match(imageBody, /"clipboardId": item\.id[\s\S]*"mime": item\.mime[\s\S]*"preview": item\.preview/, "formatImageEntry must preserve source item fields");
  assert.match(textBody, /const preview = \(item\.preview \|\| ""\)\.trim\(\)/, "formatTextEntry must trim preview text");
  assert.match(textBody, /const lines = preview\.split\('\\n'\)\.filter\(l => l\.trim\(\)\)/, "formatTextEntry must ignore blank lines");
  assert.match(textBody, /let title = lines\[0\] \|\| "Empty text"[\s\S]*title = title\.substring\(0, 57\) \+ "\.\.\."/, "formatTextEntry must default and truncate titles");
  assert.match(textBody, /if \(lines\.length > 1\)[\s\S]*description = lines\[1\][\s\S]*description = description\.substring\(0, 77\) \+ "\.\.\."/, "formatTextEntry must use and truncate second-line descriptions");
  assert.match(textBody, /const chars = preview\.length[\s\S]*const words = preview\.split\(\/\\s\+\/\)\.length[\s\S]*word\$\{words !== 1 \? 's' : ''\}/, "formatTextEntry must describe single-line text by size");
  assert.match(textBody, /"icon": "text-x-generic"[\s\S]*"isImage": false[\s\S]*"clipboardId": item\.id[\s\S]*"preview": preview/, "formatTextEntry must expose text entry fields");
  assert.match(metaBody, /const re = \/\\\[\\\[\\s\*binary data/, "parseImageMeta must recognize cliphist binary metadata");
  assert.match(metaBody, /\(\[\\d\\\.\]\+\\s\*\(\?:KiB\|MiB\|GiB\|B\)\)[\s\S]*\(\\w\+\)[\s\S]*\(\\d\+\)x\(\\d\+\)/, "parseImageMeta must capture size, format, width, and height");
  assert.match(metaBody, /if \(!match\)[\s\S]*return null;/, "parseImageMeta must return null for non-image previews");
  assert.match(metaBody, /"size": match\[1\][\s\S]*"fmt": \(match\[2\] \|\| ""\)\.toUpperCase\(\)[\s\S]*"w": Number\(match\[3\]\)[\s\S]*"h": Number\(match\[4\]\)/, "parseImageMeta must normalize parsed metadata");
  assert.match(getImageBody, /return ClipboardService\.getImageData \? ClipboardService\.getImageData\(clipboardId\) : null/, "getImageForItem must call optional image data provider safely");
}

const tests = [
  testClipboardPluginCommandAndLifecycleGuards,
  testClipboardPluginResultStateGuards,
  testClipboardPluginFormattingGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
