#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/Theming/TemplateRegistry.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  const callArgs = argNames.length > 0 ? `, ${argNames.join(", ")}` : "";
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx${callArgs}); }`);
}

function qmlFunctionWithLiteralBody(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  const callArgs = argNames.length > 0 ? `, ${argNames.join(", ")}` : "";
  return new Function("ctx", ...argNames, "with (ctx) { return (function(" + argNames.join(", ") + ") " + body + ").call(ctx" + callArgs + "); }");
}

function createContext() {
  const buildUserTemplatesToml = qmlFunction("buildUserTemplatesToml");
  const execCalls = [];
  const logs = [];
  const ctx = {
    Quickshell: {
      shellDir: "/shell",
      execDetached(args) {
        execCalls.push(args);
      },
    },
    Settings: {
      cacheDir: "/cache/",
      configDir: "/config/",
    },
    fileCheckProcess: {
      command: [],
      running: false,
    },
    Logger: {
      d(...args) {
        logs.push(args);
      },
    },
  };
  ctx.execCalls = execCalls;
  ctx.logs = logs;
  ctx.buildUserTemplatesToml = () => buildUserTemplatesToml(ctx);
  return ctx;
}

function testTemplateRegistryBuildsUserTemplateTomlSkeleton() {
  const buildUserTemplatesToml = qmlFunction("buildUserTemplatesToml");
  const ctx = createContext();

  assert.equal(buildUserTemplatesToml(ctx), [
    "[config]",
    "",
    "[templates]",
    "",
    "# User-defined templates",
    "# Add your custom templates below",
    "# Example:",
    "# [templates.myapp]",
    "# input_path = \"~/.config/noctalia/templates/myapp.css\"",
    "# output_path = \"~/.config/myapp/theme.css\"",
    "# post_hook = \"myapp --reload-theme\"",
    "",
    "# Remove this section and add your own templates",
    "#[templates.placeholder]",
    "#input_path = \"/shell/Assets/MatugenTemplates/noctalia.json\"",
    "#output_path = \"/cache/placeholder.json\"",
    "",
  ].join("\n") + "\n");
}

function testTemplateRegistryWriteChecksForExistingUserTemplatesFile() {
  const writeUserTemplatesToml = qmlFunction("writeUserTemplatesToml");
  const ctx = createContext();

  writeUserTemplatesToml(ctx);

  assert.deepEqual(ctx.fileCheckProcess.command, ["test", "-f", "/config/user-templates.toml"]);
  assert.equal(ctx.fileCheckProcess.running, true);
}

function testTemplateRegistryDoWriteCreatesDirectoryAndWritesEscapedHeredoc() {
  const doWriteUserTemplatesToml = qmlFunctionWithLiteralBody("doWriteUserTemplatesToml");
  const ctx = createContext();
  ctx.Settings.configDir = "/config/with'quote/";

  doWriteUserTemplatesToml(ctx);

  assert.deepEqual(ctx.execCalls[0], ["mkdir", "-p", "/config/with'quote/"]);
  assert.equal(ctx.execCalls[1][0], "sh");
  assert.equal(ctx.execCalls[1][1], "-c");
  assert.match(ctx.execCalls[1][2], /^cat > '\/config\/with'\\''quote\/user-templates\.toml' << 'EOF'\n/);
  assert.match(ctx.execCalls[1][2], /\[templates\]\n/);
  assert.match(ctx.execCalls[1][2], /EOF\n$/);
  assert.deepEqual(ctx.logs[0], ["TemplateRegistry", "User templates config written to:", "/config/with'quote/user-templates.toml"]);
}

const tests = [
  testTemplateRegistryBuildsUserTemplateTomlSkeleton,
  testTemplateRegistryWriteChecksForExistingUserTemplatesFile,
  testTemplateRegistryDoWriteCreatesDirectoryAndWritesEscapedHeredoc,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
