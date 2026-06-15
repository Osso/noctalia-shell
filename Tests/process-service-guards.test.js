#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testProcessServiceLifecycleAndCommands() {
  const source = readQml("Services/System/ProcessService.qml");
  const addRefBody = extractFunctionBody(source, "addRef");
  const removeRefBody = extractFunctionBody(source, "removeRef");
  const setSortBody = extractFunctionBody(source, "setSortBy");
  const toggleSortBody = extractFunctionBody(source, "toggleSortDirection");
  const updateBody = extractFunctionBody(source, "updateProcesses");
  const killBody = extractFunctionBody(source, "killProcess");
  const forceKillBody = extractFunctionBody(source, "forceKillProcess");

  assert.match(addRefBody, /refCount\+\+/, "addRef must increment the reference count");
  assert.match(addRefBody, /if \(refCount === 1\)[\s\S]*updateProcesses\(\)/, "addRef must start monitoring on the first reference");
  assert.match(removeRefBody, /refCount = Math\.max\(0, refCount - 1\)/, "removeRef must clamp reference count at zero");
  assert.match(removeRefBody, /if \(refCount === 0\)[\s\S]*Logger\.d\("ProcessService", "Deactivated - stopping process monitoring"\)/, "removeRef must log deactivation");
  assert.match(setSortBody, /if \(sortBy !== newSort\)[\s\S]*sortBy = newSort[\s\S]*applySorting\(\)/, "setSortBy must only resort when the sort key changes");
  assert.match(toggleSortBody, /sortDescending = !sortDescending[\s\S]*applySorting\(\)/, "toggleSortDirection must flip direction and resort");
  assert.match(updateBody, /if \(!isActive\) return;/, "updateProcesses must avoid work without active references");
  assert.match(updateBody, /psProcess\.running = true/, "updateProcesses must start the ps process");
  assert.match(killBody, /if \(pid > 0\)[\s\S]*killProcessCmd\.command = \["kill", pid\.toString\(\)\][\s\S]*killProcessCmd\.running = true/, "killProcess must run kill for positive pids");
  assert.match(forceKillBody, /if \(pid > 0\)[\s\S]*killProcessCmd\.command = \["kill", "-9", pid\.toString\(\)\][\s\S]*killProcessCmd\.running = true/, "forceKillProcess must run kill -9 for positive pids");
}

function testProcessServiceFormattingAndIcons() {
  const source = readQml("Services/System/ProcessService.qml");
  const cpuBody = extractFunctionBody(source, "formatCpu");
  const memoryBody = extractFunctionBody(source, "formatMemory");
  const iconBody = extractFunctionBody(source, "getProcessIcon");

  assert.match(cpuBody, /return cpu\.toFixed\(1\) \+ "%"/, "formatCpu must render one decimal percent values");
  assert.match(memoryBody, /if \(memKB < 1024\)[\s\S]*return memKB\.toFixed\(0\) \+ " KB"/, "formatMemory must render KB values");
  assert.match(memoryBody, /else if \(memKB < 1024 \* 1024\)[\s\S]*return \(memKB \/ 1024\)\.toFixed\(1\) \+ " MB"/, "formatMemory must render MB values");
  assert.match(memoryBody, /return \(memKB \/ \(1024 \* 1024\)\)\.toFixed\(2\) \+ " GB"/, "formatMemory must render GB values");
  assert.match(iconBody, /const cmd = command\.toLowerCase\(\)/, "getProcessIcon must normalize commands");
  assert.match(iconBody, /firefox[\s\S]*chrome[\s\S]*chromium[\s\S]*brave[\s\S]*return "web"/, "getProcessIcon must identify browsers");
  assert.match(iconBody, /code[\s\S]*nvim[\s\S]*vim[\s\S]*emacs[\s\S]*return "code"/, "getProcessIcon must identify editors");
  assert.match(iconBody, /kitty[\s\S]*wezterm[\s\S]*alacritty[\s\S]*terminal[\s\S]*konsole[\s\S]*return "terminal"/, "getProcessIcon must identify terminals");
  assert.match(iconBody, /spotify[\s\S]*music[\s\S]*return "music"/, "getProcessIcon must identify music players");
  assert.match(iconBody, /vlc[\s\S]*mpv[\s\S]*return "video"/, "getProcessIcon must identify video players");
  assert.match(iconBody, /discord[\s\S]*slack[\s\S]*telegram[\s\S]*signal[\s\S]*return "chat"/, "getProcessIcon must identify chat apps");
  assert.match(iconBody, /docker[\s\S]*containerd[\s\S]*podman[\s\S]*return "docker"/, "getProcessIcon must identify container runtimes");
  assert.match(iconBody, /kworker[\s\S]*kthread[\s\S]*migration[\s\S]*return "cpu"/, "getProcessIcon must identify kernel workers");
  assert.match(iconBody, /return "process"/, "getProcessIcon must fall back to a generic process icon");
}

function testProcessServiceParsing() {
  const source = readQml("Services/System/ProcessService.qml");
  const body = extractFunctionBody(source, "parseProcessOutput");

  assert.match(body, /if \(!text\) return;/, "parseProcessOutput must ignore empty output");
  assert.match(body, /const lines = text\.trim\(\)\.split\('\\n'\)/, "parseProcessOutput must parse ps output by line");
  assert.match(body, /const parts = line\.split\(\/\\s\+\/\)/, "parseProcessOutput must split ps rows by whitespace");
  assert.match(body, /if \(parts\.length < 5\) continue;/, "parseProcessOutput must skip malformed rows");
  assert.match(body, /const pid = parseInt\(parts\[0\]\) \|\| 0/, "parseProcessOutput must parse pids");
  assert.match(body, /const cpu = parseFloat\(parts\[1\]\) \|\| 0/, "parseProcessOutput must parse cpu usage");
  assert.match(body, /const memPercent = parseFloat\(parts\[2\]\) \|\| 0/, "parseProcessOutput must parse memory percentage");
  assert.match(body, /const rssKB = parseInt\(parts\[3\]\) \|\| 0/, "parseProcessOutput must parse RSS memory");
  assert.match(body, /const command = parts\.slice\(4\)\.join\(' '\)/, "parseProcessOutput must preserve command arguments");
  assert.match(body, /if \(cmdName\.startsWith\('\['\)\)[\s\S]*cmdName = cmdName\.split\('\]'\)\[0\]\.replace\('\[', ''\)\.split\('\/'\)\[0\]/, "parseProcessOutput must normalize kernel thread names");
  assert.match(body, /const firstArg = command\.split\(' '\)\[0\][\s\S]*cmdName = firstArg\.split\('\/'\)\.pop\(\)/, "parseProcessOutput must extract executable basenames");
  assert.match(body, /displayName: cmdName\.length > 25 \? cmdName\.substring\(0, 25\) \+ ".?" : cmdName/, "parseProcessOutput must truncate long display names");
  assert.match(body, /totalCpu \+= cpu[\s\S]*totalMem \+= memPercent/, "parseProcessOutput must accumulate totals");
  assert.match(body, /allProcesses = newProcesses[\s\S]*processCount = newProcesses\.length/, "parseProcessOutput must publish the parsed process list");
  assert.match(body, /totalCpuUsage = Math\.min\(totalCpu, 100\)[\s\S]*totalMemoryUsage = Math\.min\(totalMem, 100\)/, "parseProcessOutput must cap aggregate percentages");
  assert.match(body, /applySorting\(\)/, "parseProcessOutput must sort parsed processes");
}

function testProcessServiceSorting() {
  const source = readQml("Services/System/ProcessService.qml");
  const body = extractFunctionBody(source, "applySorting");

  assert.match(body, /if \(!allProcesses \|\| allProcesses\.length === 0\) return;/, "applySorting must ignore empty process lists");
  assert.match(body, /const sorted = allProcesses\.slice\(\)/, "applySorting must sort a copy of all processes");
  assert.match(body, /case "cpu":[\s\S]*valueA = a\.cpu \|\| 0[\s\S]*valueB = b\.cpu \|\| 0/, "applySorting must support CPU sorting");
  assert.match(body, /case "memory":[\s\S]*valueA = a\.memoryKB \|\| 0[\s\S]*valueB = b\.memoryKB \|\| 0/, "applySorting must support memory sorting");
  assert.match(body, /case "name":[\s\S]*valueA = \(a\.command \|\| ""\)\.toLowerCase\(\)[\s\S]*return sortDescending \? valueB\.localeCompare\(valueA\) : valueA\.localeCompare\(valueB\)/, "applySorting must support name sorting");
  assert.match(body, /case "pid":[\s\S]*valueA = a\.pid \|\| 0[\s\S]*valueB = b\.pid \|\| 0/, "applySorting must support PID sorting");
  assert.match(body, /default:[\s\S]*return 0/, "applySorting must leave unknown sort keys unchanged");
  assert.match(body, /return sortDescending \? \(valueB - valueA\) : \(valueA - valueB\)/, "applySorting must honor numeric sort direction");
  assert.match(body, /processes = sorted\.slice\(0, processLimit\)/, "applySorting must publish only the configured process limit");
}

const tests = [
  testProcessServiceLifecycleAndCommands,
  testProcessServiceFormattingAndIcons,
  testProcessServiceParsing,
  testProcessServiceSorting,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
