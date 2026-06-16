#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testLoggerFormattingAndStackGuards() {
  const source = readQml("Commons/Logger.qml");
  const formatBody = extractFunctionBody(source, "_formatMessage");
  const stackBody = extractFunctionBody(source, "_getStackTrace");

  assert.match(formatBody, /var t = Time\.getFormattedTimestamp\(\)/, "_formatMessage must timestamp log messages");
  assert.match(formatBody, /if \(args\.length > 1\)/, "_formatMessage must treat first argument as module when present");
  assert.match(formatBody, /const maxLength = 14[\s\S]*args\.shift\(\)\.substring\(0, maxLength\)\.padStart\(maxLength, " "\)/, "_formatMessage must clamp and pad module labels");
  assert.match(formatBody, /\\x1b\[36m\[\$\{t\}\]\\x1b\[0m[\s\S]*\\x1b\[35m\$\{module\}\\x1b\[0m/, "_formatMessage must color timestamp and module labels");
  assert.match(formatBody, /args\.join\(" "\)/, "_formatMessage must join message arguments");
  assert.match(formatBody, /else \{[\s\S]*return `\[\\x1b\[36m\[\$\{t\}\]\\x1b\[0m ` \+ args\.join\(" "\)/, "_formatMessage must format module-less messages");
  assert.match(stackBody, /try \{[\s\S]*throw new Error\("Stack trace"\)[\s\S]*\} catch \(e\) \{[\s\S]*return e\.stack/, "_getStackTrace must capture JavaScript stack text");
}

function testLoggerLevelGuards() {
  const source = readQml("Commons/Logger.qml");
  const debugBody = extractFunctionBody(source, "d");
  const infoBody = extractFunctionBody(source, "i");
  const warnBody = extractFunctionBody(source, "w");
  const errorBody = extractFunctionBody(source, "e");

  assert.match(debugBody, /if \(Settings && Settings\.isDebug\)[\s\S]*var msg = _formatMessage\(\.\.\.args\)[\s\S]*console\.debug\(msg\)/, "d must log only when debug mode is enabled");
  assert.match(infoBody, /var msg = _formatMessage\(\.\.\.args\)[\s\S]*console\.info\(msg\)/, "i must format and write info logs");
  assert.match(warnBody, /var msg = _formatMessage\(\.\.\.args\)[\s\S]*console\.warn\(msg\)/, "w must format and write warning logs");
  assert.match(errorBody, /var msg = _formatMessage\(\.\.\.args\)[\s\S]*console\.error\(msg\)/, "e must format and write error logs");
}

function testLoggerCallStackGuards() {
  const source = readQml("Commons/Logger.qml");
  const callStackBody = extractFunctionBody(source, "callStack");

  assert.match(callStackBody, /var stack = _getStackTrace\(\)/, "callStack must capture a stack trace");
  assert.match(callStackBody, /Logger\.i\("Debug", "--------------------------"\)[\s\S]*Logger\.i\("Debug", "Current call stack"\)/, "callStack must print a visible header");
  assert.match(callStackBody, /var stackLines = stack\.split\('\\n'\)/, "callStack must split stack text into lines");
  assert.match(callStackBody, /for \(var i = 0; i < stackLines\.length; i\+\+\)/, "callStack must iterate every stack line");
  assert.match(callStackBody, /var line = stackLines\[i\]\.trim\(\)/, "callStack must trim stack lines");
  assert.match(callStackBody, /if \(line\.length > 0\)[\s\S]*Logger\.i\("Debug", `- \$\{line\}`\)/, "callStack must log only non-empty lines");
  assert.match(callStackBody, /Logger\.i\("Debug", "--------------------------"\);?\s*\}/, "callStack must print a closing separator");
}

const tests = [
  testLoggerFormattingAndStackGuards,
  testLoggerLevelGuards,
  testLoggerCallStackGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
