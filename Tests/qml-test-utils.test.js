#!/usr/bin/env node

const assert = require("assert/strict");
const { extractComponentBlocks, extractFunctionBody, extractHandlerBlock } = require("./qml-test-utils");

function testComponentExtractionIgnoresCommentsAndStrings() {
  const source = `
// NButton { commented: true }
property string decoy: "NButton { string }"
property string multilineDecoy: \`
NButton { template: true }
\${condition ? { text: \`NButton { nested: true }\` } : ""}
\`
NButton
{
  property var closingBracePattern: /}/
  property var returnedPattern: function() { return /}/ }
  property var arrowPattern: value => /}/
  text: "real { button }"
}
`;
  const blocks = extractComponentBlocks(source, "NButton");
  assert.equal(blocks.length, 1);
  assert.match(blocks[0], /closingBracePattern: \/}\//);
  assert.match(blocks[0], /text: "real \{ button \}"/);
}

function testHandlerExtractionIgnoresCommentedAndStringDecoys() {
  const source = `
// onClicked: { commented() }
property string decoy: "onClicked: { string }"
property string multilineDecoy: \`
onClicked: { template() }
\${condition ? { text: \`onClicked: { nested() }\` } : ""}
\`
onClicked: action => {
  const closingBracePattern = /}/
  const returnedPattern = function() { return /}/ }
  const arrowPattern = value => /}/
  dispatch(action)
}
`;
  const handler = extractHandlerBlock(source, "onClicked");
  assert.match(handler, /dispatch\(action\)/);
  assert.doesNotMatch(handler, /commented/);
}

function testComponentExtractionMasksNestedMultilineTemplateInterpolation() {
  const source = [
    "property string decoy: `",
    "${condition ? { value: 1 } : `",
    "NButton { decoy: true }",
    "`}",
    "`",
    "NButton {",
    "  objectName: \"realButton\"",
    "}",
  ].join("\n");

  const blocks = extractComponentBlocks(source, "NButton");
  assert.equal(blocks.length, 1);
  assert.match(blocks[0], /realButton/);
}

function testHandlerExtractionMasksNestedMultilineTemplateInterpolation() {
  const source = [
    "property string decoy: `",
    "${condition ? { value: 1 } : `",
    "onClicked: { decoy() }",
    "`}",
    "`",
    "onClicked: {",
    "  dispatchRealAction()",
    "}",
  ].join("\n");

  const handler = extractHandlerBlock(source, "onClicked");
  assert.match(handler, /dispatchRealAction\(\)/);
  assert.doesNotMatch(handler, /decoy/);
}

function testTemplateInterpolationMasksRegexBeforeNestedTemplate() {
  const source = [
    "property string decoy: `",
    "${value => /}/.test(value) ? `",
    "NButton { decoy: true }",
    "` : \"\"}",
    "`",
    "NButton {",
    "  objectName: \"realButton\"",
    "}",
  ].join("\n");

  const blocks = extractComponentBlocks(source, "NButton");
  assert.equal(blocks.length, 1);
  assert.match(blocks[0], /realButton/);
}

function testFunctionExtractionIgnoresStringBraces() {
  const body = extractFunctionBody('function target() { return "}"; const sentinel = true; }', "target");
  assert.match(body, /const sentinel = true/);
  assert.equal(body, '{ return "}"; const sentinel = true; }');
}

function testComponentExtractionHandlesRegexLiteralAfterReturn() {
  const source = `
NButton {
  function closingBracePattern() {
    return /}/
  }
  objectName: "afterRegex"
}
`;

  const blocks = extractComponentBlocks(source, "NButton");
  assert.equal(blocks.length, 1);
  assert.match(blocks[0], /afterRegex/);
}

function testHandlerExtractionHandlesRegexLiteralAfterArrow() {
  const source = `
onClicked: {
  const matches = values.filter(value => /}/.test(value))
  dispatch(matches)
}
`;

  const handler = extractHandlerBlock(source, "onClicked");
  assert.match(handler, /dispatch\(matches\)/);
}

for (const test of [
  testComponentExtractionIgnoresCommentsAndStrings,
  testHandlerExtractionIgnoresCommentedAndStringDecoys,
  testComponentExtractionMasksNestedMultilineTemplateInterpolation,
  testHandlerExtractionMasksNestedMultilineTemplateInterpolation,
  testTemplateInterpolationMasksRegexBeforeNestedTemplate,
  testFunctionExtractionIgnoresStringBraces,
  testComponentExtractionHandlesRegexLiteralAfterReturn,
  testHandlerExtractionHandlesRegexLiteralAfterArrow,
]) {
  test();
  console.log(`ok ${test.name}`);
}
