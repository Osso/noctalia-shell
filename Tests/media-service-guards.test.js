#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(readQml("Services/Media/MediaService.qml"), functionName);
  const args = argNames.join(", ");
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${args}) ${body}).call(ctx, ${args}); }`);
}

function makePlayer(overrides = {}) {
  const calls = [];
  return {
    canControl: true,
    canGoNext: true,
    canGoPrevious: true,
    canPause: true,
    canPlay: true,
    canSeek: true,
    desktopEntry: "",
    identity: "player",
    isPlaying: false,
    length: 300,
    next: () => calls.push("next"),
    pause: () => calls.push("pause"),
    play: () => calls.push("play"),
    playbackState: 0,
    position: 10,
    previous: () => calls.push("previous"),
    stop: () => calls.push("stop"),
    trackAlbum: "",
    trackArtist: "",
    trackArtUrl: "",
    trackTitle: "Track",
    calls,
    ...overrides,
  };
}

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

function testMediaServicePlayerFilteringExecutesVirtualPlayers() {
  const getAvailablePlayers = qmlFunction("getAvailablePlayers");
  const generic = makePlayer({
    canPause: true,
    identity: "firefox",
    playbackState: 1,
    position: 42,
    trackArtist: "Browser Artist",
    trackArtUrl: "cover.png",
    trackTitle: "Example Song",
  });
  const specific = makePlayer({
    canPause: false,
    identity: "spotify",
    playbackState: 0,
    trackTitle: "Example Song - Spotify",
  });
  const unmatchedGeneric = makePlayer({ identity: "chrome", trackTitle: "Other Song" });
  const blocked = makePlayer({ identity: "Blocked Player", trackTitle: "Blocked" });
  const inert = makePlayer({ canControl: false, identity: "vlc", trackTitle: "No Control" });
  const ctx = {
    Mpris: { players: { values: [generic, specific, unmatchedGeneric, blocked, inert] } },
    Settings: { data: { audio: { mprisBlacklist: ["blocked"] } } },
  };

  const players = getAvailablePlayers(ctx);

  assert.equal(players.length, 2, "only controllable non-blacklisted players are returned");
  assert.equal(players[0].identity, "spotify", "virtual player keeps the specific player identity");
  assert.equal(players[0].trackArtUrl, "cover.png", "virtual player uses richer generic metadata");
  assert.equal(players[0].canPause, true, "virtual player exposes state-source capabilities");
  assert.equal(players[0]._stateSource, generic, "virtual player keeps state source");
  assert.equal(players[0]._controlTarget, specific, "virtual player controls the specific target");
  assert.equal(players[1], unmatchedGeneric, "unmatched generic players remain available");
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

function testMediaServiceActivePlayerSelectionExecutesPriorities() {
  const findActivePlayer = qmlFunction("findActivePlayer");
  const switchToPlayer = qmlFunction("switchToPlayer", "index");
  const updateCurrentPlayer = qmlFunction("updateCurrentPlayer");
  const stopped = makePlayer({ identity: "mpv", position: 10 });
  const preferred = makePlayer({ identity: "spotify", position: 20 });
  const playing = makePlayer({ identity: "vlc", playbackState: 1, position: 30 });
  const ctx = {
    Logger: { d: () => {} },
    MprisPlaybackState: { Playing: 1 },
    Settings: { data: { audio: { preferredPlayer: "spotify" } } },
    currentPlayer: stopped,
    currentPosition: 0,
    getAvailablePlayers: () => [stopped, preferred, playing],
    selectedPlayerIndex: 0,
  };
  ctx.findActivePlayer = () => findActivePlayer(ctx);

  assert.equal(findActivePlayer(ctx), playing, "playing player wins over preferred player");
  assert.equal(ctx.selectedPlayerIndex, 2, "playing player updates selected index");

  playing.playbackState = 0;
  assert.equal(findActivePlayer(ctx), preferred, "preferred player wins when none are playing");
  assert.equal(ctx.selectedPlayerIndex, 1, "preferred player updates selected index");

  ctx.Settings.data.audio.preferredPlayer = "";
  ctx.selectedPlayerIndex = 0;
  assert.equal(findActivePlayer(ctx), stopped, "valid manual selection is preserved");

  ctx.selectedPlayerIndex = 99;
  assert.equal(findActivePlayer(ctx), stopped, "invalid selection resets to first player");
  assert.equal(ctx.selectedPlayerIndex, 0, "invalid selected index resets");

  switchToPlayer(ctx, 1);
  assert.equal(ctx.currentPlayer, preferred, "switchToPlayer applies selected player");
  assert.equal(ctx.currentPosition, 20, "switchToPlayer syncs position");

  ctx.getAvailablePlayers = () => [stopped, playing];
  playing.playbackState = 1;
  updateCurrentPlayer(ctx);
  assert.equal(ctx.currentPlayer, playing, "updateCurrentPlayer applies active player");
  assert.equal(ctx.currentPosition, 30, "updateCurrentPlayer syncs position");
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

function testMediaServicePlaybackControlsExecuteTargets() {
  const playPause = qmlFunction("playPause");
  const play = qmlFunction("play");
  const stop = qmlFunction("stop");
  const pause = qmlFunction("pause");
  const next = qmlFunction("next");
  const previous = qmlFunction("previous");
  const state = makePlayer({ playbackState: 1 });
  const control = makePlayer();
  const ctx = {
    MprisPlaybackState: { Playing: 1 },
    currentPlayer: { _controlTarget: control, _stateSource: state },
  };

  playPause(ctx);
  assert.deepEqual(control.calls, ["pause"], "playPause pauses the control target when state source is playing");

  state.playbackState = 0;
  playPause(ctx);
  assert.deepEqual(control.calls, ["pause", "play"], "playPause plays the control target when state source is not playing");

  play(ctx);
  pause(ctx);
  next(ctx);
  previous(ctx);
  stop(ctx);
  assert.deepEqual(control.calls.slice(2), ["play", "pause", "next", "previous", "stop"], "transport helpers target the control target");

  control.canPlay = false;
  control.canPause = false;
  control.canGoNext = false;
  control.canGoPrevious = false;
  play(ctx);
  pause(ctx);
  next(ctx);
  previous(ctx);
  assert.deepEqual(control.calls.slice(7), [], "guarded transport helpers skip unavailable capabilities");
}

function testMediaServiceSeekHelpers() {
  const source = readQml("Services/Media/MediaService.qml");
  const seekBody = extractFunctionBody(source, "seek");
  const seekRelativeBody = extractFunctionBody(source, "seekRelative");
  const seekByRatioBody = extractFunctionBody(source, "seekByRatio");

  assert.match(source, /function seek\(position\)/, "seek must type absolute position input");
  assert.match(source, /function seekRelative\(offset\)/, "seekRelative must type offset input");
  assert.match(source, /function seekByRatio\(ratio\)/, "seekByRatio must type ratio input");
  assert.match(seekBody, /let target = currentPlayer \? \(currentPlayer\._controlTarget \|\| currentPlayer\) : null/, "seek must resolve the control target");
  assert.match(seekBody, /if \(target && target\.canSeek\)[\s\S]*target\.position = position[\s\S]*currentPosition = position/, "seek must update backend and local position");
  assert.match(seekRelativeBody, /if \(target && target\.canSeek && target\.length > 0\)/, "seekRelative must require seekable tracks with length");
  assert.match(seekRelativeBody, /let seekPosition = target\.position \+ offset/, "seekRelative must add the offset to current backend position");
  assert.match(seekRelativeBody, /target\.position = seekPosition[\s\S]*currentPosition = seekPosition/, "seekRelative must update backend and local position");
  assert.match(seekByRatioBody, /if \(target && target\.canSeek && target\.length > 0\)/, "seekByRatio must require seekable tracks with length");
  assert.match(seekByRatioBody, /let seekPosition = ratio \* target\.length/, "seekByRatio must convert ratio to absolute position");
  assert.match(seekByRatioBody, /target\.position = seekPosition[\s\S]*currentPosition = seekPosition/, "seekByRatio must update backend and local position");
}

function testMediaServiceSeekHelpersExecuteTargets() {
  const seek = qmlFunction("seek", "position");
  const seekRelative = qmlFunction("seekRelative", "offset");
  const seekByRatio = qmlFunction("seekByRatio", "ratio");
  const control = makePlayer({ length: 200, position: 50 });
  const ctx = {
    currentPlayer: { _controlTarget: control },
    currentPosition: 0,
  };

  seek(ctx, 25);
  assert.equal(control.position, 25, "seek applies absolute target position");
  assert.equal(ctx.currentPosition, 25, "seek mirrors current position");

  seekRelative(ctx, 10);
  assert.equal(control.position, 35, "seekRelative adds offset to backend position");
  assert.equal(ctx.currentPosition, 35, "seekRelative mirrors current position");

  seekByRatio(ctx, 0.5);
  assert.equal(control.position, 100, "seekByRatio converts ratio to absolute position");
  assert.equal(ctx.currentPosition, 100, "seekByRatio mirrors current position");

  control.canSeek = false;
  seek(ctx, 150);
  seekRelative(ctx, 10);
  seekByRatio(ctx, 0.75);
  assert.equal(control.position, 100, "seek helpers skip non-seekable targets");
}

const tests = [
  testMediaServicePlayerFilteringAndVirtualPlayers,
  testMediaServicePlayerFilteringExecutesVirtualPlayers,
  testMediaServiceActivePlayerSelection,
  testMediaServiceActivePlayerSelectionExecutesPriorities,
  testMediaServicePlaybackControlsDelegateSafely,
  testMediaServicePlaybackControlsExecuteTargets,
  testMediaServiceSeekHelpers,
  testMediaServiceSeekHelpersExecuteTargets,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
