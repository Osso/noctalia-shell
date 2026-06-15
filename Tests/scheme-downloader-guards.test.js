#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testSchemeDownloaderCacheAndFetchEntryPoints() {
  const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml");
  const loadBody = extractFunctionBody(source, "loadSchemesFromCache");
  const saveBody = extractFunctionBody(source, "saveSchemesToCache");
  const fetchBody = extractFunctionBody(source, "fetchAvailableSchemes");
  const apiBody = extractFunctionBody(source, "fetchAvailableSchemesFromAPI");

  assert.match(loadBody, /const cacheData = ShellState\.getColorSchemesList\(\)/, "loadSchemesFromCache must read ShellState cache");
  assert.match(loadBody, /const cachedSchemes = cacheData\.schemes \|\| \[\]/, "loadSchemesFromCache must tolerate missing cached schemes");
  assert.match(loadBody, /if \(!cachedTimestamp \|\| \(now >= cachedTimestamp \+ schemesCacheUpdateFrequency\)\)/, "loadSchemesFromCache must detect missing or expired cache");
  assert.match(loadBody, /timeSinceLastFetch >= minApiFetchInterval[\s\S]*fetchAvailableSchemesFromAPI\(\)/, "loadSchemesFromCache must refetch expired cache outside the rate window");
  assert.match(loadBody, /availableSchemes = cachedSchemes[\s\S]*hasInitialData = true[\s\S]*fetching = false/, "loadSchemesFromCache must use cached data when available");
  assert.match(loadBody, /Logger\.e\("ColorSchemeDownload",\s*"Failed to load schemes from cache:",\s*error\)/, "loadSchemesFromCache must log cache read failures");
  assert.match(saveBody, /ShellState\.setColorSchemesList\(\{[\s\S]*schemes: availableSchemes[\s\S]*timestamp: Time\.timestamp/, "saveSchemesToCache must persist schemes and timestamp");
  assert.match(saveBody, /Logger\.e\("ColorSchemeDownload",\s*"Failed to save schemes to cache:",\s*error\)/, "saveSchemesToCache must log cache save failures");
  assert.match(fetchBody, /if \(fetching\)[\s\S]*return;/, "fetchAvailableSchemes must avoid concurrent fetches");
  assert.match(fetchBody, /typeof ShellState !== 'undefined' && ShellState\.isLoaded[\s\S]*loadSchemesFromCache\(\)/, "fetchAvailableSchemes must prefer loaded ShellState cache");
  assert.match(fetchBody, /else[\s\S]*fetchAvailableSchemesFromAPI\(\)/, "fetchAvailableSchemes must fall back to API when ShellState is unavailable");
  assert.match(apiBody, /if \(fetching\)[\s\S]*return;/, "fetchAvailableSchemesFromAPI must avoid concurrent API fetches");
  assert.match(apiBody, /timeSinceLastFetch < minApiFetchInterval[\s\S]*return;/, "fetchAvailableSchemesFromAPI must rate-limit repeated fetches");
  assert.match(apiBody, /fetching = true[\s\S]*lastApiFetchTime = now[\s\S]*downloadError = ""/, "fetchAvailableSchemesFromAPI must set fetch state before requesting");
  assert.match(apiBody, /response\[i\]\.type === "dir"[\s\S]*"name": response\[i\]\.name[\s\S]*"path": response\[i\]\.path[\s\S]*"url": response\[i\]\.url/, "fetchAvailableSchemesFromAPI must keep directory entries as schemes");
  assert.match(apiBody, /availableSchemes = schemes[\s\S]*hasInitialData = true[\s\S]*saveSchemesToCache\(\)/, "fetchAvailableSchemesFromAPI must publish and cache successful results");
  assert.match(apiBody, /xhr\.status === 403[\s\S]*ShellState\.getColorSchemesList\(\)/, "fetchAvailableSchemesFromAPI must try cached schemes on rate limit");
  assert.match(apiBody, /xhr\.open\("GET",\s*"https:\/\/api\.github\.com\/repos\/noctalia-dev\/noctalia-colorschemes\/contents"\)/, "fetchAvailableSchemesFromAPI must request repository contents");
}

function testSchemeDownloaderTreeResolutionFallbacks() {
  const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml");
  const downloadBody = extractFunctionBody(source, "downloadScheme");
  const treeBody = extractFunctionBody(source, "getSchemeTree");
  const shaBody = extractFunctionBody(source, "getSchemeTreeWithSha");
  const directBody = extractFunctionBody(source, "getSchemeFilesDirect");
  const recursiveBody = extractFunctionBody(source, "getAllFilesRecursive");

  assert.match(downloadBody, /if \(downloading\)[\s\S]*return;/, "downloadScheme must avoid concurrent downloads");
  assert.match(downloadBody, /downloading = true[\s\S]*downloadingScheme = scheme\.name[\s\S]*downloadError = ""/, "downloadScheme must set download state");
  assert.match(downloadBody, /if \(cachedBranchSha\)[\s\S]*getSchemeTreeWithSha\(scheme,\s*cachedBranch,\s*cachedBranchSha\)/, "downloadScheme must reuse cached branch SHA");
  assert.match(downloadBody, /else if \(cachedBranch\)[\s\S]*getSchemeTree\(scheme,\s*cachedBranch\)/, "downloadScheme must reuse cached branch name");
  assert.match(downloadBody, /repoInfo\.default_branch \|\| "main"[\s\S]*cachedBranch = defaultBranch[\s\S]*getSchemeTree\(scheme,\s*defaultBranch\)/, "downloadScheme must fetch and cache default branch");
  assert.match(downloadBody, /getSchemeFilesDirect\(scheme\)/, "downloadScheme must fall back to direct file listing");
  assert.match(treeBody, /refResponse\.object \? refResponse\.object\.sha : null/, "getSchemeTree must read branch ref SHA");
  assert.match(treeBody, /cachedBranchSha = sha[\s\S]*getSchemeTreeWithSha\(scheme,\s*branch,\s*sha\)/, "getSchemeTree must cache SHA and request recursive tree");
  assert.match(treeBody, /xhr\.open\("GET",\s*"https:\/\/api\.github\.com\/repos\/noctalia-dev\/noctalia-colorschemes\/git\/refs\/heads\/" \+ branch\)/, "getSchemeTree must request the branch ref endpoint");
  assert.match(shaBody, /response\.tree && Array\.isArray\(response\.tree\)/, "getSchemeTreeWithSha must require a tree array");
  assert.match(shaBody, /item\.type === "blob" && item\.path\.startsWith\(scheme\.path \+ "\/"\)/, "getSchemeTreeWithSha must filter files under the scheme path");
  assert.match(shaBody, /"url": "https:\/\/raw\.githubusercontent\.com\/noctalia-dev\/noctalia-colorschemes\/" \+ branch \+ "\/" \+ item\.path/, "getSchemeTreeWithSha must build raw file URLs");
  assert.match(shaBody, /downloadSchemeFiles\(scheme\.name,\s*files\)/, "getSchemeTreeWithSha must pass collected files to downloader");
  assert.match(shaBody, /downloadError = I18n\.tr\("settings\.color-scheme\.download\.error\.parse-failed"/, "getSchemeTreeWithSha must report parse failures");
  assert.match(directBody, /getAllFilesRecursive\(scheme,\s*response,\s*\[\]\)/, "getSchemeFilesDirect must recurse through contents responses");
  assert.match(directBody, /downloadError = I18n\.tr\("settings\.color-scheme\.download\.error\.api-error"/, "getSchemeFilesDirect must report API failures");
  assert.match(recursiveBody, /if \(!callback\)[\s\S]*downloadSchemeFiles\(scheme\.name,\s*allFiles\)/, "getAllFilesRecursive must default to downloading collected files");
  assert.match(recursiveBody, /if \(items\.length === 0\)[\s\S]*callback\(\)[\s\S]*return;/, "getAllFilesRecursive must finish immediately for empty lists");
  assert.match(recursiveBody, /if \(item\.type === "file"\)[\s\S]*allFiles\.push\(\{[\s\S]*"path": item\.path[\s\S]*"url": item\.download_url[\s\S]*"name": item\.name/, "getAllFilesRecursive must collect file items");
  assert.match(recursiveBody, /else if \(item\.type === "dir"\)[\s\S]*pending\+\+[\s\S]*xhr\.open\("GET",\s*item\.url\)/, "getAllFilesRecursive must request directory items");
  assert.match(recursiveBody, /getAllFilesRecursive\(scheme,\s*dirResponse,\s*allFiles,\s*function \(\) \{[\s\S]*checkComplete\(\)/, "getAllFilesRecursive must recurse into directories");
}

function testSchemeDownloaderFileDownloadAndInstallChecks() {
  const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml");
  const filesBody = extractFunctionBody(source, "downloadSchemeFiles");
  const installedBody = extractFunctionBody(source, "isSchemeInstalled");
  const downloadedBody = extractFunctionBody(source, "isSchemeDownloaded");

  assert.match(filesBody, /if \(files\.length === 0\)[\s\S]*downloadError = I18n\.tr\("settings\.color-scheme\.download\.error\.no-files"\)[\s\S]*downloading = false[\s\S]*downloadingScheme = ""/, "downloadSchemeFiles must reject empty file lists");
  assert.match(filesBody, /var targetDir = ColorSchemeService\.downloadedSchemesDirectory \+ "\/" \+ schemeName/, "downloadSchemeFiles must install into downloaded schemes directory");
  assert.match(filesBody, /var downloadScript = "mkdir -p '" \+ targetDir \+ "'\\n"/, "downloadSchemeFiles must create the target directory");
  assert.match(filesBody, /if \(filePath\.startsWith\(schemeName \+ "\/"\)\)[\s\S]*relativePath = filePath\.substring\(schemeName\.length \+ 1\)/, "downloadSchemeFiles must strip scheme directory prefixes");
  assert.match(filesBody, /downloadScript \+= "curl -L -s -o '" \+ localPath \+ "' '" \+ downloadUrl \+ "' \|\| wget -q -O '" \+ localPath \+ "' '" \+ downloadUrl \+ "'\\n"/, "downloadSchemeFiles must support curl and wget downloads");
  assert.match(filesBody, /command: \["sh",\s*"-c",\s*` \+ JSON\.stringify\(downloadScript\) \+ `\]/, "downloadSchemeFiles must execute generated shell script safely through JSON stringification");
  assert.match(filesBody, /if \(exitCode === 0\)[\s\S]*pendingApplyScheme = schemeName[\s\S]*ColorSchemeService\.loadColorSchemes\(\)[\s\S]*downloading = false/, "downloadSchemeFiles must reload and mark successful downloads");
  assert.match(filesBody, /downloadError = I18n\.tr\("settings\.color-scheme\.download\.error\.download-failed"/, "downloadSchemeFiles must report failed downloads");
  assert.match(filesBody, /root\.lastStderrOutput = ""[\s\S]*downloadProcess\.destroy\(\)/, "downloadSchemeFiles must clear stderr and destroy the process");
  assert.match(filesBody, /downloadProcess\.running = true/, "downloadSchemeFiles must start the process");
  assert.match(installedBody, /for \(var i = 0; i < ColorSchemeService\.schemes\.length; i\+\+\)/, "isSchemeInstalled must scan loaded schemes");
  assert.match(installedBody, /path\.indexOf\("\/" \+ schemeName \+ "\/"\) !== -1 \|\| path\.indexOf\("\/" \+ schemeName \+ "\.json"\) !== -1/, "isSchemeInstalled must match directory and single-file schemes");
  assert.match(installedBody, /return false/, "isSchemeInstalled must fail closed");
  assert.match(downloadedBody, /path\.indexOf\(ColorSchemeService\.downloadedSchemesDirectory\) !== -1/, "isSchemeDownloaded must require downloaded directory paths");
  assert.match(downloadedBody, /return false/, "isSchemeDownloaded must fail closed");
}

function testSchemeDownloaderDeleteAndPrefetchFlow() {
  const source = readQml("Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml");
  const deleteBody = extractFunctionBody(source, "deleteScheme");
  const prefetchBody = extractFunctionBody(source, "preFetchSchemeColors");

  assert.match(deleteBody, /if \(downloading\)[\s\S]*return;/, "deleteScheme must not delete while a download is active");
  assert.match(deleteBody, /var currentScheme = Settings\.data\.colorSchemes\.predefinedScheme \|\| ""/, "deleteScheme must read the active predefined scheme");
  assert.match(deleteBody, /var deletedSchemeDisplayName = ColorSchemeService\.getBasename\(schemeName\)/, "deleteScheme must compare display names");
  assert.match(deleteBody, /var needsReset = \(currentScheme === deletedSchemeDisplayName\)/, "deleteScheme must detect deleting the active scheme");
  assert.match(deleteBody, /var targetDir = ColorSchemeService\.downloadedSchemesDirectory \+ "\/" \+ schemeName/, "deleteScheme must delete only from downloaded schemes directory");
  assert.match(deleteBody, /var deleteScript = "rm -rf '" \+ targetDir \+ "'"/, "deleteScheme must build a directory deletion script");
  assert.match(deleteBody, /if \(exitCode === 0\)[\s\S]*ToastService\.showNotice/, "deleteScheme must notify on successful deletion");
  assert.match(deleteBody, /if \(needsReset\)[\s\S]*Settings\.data\.colorSchemes\.predefinedScheme = "Noctalia \(default\)"[\s\S]*ColorSchemeService\.setPredefinedScheme\("Noctalia \(default\)"\)/, "deleteScheme must reset settings when deleting the active scheme");
  assert.match(deleteBody, /ColorSchemeService\.loadColorSchemes\(\)/, "deleteScheme must reload color schemes after deletion");
  assert.match(deleteBody, /else[\s\S]*ToastService\.showError/, "deleteScheme must notify on failed deletion");
  assert.match(deleteBody, /deleteProcess\.destroy\(\)[\s\S]*deleteProcess\.running = true/, "deleteScheme must destroy and start its process at the right lifecycle points");
  assert.match(prefetchBody, /if \(availableSchemes\.length > 0 && visible\)/, "preFetchSchemeColors must only prefetch while visible with schemes");
  assert.match(prefetchBody, /Qt\.callLater\(function \(\) \{[\s\S]*for \(var i = 0; i < availableSchemes\.length; i\+\+\)/, "preFetchSchemeColors must defer prefetch over all schemes");
  assert.match(prefetchBody, /if \(!schemeColorsCache\[scheme\.name\]\)[\s\S]*fetchSchemeColors\(scheme\)/, "preFetchSchemeColors must skip cached scheme colors");
}

const tests = [
  testSchemeDownloaderCacheAndFetchEntryPoints,
  testSchemeDownloaderTreeResolutionFallbacks,
  testSchemeDownloaderFileDownloadAndInstallChecks,
  testSchemeDownloaderDeleteAndPrefetchFlow,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
