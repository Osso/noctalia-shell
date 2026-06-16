#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Cards/TimerCard.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testTimerCardFunctionSignaturesAreTyped() {
  assert.match(source, /function formatTime\(seconds: int, hideHoursWhenZero: bool\): string/, "formatTime must type duration input and string output");
  assert.match(source, /function formatTimeFromDigits\(digits: string\): string/, "formatTimeFromDigits must type digit input and string output");
  assert.match(source, /function parseDigitsToTime\(digits: string\)/, "parseDigitsToTime must type digit input");
  assert.match(source, /function applyTimeFromBuffer\(\)/, "applyTimeFromBuffer must remain an explicit callable");
  assert.match(source, /function startTimer\(\)/, "startTimer must remain an explicit callable");
  assert.match(source, /function pauseTimer\(\)/, "pauseTimer must remain an explicit callable");
  assert.match(source, /function resetTimer\(\)/, "resetTimer must remain an explicit callable");
}

function testTimerCardFormattingDelegates() {
  const formatTimeBody = extractFunctionBody(source, "formatTime");
  const formatDigitsBody = extractFunctionBody(source, "formatTimeFromDigits");
  const parseDigitsBody = extractFunctionBody(source, "parseDigitsToTime");

  assert.match(formatTimeBody, /return TimerDigits\.formatDuration\(seconds, hideHoursWhenZero\)/, "formatTime must delegate to TimerDigits.formatDuration");
  assert.match(formatDigitsBody, /return TimerDigits\.formatFromDigits\(digits\)/, "formatTimeFromDigits must delegate to TimerDigits.formatFromDigits");
  assert.match(parseDigitsBody, /Time\.timerRemainingSeconds = TimerDigits\.totalSecondsFromDigits\(digits\)/, "parseDigitsToTime must update persistent timer remaining seconds");
}

function testTimerCardTimerControlDelegates() {
  const applyBufferBody = extractFunctionBody(source, "applyTimeFromBuffer");
  const startBody = extractFunctionBody(source, "startTimer");
  const pauseBody = extractFunctionBody(source, "pauseTimer");
  const resetBody = extractFunctionBody(source, "resetTimer");

  assert.match(applyBufferBody, /if \(timerDisplayItem\.inputBuffer !== ""\)[\s\S]*parseDigitsToTime\(timerDisplayItem\.inputBuffer\)[\s\S]*timerDisplayItem\.inputBuffer = ""/, "applyTimeFromBuffer must consume and clear non-empty input");
  assert.match(startBody, /Time\.timerStart\(\)/, "startTimer must delegate to Time.timerStart");
  assert.match(pauseBody, /Time\.timerPause\(\)/, "pauseTimer must delegate to Time.timerPause");
  assert.match(resetBody, /Time\.timerReset\(\)/, "resetTimer must delegate to Time.timerReset");
}

function testTimerCardAppliesBufferedDigitsToTime() {
  const parseDigitsToTime = qmlFunction("parseDigitsToTime", "digits");
  const applyTimeFromBuffer = qmlFunction("applyTimeFromBuffer");
  const calls = [];
  const ctx = {
    Time: { timerRemainingSeconds: 0 },
    TimerDigits: {
      totalSecondsFromDigits(digits) {
        calls.push(digits);
        return digits === "1234" ? 754 : 0;
      },
    },
    timerDisplayItem: { inputBuffer: "1234" },
  };
  ctx.parseDigitsToTime = digits => parseDigitsToTime(ctx, digits);

  applyTimeFromBuffer(ctx);

  assert.deepEqual(calls, ["1234"], "applyTimeFromBuffer must parse the buffered digits exactly once");
  assert.equal(ctx.Time.timerRemainingSeconds, 754, "applyTimeFromBuffer must persist parsed seconds");
  assert.equal(ctx.timerDisplayItem.inputBuffer, "", "applyTimeFromBuffer must clear consumed input");
}

function testTimerCardEmptyBufferDoesNotChangeTime() {
  const parseDigitsToTime = qmlFunction("parseDigitsToTime", "digits");
  const applyTimeFromBuffer = qmlFunction("applyTimeFromBuffer");
  const calls = [];
  const ctx = {
    Time: { timerRemainingSeconds: 45 },
    TimerDigits: {
      totalSecondsFromDigits(digits) {
        calls.push(digits);
        return 0;
      },
    },
    timerDisplayItem: { inputBuffer: "" },
  };
  ctx.parseDigitsToTime = digits => parseDigitsToTime(ctx, digits);

  applyTimeFromBuffer(ctx);

  assert.deepEqual(calls, [], "empty input must not be parsed");
  assert.equal(ctx.Time.timerRemainingSeconds, 45, "empty input must leave existing time untouched");
  assert.equal(ctx.timerDisplayItem.inputBuffer, "", "empty input must stay empty");
}

const tests = [
  testTimerCardFunctionSignaturesAreTyped,
  testTimerCardFormattingDelegates,
  testTimerCardTimerControlDelegates,
  testTimerCardAppliesBufferedDigitsToTime,
  testTimerCardEmptyBufferDoesNotChangeTime,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
