#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testLauncherSearchTextPluginRegistrationAndResultAggregation() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const setBody = extractFunctionBody(source, "setSearchText");
  const registerBody = extractFunctionBody(source, "registerPlugin");
  const updateBody = extractFunctionBody(source, "updateResults");

  assert.match(setBody, /searchText = text/, "setSearchText must update the launcher search text");
  assert.match(registerBody, /plugins\.push\(plugin\)/, "registerPlugin must store plugins");
  assert.match(registerBody, /plugin\.launcher = root/, "registerPlugin must provide launcher back-reference");
  assert.match(registerBody, /if \(plugin\.init\)\s+plugin\.init\(\)/, "registerPlugin must initialize capable plugins");
  assert.match(updateBody, /results = \[\][\s\S]*activePlugin = null/, "updateResults must reset prior results and active plugin");
  assert.match(updateBody, /if \(searchText\.startsWith\(">"\)\)/, "updateResults must detect command mode");
  assert.match(updateBody, /plugin\.handleCommand && plugin\.handleCommand\(searchText\)[\s\S]*activePlugin = plugin[\s\S]*results = plugin\.getResults\(searchText\)/, "updateResults must route command text to matching plugins");
  assert.match(updateBody, /let allCommands = \[\][\s\S]*allCommands = allCommands\.concat\(plugin\.commands\(\)\)/, "updateResults must collect commands from all command plugins");
  assert.match(updateBody, /if \(searchText === ">"\)[\s\S]*results = allCommands/, "updateResults must show all commands for bare command prefix");
  assert.match(updateBody, /const query = searchText\.substring\(1\)/, "updateResults must strip command prefix before filtering");
  assert.match(updateBody, /Fuzzysort\.go\(query,\s*allCommands,\s*\{[\s\S]*"keys": \["name"\][\s\S]*"limit": 50/, "updateResults must use fuzzy command filtering when available");
  assert.match(updateBody, /results = fuzzyResults\.map\(result => result\.obj\)/, "updateResults must unwrap fuzzy command results");
  assert.match(updateBody, /const queryLower = query\.toLowerCase\(\)[\s\S]*cmdName\.includes\(queryLower\)/, "updateResults must provide simple command filtering fallback");
  assert.match(updateBody, /if \(plugin\.handleSearch\)[\s\S]*const pluginResults = plugin\.getResults\(searchText\)[\s\S]*results = results\.concat\(pluginResults\)/, "updateResults must aggregate search results from searchable plugins");
  assert.match(updateBody, /selectedIndex = 0/, "updateResults must reset selection after recomputing results");
}

function testLauncherLinearNavigationHelpersClampAndWrap() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const nextBody = extractFunctionBody(source, "selectNextWrapped");
  const previousBody = extractFunctionBody(source, "selectPreviousWrapped");
  const firstBody = extractFunctionBody(source, "selectFirst");
  const lastBody = extractFunctionBody(source, "selectLast");
  const nextPageBody = extractFunctionBody(source, "selectNextPage");
  const previousPageBody = extractFunctionBody(source, "selectPreviousPage");

  assert.match(nextBody, /if \(results\.length > 0\)[\s\S]*selectedIndex = \(selectedIndex \+ 1\) % results\.length/, "selectNextWrapped must wrap forward through results");
  assert.match(previousBody, /if \(results\.length > 0\)[\s\S]*selectedIndex = \(\(\(selectedIndex - 1\) % results\.length\) \+ results\.length\) % results\.length/, "selectPreviousWrapped must wrap backward through results");
  assert.match(firstBody, /selectedIndex = 0/, "selectFirst must select the first result");
  assert.match(lastBody, /if \(results\.length > 0\)[\s\S]*selectedIndex = results\.length - 1[\s\S]*else[\s\S]*selectedIndex = 0/, "selectLast must select the last result or reset when empty");
  assert.match(nextPageBody, /const page = Math\.max\(1,\s*Math\.floor\(600 \/ entryHeight\)\)/, "selectNextPage must derive a nonzero page size");
  assert.match(nextPageBody, /selectedIndex = Math\.min\(selectedIndex \+ page,\s*results\.length - 1\)/, "selectNextPage must clamp to the final result");
  assert.match(previousPageBody, /const page = Math\.max\(1,\s*Math\.floor\(600 \/ entryHeight\)\)/, "selectPreviousPage must derive a nonzero page size");
  assert.match(previousPageBody, /selectedIndex = Math\.max\(selectedIndex - page,\s*0\)/, "selectPreviousPage must clamp to the first result");
}

function testLauncherGridRowNavigationPreservesColumnsWhenPossible() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const previousRowBody = extractFunctionBody(source, "selectPreviousRow");
  const nextRowBody = extractFunctionBody(source, "selectNextRow");

  assert.match(previousRowBody, /if \(results\.length > 0 && isGridView\)/, "selectPreviousRow must only run in populated grid view");
  assert.match(previousRowBody, /const currentRow = Math\.floor\(selectedIndex \/ gridColumns\)[\s\S]*const currentCol = selectedIndex % gridColumns/, "selectPreviousRow must compute current grid position");
  assert.match(previousRowBody, /if \(currentRow > 0\)[\s\S]*const targetRow = currentRow - 1[\s\S]*const targetIndex = targetRow \* gridColumns \+ currentCol/, "selectPreviousRow must target the same column in the prior row");
  assert.match(previousRowBody, /const itemsInTargetRow = Math\.min\(gridColumns,\s*results\.length - targetRow \* gridColumns\)/, "selectPreviousRow must handle short rows");
  assert.match(previousRowBody, /selectedIndex = targetRow \* gridColumns \+ itemsInTargetRow - 1/, "selectPreviousRow must fall back to the last item in a short row");
  assert.match(previousRowBody, /const totalRows = Math\.ceil\(results\.length \/ gridColumns\)[\s\S]*const lastRow = totalRows - 1/, "selectPreviousRow must wrap to the last row from the first row");
  assert.match(previousRowBody, /selectedIndex = results\.length - 1/, "selectPreviousRow must clamp wrapped short last rows to final item");
  assert.match(nextRowBody, /if \(results\.length > 0 && isGridView\)/, "selectNextRow must only run in populated grid view");
  assert.match(nextRowBody, /const currentRow = Math\.floor\(selectedIndex \/ gridColumns\)[\s\S]*const currentCol = selectedIndex % gridColumns/, "selectNextRow must compute current grid position");
  assert.match(nextRowBody, /if \(currentRow < totalRows - 1\)[\s\S]*const targetRow = currentRow \+ 1/, "selectNextRow must target the same column in the next row");
  assert.match(nextRowBody, /const itemsInTargetRow = results\.length - targetRow \* gridColumns/, "selectNextRow must handle partially filled target rows");
  assert.match(nextRowBody, /selectedIndex = Math\.min\(currentCol,\s*results\.length - 1\)/, "selectNextRow must wrap from the last row back to the first row");
}

function testLauncherGridColumnNavigationWrapsRows() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const previousColumnBody = extractFunctionBody(source, "selectPreviousColumn");
  const nextColumnBody = extractFunctionBody(source, "selectNextColumn");

  assert.match(previousColumnBody, /if \(results\.length > 0 && isGridView\)/, "selectPreviousColumn must only run in populated grid view");
  assert.match(previousColumnBody, /const currentRow = Math\.floor\(selectedIndex \/ gridColumns\)[\s\S]*const currentCol = selectedIndex % gridColumns/, "selectPreviousColumn must compute current grid position");
  assert.match(previousColumnBody, /if \(currentCol > 0\)[\s\S]*selectedIndex = currentRow \* gridColumns \+ \(currentCol - 1\)/, "selectPreviousColumn must move left in the same row");
  assert.match(previousColumnBody, /if \(currentRow > 0\)[\s\S]*selectedIndex = \(currentRow - 1\) \* gridColumns \+ \(gridColumns - 1\)/, "selectPreviousColumn must wrap to the prior row");
  assert.match(previousColumnBody, /const totalRows = Math\.ceil\(results\.length \/ gridColumns\)[\s\S]*selectedIndex = Math\.min\(lastRowIndex,\s*results\.length - 1\)/, "selectPreviousColumn must wrap from first item to the final available item");
  assert.match(nextColumnBody, /if \(results\.length > 0 && isGridView\)/, "selectNextColumn must only run in populated grid view");
  assert.match(nextColumnBody, /const itemsInCurrentRow = Math\.min\(gridColumns,\s*results\.length - currentRow \* gridColumns\)/, "selectNextColumn must account for short current rows");
  assert.match(nextColumnBody, /if \(currentCol < itemsInCurrentRow - 1\)[\s\S]*selectedIndex = currentRow \* gridColumns \+ \(currentCol \+ 1\)/, "selectNextColumn must move right in the same row");
  assert.match(nextColumnBody, /if \(currentRow < totalRows - 1\)[\s\S]*selectedIndex = \(currentRow \+ 1\) \* gridColumns/, "selectNextColumn must wrap to the first item in the next row");
  assert.match(nextColumnBody, /else[\s\S]*selectedIndex = 0/, "selectNextColumn must wrap from the final row to the first item");
}

function testLauncherActivateInvokesSelectedResult() {
  const source = readQml("Modules/Panels/Launcher/Launcher.qml");
  const body = extractFunctionBody(source, "activate");

  assert.match(body, /if \(results\.length > 0 && results\[selectedIndex\]\)/, "activate must require a selected result");
  assert.match(body, /const item = results\[selectedIndex\]/, "activate must read the selected result");
  assert.match(body, /if \(item\.onActivate\)[\s\S]*item\.onActivate\(\)/, "activate must invoke selectable result actions");
}

const tests = [
  testLauncherSearchTextPluginRegistrationAndResultAggregation,
  testLauncherLinearNavigationHelpersClampAndWrap,
  testLauncherGridRowNavigationPreservesColumnsWhenPossible,
  testLauncherGridColumnNavigationWrapsRows,
  testLauncherActivateInvokesSelectedResult,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
