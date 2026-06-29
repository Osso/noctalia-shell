#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Hardware/FanService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testFanHwmonDetectionGuards() {
  const checkNextBody = extractFunctionBody(source, "checkNext");

  assert.match(checkNextBody, /if \(currentIndex >= 16\)[\s\S]*Logger\.w\("FanService", "No supported fan sensor found"\)[\s\S]*return/, "checkNext must stop after configured hwmon probes");
  assert.match(checkNextBody, /fanHwmonDetector\.path = `\/sys\/class\/hwmon\/hwmon\$\{currentIndex\}\/name`[\s\S]*fanHwmonDetector\.reload\(\)/, "checkNext must probe hwmon name files");
  assert.match(source, /root\.supportedFanSensorNames\.includes\(name\)[\s\S]*fanInputChecker\.hwmonIndex = currentIndex[\s\S]*fanInputChecker\.sensorName = name[\s\S]*fanInputChecker\.path = `\/sys\/class\/hwmon\/hwmon\$\{currentIndex\}\/fan1_input`[\s\S]*fanInputChecker\.reload\(\)/, "fan hwmon loader must verify supported sensors expose fan input");
  assert.match(source, /fanHwmonDetector\.currentIndex\+\+[\s\S]*Qt\.callLater\(\(\) => fanHwmonDetector\.checkNext\(\)\)/, "fan input failure must continue scanning hwmon paths");
}

function testFanHwmonDetectionPublishesSuccessfulSensor() {
  assert.match(source, /property bool sensorDetected: fanHwmonPath !== ""/, "FanService must expose sensor detection separately from available RPM readings");
  assert.match(source, /function publishFanSensor\(hwmonIndex, sensorName\)/, "publishFanSensor must type hwmon index and sensor name inputs");
  const publishFanSensor = qmlFunction("publishFanSensor", "hwmonIndex", "sensorName");
  const logs = [];
  const ctx = {
    root: {
      fanSensorName: "",
      fanHwmonPath: "",
      isPollingActive() {
        return true;
      },
      readAllFans() {
        logs.push(["read-all"]);
      },
    },
    Logger: {
      i(...args) {
        logs.push(args);
      },
    },
  };

  publishFanSensor(ctx, 4, "thinkpad");

  assert.equal(ctx.root.fanSensorName, "thinkpad");
  assert.equal(ctx.root.fanHwmonPath, "/sys/class/hwmon/hwmon4");
  assert.deepEqual(logs, [["read-all"], ["FanService", "Found thinkpad fan sensor at /sys/class/hwmon/hwmon4"]]);
}

function testFanPollingLifecycleGuards() {
  assert.match(source, /property int pollingRefs: 0/, "FanService must track polling consumers");
  assert.match(source, /running: root\.isPollingActive\(\) && root\.fanHwmonPath !== ""/, "fan polling timer must run only while a consumer is active and a sensor exists");

  const beginPolling = qmlFunction("beginPolling");
  const endPolling = qmlFunction("endPolling");
  const isPollingActive = qmlFunction("isPollingActive");
  const calls = [];
  const ctx = {
    pollingRefs: 0,
    readAllFans() {
      calls.push("read-all");
    },
  };
  ctx.root = ctx;

  assert.equal(isPollingActive(ctx), false);
  beginPolling(ctx);
  assert.equal(ctx.pollingRefs, 1);
  assert.equal(isPollingActive(ctx), true);
  assert.deepEqual(calls, ["read-all"]);
  beginPolling(ctx);
  assert.equal(ctx.pollingRefs, 2);
  endPolling(ctx);
  assert.equal(ctx.pollingRefs, 1);
  endPolling(ctx);
  assert.equal(ctx.pollingRefs, 0);
  endPolling(ctx);
  assert.equal(ctx.pollingRefs, 0);
}

function testFanDetectedIndexCacheGuards() {
  assert.match(source, /property var detectedFanIndices: \[\]/, "FanService must cache detected fan input indices");
  assert.match(source, /function fanIndicesToRead\(\)/, "FanService must centralize fan index selection");
  assert.match(source, /function rememberDetectedFanIndices\(fans\)/, "FanService must remember discovered fan input indices");

  const fanIndicesToRead = qmlFunction("fanIndicesToRead");
  const rememberDetectedFanIndices = qmlFunction("rememberDetectedFanIndices", "fans");
  const ctx = {
    detectedFanIndices: [],
    maxFanSensors: 4,
  };
  ctx.root = ctx;

  assert.deepEqual(fanIndicesToRead(ctx), [1, 2, 3, 4]);
  rememberDetectedFanIndices(ctx, [{ index: 2 }, { index: 1 }]);
  assert.deepEqual(ctx.detectedFanIndices, [1, 2]);
  assert.deepEqual(fanIndicesToRead(ctx), [1, 2]);
}

function testFanReadPipelineGuards() {
  const readAllBody = extractFunctionBody(source, "readAllFans");
  const readNextBody = extractFunctionBody(source, "readNextFan");
  const finalizeBody = extractFunctionBody(source, "finalizeFanReading");

  assert.match(readAllBody, /if \(root\.fanHwmonPath === ""\) return/, "readAllFans must no-op before hwmon path detection");
  assert.match(readAllBody, /root\.collectedFans = \[\][\s\S]*root\.pendingFanReads = root\.fanIndicesToRead\(\)/, "readAllFans must reset collected state and queue pending fan indices");
  assert.match(readAllBody, /root\.pendingFanReads = root\.fanIndicesToRead\(\)/, "readAllFans must use cached fan sensor indices when known");
  assert.match(readAllBody, /readNextFan\(\)/, "readAllFans must start the read pipeline");
  assert.match(readNextBody, /if \(root\.pendingFanReads\.length === 0\)[\s\S]*finalizeFanReading\(\)[\s\S]*return/, "readNextFan must finalize after pending reads are exhausted");
  assert.match(readNextBody, /const fanIndex = root\.pendingFanReads\[0\][\s\S]*fanReader\.path = `\$\{root\.fanHwmonPath\}\/fan\$\{fanIndex\}_input`[\s\S]*fanReader\.reload\(\)/, "readNextFan must peek next index and load fan input path");
  assert.match(finalizeBody, /root\.collectedFans\.sort\(\(a, b\) => a\.index - b\.index\)/, "finalizeFanReading must sort fans by sensor index");
  assert.match(finalizeBody, /root\.rememberDetectedFanIndices\(root\.collectedFans\)/, "finalizeFanReading must cache detected fan input indices before publishing");
  assert.match(finalizeBody, /root\.pendingLabelReads = root\.findMissingLabelIndices\(root\.collectedFans\)[\s\S]*root\.readNextFanLabel\(\)/, "finalizeFanReading must load only missing labels before publishing fans");
  assert.match(finalizeBody, /root\.publishFinalFans\(\)/, "finalizeFanReading must publish immediately when labels are cached");
}

function testFanReaderAndLabelGuards() {
  assert.match(source, /const rpm = parseInt\(text\(\)\.trim\(\)\) \|\| 0[\s\S]*const fanIndex = root\.pendingFanReads\.shift\(\)/, "fan reader must parse rpm and consume pending index together");
  assert.match(source, /if \(rpm >= 0\)[\s\S]*root\.collectedFans\.push\(\{[\s\S]*index: fanIndex,[\s\S]*rpm: rpm,[\s\S]*label: root\.labelForFan\(fanIndex\)/, "fan reader must collect non-negative fan readings with cached labels or default labels");
  assert.match(source, /root\.pendingFanReads = \[\][\s\S]*root\.finalizeFanReading\(\)/, "fan reader failure must stop pipeline and finalize");
  assert.match(source, /property int fanIndex: 0[\s\S]*root\.cacheFanLabel\(fanIndex, label\)[\s\S]*root\.readNextFanLabel\(\)/, "label reader must cache labels by fan index and continue the label pipeline");
}

function testFanLabelCacheHelpersExecute() {
  const labelForFan = qmlFunction("labelForFan", "fanIndex");
  const findMissingLabelIndices = qmlFunction("findMissingLabelIndices", "fans");
  const cacheFanLabel = qmlFunction("cacheFanLabel", "fanIndex", "label");
  const applyCachedLabels = qmlFunction("applyCachedLabels", "fans");
  const ctx = {
    fanLabelCache: {
      1: "CPU Fan",
    },
    labelForFan(fanIndex) {
      return labelForFan(ctx, fanIndex);
    },
  };
  ctx.root = ctx;

  assert.equal(labelForFan(ctx, 1), "CPU Fan");
  assert.equal(labelForFan(ctx, 2), "Fan 2");
  assert.deepEqual(findMissingLabelIndices(ctx, [{ index: 1 }, { index: 2 }]), [2]);
  cacheFanLabel(ctx, 2, "Chassis");
  cacheFanLabel(ctx, 3, "");
  assert.deepEqual(ctx.fanLabelCache, { 1: "CPU Fan", 2: "Chassis" });
  assert.deepEqual(applyCachedLabels(ctx, [
    { index: 1, rpm: 1200, label: "Fan 1" },
    { index: 2, rpm: 900, label: "Fan 2" },
  ]), [
    { index: 1, rpm: 1200, label: "CPU Fan" },
    { index: 2, rpm: 900, label: "Chassis" },
  ]);
}

function testFanLabelPipelineSkipsCachedLabels() {
  const finalizeFanReading = qmlFunction("finalizeFanReading");
  const readNextFanLabel = qmlFunction("readNextFanLabel");
  const publishFinalFans = qmlFunction("publishFinalFans");
  const calls = [];
  const ctx = {
    collectedFans: [
      { index: 2, rpm: 900, label: "Fan 2" },
      { index: 1, rpm: 1200, label: "Fan 1" },
    ],
    pendingLabelReads: [],
    fanHwmonPath: "/sys/class/hwmon/hwmon5",
    fanLabelCache: {
      1: "CPU Fan",
      2: "Chassis",
    },
    fans: [],
    rememberDetectedFanIndices(fans) {
      ctx.detectedFanIndices = fans.map(fan => fan.index).sort((a, b) => a - b);
    },
    findMissingLabelIndices(fans) {
      return fans.filter(fan => ctx.fanLabelCache[fan.index] === undefined).map(fan => fan.index);
    },
    applyCachedLabels(fans) {
      return fans.map(fan => Object.assign({}, fan, { label: ctx.fanLabelCache[fan.index] || `Fan ${fan.index}` }));
    },
    readNextFanLabel() {
      calls.push("read-label");
      return readNextFanLabel(ctx);
    },
    publishFinalFans() {
      calls.push("publish");
      return publishFinalFans(ctx);
    },
    labelReader: {
      path: "",
      fanIndex: 0,
      reload() {
        calls.push(["reload", this.path]);
      },
    },
  };
  ctx.root = ctx;

  finalizeFanReading(ctx);
  assert.deepEqual(calls, ["publish"]);
  assert.deepEqual(ctx.fans, [
    { index: 1, rpm: 1200, label: "CPU Fan" },
    { index: 2, rpm: 900, label: "Chassis" },
  ]);

  ctx.fanLabelCache = { 1: "CPU Fan" };
  calls.length = 0;
  finalizeFanReading(ctx);
  assert.deepEqual(calls, ["read-label", ["reload", "/sys/class/hwmon/hwmon5/fan2_label"]]);
}

function testFanSummaryHelpers() {
  const averageBody = extractFunctionBody(source, "getAverageRpm");
  const maxBody = extractFunctionBody(source, "getMaxRpm");
  const formatBody = extractFunctionBody(source, "formatRpm");

  assert.match(source, /function getAverageRpm\(\)/, "getAverageRpm must declare int output");
  assert.match(source, /function getMaxRpm\(\)/, "getMaxRpm must declare int output");
  assert.match(source, /function formatRpm\(rpm\)/, "formatRpm must type rpm input and string output");
  assert.match(averageBody, /if \(fans\.length === 0\) return 0/, "getAverageRpm must return zero without fans");
  assert.match(averageBody, /fans\.forEach\(f => sum \+= f\.rpm\)[\s\S]*return Math\.round\(sum \/ fans\.length\)/, "getAverageRpm must average fan rpm values");
  assert.match(maxBody, /if \(fans\.length === 0\) return 0/, "getMaxRpm must return zero without fans");
  assert.match(maxBody, /fans\.forEach\(f => \{ if \(f\.rpm > max\) max = f\.rpm; \}\)[\s\S]*return max/, "getMaxRpm must track highest fan rpm");
  assert.match(formatBody, /if \(rpm < 1000\) return rpm \+ ""/, "formatRpm must keep sub-1000 rpm literal");
  assert.match(formatBody, /return \(rpm \/ 1000\)\.toFixed\(1\) \+ "k"/, "formatRpm must shorten thousands with one decimal");
}

const tests = [
  testFanHwmonDetectionGuards,
  testFanHwmonDetectionPublishesSuccessfulSensor,
  testFanPollingLifecycleGuards,
  testFanDetectedIndexCacheGuards,
  testFanReadPipelineGuards,
  testFanReaderAndLabelGuards,
  testFanLabelCacheHelpersExecute,
  testFanLabelPipelineSkipsCachedLabels,
  testFanSummaryHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
