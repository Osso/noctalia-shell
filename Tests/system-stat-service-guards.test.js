#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testSystemStatServiceIntervalAndMemoryGuards() {
  const source = readQml("Services/System/SystemStatService.qml");
  const normalizeBody = extractFunctionBody(source, "normalizeInterval");
  const memoryBody = extractFunctionBody(source, "parseMemoryInfo");

  assert.match(normalizeBody, /Math\.max\(minimumIntervalMs, value \|\| defaultIntervalMs\)/, "normalizeInterval must clamp falsy and short intervals");
  assert.match(memoryBody, /if \(!text\)\s+return;/, "parseMemoryInfo must ignore empty input");
  assert.match(memoryBody, /const lines = text\.split\('\\n'\)/, "parseMemoryInfo must parse line-oriented /proc/meminfo");
  assert.match(memoryBody, /line\.startsWith\('MemTotal:'\)[\s\S]*memTotal = parseInt\(line\.split\(\/\\s\+\/\)\[1\]\) \|\| 0/, "parseMemoryInfo must parse MemTotal safely");
  assert.match(memoryBody, /line\.startsWith\('MemAvailable:'\)[\s\S]*memAvailable = parseInt\(line\.split\(\/\\s\+\/\)\[1\]\) \|\| 0/, "parseMemoryInfo must parse MemAvailable safely");
  assert.match(memoryBody, /if \(memTotal > 0\)[\s\S]*const usageKb = memTotal - memAvailable/, "parseMemoryInfo must only compute usage with valid total memory");
  assert.match(memoryBody, /root\.memGb = \(usageKb \/ 1048576\)\.toFixed\(1\)/, "parseMemoryInfo must expose used memory in GiB");
  assert.match(memoryBody, /root\.memPercent = Math\.round\(\(usageKb \/ memTotal\) \* 100\)/, "parseMemoryInfo must expose rounded memory percentage");
}

function testSystemStatServiceCpuAndNetworkGuards() {
  const source = readQml("Services/System/SystemStatService.qml");
  const cpuBody = extractFunctionBody(source, "calculateCpuUsage");
  const networkBody = extractFunctionBody(source, "calculateNetworkSpeed");

  assert.match(cpuBody, /if \(!text\)\s+return;/, "calculateCpuUsage must ignore empty input");
  assert.match(cpuBody, /if \(!cpuLine\.startsWith\('cpu '\)\)\s+return;/, "calculateCpuUsage must require the aggregate cpu line");
  assert.match(cpuBody, /"user": parseInt\(parts\[1\]\) \|\| 0[\s\S]*"guestNice": parseInt\(parts\[10\]\) \|\| 0/, "calculateCpuUsage must parse all aggregate CPU counters");
  assert.match(cpuBody, /const totalIdle = stats\.idle \+ stats\.iowait/, "calculateCpuUsage must include iowait in idle time");
  assert.match(cpuBody, /if \(root\.prevCpuStats\)[\s\S]*const diffTotal = total - prevTotal[\s\S]*const diffIdle = totalIdle - prevTotalIdle/, "calculateCpuUsage must compare against previous samples");
  assert.match(cpuBody, /if \(diffTotal > 0\)[\s\S]*root\.cpuUsage = \(\(\(diffTotal - diffIdle\) \/ diffTotal\) \* 100\)\.toFixed\(1\)/, "calculateCpuUsage must avoid divide-by-zero and publish usage percentage");
  assert.match(cpuBody, /root\.prevCpuStats = stats/, "calculateCpuUsage must store the latest sample");
  assert.match(networkBody, /if \(!text\) \{[\s\S]*return;[\s\S]*\}/, "calculateNetworkSpeed must ignore empty input");
  assert.match(networkBody, /const currentTime = Date\.now\(\) \/ 1000/, "calculateNetworkSpeed must timestamp samples in seconds");
  assert.match(networkBody, /for \(var i = 2; i < lines\.length; i\+\+\)/, "calculateNetworkSpeed must skip /proc/net/dev headers");
  assert.match(networkBody, /if \(colonIndex === -1\)[\s\S]*continue;/, "calculateNetworkSpeed must skip malformed interface rows");
  assert.match(networkBody, /if \(iface === 'lo'\)[\s\S]*continue;/, "calculateNetworkSpeed must exclude loopback");
  assert.match(networkBody, /const rxBytes = parseInt\(stats\[0\], 10\) \|\| 0[\s\S]*const txBytes = parseInt\(stats\[8\], 10\) \|\| 0/, "calculateNetworkSpeed must parse RX and TX byte counters");
  assert.match(networkBody, /if \(root\.prevTime > 0\)[\s\S]*const timeDiff = currentTime - root\.prevTime/, "calculateNetworkSpeed must require a previous sample");
  assert.match(networkBody, /if \(rxDiff < 0\)[\s\S]*rxDiff = 0[\s\S]*if \(txDiff < 0\)[\s\S]*txDiff = 0/, "calculateNetworkSpeed must handle counter resets");
  assert.match(networkBody, /root\.rxSpeed = Math\.round\(rxDiff \/ timeDiff\)[\s\S]*root\.txSpeed = Math\.round\(txDiff \/ timeDiff\)/, "calculateNetworkSpeed must publish bytes-per-second rates");
  assert.match(networkBody, /root\.prevRxBytes = totalRx[\s\S]*root\.prevTxBytes = totalTx[\s\S]*root\.prevTime = currentTime/, "calculateNetworkSpeed must store the latest counters");
}

function testSystemStatServiceSpeedFormattingGuards() {
  const source = readQml("Services/System/SystemStatService.qml");
  const speedBody = extractFunctionBody(source, "formatSpeed");
  const compactBody = extractFunctionBody(source, "formatCompactSpeed");

  assert.match(speedBody, /if \(bytesPerSecond < 1024 \* 1024\)/, "formatSpeed must keep sub-megabyte values in KB");
  assert.match(speedBody, /if \(kb < 10\)[\s\S]*return kb\.toFixed\(1\) \+ "KB"[\s\S]*return Math\.round\(kb\) \+ "KB"/, "formatSpeed must show one decimal only for small KB values");
  assert.match(speedBody, /bytesPerSecond < 1024 \* 1024 \* 1024[\s\S]*toFixed\(1\) \+ "MB"/, "formatSpeed must format megabyte values");
  assert.match(speedBody, /toFixed\(1\) \+ "GB"/, "formatSpeed must format gigabyte values");
  assert.match(compactBody, /if \(!bytesPerSecond \|\| bytesPerSecond <= 0\)\s+return "0"/, "formatCompactSpeed must hide empty or negative rates");
  assert.match(compactBody, /const units = \["", "K", "M", "G"\]/, "formatCompactSpeed must use compact unit suffixes");
  assert.match(compactBody, /while \(value >= 1024 && unitIndex < units\.length - 1\)[\s\S]*value = value \/ 1024\.0[\s\S]*unitIndex\+\+/, "formatCompactSpeed must promote through binary units");
  assert.match(compactBody, /if \(unitIndex < units\.length - 1 && value >= 100\)[\s\S]*value = value \/ 1024\.0[\s\S]*unitIndex\+\+/, "formatCompactSpeed must promote crowded three-digit values");
  assert.match(compactBody, /const display = Math\.round\(value\)\.toString\(\)[\s\S]*return display \+ units\[unitIndex\]/, "formatCompactSpeed must return rounded compact strings");
}

function testSystemStatServiceTemperatureGuards() {
  const source = readQml("Services/System/SystemStatService.qml");
  const checkNameBody = extractFunctionBody(source, "checkNext");
  const updateBody = extractFunctionBody(source, "updateCpuTemperature");
  const intelBody = extractFunctionBody(source, "checkNextIntelTemp");

  assert.match(checkNameBody, /if \(currentIndex >= 16\)[\s\S]*Logger\.w\("No supported temperature sensor found"\)[\s\S]*return;/, "checkNext must stop probing unsupported hwmon paths");
  assert.match(checkNameBody, /cpuTempNameReader\.path = `\/sys\/class\/hwmon\/hwmon\$\{currentIndex\}\/name`[\s\S]*cpuTempNameReader\.reload\(\)/, "checkNext must probe the next hwmon name file");
  assert.match(updateBody, /root\.cpuTempSensorName === "k10temp" \|\| root\.cpuTempSensorName === "zenpower"/, "updateCpuTemperature must recognize AMD sensors");
  assert.match(updateBody, /cpuTempReader\.path = `\$\{root\.cpuTempHwmonPath\}\/temp1_input`[\s\S]*cpuTempReader\.reload\(\)/, "updateCpuTemperature must read AMD Tctl temperature");
  assert.match(updateBody, /root\.cpuTempSensorName === "coretemp"[\s\S]*root\.intelTempValues = \[\][\s\S]*root\.intelTempFilesChecked = 0[\s\S]*checkNextIntelTemp\(\)/, "updateCpuTemperature must reset Intel averaging state");
  assert.match(intelBody, /if \(root\.intelTempFilesChecked >= root\.intelTempMaxFiles\)/, "checkNextIntelTemp must stop after configured probes");
  assert.match(intelBody, /for \(var i = 0; i < root\.intelTempValues\.length; i\+\+\)[\s\S]*sum \+= root\.intelTempValues\[i\]/, "checkNextIntelTemp must sum collected Intel temperatures");
  assert.match(intelBody, /root\.cpuTemp = Math\.round\(sum \/ root\.intelTempValues\.length\)/, "checkNextIntelTemp must publish averaged Intel temperature");
  assert.match(intelBody, /Logger\.w\("SystemStat", "No temperature sensors found for coretemp"\)[\s\S]*root\.cpuTemp = 0/, "checkNextIntelTemp must fail closed when no Intel sensors load");
  assert.match(intelBody, /root\.intelTempFilesChecked\+\+[\s\S]*cpuTempReader\.path = `\$\{root\.cpuTempHwmonPath\}\/temp\$\{root\.intelTempFilesChecked\}_input`[\s\S]*cpuTempReader\.reload\(\)/, "checkNextIntelTemp must probe the next Intel temp input");
}

const tests = [
  testSystemStatServiceIntervalAndMemoryGuards,
  testSystemStatServiceCpuAndNetworkGuards,
  testSystemStatServiceSpeedFormattingGuards,
  testSystemStatServiceTemperatureGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
