#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testSettingsPanelTabModelGuards() {
  const source = readQml("Modules/Panels/Settings/SettingsPanel.qml");
  const body = extractFunctionBody(source, "updateTabsModel");

  assert.match(body, /let newTabs = \[/, "updateTabsModel must build an ordered tab list");
  assert.match(body, /"id": SettingsPanel\.Tab\.General[\s\S]*"source": generalTab/, "updateTabsModel must include General tab first");
  assert.match(body, /"id": SettingsPanel\.Tab\.UserInterface[\s\S]*"source": userInterfaceTab/, "updateTabsModel must include User Interface tab");
  assert.match(body, /"id": SettingsPanel\.Tab\.Bar[\s\S]*"source": barTab/, "updateTabsModel must include Bar tab");
  assert.match(body, /"id": SettingsPanel\.Tab\.ControlCenter[\s\S]*"source": controlCenterTab/, "updateTabsModel must include Control Center tab");
  assert.match(body, /"id": SettingsPanel\.Tab\.SessionMenu[\s\S]*"source": sessionMenuTab/, "updateTabsModel must include Session Menu tab");
  assert.match(body, /"id": SettingsPanel\.Tab\.SystemMonitor[\s\S]*"source": systemMonitorTab/, "updateTabsModel must include System Monitor tab");
  assert.match(body, /"id": SettingsPanel\.Tab\.About[\s\S]*"source": aboutTab/, "updateTabsModel must include About tab");
  assert.match(body, /root\.tabsModel = newTabs/, "updateTabsModel must publish the generated tabs model");
}

function testSettingsPanelScrollGuards() {
  const source = readQml("Modules/Panels/Settings/SettingsPanel.qml");
  const downBody = extractFunctionBody(source, "scrollDown");
  const upBody = extractFunctionBody(source, "scrollUp");
  const pageDownBody = extractFunctionBody(source, "scrollPageDown");
  const pageUpBody = extractFunctionBody(source, "scrollPageUp");

  assert.match(downBody, /if \(activeScrollView && activeScrollView\.ScrollBar\.vertical\)/, "scrollDown must require active vertical scrollbar");
  assert.match(downBody, /const stepSize = activeScrollView\.height \* 0\.1[\s\S]*Math\.min\(scrollBar\.position \+ stepSize \/ activeScrollView\.contentHeight, 1\.0 - scrollBar\.size\)/, "scrollDown must move 10 percent and clamp to bottom");
  assert.match(upBody, /const stepSize = activeScrollView\.height \* 0\.1[\s\S]*Math\.max\(scrollBar\.position - stepSize \/ activeScrollView\.contentHeight, 0\)/, "scrollUp must move 10 percent and clamp to top");
  assert.match(pageDownBody, /const pageSize = activeScrollView\.height \* 0\.9[\s\S]*Math\.min\(scrollBar\.position \+ pageSize \/ activeScrollView\.contentHeight, 1\.0 - scrollBar\.size\)/, "scrollPageDown must move 90 percent and clamp to bottom");
  assert.match(pageUpBody, /const pageSize = activeScrollView\.height \* 0\.9[\s\S]*Math\.max\(scrollBar\.position - pageSize \/ activeScrollView\.contentHeight, 0\)/, "scrollPageUp must move 90 percent and clamp to top");
}

function testSettingsPanelTabNavigationGuards() {
  const source = readQml("Modules/Panels/Settings/SettingsPanel.qml");
  const nextBody = extractFunctionBody(source, "selectNextTab");
  const previousBody = extractFunctionBody(source, "selectPreviousTab");

  assert.match(nextBody, /if \(tabsModel\.length > 0\)[\s\S]*currentTabIndex = \(currentTabIndex \+ 1\) % tabsModel\.length/, "selectNextTab must wrap forward through tabs");
  assert.match(previousBody, /if \(tabsModel\.length > 0\)[\s\S]*currentTabIndex = \(currentTabIndex - 1 \+ tabsModel\.length\) % tabsModel\.length/, "selectPreviousTab must wrap backward through tabs");
  assert.match(source, /function onTabPressed\(\) \{[\s\S]*selectNextTab\(\)/, "Tab handler must use selectNextTab");
  assert.match(source, /function onBackTabPressed\(\) \{[\s\S]*selectPreviousTab\(\)/, "BackTab handler must use selectPreviousTab");
  assert.match(source, /function onPageDownPressed\(\) \{[\s\S]*scrollPageDown\(\)/, "PageDown handler must use scrollPageDown");
  assert.match(source, /function onPageUpPressed\(\) \{[\s\S]*scrollPageUp\(\)/, "PageUp handler must use scrollPageUp");
}

const tests = [
  testSettingsPanelTabModelGuards,
  testSettingsPanelScrollGuards,
  testSettingsPanelTabNavigationGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
