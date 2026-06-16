#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Modules/Panels/Launcher/Plugins/CalculatorPlugin.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function testCalculatorPluginEvaluateExpressionComputesAndRoundsMath() {
  const evaluateExpression = qmlFunction("evaluateExpression", "expr");

  assert.equal(evaluateExpression({}, "1 + 2 * 3"), 7);
  assert.equal(evaluateExpression({}, "(10 - 4) / 3"), 2);
  assert.equal(evaluateExpression({}, "0.1 + 0.2"), 0.3);
  assert.equal(evaluateExpression({}, "11 % 4"), 3);
}

function testCalculatorPluginEvaluateExpressionRejectsUnsafeCharacters() {
  const evaluateExpression = qmlFunction("evaluateExpression", "expr");

  assert.throws(() => evaluateExpression({}, "process.exit()"), /Invalid characters in expression/);
  assert.throws(() => evaluateExpression({}, "2 + abc"), /Invalid characters in expression/);
}

function testCalculatorPluginEvaluateExpressionRejectsEmptyInvalidOrNonFiniteResults() {
  const evaluateExpression = qmlFunction("evaluateExpression", "expr");

  assert.throws(() => evaluateExpression({}, "   "), /Empty expression/);
  assert.throws(() => evaluateExpression({}, "1 +"), /Invalid mathematical expression/);
  assert.throws(() => evaluateExpression({}, "1 / 0"), /Invalid mathematical expression/);
}

function testCalculatorPluginIsMathExpressionAcceptsOnlyMathCharacters() {
  const isMathExpression = qmlFunction("isMathExpression", "expr");

  assert.equal(isMathExpression({}, "1 + 2 * (3 - 4.5) / 6 % 2"), true);
  assert.equal(isMathExpression({}, "sqrt(4)"), false);
  assert.equal(isMathExpression({}, "1 + alert(2)"), false);
  assert.equal(isMathExpression({}, ">1 + 2"), false);
}

const tests = [
  testCalculatorPluginEvaluateExpressionComputesAndRoundsMath,
  testCalculatorPluginEvaluateExpressionRejectsUnsafeCharacters,
  testCalculatorPluginEvaluateExpressionRejectsEmptyInvalidOrNonFiniteResults,
  testCalculatorPluginIsMathExpressionAcceptsOnlyMathCharacters,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
