#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testMediaServicePlayerFilteringAndVirtualPlayers() {
  const source = readQml("Services/Media/MediaService.qml");
  const body = extractFunctionBody(source, "getAvailablePlayers");

  assert.match(body, /if \(!Mpris\.players \|\| !Mpris\.players\.values\)[\s\S]*return \[\]/, "getAvailablePlayers must fail closed without MPRIS players");
  assert.match(body, /const genericBrowsers = \["firefox", "chromium", "chrome"\]/, "getAvailablePlayers must identify generic browser players");
  assert.match(body, /Settings\.data\.audio && Settings\.data\.audio\.mprisBlacklist/, "getAvailablePlayers must read the configured MPRIS blacklist");
  assert.match(body, /blacklist\.find\(b =>[\s\S]*identity\.includes\(s\)/, "getAvailablePlayers must drop blacklisted identities");
  assert.match(body, /genericBrowsers\.some\(b => identity\.includes\(b\)\)/, "getAvailablePlayers must separate generic browser players");
  assert.match(body, /title2 && \(title1\.includes\(title2\) \|\| title2\.includes\(title1\)\)/, "getAvailablePlayers must pair matching generic and specific players by title");
  assert.match(body, /let dataPlayer = genericPlayer[\s\S]*let identityPlayer = specificPlayer/, "getAvailablePlayers must keep specific player identity with generic player data by default");
  assert.match(body, /if \(scoreSpecific > scoreGeneric\)[\s\S]*dataPlayer = specificPlayer/, "getAvailablePlayers must prefer richer specific metadata when available");
  assert.match(body, /"_stateSource": dataPlayer[\s\S]*"_controlTarget": identityPlayer/, "getAvailablePlayers must preserve state and control targets on virtual players");
  assert.match(body, /matchedGenericIndices\[j\] = true/, "getAvailablePlayers must avoid duplicating matched generic players");
  assert.match(body, /if \(!matchedGenericIndices\[i\]\)[\s\S]*finalPlayers\.push\(genericPlayers\[i\]\)/, "getAvailablePlayers must keep unmatched generic players");
  assert.match(body, /if \(player && player\.canControl\)[\s\S]*controllablePlayers\.push\(player\)/, "getAvailablePlayers must return only controllable players");
}

function testMediaServiceActivePlayerSelection() {
  const source = readQml("Services/Media/MediaService.qml");
  const findBody = extractFunctionBody(source, "findActivePlayer");
  const switchBody = extractFunctionBody(source, "switchToPlayer");
  const updateBody = extractFunctionBody(source, "updateCurrentPlayer");

  assert.match(findBody, /let availablePlayers = getAvailablePlayers\(\)/, "findActivePlayer must use filtered available players");
  assert.match(findBody, /if \(availablePlayers\.length === 0\)[\s\S]*return null/, "findActivePlayer must return null with no players");
  assert.match(findBody, /playbackState === MprisPlaybackState\.Playing[\s\S]*selectedPlayerIndex = i[\s\S]*return availablePlayers\[i\]/, "findActivePlayer must prefer actively playing players");
  assert.match(findBody, /const preferred = \(Settings\.data\.audio\.preferredPlayer \|\| ""\)/, "findActivePlayer must read preferred player setting");
  assert.match(findBody, /identity\.includes\(pref\)[\s\S]*selectedPlayerIndex = i[\s\S]*return p/, "findActivePlayer must select preferred matching identity");
  assert.match(findBody, /if \(selectedPlayerIndex < availablePlayers\.length\)[\s\S]*return availablePlayers\[selectedPlayerIndex\]/, "findActivePlayer must keep valid manual selection");
  assert.match(findBody, /selectedPlayerIndex = 0[\s\S]*return availablePlayers\[0\]/, "findActivePlayer must reset invalid selections");
  assert.match(switchBody, /if \(index >= 0 && index < availablePlayers\.length\)/, "switchToPlayer must bounds-check target index");
  assert.match(switchBody, /if \(newPlayer !== currentPlayer\)[\s\S]*currentPlayer = newPlayer[\s\S]*selectedPlayerIndex = index/, "switchToPlayer must update player and index together");
  assert.match(switchBody, /currentPosition = currentPlayer \? currentPlayer\.position : 0/, "switchToPlayer must sync current position from the selected player");
  assert.match(updateBody, /let newPlayer = findActivePlayer\(\)/, "updateCurrentPlayer must find the best active player");
  assert.match(updateBody, /if \(newPlayer !== currentPlayer\)[\s\S]*currentPlayer = newPlayer[\s\S]*currentPosition = currentPlayer \? currentPlayer\.position : 0/, "updateCurrentPlayer must update player and position together");
}

function testMediaServicePlaybackControlsDelegateSafely() {
  const source = readQml("Services/Media/MediaService.qml");
  const playPauseBody = extractFunctionBody(source, "playPause");
  const playBody = extractFunctionBody(source, "play");
  const stopBody = extractFunctionBody(source, "stop");
  const pauseBody = extractFunctionBody(source, "pause");
  const nextBody = extractFunctionBody(source, "next");
  const previousBody = extractFunctionBody(source, "previous");

  assert.match(playPauseBody, /if \(currentPlayer\)/, "playPause must ignore missing players");
  assert.match(playPauseBody, /let stateSource = currentPlayer\._stateSource \|\| currentPlayer/, "playPause must read state from virtual player state source");
  assert.match(playPauseBody, /let controlTarget = currentPlayer\._controlTarget \|\| currentPlayer/, "playPause must control the virtual player target");
  assert.match(playPauseBody, /playbackState === MprisPlaybackState\.Playing[\s\S]*controlTarget\.pause\(\)[\s\S]*else[\s\S]*controlTarget\.play\(\)/, "playPause must toggle based on playback state");
  assert.match(playBody, /let target = currentPlayer \? \(currentPlayer\._controlTarget \|\| currentPlayer\) : null/, "play must resolve the control target");
  assert.match(playBody, /if \(target && target\.canPlay\)[\s\S]*target\.play\(\)/, "play must require canPlay");
  assert.match(stopBody, /if \(target\)[\s\S]*target\.stop\(\)/, "stop must target the resolved player when present");
  assert.match(pauseBody, /if \(target && target\.canPause\)[\s\S]*target\.pause\(\)/, "pause must require canPause");
  assert.match(nextBody, /if \(target && target\.canGoNext\)[\s\S]*target\.next\(\)/, "next must require canGoNext");
  assert.match(previousBody, /if \(target && target\.canGoPrevious\)[\s\S]*target\.previous\(\)/, "previous must require canGoPrevious");
}

function testMediaServiceSeekHelpers() {
  const source = readQml("Services/Media/MediaService.qml");
  const seekBody = extractFunctionBody(source, "seek");
  const seekRelativeBody = extractFunctionBody(source, "seekRelative");
  const seekByRatioBody = extractFunctionBody(source, "seekByRatio");

  assert.match(seekBody, /let target = currentPlayer \? \(currentPlayer\._controlTarget \|\| currentPlayer\) : null/, "seek must resolve the control target");
  assert.match(seekBody, /if \(target && target\.canSeek\)[\s\S]*target\.position = position[\s\S]*currentPosition = position/, "seek must update backend and local position");
  assert.match(seekRelativeBody, /if \(target && target\.canSeek && target\.length > 0\)/, "seekRelative must require seekable tracks with length");
  assert.match(seekRelativeBody, /let seekPosition = target\.position \+ offset/, "seekRelative must add the offset to current backend position");
  assert.match(seekRelativeBody, /target\.position = seekPosition[\s\S]*currentPosition = seekPosition/, "seekRelative must update backend and local position");
  assert.match(seekByRatioBody, /if \(target && target\.canSeek && target\.length > 0\)/, "seekByRatio must require seekable tracks with length");
  assert.match(seekByRatioBody, /let seekPosition = ratio \* target\.length/, "seekByRatio must convert ratio to absolute position");
  assert.match(seekByRatioBody, /target\.position = seekPosition[\s\S]*currentPosition = seekPosition/, "seekByRatio must update backend and local position");
}

const tests = [
  testMediaServicePlayerFilteringAndVirtualPlayers,
  testMediaServiceActivePlayerSelection,
  testMediaServicePlaybackControlsDelegateSafely,
  testMediaServiceSeekHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
