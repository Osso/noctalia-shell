#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testFanHwmonDetectionGuards() {
  const source = readQml("Services/Hardware/FanService.qml");
  const checkNextBody = extractFunctionBody(source, "checkNext");

  assert.match(checkNextBody, /if \(currentIndex >= 16\)[\s\S]*Logger\.w\("FanService", "No supported fan sensor found"\)[\s\S]*return/, "checkNext must stop after configured hwmon probes");
  assert.match(checkNextBody, /fanHwmonDetector\.path = `\/sys\/class\/hwmon\/hwmon\$\{currentIndex\}\/name`[\s\S]*fanHwmonDetector\.reload\(\)/, "checkNext must probe hwmon name files");
  assert.match(source, /root\.supportedFanSensorNames\.includes\(name\)[\s\S]*fanInputChecker\.hwmonIndex = currentIndex[\s\S]*fanInputChecker\.sensorName = name[\s\S]*fanInputChecker\.path = `\/sys\/class\/hwmon\/hwmon\$\{currentIndex\}\/fan1_input`[\s\S]*fanInputChecker\.reload\(\)/, "fan hwmon loader must verify supported sensors expose fan input");
  assert.match(source, /fanHwmonDetector\.currentIndex\+\+[\s\S]*Qt\.callLater\(\(\) => fanHwmonDetector\.checkNext\(\)\)/, "fan input failure must continue scanning hwmon paths");
}

function testFanReadPipelineGuards() {
  const source = readQml("Services/Hardware/FanService.qml");
  const readAllBody = extractFunctionBody(source, "readAllFans");
  const readNextBody = extractFunctionBody(source, "readNextFan");
  const finalizeBody = extractFunctionBody(source, "finalizeFanReading");

  assert.match(readAllBody, /if \(root\.fanHwmonPath === ""\) return/, "readAllFans must no-op before hwmon path detection");
  assert.match(readAllBody, /root\.collectedFans = \[\][\s\S]*root\.pendingFanReads = \[\]/, "readAllFans must reset pending and collected fan state");
  assert.match(readAllBody, /for \(let i = 1; i <= root\.maxFanSensors; i\+\+\)[\s\S]*root\.pendingFanReads\.push\(i\)/, "readAllFans must queue configured fan sensor indices");
  assert.match(readAllBody, /readNextFan\(\)/, "readAllFans must start the read pipeline");
  assert.match(readNextBody, /if \(root\.pendingFanReads\.length === 0\)[\s\S]*finalizeFanReading\(\)[\s\S]*return/, "readNextFan must finalize after pending reads are exhausted");
  assert.match(readNextBody, /const fanIndex = root\.pendingFanReads\[0\][\s\S]*fanReader\.path = `\$\{root\.fanHwmonPath\}\/fan\$\{fanIndex\}_input`[\s\S]*fanReader\.reload\(\)/, "readNextFan must peek next index and load fan input path");
  assert.match(finalizeBody, /root\.collectedFans\.sort\(\(a, b\) => a\.index - b\.index\)/, "finalizeFanReading must sort fans by sensor index");
  assert.match(finalizeBody, /root\.collectedFans\.forEach\(\(fan, idx\) => \{[\s\S]*labelReader\.path = labelPath[\s\S]*labelReader\.reload\(\)/, "finalizeFanReading must try to load labels for collected fans");
  assert.match(finalizeBody, /root\.fans = root\.collectedFans/, "finalizeFanReading must publish collected fans");
}

function testFanReaderAndLabelGuards() {
  const source = readQml("Services/Hardware/FanService.qml");

  assert.match(source, /const rpm = parseInt\(text\(\)\.trim\(\)\) \|\| 0[\s\S]*const fanIndex = root\.pendingFanReads\.shift\(\)/, "fan reader must parse rpm and consume pending index together");
  assert.match(source, /if \(rpm >= 0\)[\s\S]*root\.collectedFans\.push\(\{[\s\S]*index: fanIndex,[\s\S]*rpm: rpm,[\s\S]*label: `Fan \$\{fanIndex\}`/, "fan reader must collect non-negative fan readings with default labels");
  assert.match(source, /root\.pendingFanReads = \[\][\s\S]*root\.finalizeFanReading\(\)/, "fan reader failure must stop pipeline and finalize");
  assert.match(source, /const label = text\(\)\.trim\(\)[\s\S]*if \(label && root\.collectedFans\.length > 0\)[\s\S]*lastFan\.label = label/, "label reader must update the most recent collected fan when a label exists");
}

function testFanSummaryHelpers() {
  const source = readQml("Services/Hardware/FanService.qml");
  const averageBody = extractFunctionBody(source, "getAverageRpm");
  const maxBody = extractFunctionBody(source, "getMaxRpm");
  const formatBody = extractFunctionBody(source, "formatRpm");

  assert.match(source, /function getAverageRpm\(\): int/, "getAverageRpm must declare int output");
  assert.match(source, /function getMaxRpm\(\): int/, "getMaxRpm must declare int output");
  assert.match(source, /function formatRpm\(rpm: int\): string/, "formatRpm must type rpm input and string output");
  assert.match(averageBody, /if \(fans\.length === 0\) return 0/, "getAverageRpm must return zero without fans");
  assert.match(averageBody, /fans\.forEach\(f => sum \+= f\.rpm\)[\s\S]*return Math\.round\(sum \/ fans\.length\)/, "getAverageRpm must average fan rpm values");
  assert.match(maxBody, /if \(fans\.length === 0\) return 0/, "getMaxRpm must return zero without fans");
  assert.match(maxBody, /fans\.forEach\(f => \{ if \(f\.rpm > max\) max = f\.rpm; \}\)[\s\S]*return max/, "getMaxRpm must track highest fan rpm");
  assert.match(formatBody, /if \(rpm < 1000\) return rpm \+ ""/, "formatRpm must keep sub-1000 rpm literal");
  assert.match(formatBody, /return \(rpm \/ 1000\)\.toFixed\(1\) \+ "k"/, "formatRpm must shorten thousands with one decimal");
}

const tests = [
  testFanHwmonDetectionGuards,
  testFanReadPipelineGuards,
  testFanReaderAndLabelGuards,
  testFanSummaryHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
