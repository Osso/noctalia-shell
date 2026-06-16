#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Settings/SettingsPanel.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testSettingsPanelTabModelGuards() {
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
  const nextBody = extractFunctionBody(source, "selectNextTab");
  const previousBody = extractFunctionBody(source, "selectPreviousTab");

  assert.match(nextBody, /if \(tabsModel\.length > 0\)[\s\S]*currentTabIndex = \(currentTabIndex \+ 1\) % tabsModel\.length/, "selectNextTab must wrap forward through tabs");
  assert.match(previousBody, /if \(tabsModel\.length > 0\)[\s\S]*currentTabIndex = \(currentTabIndex - 1 \+ tabsModel\.length\) % tabsModel\.length/, "selectPreviousTab must wrap backward through tabs");
  assert.match(source, /function onTabPressed\(\) \{[\s\S]*selectNextTab\(\)/, "Tab handler must use selectNextTab");
  assert.match(source, /function onBackTabPressed\(\) \{[\s\S]*selectPreviousTab\(\)/, "BackTab handler must use selectPreviousTab");
  assert.match(source, /function onPageDownPressed\(\) \{[\s\S]*scrollPageDown\(\)/, "PageDown handler must use scrollPageDown");
  assert.match(source, /function onPageUpPressed\(\) \{[\s\S]*scrollPageUp\(\)/, "PageUp handler must use scrollPageUp");
}

function testSettingsPanelTabNavigationExecutesWrap() {
  const selectNextTab = qmlFunction("selectNextTab");
  const selectPreviousTab = qmlFunction("selectPreviousTab");
  const ctx = {
    tabsModel: [{}, {}, {}],
    currentTabIndex: 2,
  };

  selectNextTab(ctx);
  assert.equal(ctx.currentTabIndex, 0, "selectNextTab must wrap from last tab to first");

  selectPreviousTab(ctx);
  assert.equal(ctx.currentTabIndex, 2, "selectPreviousTab must wrap from first tab to last");

  ctx.tabsModel = [];
  selectNextTab(ctx);
  assert.equal(ctx.currentTabIndex, 2, "selectNextTab must ignore empty tab models");
}

function testSettingsPanelScrollExecutesClampBoundaries() {
  const scrollDown = qmlFunction("scrollDown");
  const scrollUp = qmlFunction("scrollUp");
  const scrollPageDown = qmlFunction("scrollPageDown");
  const scrollPageUp = qmlFunction("scrollPageUp");
  const scrollBar = {
    position: 0.92,
    size: 0.1,
  };
  const ctx = {
    activeScrollView: {
      height: 100,
      contentHeight: 1000,
      ScrollBar: { vertical: scrollBar },
    },
  };

  scrollDown(ctx);
  assert.equal(scrollBar.position, 0.9, "scrollDown must clamp to bottom");

  scrollBar.position = 0.05;
  scrollUp(ctx);
  assert.equal(scrollBar.position, 0.04, "scrollUp must move one small step upward");

  scrollBar.position = 0.2;
  scrollPageDown(ctx);
  assert.equal(scrollBar.position, 0.29000000000000004, "scrollPageDown must move one page downward");

  scrollBar.position = 0.04;
  scrollPageUp(ctx);
  assert.equal(scrollBar.position, 0, "scrollPageUp must clamp to top");
}

const tests = [
  testSettingsPanelTabModelGuards,
  testSettingsPanelScrollGuards,
  testSettingsPanelTabNavigationGuards,
  testSettingsPanelTabNavigationExecutesWrap,
  testSettingsPanelScrollExecutesClampBoundaries,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
