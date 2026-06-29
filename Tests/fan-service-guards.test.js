#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Hardware/FanService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testFanHwmonDetectionGuards() {
  const buildFanDetectionScript = qmlFunction("buildFanDetectionScript");
  const parseFanDetectionOutput = qmlFunction("parseFanDetectionOutput", "output");
  const parseFanDetectionHeader = qmlFunction("parseFanDetectionHeader", "line");
  const parseDetectedFanLines = qmlFunction("parseDetectedFanLines", "lines");
  const ctx = {
    supportedFanSensorNames: ["thinkpad", "dell_smm"],
    parseFanDetectionHeader(line) {
      return parseFanDetectionHeader(ctx, line);
    },
    parseDetectedFanLines(lines) {
      return parseDetectedFanLines(ctx, lines);
    },
  };
  ctx.root = ctx;

  const script = buildFanDetectionScript(ctx);
  assert.match(script, /for name_path in \/sys\/class\/hwmon\/hwmon\*\/name/, "fan detection must scan hwmon name files in one process");
  assert.match(script, /fan1_input/, "fan detection must verify that the matched hwmon exposes fan input");
  assert.match(script, /fan\*_input/, "fan detection must enumerate available fan inputs once");
  assert.match(script, /fan\$\{idx\}_label/, "fan detection must cache fan labels or missing-label state once");
  assert.match(script, /thinkpad dell_smm/, "fan detection must include supported sensor names");
  assert.doesNotMatch(source, /id: fanHwmonDetector|id: fanInputChecker/, "fan startup detection must not use path-churning FileViews");
  assert.match(source, /fanDetectorProcess\.running = true/, "FanService startup must run the single detector process");
  assert.match(source, /root\.publishFanSensor\(detected\.hwmonIndex, detected\.sensorName, detected\.fanIndices, detected\.fanLabels\)/, "detector process must publish parsed sensors");

  assert.deepEqual(parseFanDetectionOutput(ctx, "hwmon\t5\tthinkpad\nfan\t1\tCPU Fan\nfan\t2\t\n"), {
    hwmonIndex: 5,
    sensorName: "thinkpad",
    fanIndices: [1, 2],
    fanLabels: { 1: "CPU Fan", 2: null },
  });
  assert.equal(parseFanDetectionOutput(ctx, ""), null);
  assert.equal(parseFanDetectionOutput(ctx, "bad\tthinkpad\n"), null);
  assert.equal(parseFanDetectionOutput(ctx, "hwmon\tbad\tthinkpad\n"), null);
}

function testFanHwmonDetectionPublishesSuccessfulSensor() {
  assert.match(source, /property bool sensorDetected: fanHwmonPath !== ""/, "FanService must expose sensor detection separately from available RPM readings");
  assert.match(source, /function publishFanSensor\(hwmonIndex, sensorName, fanIndices, fanLabels\)/, "publishFanSensor must accept detected fan indices and labels");
  const publishFanSensor = qmlFunction("publishFanSensor", "hwmonIndex", "sensorName", "fanIndices", "fanLabels");
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

  publishFanSensor(ctx, 4, "thinkpad", [2, 1], { 1: "CPU Fan", 2: null });

  assert.equal(ctx.root.fanSensorName, "thinkpad");
  assert.equal(ctx.root.fanHwmonPath, "/sys/class/hwmon/hwmon4");
  assert.deepEqual(ctx.root.detectedFanIndices, [1, 2]);
  assert.deepEqual(ctx.root.fanLabelCache, { 1: "CPU Fan", 2: null });
  assert.deepEqual(logs, [["FanService", "Found thinkpad fan sensor at /sys/class/hwmon/hwmon4"]]);
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
  assert.deepEqual(calls, []);
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
  assert.match(readNextBody, /const fanIndex = root\.pendingFanReads\[0\][\s\S]*root\.loadFanInput\(fanIndex\)/, "readNextFan must peek next index and load fan input path");
  assert.match(finalizeBody, /root\.collectedFans\.sort\(\(a, b\) => a\.index - b\.index\)/, "finalizeFanReading must sort fans by sensor index");
  assert.match(finalizeBody, /root\.rememberDetectedFanIndices\(root\.collectedFans\)/, "finalizeFanReading must cache detected fan input indices before publishing");
  assert.match(finalizeBody, /root\.pendingLabelReads = root\.findMissingLabelIndices\(root\.collectedFans\)[\s\S]*root\.publishFinalFans\(\)[\s\S]*root\.readNextFanLabel\(\)/, "finalizeFanReading must publish RPMs before optional label reads so missing labels cannot stall display");
}

function testFanReaderAndLabelGuards() {
  assert.match(source, /const rpm = parseInt\(text\(\)\.trim\(\)\) \|\| 0[\s\S]*const fanIndex = root\.pendingFanReads\.shift\(\)/, "fan reader must parse rpm and consume pending index together");
  assert.match(source, /if \(rpm >= 0\)[\s\S]*root\.collectedFans\.push\(\{[\s\S]*index: fanIndex,[\s\S]*rpm: rpm,[\s\S]*label: root\.labelForFan\(fanIndex\)/, "fan reader must collect non-negative fan readings with cached labels or default labels");
  assert.match(source, /root\.pendingFanReads = \[\][\s\S]*root\.finalizeFanReading\(\)/, "fan reader failure must stop pipeline and finalize");
  assert.match(source, /property int fanIndex: 0[\s\S]*root\.cacheFanLabel\(fanIndex, label\)[\s\S]*root\.readNextFanLabel\(\)/, "label reader must cache labels by fan index and continue the label pipeline");
  assert.match(source, /onLoadFailed: function\(error\) \{[\s\S]*root\.cacheFanLabel\(fanIndex, ""\)[\s\S]*root\.readNextFanLabel\(\)/, "label reader failure must cache missing labels before continuing so missing files are not retried every poll");
  assert.match(source, /function loadFanInput\(fanIndex\)[\s\S]*if \(fanReader\.path === nextPath\)[\s\S]*fanReader\.reload\(\)[\s\S]*fanReader\.path = nextPath/, "fan input loader must reload only when re-reading the same path");
  assert.match(source, /function loadFanLabel\(fanIndex\)[\s\S]*if \(labelReader\.path === nextPath\)[\s\S]*labelReader\.reload\(\)[\s\S]*labelReader\.path = nextPath/, "fan label loader must reload only when re-reading the same path");
  assert.doesNotMatch(source, /fanReader\.path = `\$\{root\.fanHwmonPath\}\/fan\$\{fanIndex\}_input`;\s*fanReader\.reload\(\)/, "fan input reads must not reload immediately after changing path");
  assert.doesNotMatch(source, /labelReader\.path = `\$\{root\.fanHwmonPath\}\/fan\$\{fanIndex\}_label`;\s*labelReader\.reload\(\)/, "fan label reads must not reload immediately after changing path");
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
  assert.deepEqual(ctx.fanLabelCache, { 1: "CPU Fan", 2: "Chassis", 3: null });
  assert.equal(labelForFan(ctx, 3), "Fan 3");
  assert.deepEqual(findMissingLabelIndices(ctx, [{ index: 1 }, { index: 2 }, { index: 3 }]), []);
  assert.deepEqual(applyCachedLabels(ctx, [
    { index: 1, rpm: 1200, label: "Fan 1" },
    { index: 2, rpm: 900, label: "Fan 2" },
    { index: 3, rpm: 700, label: "Fan 3" },
  ]), [
    { index: 1, rpm: 1200, label: "CPU Fan" },
    { index: 2, rpm: 900, label: "Chassis" },
    { index: 3, rpm: 700, label: "Fan 3" },
  ]);
}

function testFanLabelPipelineSkipsCachedLabels() {
  const finalizeFanReading = qmlFunction("finalizeFanReading");
  const readNextFanLabel = qmlFunction("readNextFanLabel");
  const publishFinalFans = qmlFunction("publishFinalFans");
  const loadFanLabel = qmlFunction("loadFanLabel", "fanIndex");
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
    loadFanLabel(fanIndex) {
      return loadFanLabel(ctx, fanIndex);
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
  assert.deepEqual(calls, ["publish", "read-label"]);
  assert.equal(ctx.labelReader.path, "/sys/class/hwmon/hwmon5/fan2_label");
}

function testFanPublishHelpers() {
  const publishBody = extractFunctionBody(source, "publishFinalFans");
  assert.match(publishBody, /root\.fans = root\.applyCachedLabels\(root\.collectedFans\)/, "publishFinalFans must publish cached-label fan data");
  assert.doesNotMatch(publishBody, /Logger\./, "publishFinalFans must not log every fan speed update during idle polling");
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
  testFanPublishHelpers,
  testFanSummaryHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
