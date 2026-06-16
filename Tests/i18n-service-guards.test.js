#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testI18nLanguageDiscoveryGuards() {
  const source = readQml("Commons/I18n.qml");
  const scanBody = extractFunctionBody(source, "scanAvailableLanguages");
  const parseBody = extractFunctionBody(source, "parseDirectoryListing");
  const detectBody = extractFunctionBody(source, "detectLanguage");

  assert.match(scanBody, /Logger\.d\("I18n", "Scanning for available translation files\.\.\."\)/, "scanAvailableLanguages must log directory scans");
  assert.match(scanBody, /directoryScanner\.running = true/, "scanAvailableLanguages must start the scanner process");
  assert.match(parseBody, /if \(!output \|\| output\.trim\(\) === ""\)[\s\S]*availableLanguages = \["en"\][\s\S]*detectLanguage\(\)[\s\S]*return;/, "parseDirectoryListing must fallback on empty output");
  assert.match(parseBody, /const entries = output\.trim\(\)\.split\('\\n'\)/, "parseDirectoryListing must parse newline-separated entries");
  assert.match(parseBody, /entry\.endsWith\('\.json'\)/, "parseDirectoryListing must only accept JSON translation files");
  assert.match(parseBody, /langCode\.length >= 2 && langCode\.length <= 5/, "parseDirectoryListing must reject malformed language codes");
  assert.match(parseBody, /languages\.sort\(\)[\s\S]*languages\.unshift\("en"\)/, "parseDirectoryListing must keep english first when available");
  assert.match(parseBody, /catch \(e\)[\s\S]*Logger\.e\("I18n", `Failed to parse directory listing: \$\{e\}`\)[\s\S]*availableLanguages = \["en"\][\s\S]*detectLanguage\(\)/, "parseDirectoryListing must fail closed to english");
  assert.match(detectBody, /if \(availableLanguages\.length === 0\)[\s\S]*Logger\.w\("I18n", "No available languages found"\)[\s\S]*return;/, "detectLanguage must stop when no languages are available");
  assert.match(detectBody, /Qt\.locale\(\)\.uiLanguages\.length/, "detectLanguage must inspect Qt preferred languages");
  assert.match(detectBody, /availableLanguages\.includes\(fullUserLang\)[\s\S]*detectedLang = fullUserLang/, "detectLanguage must prefer exact locale matches");
  assert.match(detectBody, /const shortUserLang = fullUserLang\.substring\(0, 2\)[\s\S]*availableLanguages\.includes\(shortUserLang\)/, "detectLanguage must fallback to short locale matches");
  assert.match(detectBody, /detectedLang = availableLanguages\.includes\("en"\) \? "en" : availableLanguages\[0\]/, "detectLanguage must fallback to english or the first language");
  assert.match(detectBody, /Settings\.data\.general\.language !== ""[\s\S]*setLanguage\(Settings\.data\.general\.language\)/, "detectLanguage must prefer configured languages");
  assert.match(detectBody, /setLanguage\(root\.systemDetectedLangCode, root\.fullLocaleCode\)/, "detectLanguage must apply detected locale when no configured language is valid");
}

function testI18nLoadingAndLookupGuards() {
  const source = readQml("Commons/I18n.qml");
  const setBody = extractFunctionBody(source, "setLanguage");
  const loadBody = extractFunctionBody(source, "loadTranslations");
  const hasBody = extractFunctionBody(source, "hasTranslation");
  const keysBody = extractFunctionBody(source, "getAllKeys");
  const reloadBody = extractFunctionBody(source, "reload");

  assert.match(setBody, /if \(typeof fullLocale === "undefined"\)[\s\S]*fullLocale = newLangCode/, "setLanguage must default full locale to language code");
  assert.match(setBody, /newLangCode !== langCode && availableLanguages\.includes\(newLangCode\)/, "setLanguage must only reload changed available languages");
  assert.match(setBody, /langCode = newLangCode[\s\S]*fullLocaleCode = fullLocale[\s\S]*locale = Qt\.locale\(fullLocale\)/, "setLanguage must update language and locale state together");
  assert.match(setBody, /languageChanged\(langCode\)[\s\S]*loadTranslations\(\)/, "setLanguage must notify and reload after language changes");
  assert.match(setBody, /Logger\.w\("I18n", `Language "\$\{newLangCode\}" is not available`\)/, "setLanguage must warn for unavailable languages");
  assert.match(loadBody, /if \(langCode === ""\)\s+return;/, "loadTranslations must no-op before language selection");
  assert.match(loadBody, /fileView\.path = filePath[\s\S]*isLoaded = false/, "loadTranslations must point FileView at the selected file and clear loaded state");
  assert.match(loadBody, /langCode !== "en" && availableLanguages\.includes\("en"\)[\s\S]*fallbackFileView\.path = `file:\/\/\$\{Quickshell\.shellDir\}\/Assets\/Translations\/en\.json`/, "loadTranslations must load english fallback for non-english languages");
  assert.match(hasBody, /if \(!isLoaded\)\s+return false;/, "hasTranslation must return false until translations are loaded");
  assert.match(hasBody, /const keys = key\.split\("\."\)[\s\S]*var value = translations/, "hasTranslation must walk nested translation keys");
  assert.match(hasBody, /return typeof value === "string"/, "hasTranslation must only accept leaf strings");
  assert.match(keysBody, /if \(typeof obj === "undefined"\)\s+obj = translations/, "getAllKeys must default to active translations");
  assert.match(keysBody, /const fullKey = prefix \? `\$\{prefix\}\.\$\{key\}` : key/, "getAllKeys must preserve nested key paths");
  assert.match(keysBody, /keys = keys\.concat\(getAllKeys\(value, fullKey\)\)/, "getAllKeys must recurse into nested objects");
  assert.match(keysBody, /keys\.push\(fullKey\)/, "getAllKeys must return string leaves");
  assert.match(reloadBody, /Logger\.d\("I18n", "Reloading translations"\)[\s\S]*loadTranslations\(\)/, "reload must delegate to loadTranslations");
}

function testI18nTranslationAndPluralGuards() {
  const source = readQml("Commons/I18n.qml");
  const trBody = extractFunctionBody(source, "tr");
  const trpBody = extractFunctionBody(source, "trp");

  assert.match(trBody, /if \(typeof interpolations === "undefined"\)\s+interpolations = \{\}/, "tr must default interpolations to an object");
  assert.match(trBody, /if \(!isLoaded\)[\s\S]*return key;/, "tr must return the key before translations are loaded");
  assert.match(trBody, /const keys = key\.split\("\."\)/, "tr must support nested translation keys");
  assert.match(trBody, /var value = translations[\s\S]*var notFound = false/, "tr must search active translations first");
  assert.match(trBody, /notFound && availableLanguages\.includes\("en"\) && langCode !== "en"[\s\S]*value = fallbackTranslations/, "tr must fallback to english when active language misses a key");
  assert.match(trBody, /return `## \$\{key\} ##`/, "tr must make missing fallback keys visible");
  assert.match(trBody, /value = `<i>\$\{value\}<\/i>`/, "tr must mark fallback strings as untranslated");
  assert.match(trBody, /if \(typeof value !== "string"\)[\s\S]*return key;/, "tr must reject non-string translation values");
  assert.match(trBody, /new RegExp\(`\\\\\{\$\{placeholder\}\\\\\}`, 'g'\)[\s\S]*result = result\.replace\(regex, interpolations\[placeholder\]\)/, "tr must replace all matching interpolation placeholders");
  assert.match(trpBody, /if \(typeof defaultSingular === "undefined"\)\s+defaultSingular = ""/, "trp must default singular fallback text");
  assert.match(trpBody, /if \(typeof defaultPlural === "undefined"\)\s+defaultPlural = ""/, "trp must default plural fallback text");
  assert.match(trpBody, /const pluralKey = count === 1 \? key : `\$\{key\}_plural`/, "trp must choose singular or plural keys from count");
  assert.match(trpBody, /"count": count/, "trp must inject count into interpolations");
  assert.match(trpBody, /for \(var prop in interpolations\)[\s\S]*finalInterpolations\[prop\] = interpolations\[prop\]/, "trp must preserve caller interpolations");
  assert.match(trpBody, /return tr\(pluralKey, finalInterpolations\)/, "trp must delegate final translation lookup");
}

const tests = [
  testI18nLanguageDiscoveryGuards,
  testI18nLoadingAndLookupGuards,
  testI18nTranslationAndPluralGuards,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
