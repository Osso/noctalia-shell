#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assertPropertyType(relativePath, propertyName, expectedType) {
  const source = readQml(relativePath);
  const declaration = new RegExp(`\\bproperty\\s+${expectedType}\\s+${propertyName}\\b`);

  assert.match(source, declaration, `${relativePath} must declare ${propertyName} as ${expectedType}`);
}

function testSliderCutoutColorsAreTyped() {
  const sliderFiles = [
    "Widgets/NSlider.qml",
    "Widgets/NColorSlider.qml",
    "Widgets/NValueSlider.qml",
  ];

  for (const sliderFile of sliderFiles) {
    assertPropertyType(sliderFile, "cutoutColor", "color");
  }
}

function testPopupAnchorItemsAreTyped() {
  const popupFiles = [
    "Widgets/NPopupContextMenu.qml",
    "Modules/Bar/Extras/TrayMenu.qml",
  ];

  for (const popupFile of popupFiles) {
    assertPropertyType(popupFile, "anchorItem", "Item");
  }
}

function testTooltipTargetItemIsTyped() {
  assertPropertyType("Modules/Tooltip/Tooltip.qml", "targetItem", "Item");
}

function testTooltipServiceCallsUseTargetItemFirst() {
  const callSiteFiles = [
    "Widgets/NColorSlider.qml",
    "Widgets/NColorPickerDialog.qml",
  ];

  for (const callSiteFile of callSiteFiles) {
    const source = readQml(callSiteFile);
    assert.doesNotMatch(source, /TooltipService\.show\(screen,/, `${callSiteFile} must pass the target item as the first TooltipService.show argument`);
  }
}

function testTooltipServiceTracksTypedTooltipInstances() {
  const tooltipServiceFile = "Services/UI/TooltipService.qml";

  assertPropertyType(tooltipServiceFile, "activeTooltip", "Tooltip");
  assertPropertyType(tooltipServiceFile, "pendingTooltip", "Tooltip");
}

const tests = [
  testSliderCutoutColorsAreTyped,
  testPopupAnchorItemsAreTyped,
  testTooltipTargetItemIsTyped,
  testTooltipServiceCallsUseTargetItemFirst,
  testTooltipServiceTracksTypedTooltipInstances,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
