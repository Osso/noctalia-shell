#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/UI/BarService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testBarServiceRegistrationAndLookupHelpers() {
  const registerBarBody = extractFunctionBody(source, "registerBar");
  const isReadyBody = extractFunctionBody(source, "isBarReady");
  const registerWidgetBody = extractFunctionBody(source, "registerWidget");
  const unregisterWidgetBody = extractFunctionBody(source, "unregisterWidget");
  const lookupBody = extractFunctionBody(source, "lookupWidget");

  assert.match(registerBarBody, /if \(!readyBars\[screenName\]\)/, "registerBar must only emit readiness once per screen");
  assert.match(registerBarBody, /readyBars\[screenName\] = true/, "registerBar must mark the screen ready");
  assert.match(registerBarBody, /barReadyChanged\(screenName\)/, "registerBar must emit readiness changes");
  assert.match(isReadyBody, /return readyBars\[screenName\] \|\| false/, "isBarReady must fail closed for unknown screens");
  assert.match(registerWidgetBody, /const key = \[screenName,\s*section,\s*widgetId,\s*index\]\.join\("\|"\)/, "registerWidget must build stable registry keys");
  assert.match(registerWidgetBody, /widgetInstances\[key\] = \{[\s\S]*"screenName": screenName[\s\S]*"section": section[\s\S]*"widgetId": widgetId[\s\S]*"index": index[\s\S]*"instance": instance/, "registerWidget must store widget metadata and instance");
  assert.match(registerWidgetBody, /timerCheckVisualizer\.restart\(\)/, "registerWidget must rescan visualizer state");
  assert.match(registerWidgetBody, /root\.activeWidgetsChanged\(\)/, "registerWidget must emit active widget changes");
  assert.match(unregisterWidgetBody, /const key = \[screenName,\s*section,\s*widgetId,\s*index\]\.join\("\|"\)/, "unregisterWidget must use the same stable key");
  assert.match(unregisterWidgetBody, /delete widgetInstances\[key\]/, "unregisterWidget must delete the registered widget");
  assert.match(unregisterWidgetBody, /root\.activeWidgetsChanged\(\)/, "unregisterWidget must emit active widget changes");
  assert.match(lookupBody, /if \(screenName && section !== null\)/, "lookupWidget must support exact screen and section lookups");
  assert.match(lookupBody, /widget\.widgetId === widgetId && widget\.screenName === screenName && widget\.section === section/, "lookupWidget must match exact widget metadata");
  assert.match(lookupBody, /if \(index === null\)[\s\S]*return widget\.instance[\s\S]*else if \(widget\.index == index\)[\s\S]*return widget\.instance/, "lookupWidget must optionally match index");
  assert.match(lookupBody, /if \(!screenName \|\| widget\.screenName === screenName\)[\s\S]*if \(section === null \|\| widget\.section === section\)[\s\S]*return widget\.instance/, "lookupWidget must support fallback filtered lookup");
  assert.match(lookupBody, /return undefined/, "lookupWidget must return undefined for missing widgets");
}

function testBarServiceWidgetEnumerationHelpers() {
  const allInstancesBody = extractFunctionBody(source, "getAllWidgetInstances");
  const metadataBody = extractFunctionBody(source, "getWidgetWithMetadata");
  const sectionBody = extractFunctionBody(source, "getWidgetsBySection");
  const registeredBody = extractFunctionBody(source, "getAllRegisteredWidgets");
  const hasBody = extractFunctionBody(source, "hasWidget");

  assert.match(allInstancesBody, /var instances = \[\]/, "getAllWidgetInstances must collect matching instances");
  assert.match(allInstancesBody, /if \(widgetId && widget\.widgetId !== widgetId\)\s+matches = false/, "getAllWidgetInstances must filter by widget id");
  assert.match(allInstancesBody, /if \(screenName && widget\.screenName !== screenName\)\s+matches = false/, "getAllWidgetInstances must filter by screen");
  assert.match(allInstancesBody, /if \(section !== null && widget\.section !== section\)\s+matches = false/, "getAllWidgetInstances must filter by section");
  assert.match(allInstancesBody, /instances\.push\(widget\.instance\)/, "getAllWidgetInstances must return instances only");
  assert.match(metadataBody, /if \(widget\.widgetId === widgetId\)[\s\S]*return widget/, "getWidgetWithMetadata must return the full metadata record");
  assert.match(metadataBody, /return undefined/, "getWidgetWithMetadata must return undefined when no widget matches");
  assert.match(sectionBody, /if \(widget\.section === section\)[\s\S]*widgets\.push\(widget\.instance\)/, "getWidgetsBySection must collect section instances");
  assert.match(sectionBody, /widgets\.sort\(function \(a,\s*b\)/, "getWidgetsBySection must sort widgets");
  assert.match(sectionBody, /var aWidget = getWidgetWithMetadata\(a\.widgetId,\s*aScreenName,\s*a\.section\)/, "getWidgetsBySection must recover metadata for sort order");
  assert.match(sectionBody, /return aIndex - bIndex/, "getWidgetsBySection must sort by stored index");
  assert.match(registeredBody, /result\.push\(\{[\s\S]*"key": key[\s\S]*"widgetId": widgetInstances\[key\]\.widgetId[\s\S]*"section": widgetInstances\[key\]\.section[\s\S]*"screenName": widgetInstances\[key\]\.screenName[\s\S]*"index": widgetInstances\[key\]\.index/, "getAllRegisteredWidgets must expose debug metadata");
  assert.match(hasBody, /if \(widget\.widgetId === widgetId\)/, "hasWidget must match widget ids");
  assert.match(hasBody, /if \(section === null \|\| widget\.section === section\)/, "hasWidget must optionally filter by section");
  assert.match(hasBody, /if \(!screenName \|\| widget\.screenName === screenName\)[\s\S]*return true/, "hasWidget must optionally filter by screen");
  assert.match(hasBody, /return false/, "hasWidget must fail closed when no widget matches");
}

function testBarServiceDirectionAndContextMenuHelpers() {
  const pillBody = extractFunctionBody(source, "getPillDirection");
  const tooltipBody = extractFunctionBody(source, "getTooltipDirection");
  const menuBody = extractFunctionBody(source, "getContextMenuPosition");

  assert.match(pillBody, /if \(widgetInstance\.section === "left"\)[\s\S]*return true/, "getPillDirection must point left-section pills inward");
  assert.match(pillBody, /else if \(widgetInstance\.section === "right"\)[\s\S]*return false/, "getPillDirection must point right-section pills inward");
  assert.match(pillBody, /widgetInstance\.sectionWidgetIndex < widgetInstance\.sectionWidgetsCount \/ 2[\s\S]*return false[\s\S]*else[\s\S]*return true/, "getPillDirection must split middle-section widgets by index");
  assert.match(pillBody, /catch \(e\)[\s\S]*Logger\.e\(e\)/, "getPillDirection must log malformed widget instances");
  assert.match(pillBody, /return false/, "getPillDirection must fail closed");
  assert.match(tooltipBody, /case "right":[\s\S]*return "left"/, "getTooltipDirection must point tooltips away from right bars");
  assert.match(tooltipBody, /case "left":[\s\S]*return "right"/, "getTooltipDirection must point tooltips away from left bars");
  assert.match(tooltipBody, /case "bottom":[\s\S]*return "top"/, "getTooltipDirection must point tooltips above bottom bars");
  assert.match(tooltipBody, /default:[\s\S]*return "bottom"/, "getTooltipDirection must default below top bars");
  assert.match(menuBody, /if \(!anchorItem\)[\s\S]*return \{[\s\S]*"x": 0[\s\S]*"y": 0/, "getContextMenuPosition must fail closed without an anchor");
  assert.match(menuBody, /const mWidth = menuWidth \|\| 180/, "getContextMenuPosition must default menu width");
  assert.match(menuBody, /const mHeight = menuHeight \|\| 100/, "getContextMenuPosition must default menu height");
  assert.match(menuBody, /const anchorCenterX = anchorItem\.width \/ 2[\s\S]*const anchorCenterY = anchorItem\.height \/ 2/, "getContextMenuPosition must position from anchor center");
  assert.match(menuBody, /barPosition === "left"[\s\S]*menuX = anchorItem\.width \+ Style\.marginM[\s\S]*menuY = anchorCenterY - \(mHeight \/ 2\)/, "getContextMenuPosition must place menus right of left bars");
  assert.match(menuBody, /barPosition === "right"[\s\S]*menuX = -mWidth - Style\.marginM/, "getContextMenuPosition must place menus left of right bars");
  assert.match(menuBody, /barPosition === "top"[\s\S]*menuY = Style\.barHeight/, "getContextMenuPosition must place menus below top bars");
  assert.match(menuBody, /else[\s\S]*menuY = -mHeight - Style\.marginM/, "getContextMenuPosition must place menus above bottom bars");
}

function testBarServiceWidgetSettingsDialogWiring() {
  const body = extractFunctionBody(source, "openWidgetSettings");

  assert.match(body, /PanelService\.getPopupMenuWindow\(screen\)/, "openWidgetSettings must use the popup menu window for the target screen");
  assert.match(body, /if \(!popupMenuWindow\)[\s\S]*Logger\.e\("BarService",\s*"No popup menu window found for screen"\)[\s\S]*return;/, "openWidgetSettings must fail closed without a popup menu window");
  assert.match(body, /Qt\.createComponent\(Quickshell\.shellDir \+ "\/Modules\/Panels\/Settings\/Bar\/BarWidgetSettingsDialog\.qml"\)/, "openWidgetSettings must load the widget settings dialog component");
  assert.match(body, /component\.createObject\(popupMenuWindow\.dialogParent,\s*\{[\s\S]*"widgetIndex": index[\s\S]*"widgetData": widgetData[\s\S]*"widgetId": widgetId[\s\S]*"sectionId": section/, "openWidgetSettings must pass widget context to the dialog");
  assert.match(body, /dialog\.updateWidgetSettings\.connect\(\(sec,\s*idx,\s*settings\) =>/, "openWidgetSettings must listen for dialog setting updates");
  assert.match(body, /widgets\[idx\] = Object\.assign\(\{\},\s*widgets\[idx\],\s*settings\)/, "openWidgetSettings must merge updated widget settings");
  assert.match(body, /Settings\.saveImmediate\(\)/, "openWidgetSettings must persist dialog changes immediately");
  assert.match(body, /popupMenuWindow\.hasDialog = true/, "openWidgetSettings must mark the popup window as owning a dialog");
  assert.match(body, /dialog\.closed\.connect\(\(\) =>[\s\S]*popupMenuWindow\.hasDialog = false[\s\S]*popupMenuWindow\.close\(\)[\s\S]*dialog\.destroy\(\)/, "openWidgetSettings must clean up when the dialog closes");
  assert.match(body, /popupMenuWindow\.open\(\)[\s\S]*dialog\.open\(\)/, "openWidgetSettings must open the parent window and dialog");
  assert.match(body, /if \(component\.status === Component\.Ready\)[\s\S]*instantiateAndOpen\(\)/, "openWidgetSettings must open immediately when the component is ready");
  assert.match(body, /else if \(component\.status === Component\.Error\)[\s\S]*component\.errorString\(\)/, "openWidgetSettings must log immediate component load errors");
  assert.match(body, /component\.statusChanged\.connect\(function \(\)[\s\S]*if \(component\.status === Component\.Ready\)[\s\S]*instantiateAndOpen\(\)/, "openWidgetSettings must wait for async component readiness");
}

function testBarServiceEnumerationHelpersExecuteFiltersAndOrdering() {
  const getAllWidgetInstances = qmlFunction("getAllWidgetInstances", "widgetId", "screenName", "section");
  const getWidgetWithMetadata = qmlFunction("getWidgetWithMetadata", "widgetId", "screenName", "section");
  const getWidgetsBySection = qmlFunction("getWidgetsBySection", "section", "screenName");
  const getAllRegisteredWidgets = qmlFunction("getAllRegisteredWidgets");
  const hasWidget = qmlFunction("hasWidget", "widgetId", "section", "screenName");
  const leftClock = { widgetId: "Clock", section: "left", screen: { name: "eDP-1" } };
  const leftVolume = { widgetId: "Volume", section: "left", screen: { name: "eDP-1" } };
  const rightClock = { widgetId: "Clock", section: "right", screen: { name: "HDMI-A-1" } };
  const ctx = {
    widgetInstances: {
      "eDP-1|left|Clock|1": { screenName: "eDP-1", section: "left", widgetId: "Clock", index: 1, instance: leftClock },
      "eDP-1|left|Volume|0": { screenName: "eDP-1", section: "left", widgetId: "Volume", index: 0, instance: leftVolume },
      "HDMI-A-1|right|Clock|0": { screenName: "HDMI-A-1", section: "right", widgetId: "Clock", index: 0, instance: rightClock },
    },
  };
  ctx.getWidgetWithMetadata = (...args) => getWidgetWithMetadata(ctx, ...args);

  assert.deepEqual(getAllWidgetInstances(ctx, "Clock", null, null), [leftClock, rightClock], "getAllWidgetInstances must filter by widget id");
  assert.deepEqual(getWidgetWithMetadata(ctx, "Clock", "eDP-1", "left").instance, leftClock, "getWidgetWithMetadata must return matching metadata");
  assert.deepEqual(getWidgetsBySection(ctx, "left", "eDP-1"), [leftVolume, leftClock], "getWidgetsBySection must sort instances by registered index");
  assert.equal(hasWidget(ctx, "Clock", "right", "HDMI-A-1"), true, "hasWidget must find matching widgets");
  assert.equal(hasWidget(ctx, "Clock", "left", "HDMI-A-1"), false, "hasWidget must honor section filters");
  assert.deepEqual(getAllRegisteredWidgets(ctx).map(widget => widget.key).sort(), Object.keys(ctx.widgetInstances).sort(), "getAllRegisteredWidgets must expose registry keys");
}

function testBarServiceDirectionHelpersExecutePositions() {
  const getPillDirection = qmlFunction("getPillDirection", "widgetInstance");
  const getTooltipDirection = qmlFunction("getTooltipDirection");
  const getContextMenuPosition = qmlFunction("getContextMenuPosition", "anchorItem", "menuWidth", "menuHeight");
  const ctx = {
    Logger: { e() {}, w() {} },
    Settings: { data: { bar: { position: "left" } } },
    Style: { marginM: 8, barHeight: 32 },
  };
  const anchor = { width: 40, height: 20 };

  assert.equal(getPillDirection(ctx, { section: "left" }), true, "left section pills must point inward");
  assert.equal(getPillDirection(ctx, { section: "right" }), false, "right section pills must point inward");
  assert.equal(getPillDirection(ctx, { section: "center", sectionWidgetIndex: 0, sectionWidgetsCount: 4 }), false, "first half center pills must point left");
  assert.equal(getPillDirection(ctx, { section: "center", sectionWidgetIndex: 3, sectionWidgetsCount: 4 }), true, "second half center pills must point right");
  assert.equal(getTooltipDirection(ctx), "right", "left bars must show tooltips to the right");
  assert.deepEqual(getContextMenuPosition(ctx, anchor, 100, 50), { x: 48, y: -15 }, "left bars must place menus to the right of anchors");

  ctx.Settings.data.bar.position = "bottom";
  assert.equal(getTooltipDirection(ctx), "top", "bottom bars must show tooltips above");
  assert.deepEqual(getContextMenuPosition(ctx, anchor, 100, 50), { x: -30, y: -58 }, "bottom bars must place menus above anchors");
  assert.deepEqual(getContextMenuPosition(ctx, null, 100, 50), { x: 0, y: 0 }, "missing anchors must fail closed");
}

const tests = [
  testBarServiceRegistrationAndLookupHelpers,
  testBarServiceWidgetEnumerationHelpers,
  testBarServiceDirectionAndContextMenuHelpers,
  testBarServiceWidgetSettingsDialogWiring,
  testBarServiceEnumerationHelpersExecuteFiltersAndOrdering,
  testBarServiceDirectionHelpersExecutePositions,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
