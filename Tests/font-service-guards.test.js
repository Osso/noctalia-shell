#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testFontServiceLoadingPipeline() {
  const source = readQml("Services/System/FontService.qml");
  const initBody = extractFunctionBody(source, "init");
  const loadMonoBody = extractFunctionBody(source, "loadFontconfigMonospaceFonts");
  const loadSystemBody = extractFunctionBody(source, "loadSystemFonts");
  const processBody = extractFunctionBody(source, "processFontsAsync");
  const finalizeBody = extractFunctionBody(source, "finalizeFontLoading");

  assert.match(initBody, /Logger\.i\("Font", "Service started"\)/, "init must log startup");
  assert.match(initBody, /loadFontconfigMonospaceFonts\(\)/, "init must start fontconfig loading");
  assert.match(loadMonoBody, /fontconfigProcess\.command = \["fc-list", ":mono", "family"\]/, "loadFontconfigMonospaceFonts must query fontconfig monospace families");
  assert.match(loadMonoBody, /fontconfigProcess\.running = true/, "loadFontconfigMonospaceFonts must start the process");
  assert.match(loadSystemBody, /if \(isLoading\)\s+return;/, "loadSystemFonts must avoid concurrent loads");
  assert.match(loadSystemBody, /isLoading = true/, "loadSystemFonts must expose loading state");
  assert.match(loadSystemBody, /var fontFamilies = Qt\.fontFamilies\(\)/, "loadSystemFonts must read Qt font families");
  assert.match(loadSystemBody, /fontFamilies\.sort\(function \(a, b\)[\s\S]*return a\.localeCompare\(b\)/, "loadSystemFonts must sort families for stable order");
  assert.match(loadSystemBody, /availableFonts\.clear\(\)[\s\S]*monospaceFonts\.clear\(\)[\s\S]*displayFonts\.clear\(\)[\s\S]*fontCache = \{\}/, "loadSystemFonts must clear models and cache before reload");
  assert.match(loadSystemBody, /processFontsAsync\(fontFamilies, 0\)/, "loadSystemFonts must process from the first font");
  assert.match(processBody, /var endIndex = Math\.min\(startIndex \+ chunkSize, fontFamilies\.length\)/, "processFontsAsync must process bounded chunks");
  assert.match(processBody, /if \(!fontName \|\| fontName\.trim\(\) === ""\)\s+continue;/, "processFontsAsync must skip empty font names");
  assert.match(processBody, /availableBatch\.push\(fontObj\)/, "processFontsAsync must include every valid font in available fonts");
  assert.match(processBody, /if \(isMonospaceFont\(fontName\)\)[\s\S]*monospaceBatch\.push\(fontObj\)/, "processFontsAsync must classify monospace fonts");
  assert.match(processBody, /if \(isDisplayFont\(fontName\)\)[\s\S]*displayBatch\.push\(fontObj\)/, "processFontsAsync must classify display fonts");
  assert.match(processBody, /batchAppendToModel\(availableFonts, availableBatch\)[\s\S]*batchAppendToModel\(monospaceFonts, monospaceBatch\)[\s\S]*batchAppendToModel\(displayFonts, displayBatch\)/, "processFontsAsync must batch append all model updates");
  assert.match(processBody, /if \(hasMore\)[\s\S]*Qt\.callLater\(function \(\)[\s\S]*processFontsAsync\(fontFamilies, endIndex\)/, "processFontsAsync must defer remaining chunks");
  assert.match(processBody, /else[\s\S]*finalizeFontLoading\(\)/, "processFontsAsync must finalize after the last chunk");
  assert.match(finalizeBody, /fontsLoaded = true[\s\S]*isLoading = false/, "finalizeFontLoading must mark loading complete");
}

function testFontServiceClassificationAndCaching() {
  const source = readQml("Services/System/FontService.qml");
  const monospaceBody = extractFunctionBody(source, "isMonospaceFont");
  const displayBody = extractFunctionBody(source, "isDisplayFont");

  assert.match(monospaceBody, /if \(fontCache\.hasOwnProperty\(fontName\)\)[\s\S]*return fontCache\[fontName\]\.isMonospace/, "isMonospaceFont must use cached classification");
  assert.match(monospaceBody, /if \(fontconfigMonospaceFonts\.hasOwnProperty\(fontName\)\)[\s\S]*result = true/, "isMonospaceFont must trust fontconfig monospace data");
  assert.match(monospaceBody, /lowerFontName\.includes\("mono"\) \|\| lowerFontName\.includes\("monospace"\)/, "isMonospaceFont must fall back to monospace naming patterns");
  assert.match(monospaceBody, /if \(!fontCache\[fontName\]\)[\s\S]*fontCache\[fontName\] = \{\}/, "isMonospaceFont must initialize cache entries");
  assert.match(monospaceBody, /fontCache\[fontName\]\.isMonospace = result[\s\S]*return result/, "isMonospaceFont must cache and return the result");
  assert.match(displayBody, /if \(fontCache\.hasOwnProperty\(fontName\) && fontCache\[fontName\]\.hasOwnProperty\('isDisplay'\)\)[\s\S]*return fontCache\[fontName\]\.isDisplay/, "isDisplayFont must use cached display classification");
  assert.match(displayBody, /var lowerFontName = fontName\.toLowerCase\(\)/, "isDisplayFont must normalize font names");
  assert.match(displayBody, /lowerFontName\.includes\("display"\) \|\| lowerFontName\.includes\("headline"\) \|\| lowerFontName\.includes\("title"\)/, "isDisplayFont must identify display naming patterns");
  assert.match(displayBody, /if \(!fontCache\[fontName\]\)[\s\S]*fontCache\[fontName\] = \{\}/, "isDisplayFont must initialize cache entries");
  assert.match(displayBody, /fontCache\[fontName\]\.isDisplay = result[\s\S]*return result/, "isDisplayFont must cache and return the result");
}

function testFontServiceModelUtilitiesAndSearch() {
  const source = readQml("Services/System/FontService.qml");
  const batchBody = extractFunctionBody(source, "batchAppendToModel");
  const sortBody = extractFunctionBody(source, "sortModel");
  const fallbackBody = extractFunctionBody(source, "addFallbackFonts");
  const searchBody = extractFunctionBody(source, "searchFonts");

  assert.match(batchBody, /for \(var i = 0; i < items\.length; i\+\+\)[\s\S]*model\.append\(items\[i\]\)/, "batchAppendToModel must append every item");
  assert.match(sortBody, /for \(var i = 0; i < model\.count; i\+\+\)[\s\S]*fontsArray\.push\(\{[\s\S]*"key": model\.get\(i\)\.key[\s\S]*"name": model\.get\(i\)\.name/, "sortModel must snapshot model rows");
  assert.match(sortBody, /fontsArray\.sort\(function \(a, b\)[\s\S]*return a\.name\.localeCompare\(b\.name\)/, "sortModel must sort by display name");
  assert.match(sortBody, /model\.clear\(\)[\s\S]*batchAppendToModel\(model, fontsArray\)/, "sortModel must rebuild through batch append");
  assert.match(fallbackBody, /var existingFonts = \{\}[\s\S]*existingFonts\[model\.get\(i\)\.name\] = true/, "addFallbackFonts must build an existing-font lookup");
  assert.match(fallbackBody, /if \(!existingFonts\[fontName\]\)[\s\S]*toAdd\.push\(\{[\s\S]*"key": fontName[\s\S]*"name": fontName/, "addFallbackFonts must only add missing fallback fonts");
  assert.match(fallbackBody, /if \(toAdd\.length > 0\)[\s\S]*batchAppendToModel\(model, toAdd\)[\s\S]*sortModel\(model\)/, "addFallbackFonts must append and sort when needed");
  assert.match(searchBody, /if \(!query \|\| query\.trim\(\) === ""\)\s+return availableFonts/, "searchFonts must return full model for blank queries");
  assert.match(searchBody, /var lowerQuery = query\.toLowerCase\(\)/, "searchFonts must normalize queries");
  assert.match(searchBody, /for \(var i = 0; i < availableFonts\.count; i\+\+\)[\s\S]*var font = availableFonts\.get\(i\)/, "searchFonts must scan available fonts");
  assert.match(searchBody, /if \(font\.name\.toLowerCase\(\)\.includes\(lowerQuery\)\)[\s\S]*results\.push\(font\)/, "searchFonts must include matching fonts");
  assert.match(searchBody, /return results/, "searchFonts must return filtered results");
}

const tests = [
  testFontServiceLoadingPipeline,
  testFontServiceClassificationAndCaching,
  testFontServiceModelUtilitiesAndSearch,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
