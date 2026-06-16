#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testTimerCardFunctionSignaturesAreTyped() {
  const source = readQml("Modules/Cards/TimerCard.qml");

  assert.match(source, /function formatTime\(seconds: int, hideHoursWhenZero: bool\): string/, "formatTime must type duration input and string output");
  assert.match(source, /function formatTimeFromDigits\(digits: string\): string/, "formatTimeFromDigits must type digit input and string output");
  assert.match(source, /function parseDigitsToTime\(digits: string\)/, "parseDigitsToTime must type digit input");
  assert.match(source, /function applyTimeFromBuffer\(\)/, "applyTimeFromBuffer must remain an explicit callable");
  assert.match(source, /function startTimer\(\)/, "startTimer must remain an explicit callable");
  assert.match(source, /function pauseTimer\(\)/, "pauseTimer must remain an explicit callable");
  assert.match(source, /function resetTimer\(\)/, "resetTimer must remain an explicit callable");
}

function testTimerCardFormattingDelegates() {
  const source = readQml("Modules/Cards/TimerCard.qml");
  const formatTimeBody = extractFunctionBody(source, "formatTime");
  const formatDigitsBody = extractFunctionBody(source, "formatTimeFromDigits");
  const parseDigitsBody = extractFunctionBody(source, "parseDigitsToTime");

  assert.match(formatTimeBody, /return TimerDigits\.formatDuration\(seconds, hideHoursWhenZero\)/, "formatTime must delegate to TimerDigits.formatDuration");
  assert.match(formatDigitsBody, /return TimerDigits\.formatFromDigits\(digits\)/, "formatTimeFromDigits must delegate to TimerDigits.formatFromDigits");
  assert.match(parseDigitsBody, /Time\.timerRemainingSeconds = TimerDigits\.totalSecondsFromDigits\(digits\)/, "parseDigitsToTime must update persistent timer remaining seconds");
}

function testTimerCardTimerControlDelegates() {
  const source = readQml("Modules/Cards/TimerCard.qml");
  const applyBufferBody = extractFunctionBody(source, "applyTimeFromBuffer");
  const startBody = extractFunctionBody(source, "startTimer");
  const pauseBody = extractFunctionBody(source, "pauseTimer");
  const resetBody = extractFunctionBody(source, "resetTimer");

  assert.match(applyBufferBody, /if \(timerDisplayItem\.inputBuffer !== ""\)[\s\S]*parseDigitsToTime\(timerDisplayItem\.inputBuffer\)[\s\S]*timerDisplayItem\.inputBuffer = ""/, "applyTimeFromBuffer must consume and clear non-empty input");
  assert.match(startBody, /Time\.timerStart\(\)/, "startTimer must delegate to Time.timerStart");
  assert.match(pauseBody, /Time\.timerPause\(\)/, "pauseTimer must delegate to Time.timerPause");
  assert.match(resetBody, /Time\.timerReset\(\)/, "resetTimer must delegate to Time.timerReset");
}

const tests = [
  testTimerCardFunctionSignaturesAreTyped,
  testTimerCardFormattingDelegates,
  testTimerCardTimerControlDelegates,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
