#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testTemplateProcessorEntryPointsBuildExpectedPipelines() {
  const source = readQml("Services/Theming/TemplateProcessor.qml");
  const wallpaperBody = extractFunctionBody(source, "processWallpaperColors");
  const predefinedBody = extractFunctionBody(source, "processPredefinedScheme");
  const configBody = extractFunctionBody(source, "buildMatugenConfig");
  const scriptBody = extractFunctionBody(source, "buildMatugenScript");

  assert.match(wallpaperBody, /const content = buildMatugenConfig\(\)/, "processWallpaperColors must build a matugen config");
  assert.match(wallpaperBody, /if \(!content\)\s+return;/, "processWallpaperColors must stop when no templates are enabled");
  assert.match(wallpaperBody, /wallpaperPath\.replace\(\/'\/g,\s*"'/, "processWallpaperColors must escape wallpaper paths");
  assert.match(wallpaperBody, /buildMatugenScript\(content,\s*wp,\s*mode\)/, "processWallpaperColors must delegate shell script construction");
  assert.match(wallpaperBody, /generateProcess\.generator = "matugen"/, "processWallpaperColors must label matugen failures");
  assert.match(wallpaperBody, /generateProcess\.command = \["bash",\s*"-lc",\s*script\]/, "processWallpaperColors must execute generated shell through bash");
  assert.match(predefinedBody, /handleTerminalThemes\(mode\)/, "processPredefinedScheme must install predefined terminal themes");
  assert.match(predefinedBody, /const colors = schemeData\[mode\]/, "processPredefinedScheme must select colors for the requested mode");
  assert.match(predefinedBody, /let script = processAllTemplates\(colors,\s*mode\)/, "processPredefinedScheme must process application templates");
  assert.match(predefinedBody, /script \+= buildUserTemplateCommandForPredefined\(schemeData,\s*mode\)/, "processPredefinedScheme must append user templates");
  assert.match(predefinedBody, /generateProcess\.generator = "predefined"/, "processPredefinedScheme must label predefined failures");
  assert.match(configBody, /Settings\.data\.colorSchemes\.darkMode \? "dark" : "light"/, "buildMatugenConfig must derive mode from darkMode");
  assert.match(configBody, /Settings\.data\.colorSchemes\.useWallpaperColors[\s\S]*addWallpaperTemplates\(lines,\s*mode\)/, "buildMatugenConfig must include wallpaper templates only when enabled");
  assert.match(configBody, /addApplicationTemplates\(lines,\s*mode\)/, "buildMatugenConfig must include app templates");
  assert.match(configBody, /return \["\[config\]"\]\.concat\(lines\)\.join\("\\n"\) \+ "\\n"/, "buildMatugenConfig must emit a TOML config header");
  assert.match(scriptBody, /MATUGEN_CONFIG_EOF_/, "buildMatugenScript must use a unique config heredoc delimiter");
  assert.match(scriptBody, /WALLPAPER_PATH_EOF_/, "buildMatugenScript must use a separate wallpaper heredoc delimiter");
  assert.match(scriptBody, /matugen image "\$NOCTALIA_WP_PATH" --config '\$\{pathEsc\}' --mode \$\{mode\}/, "buildMatugenScript must run matugen image with escaped config");
  assert.match(scriptBody, /buildUserTemplateCommand\("\$NOCTALIA_WP_PATH",\s*mode\)/, "buildMatugenScript must append user template commands");
}

function testTemplateProcessorRegistersWallpaperAndApplicationTemplates() {
  const source = readQml("Services/Theming/TemplateProcessor.qml");
  const wallpaperBody = extractFunctionBody(source, "addWallpaperTemplates");
  const applicationsBody = extractFunctionBody(source, "addApplicationTemplates");
  const discordEnabledBody = extractFunctionBody(source, "isDiscordClientEnabled");
  const codeEnabledBody = extractFunctionBody(source, "isCodeClientEnabled");

  assert.match(wallpaperBody, /lines\.push\("\[templates\.noctalia\]"\)/, "addWallpaperTemplates must always include Noctalia colors");
  assert.match(wallpaperBody, /Assets\/MatugenTemplates\/noctalia\.json/, "addWallpaperTemplates must use the bundled Noctalia template");
  assert.match(wallpaperBody, /Settings\.configDir \+ 'colors\.json"/, "addWallpaperTemplates must write colors.json to config dir");
  assert.match(wallpaperBody, /TemplateRegistry\.terminals\.forEach\(terminal =>/, "addWallpaperTemplates must iterate registered terminals");
  assert.match(wallpaperBody, /Settings\.data\.templates\[terminal\.id\]/, "addWallpaperTemplates must respect per-terminal settings");
  assert.match(wallpaperBody, /postHook = terminal\.postHook \|\| `\$\{TemplateRegistry\.colorsApplyScript\} \$\{terminal\.id\}`/, "addWallpaperTemplates must add a terminal post hook");
  assert.match(applicationsBody, /if \(app\.id === "discord"\)/, "addApplicationTemplates must special-case Discord clients");
  assert.match(applicationsBody, /isDiscordClientEnabled\(client\.name\)/, "addApplicationTemplates must include only detected Discord clients");
  assert.match(applicationsBody, /\[templates\.discord_\$\{client\.name\}\]/, "addApplicationTemplates must make per-client Discord templates");
  assert.match(applicationsBody, /if \(app\.id === "code"\)/, "addApplicationTemplates must special-case Code clients");
  assert.match(applicationsBody, /isCodeClientEnabled\(client\.name\)/, "addApplicationTemplates must include only detected Code clients");
  assert.match(applicationsBody, /\[templates\.code_\$\{client\.name\}\]/, "addApplicationTemplates must make per-client Code templates");
  assert.match(applicationsBody, /Settings\.data\.templates\[app\.id\]/, "addApplicationTemplates must respect normal app template settings");
  assert.match(discordEnabledBody, /availableDiscordClients\[i\]\.name === clientName[\s\S]*return true/, "isDiscordClientEnabled must match detected clients by name");
  assert.match(codeEnabledBody, /availableCodeClients\[i\]\.name === clientName[\s\S]*return true/, "isCodeClientEnabled must match detected clients by name");
}

function testTemplateProcessorBuildsPredefinedTemplateScripts() {
  const source = readQml("Services/Theming/TemplateProcessor.qml");
  const allBody = extractFunctionBody(source, "processAllTemplates");
  const discordBody = extractFunctionBody(source, "processDiscordClients");
  const codeBody = extractFunctionBody(source, "processCodeClients");
  const templateBody = extractFunctionBody(source, "processTemplate");
  const replaceBody = extractFunctionBody(source, "replaceColorsInFile");

  assert.match(allBody, /const homeDir = Quickshell\.env\("HOME"\)/, "processAllTemplates must expand home-relative paths");
  assert.match(allBody, /processDiscordClients\(app,\s*colors,\s*mode,\s*homeDir\)/, "processAllTemplates must route Discord apps to client handling");
  assert.match(allBody, /processCodeClients\(app,\s*colors,\s*mode,\s*homeDir\)/, "processAllTemplates must route Code apps to client handling");
  assert.match(allBody, /processTemplate\(app,\s*colors,\s*mode,\s*homeDir\)/, "processAllTemplates must route normal apps to generic handling");
  assert.match(discordBody, /ColorPaletteGenerator\.generatePalette\(colors,\s*Settings\.data\.colorSchemes\.darkMode,\s*false\)/, "processDiscordClients must generate a palette from scheme colors");
  assert.match(discordBody, /if \(!isDiscordClientEnabled\(client\.name\)\)\s+return;/, "processDiscordClients must skip disabled clients");
  assert.match(discordBody, /baseConfigDir = outputDir\.replace\("\/themes",\s*""\)/, "processDiscordClients must verify the base config directory");
  assert.match(discordBody, /if \[ -d "\$\{baseConfigDir\}" \]; then/, "processDiscordClients must guard missing Discord client dirs");
  assert.match(discordBody, /replaceColorsInFile\(outputPath,\s*palette\)/, "processDiscordClients must replace template colors");
  assert.match(codeBody, /if \(!isCodeClientEnabled\(client\.name\)\)\s+return;/, "processCodeClients must skip disabled clients");
  assert.match(codeBody, /client\.name === "code"[\s\S]*"~\/\.vscode"\.replace/, "processCodeClients must locate regular VS Code config");
  assert.match(codeBody, /client\.name === "codium"[\s\S]*"~\/\.vscode-oss"\.replace/, "processCodeClients must locate VSCodium config");
  assert.match(codeBody, /replaceColorsInFile\(outputPath,\s*palette\)/, "processCodeClients must replace template colors");
  assert.match(templateBody, /if \(app\.id === "emacs" && app\.checkDoomFirst\)/, "processTemplate must special-case Emacs when Doom detection is enabled");
  assert.match(templateBody, /const doomPath = app\.outputs\[0\]\.path\.replace\("~",\s*homeDir\)/, "processTemplate must read Doom Emacs output from registry metadata");
  assert.match(templateBody, /const standardPath = app\.outputs\[1\]\.path\.replace\("~",\s*homeDir\)/, "processTemplate must read standard Emacs output from registry metadata");
  assert.match(templateBody, /app\.outputs\.forEach\(output =>/, "processTemplate must iterate generic outputs");
  assert.match(templateBody, /if \(app\.postProcess\)[\s\S]*script \+= app\.postProcess\(mode\)/, "processTemplate must append post-process hooks");
  assert.match(replaceBody, /hexValue\.replace\(\/\[\.\*\+\?\^\$\{\}\(\)\|\[\\\]\\\\\]\/g,\s*'\\\\\$&'\)/, "replaceColorsInFile must regex-escape hex values");
  assert.match(replaceBody, /colors\\\\\.\$\{colorKey\}\\\\\.default\\\\\.hex_stripped/, "replaceColorsInFile must replace stripped hex placeholders");
  assert.match(replaceBody, /colors\\\\\.\$\{colorKey\}\\\\\.default\\\\\.hex/, "replaceColorsInFile must replace full hex placeholders");
}

function testTemplateProcessorHandlesTerminalAndUserTemplateCommands() {
  const source = readQml("Services/Theming/TemplateProcessor.qml");
  const escapeBody = extractFunctionBody(source, "escapeShellPath");
  const terminalsBody = extractFunctionBody(source, "handleTerminalThemes");
  const terminalTemplateBody = extractFunctionBody(source, "getTerminalColorsTemplate");
  const userBody = extractFunctionBody(source, "buildUserTemplateCommand");
  const predefinedUserBody = extractFunctionBody(source, "buildUserTemplateCommandForPredefined");
  const userConfigBody = extractFunctionBody(source, "getUserConfigPath");

  assert.match(escapeBody, /return "'" \+ path\.replace\(\/'\/g,\s*"'/, "escapeShellPath must shell-quote single quotes");
  assert.match(terminalsBody, /Object\.keys\(terminalPaths\)\.forEach\(terminal =>/, "handleTerminalThemes must iterate known terminals");
  assert.match(terminalsBody, /Settings\.data\.templates\[terminal\]/, "handleTerminalThemes must respect terminal settings");
  assert.match(terminalsBody, /mkdir -p \$\{escapeShellPath\(outputDir\)\}/, "handleTerminalThemes must create output directories safely");
  assert.match(terminalsBody, /cp -f \$\{escapeShellPath\(templatePath\)\} \$\{escapeShellPath\(outputPath\)\}/, "handleTerminalThemes must copy templates safely");
  assert.match(terminalsBody, /copyProcess\.command = \["bash",\s*"-lc",\s*commands\.join\('; '\)\]/, "handleTerminalThemes must execute terminal copy commands through bash");
  assert.match(terminalTemplateBody, /schemeNameMap\[colorScheme\] \|\| colorScheme/, "getTerminalColorsTemplate must map display names to asset dirs");
  assert.match(terminalTemplateBody, /terminal === 'kitty'[\s\S]*extension = "\.conf"/, "getTerminalColorsTemplate must use kitty conf extension");
  assert.match(terminalTemplateBody, /terminal === 'wezterm'[\s\S]*extension = "\.toml"/, "getTerminalColorsTemplate must use wezterm toml extension");
  assert.match(terminalTemplateBody, /ColorSchemeService\.schemes\[i\]/, "getTerminalColorsTemplate must search loaded schemes first");
  assert.match(terminalTemplateBody, /downloadedSchemesDirectory/, "getTerminalColorsTemplate must build downloaded fallback path");
  assert.match(terminalTemplateBody, /return preinstalledPath/, "getTerminalColorsTemplate must fall back to preinstalled path");
  assert.match(userBody, /if \(!Settings\.data\.templates\.enableUserTemplates\)\s+return ""/, "buildUserTemplateCommand must honor user template setting");
  assert.match(userBody, /input\.startsWith\("\$"\) \? `"\$\{input\}"` : `'\$\{input\.replace/, "buildUserTemplateCommand must preserve shell variables and quote paths");
  assert.match(userBody, /matugen image \$\{inputQuoted\} --config '\$\{userConfigPath\}' --mode \$\{mode\}/, "buildUserTemplateCommand must invoke matugen image");
  assert.match(predefinedUserBody, /const tempJsonPath = Settings\.cacheDir \+ "predefined-colors\.json"/, "buildUserTemplateCommandForPredefined must write a temporary color JSON");
  assert.match(predefinedUserBody, /JSON\.stringify\(\{[\s\S]*"colors": palette[\s\S]*\},\s*null,\s*2\)/, "buildUserTemplateCommandForPredefined must serialize palette JSON");
  assert.match(predefinedUserBody, /matugen json '\$\{tempJsonPathEsc\}' --config '\$\{userConfigPath\}' --mode \$\{mode\}/, "buildUserTemplateCommandForPredefined must invoke matugen json");
  assert.match(userConfigBody, /Settings\.configDir \+ "user-templates\.toml"/, "getUserConfigPath must use the Noctalia config directory");
  assert.match(userConfigBody, /\.replace\(\/'\/g,\s*"'/, "getUserConfigPath must escape single quotes");
}

function testTemplateProcessorErrorMessagesPreferProcessOutput() {
  const source = readQml("Services/Theming/TemplateProcessor.qml");
  const body = extractFunctionBody(source, "buildErrorMessage");

  assert.match(body, /stderr\.text && stderr\.text\.trim\(\) !== ""/, "buildErrorMessage must prefer stderr text");
  assert.match(body, /stdout\.text && stdout\.text\.trim\(\) !== ""/, "buildErrorMessage must fall back to stdout text");
  assert.match(body, /I18n\.tr\("toast\.theming-processor-failed\.desc-generic"\)/, "buildErrorMessage must fall back to a translated generic description");
  assert.match(body, /I18n\.tr\(`toast\.theming-processor-failed\.title-\$\{generator\}`\)/, "buildErrorMessage must build the generator-specific title key");
  assert.match(body, /return description/, "buildErrorMessage must return the selected description");
}

const tests = [
  testTemplateProcessorEntryPointsBuildExpectedPipelines,
  testTemplateProcessorRegistersWallpaperAndApplicationTemplates,
  testTemplateProcessorBuildsPredefinedTemplateScripts,
  testTemplateProcessorHandlesTerminalAndUserTemplateCommands,
  testTemplateProcessorErrorMessagesPreferProcessOutput,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
