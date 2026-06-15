#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testApplicationsPluginCategoryNamesAndLifecycleHooks() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml");
  const categoryNameBody = extractFunctionBody(source, "getCategoryName");
  const initBody = extractFunctionBody(source, "init");
  const openedBody = extractFunctionBody(source, "onOpened");
  const selectBody = extractFunctionBody(source, "selectCategory");

  assert.match(categoryNameBody, /"all": I18n\.tr\("launcher\.categories\.all"\)/, "getCategoryName must translate the all category");
  assert.match(categoryNameBody, /"WebBrowser": I18n\.tr\("launcher\.categories\.webbrowser"\)/, "getCategoryName must translate web browser categories");
  assert.match(categoryNameBody, /return names\[category\] \|\| category/, "getCategoryName must fall back to the raw category name");
  assert.match(initBody, /loadApplications\(\)/, "init must load applications");
  assert.match(openedBody, /loadApplications\(\)/, "onOpened must refresh application entries");
  assert.match(openedBody, /selectedCategory = "all"/, "onOpened must reset selected category");
  assert.match(openedBody, /isBrowsingMode = true/, "onOpened must start in browsing mode");
  assert.match(selectBody, /selectedCategory = category/, "selectCategory must store the selected category");
  assert.match(selectBody, /if \(launcher\)[\s\S]*launcher\.updateResults\(\)/, "selectCategory must refresh launcher results when available");
}

function testApplicationsPluginCategoryNormalizationAndMatching() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml");
  const categoriesBody = extractFunctionBody(source, "getAppCategories");
  const primaryBody = extractFunctionBody(source, "getAppCategory");
  const matchesBody = extractFunctionBody(source, "appMatchesCategory");
  const availableBody = extractFunctionBody(source, "getAvailableCategories");

  assert.match(categoriesBody, /if \(!app\)\s+return \[\]/, "getAppCategories must reject missing apps");
  assert.match(categoriesBody, /Array\.isArray\(app\.categories\)/, "getAppCategories must handle array categories");
  assert.match(categoriesBody, /app\.categories\.split\(';'\)\.filter/, "getAppCategories must split semicolon category strings");
  assert.match(categoriesBody, /app\.categories\.length !== undefined[\s\S]*for \(let i = 0; i < app\.categories\.length; i\+\+\)/, "getAppCategories must handle array-like category values");
  assert.match(categoriesBody, /if \(app\.Categories\)[\s\S]*app\.Categories\.split\(';'\)\.filter/, "getAppCategories must handle legacy Categories fields");
  assert.match(primaryBody, /const appCategories = getAppCategories\(app\)/, "getAppCategory must derive normalized categories first");
  assert.match(primaryBody, /if \(cat === "AudioVideo" \|\| cat === "Audio" \|\| cat === "Video"\)[\s\S]*return "AudioVideo"/, "getAppCategory must fold audio and video categories together");
  assert.match(primaryBody, /appCategories\.includes\("Chat"\) \|\| appCategories\.includes\("InstantMessaging"\)/, "getAppCategory must map chat categories");
  assert.match(primaryBody, /appCategories\.includes\("Science"\)[\s\S]*return "Education"/, "getAppCategory must map science to education");
  assert.match(primaryBody, /appCategories\.includes\("Settings"\)[\s\S]*return "System"/, "getAppCategory must map settings to system");
  assert.match(primaryBody, /for \(let priorityCat of priorityCategories\)/, "getAppCategory must use priority ordering");
  assert.match(primaryBody, /return "Misc"/, "getAppCategory must fall back to Misc for categorized apps");
  assert.match(matchesBody, /if \(category === "all"\)\s+return true/, "appMatchesCategory must include every app in all");
  assert.match(matchesBody, /const primaryCategory = getAppCategory\(app\)/, "appMatchesCategory must use the primary category");
  assert.match(matchesBody, /if \(!primaryCategory\)\s+return false/, "appMatchesCategory must reject uncategorized apps outside all");
  assert.match(matchesBody, /category === "AudioVideo"[\s\S]*appCategories\.includes\("AudioVideo"\) \|\| appCategories\.includes\("Audio"\) \|\| appCategories\.includes\("Video"\)/, "appMatchesCategory must match audio/video aliases");
  assert.match(matchesBody, /category === "Education"[\s\S]*appCategories\.includes\("Education"\) \|\| appCategories\.includes\("Science"\)/, "appMatchesCategory must match education aliases");
  assert.match(matchesBody, /category === "System"[\s\S]*appCategories\.includes\("System"\) \|\| appCategories\.includes\("Settings"\) \|\| appCategories\.includes\("Utility"\)/, "appMatchesCategory must match system aliases");
  assert.match(matchesBody, /return category === primaryCategory/, "appMatchesCategory must otherwise avoid category overlap");
  assert.match(availableBody, /const categorySet = new Set\(\)/, "getAvailableCategories must collect unique categories");
  assert.match(availableBody, /let hasAudioVideo = false[\s\S]*let hasEducation = false[\s\S]*let hasSystem = false/, "getAvailableCategories must track folded category groups");
  assert.match(availableBody, /for \(let app of entries\)/, "getAvailableCategories must scan loaded entries");
  assert.match(availableBody, /categorySet\.add\("AudioVideo"\)/, "getAvailableCategories must expose audio/video when present");
  assert.match(availableBody, /const result = \["all"\]/, "getAvailableCategories must always include all first");
  assert.match(availableBody, /if \(result\.length === 1\)[\s\S]*fallback\.push\("Misc"\)[\s\S]*return fallback/, "getAvailableCategories must return a full fallback category list when empty");
}

function testApplicationsPluginLoadingAndExecutableSearchFields() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml");
  const loadBody = extractFunctionBody(source, "loadApplications");
  const updateBody = extractFunctionBody(source, "updateAvailableCategories");
  const executableBody = extractFunctionBody(source, "getExecutableName");

  assert.match(loadBody, /if \(typeof DesktopEntries === 'undefined'\)[\s\S]*Logger\.w\("ApplicationsPlugin",\s*"DesktopEntries service not available"\)[\s\S]*return;/, "loadApplications must fail closed without DesktopEntries");
  assert.match(loadBody, /const allApps = DesktopEntries\.applications\.values \|\| \[\]/, "loadApplications must tolerate missing application values");
  assert.match(loadBody, /allApps\.filter\(app => app && !app\.noDisplay\)/, "loadApplications must hide noDisplay applications");
  assert.match(loadBody, /app\.executableName = getExecutableName\(app\)/, "loadApplications must add executable names for search");
  assert.match(loadBody, /const seen = new Set\(\)/, "loadApplications must deduplicate loaded applications");
  assert.match(loadBody, /const key = app\.id \|\| app\.name[\s\S]*if \(seen\.has\(key\)\)/, "loadApplications must deduplicate by app id or name");
  assert.match(loadBody, /entries = filtered\.filter\(app =>/, "loadApplications must store filtered entries");
  assert.match(loadBody, /updateAvailableCategories\(\)/, "loadApplications must refresh available categories");
  assert.match(updateBody, /availableCategories = getAvailableCategories\(\)/, "updateAvailableCategories must publish computed categories");
  assert.match(executableBody, /if \(!app\)\s+return ""/, "getExecutableName must reject missing apps");
  assert.match(executableBody, /app\.command && Array\.isArray\(app\.command\) && app\.command\.length > 0/, "getExecutableName must prefer command arrays");
  assert.match(executableBody, /const parts = cmd\.split\('\/'\)/, "getExecutableName must strip command paths");
  assert.match(executableBody, /return executable\.split\(' '\)\[0\]/, "getExecutableName must strip command arguments");
  assert.match(executableBody, /if \(app\.exec\)[\s\S]*app\.exec\.split\('\/'\)/, "getExecutableName must fall back to exec strings");
  assert.match(executableBody, /return app\.id\.replace\('\.desktop',\s*''\)/, "getExecutableName must fall back to desktop ids");
}

function testApplicationsPluginResultsAndActivationPaths() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml");
  const resultsBody = extractFunctionBody(source, "getResults");
  const entryBody = extractFunctionBody(source, "createResultEntry");

  assert.match(resultsBody, /if \(!entries \|\| entries\.length === 0\)\s+return \[\]/, "getResults must return no results without entries");
  assert.match(resultsBody, /isBrowsingMode = !query \|\| query\.trim\(\) === ""/, "getResults must update browsing mode from query emptiness");
  assert.match(resultsBody, /filteredEntries = entries\.filter\(app => appMatchesCategory\(app,\s*selectedCategory\)\)/, "getResults must filter by selected category");
  assert.match(resultsBody, /const favoriteApps = Settings\.data\.appLauncher\.pinnedExecs \|\| \[\]/, "getResults must read pinned apps for browsing sort");
  assert.match(resultsBody, /Settings\.data\.appLauncher\.sortByMostUsed[\s\S]*const ua = getUsageCount\(a\)[\s\S]*return ub - ua/, "getResults must sort browsed apps by usage when enabled");
  assert.match(resultsBody, /return sorted\.map\(app => createResultEntry\(app\)\)/, "getResults must wrap browsed apps as result entries");
  assert.match(resultsBody, /typeof Fuzzysort !== 'undefined'[\s\S]*Fuzzysort\.go\(query,\s*filteredEntries/, "getResults must prefer fuzzy search when available");
  assert.match(resultsBody, /"keys": \["name",\s*"comment",\s*"genericName",\s*"executableName"\]/, "getResults must search app name, metadata, and executable name");
  assert.match(resultsBody, /for \(const r of fuzzyResults\)[\s\S]*const app = r\.obj[\s\S]*favoriteApps\.includes\(getAppKey\(app\)\)/, "getResults must prioritize pinned fuzzy results");
  assert.match(resultsBody, /return fav\.concat\(nonFav\)\.map\(result => createResultEntry\(result\.obj\)\)/, "getResults must wrap fuzzy results as entries");
  assert.match(resultsBody, /const searchTerm = query\.toLowerCase\(\)/, "getResults must use lowercase fallback search");
  assert.match(resultsBody, /name\.includes\(searchTerm\) \|\| comment\.includes\(searchTerm\) \|\| generic\.includes\(searchTerm\) \|\| executable\.includes\(searchTerm\)/, "getResults must fallback-search all app metadata fields");
  assert.match(resultsBody, /slice\(0,\s*20\)\.map\(app => createResultEntry\(app\)\)/, "getResults must limit fallback results");
  assert.match(entryBody, /"appId": getAppKey\(app\)/, "createResultEntry must use stable app keys");
  assert.match(entryBody, /"name": app\.name \|\| "Unknown"/, "createResultEntry must provide a fallback name");
  assert.match(entryBody, /"icon": app\.icon \|\| "application-x-executable"/, "createResultEntry must provide a fallback icon");
  assert.match(entryBody, /launcher\.close\(\)/, "createResultEntry activation must close the launcher first");
  assert.match(entryBody, /if \(Settings\.data\.appLauncher\.sortByMostUsed\)\s+recordUsage\(app\)/, "createResultEntry activation must record usage when configured");
  assert.match(entryBody, /customLaunchPrefixEnabled && Settings\.data\.appLauncher\.customLaunchPrefix/, "createResultEntry activation must support custom launch prefixes");
  assert.match(entryBody, /Settings\.data\.appLauncher\.useApp2Unit && app\.id/, "createResultEntry activation must support app2unit launch mode");
  assert.match(entryBody, /if \(app\.runInTerminal\)[\s\S]*terminal\.concat\(app\.command\)/, "createResultEntry activation must launch terminal apps through the configured terminal");
  assert.match(entryBody, /else if \(app\.execute\)[\s\S]*app\.execute\(\)/, "createResultEntry activation must fall back to app.execute");
  assert.match(entryBody, /Logger\.w\("ApplicationsPlugin",\s*`Could not launch: \$\{app\.name\}\. No valid launch method\.`\)/, "createResultEntry activation must log unlaunchable apps");
}

function testApplicationsPluginUsageTrackingHelpers() {
  const source = readQml("Modules/Panels/Launcher/Plugins/ApplicationsPlugin.qml");
  const keyBody = extractFunctionBody(source, "getAppKey");
  const countBody = extractFunctionBody(source, "getUsageCount");
  const recordBody = extractFunctionBody(source, "recordUsage");

  assert.match(keyBody, /if \(app && app\.id\)\s+return String\(app\.id\)/, "getAppKey must prefer desktop ids");
  assert.match(keyBody, /if \(app && app\.command && app\.command\.join\)\s+return app\.command\.join\(" "\)/, "getAppKey must fall back to command strings");
  assert.match(keyBody, /return String\(app && app\.name \? app\.name : "unknown"\)/, "getAppKey must fall back to app names or unknown");
  assert.match(countBody, /const key = getAppKey\(app\)/, "getUsageCount must use stable app keys");
  assert.match(countBody, /const m = usageAdapter && usageAdapter\.counts \? usageAdapter\.counts : null/, "getUsageCount must tolerate missing usage data");
  assert.match(countBody, /if \(!m\)\s+return 0/, "getUsageCount must default missing usage maps to zero");
  assert.match(countBody, /return typeof v === 'number' && isFinite\(v\) \? v : 0/, "getUsageCount must reject non-finite usage values");
  assert.match(recordBody, /if \(!usageAdapter\.counts\)\s+usageAdapter\.counts = \(\{\}\)/, "recordUsage must initialize the usage map");
  assert.match(recordBody, /const current = getUsageCount\(app\)/, "recordUsage must read the current count");
  assert.match(recordBody, /usageAdapter\.counts\[key\] = current \+ 1/, "recordUsage must increment the app usage count");
  assert.match(recordBody, /saveTimer\.restart\(\)/, "recordUsage must debounce persistence");
}

const tests = [
  testApplicationsPluginCategoryNamesAndLifecycleHooks,
  testApplicationsPluginCategoryNormalizationAndMatching,
  testApplicationsPluginLoadingAndExecutableSearchFields,
  testApplicationsPluginResultsAndActivationPaths,
  testApplicationsPluginUsageTrackingHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
