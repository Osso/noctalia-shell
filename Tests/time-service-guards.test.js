#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testTimeFormattingSignaturesAreTyped() {
  const source = readQml("Commons/Time.qml");

  assert.match(source, /function getFormattedTimestamp\(date: date\): string/, "getFormattedTimestamp must type date input and string output");
  assert.match(source, /function formatVagueHumanReadableDuration\(totalSeconds: real\): string/, "formatVagueHumanReadableDuration must type seconds input and string output");
  assert.match(source, /function formatRelativeTime\(date: date\): string/, "formatRelativeTime must type date input and string output");
}

function testRelativeTimeFormattingOutputsTranslatedBuckets() {
  const source = readQml("Commons/Time.qml");
  const relativeTimeBody = extractFunctionBody(source, "formatRelativeTime");
  const formatRelativeTime = new Function("ctx", "date", `with (ctx) { return (function(date) ${relativeTimeBody}).call(ctx, date); }`);
  const baseNow = Date.UTC(2026, 0, 1, 12, 0, 0);
  const ctx = {
    Date: {
      now: () => baseNow,
    },
    I18n: {
      tr(key, args = {}) {
        return args.diff === undefined ? key : `${key}:${args.diff}`;
      },
    },
  };
  const secondsAgo = seconds => new global.Date(baseNow - seconds * 1000);

  assert.equal(formatRelativeTime(ctx, null), "");
  assert.equal(formatRelativeTime(ctx, secondsAgo(30)), "notifications.time.now");
  assert.equal(formatRelativeTime(ctx, secondsAgo(90)), "notifications.time.diffM");
  assert.equal(formatRelativeTime(ctx, secondsAgo(5 * 60)), "notifications.time.diffMM:5");
  assert.equal(formatRelativeTime(ctx, secondsAgo(90 * 60)), "notifications.time.diffH");
  assert.equal(formatRelativeTime(ctx, secondsAgo(5 * 3600)), "notifications.time.diffHH:5");
  assert.equal(formatRelativeTime(ctx, secondsAgo(25 * 3600)), "notifications.time.diffD");
  assert.equal(formatRelativeTime(ctx, secondsAgo(3 * 86400)), "notifications.time.diffDD:3");
}

function testTimestampAndDurationFormattingOutputsConcreteValues() {
  const source = readQml("Commons/Time.qml");
  const timestampBody = extractFunctionBody(source, "getFormattedTimestamp");
  const vagueBody = extractFunctionBody(source, "formatVagueHumanReadableDuration");
  const getFormattedTimestamp = new Function("ctx", "date", `with (ctx) { return (function(date) ${timestampBody}).call(ctx, date); }`);
  const formatVagueHumanReadableDuration = new Function("ctx", "totalSeconds", `with (ctx) { return (function(totalSeconds) ${vagueBody}).call(ctx, totalSeconds); }`);
  const ctx = {};

  assert.equal(getFormattedTimestamp(ctx, new Date(2026, 0, 2, 3, 4, 5)), "20260102-030405");
  assert.equal(formatVagueHumanReadableDuration(ctx, "bad"), "0s");
  assert.equal(formatVagueHumanReadableDuration(ctx, -1), "0s");
  assert.equal(formatVagueHumanReadableDuration(ctx, 0), "0s");
  assert.equal(formatVagueHumanReadableDuration(ctx, 1.9), "1s");
  assert.equal(formatVagueHumanReadableDuration(ctx, 59), "59s");
  assert.equal(formatVagueHumanReadableDuration(ctx, 65), "1m");
  assert.equal(formatVagueHumanReadableDuration(ctx, 3661), "1h 1m");
  assert.equal(formatVagueHumanReadableDuration(ctx, 90061), "1d 1h 1m");
}

function testTimestampFormattingGuards() {
  const source = readQml("Commons/Time.qml");
  const timestampBody = extractFunctionBody(source, "getFormattedTimestamp");
  const vagueBody = extractFunctionBody(source, "formatVagueHumanReadableDuration");

  assert.match(timestampBody, /if \(!date\)[\s\S]*date = new Date\(\)/, "getFormattedTimestamp must default missing date to now");
  assert.match(timestampBody, /String\(date\.getMonth\(\) \+ 1\)\.padStart\(2, '0'\)/, "getFormattedTimestamp must pad one-based month");
  assert.match(timestampBody, /return `\$\{year\}\$\{month\}\$\{day\}-\$\{hours\}\$\{minutes\}\$\{seconds\}`/, "getFormattedTimestamp must use compact timestamp format");
  assert.match(vagueBody, /typeof totalSeconds !== 'number' \|\| totalSeconds < 0[\s\S]*return '0s'/, "formatVagueHumanReadableDuration must fail closed for invalid durations");
  assert.match(vagueBody, /totalSeconds = Math\.floor\(totalSeconds\)/, "formatVagueHumanReadableDuration must floor decimal seconds");
  assert.match(vagueBody, /const days = Math\.floor\(totalSeconds \/ 86400\)[\s\S]*const seconds = totalSeconds % 60/, "formatVagueHumanReadableDuration must split days hours minutes seconds");
  assert.match(vagueBody, /if \(!hours && !minutes\)[\s\S]*parts\.push\(`\$\{seconds\}s`\)/, "formatVagueHumanReadableDuration must show seconds only for short durations");
  assert.match(vagueBody, /return parts\.join\(' '\)/, "formatVagueHumanReadableDuration must join readable duration parts");
}

function testTimerStartGuards() {
  const source = readQml("Commons/Time.qml");
  const body = extractFunctionBody(source, "timerStart");

  assert.match(body, /if \(root\.timerStopwatchMode\)[\s\S]*root\.timerRunning = true[\s\S]*root\.timerStartTimestamp = root\.timestamp[\s\S]*root\.timerPausedAt = root\.timerElapsedSeconds/, "timerStart must resume stopwatch from elapsed seconds");
  assert.match(body, /if \(root\.timerRemainingSeconds <= 0\)[\s\S]*return/, "timerStart must ignore empty countdowns");
  assert.match(body, /root\.timerTotalSeconds = root\.timerRemainingSeconds[\s\S]*root\.timerPausedAt = 0/, "timerStart must snapshot countdown total and reset pause state");
}

function testTimerPauseResetAndFinishedGuards() {
  const source = readQml("Commons/Time.qml");
  const pauseBody = extractFunctionBody(source, "timerPause");
  const resetBody = extractFunctionBody(source, "timerReset");
  const finishedBody = extractFunctionBody(source, "timerOnFinished");

  assert.match(pauseBody, /if \(root\.timerRunning\)[\s\S]*if \(root\.timerStopwatchMode\)[\s\S]*root\.timerPausedAt = root\.timerElapsedSeconds[\s\S]*root\.timerPausedAt = root\.timerRemainingSeconds/, "timerPause must preserve stopwatch or countdown pause state");
  assert.match(pauseBody, /root\.timerRunning = false[\s\S]*root\.timerStartTimestamp = 0[\s\S]*SoundService\.stopSound\("alarm-beep\.wav"\)[\s\S]*root\.timerSoundPlaying = false/, "timerPause must stop timer state and alarm sound");
  assert.match(resetBody, /root\.timerRunning = false[\s\S]*root\.timerStartTimestamp = 0/, "timerReset must stop timer and clear start timestamp");
  assert.match(resetBody, /if \(root\.timerStopwatchMode\)[\s\S]*root\.timerElapsedSeconds = 0[\s\S]*root\.timerPausedAt = 0[\s\S]*root\.timerRemainingSeconds = 0[\s\S]*root\.timerTotalSeconds = 0/, "timerReset must clear stopwatch and countdown state");
  assert.match(resetBody, /SoundService\.stopSound\("alarm-beep\.wav"\)[\s\S]*root\.timerSoundPlaying = false/, "timerReset must stop alarm sound");
  assert.match(finishedBody, /root\.timerRunning = false[\s\S]*root\.timerRemainingSeconds = 0[\s\S]*root\.timerSoundPlaying = true/, "timerOnFinished must stop countdown and mark alarm playing");
  assert.match(finishedBody, /SoundService\.playSound\("alarm-beep\.wav", \{[\s\S]*repeat: true[\s\S]*volume: 0\.3/, "timerOnFinished must play repeating low-volume alarm");
}

function testTimerSoundServiceCallsExecuteAgainstFakeService() {
  const source = readQml("Commons/Time.qml");
  const timerPause = new Function("ctx", `with (ctx) { return (function() ${extractFunctionBody(source, "timerPause")}).call(ctx); }`);
  const timerReset = new Function("ctx", `with (ctx) { return (function() ${extractFunctionBody(source, "timerReset")}).call(ctx); }`);
  const timerOnFinished = new Function("ctx", `with (ctx) { return (function() ${extractFunctionBody(source, "timerOnFinished")}).call(ctx); }`);
  const soundCalls = [];
  const ctx = {
    root: null,
    timerRunning: true,
    timerStopwatchMode: false,
    timerRemainingSeconds: 42,
    timerTotalSeconds: 120,
    timerElapsedSeconds: 9,
    timerStartTimestamp: 1000,
    timerPausedAt: 0,
    timerSoundPlaying: true,
    SoundService: {
      stopSound(name) {
        soundCalls.push(["stop", name]);
      },
      playSound(name, options) {
        soundCalls.push(["play", name, options]);
      },
    },
  };
  ctx.root = ctx;

  timerPause(ctx);
  assert.equal(ctx.timerRunning, false);
  assert.equal(ctx.timerStartTimestamp, 0);
  assert.equal(ctx.timerPausedAt, 42);
  assert.equal(ctx.timerSoundPlaying, false);
  assert.deepEqual(soundCalls, [["stop", "alarm-beep.wav"]]);

  ctx.timerStopwatchMode = true;
  ctx.timerElapsedSeconds = 17;
  ctx.timerPausedAt = 99;
  ctx.timerSoundPlaying = true;
  timerReset(ctx);
  assert.equal(ctx.timerElapsedSeconds, 0);
  assert.equal(ctx.timerPausedAt, 0);
  assert.equal(ctx.timerSoundPlaying, false);
  assert.deepEqual(soundCalls, [
    ["stop", "alarm-beep.wav"],
    ["stop", "alarm-beep.wav"],
  ]);

  ctx.timerRunning = true;
  ctx.timerRemainingSeconds = 4;
  timerOnFinished(ctx);
  assert.equal(ctx.timerRunning, false);
  assert.equal(ctx.timerRemainingSeconds, 0);
  assert.equal(ctx.timerSoundPlaying, true);
  assert.deepEqual(soundCalls[2], ["play", "alarm-beep.wav", {
    repeat: true,
    volume: 0.3,
  }]);
}

const tests = [
  testTimeFormattingSignaturesAreTyped,
  testRelativeTimeFormattingOutputsTranslatedBuckets,
  testTimestampAndDurationFormattingOutputsConcreteValues,
  testTimestampFormattingGuards,
  testTimerStartGuards,
  testTimerPauseResetAndFinishedGuards,
  testTimerSoundServiceCallsExecuteAgainstFakeService,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
