#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

const source = readQml("Services/System/SoundService.qml");

function qmlFunction(functionName, ...argNames) {
  const body = extractFunctionBody(source, functionName);
  return new Function("ctx", ...argNames, `with (ctx) { return (function(${argNames.join(", ")}) ${body}).call(ctx, ${argNames.join(", ")}); }`);
}

function createLogger() {
  return {
    debug: [],
    warnings: [],
    d(...args) {
      this.debug.push(args);
    },
    w(...args) {
      this.warnings.push(args);
    },
  };
}

function createContext({ createObject } = {}) {
  const resolvePath = qmlFunction("resolvePath", "soundPath");
  const stopSound = qmlFunction("stopSound", "soundPath");
  const logger = createLogger();
  const createdPlayers = [];
  const ctx = {
    Quickshell: {
      shellDir: "/shell",
    },
    MediaPlayer: {
      Infinite: -1,
    },
    activePlayers: {},
    playersContainer: {},
    Logger: logger,
    playerComponent: {
      createObject(parent, properties) {
        if (createObject) {
          return createObject(parent, properties, ctx);
        }
        const player = {
          properties,
          stopped: false,
          destroyed: false,
          stop() {
            this.stopped = true;
          },
          destroy() {
            this.destroyed = true;
          },
        };
        createdPlayers.push(player);
        return player;
      },
    },
  };
  ctx.createdPlayers = createdPlayers;
  ctx.resolvePath = soundPath => resolvePath(ctx, soundPath);
  ctx.stopSound = soundPath => stopSound(ctx, soundPath);
  return ctx;
}

function testSoundServiceResolvePathHandlesEmptyRelativeFileAndAbsolutePaths() {
  const resolvePath = qmlFunction("resolvePath", "soundPath");
  const ctx = createContext();

  assert.equal(resolvePath(ctx, ""), "");
  assert.equal(resolvePath(ctx, null), "");
  assert.equal(resolvePath(ctx, "alarm.wav"), "/shell/Assets/Sounds/alarm.wav");
  assert.equal(resolvePath(ctx, "Assets/Sounds/alarm.wav"), "/shell/Assets/Sounds/alarm.wav");
  assert.equal(resolvePath(ctx, "/tmp/alarm.wav"), "/tmp/alarm.wav");
  assert.equal(resolvePath(ctx, "file:///tmp/alarm.wav"), "/tmp/alarm.wav");
}

function testSoundServicePlaySoundCreatesClampedPlayerAndStoresByResolvedPath() {
  const playSound = qmlFunction("playSound", "soundPath", "options");
  const ctx = createContext();

  playSound(ctx, "alarm.wav", {
    volume: 1.5,
    repeat: true,
    fallback: true,
  });

  assert.equal(ctx.createdPlayers.length, 1);
  assert.deepEqual(ctx.createdPlayers[0].properties, {
    resolvedPath: "/shell/Assets/Sounds/alarm.wav",
    source: "file:///shell/Assets/Sounds/alarm.wav",
    loops: -1,
    soundVolume: 1,
    shouldFallback: false,
  });
  assert.equal(ctx.activePlayers["/shell/Assets/Sounds/alarm.wav"], ctx.createdPlayers[0]);
  assert.equal(ctx.Logger.warnings.length, 0);
}

function testSoundServicePlaySoundStopsExistingRepeatingPlayer() {
  const playSound = qmlFunction("playSound", "soundPath", "options");
  const existingPlayer = {
    stopped: false,
    destroyed: false,
    stop() {
      this.stopped = true;
    },
    destroy() {
      this.destroyed = true;
    },
  };
  const ctx = createContext();
  ctx.activePlayers["/shell/Assets/Sounds/alarm.wav"] = existingPlayer;

  playSound(ctx, "alarm.wav", {
    repeat: true,
    volume: 0.2,
  });

  assert.equal(existingPlayer.stopped, true);
  assert.equal(existingPlayer.destroyed, true);
  assert.equal(ctx.activePlayers["/shell/Assets/Sounds/alarm.wav"], ctx.createdPlayers[0]);
}

function testSoundServicePlaySoundFallsBackWhenPlayerCreationFails() {
  const playSound = qmlFunction("playSound", "soundPath", "options");
  const attempted = [];
  const ctx = createContext({
    createObject(parent, properties) {
      attempted.push(properties.resolvedPath);
      return null;
    },
  });
  ctx.playSound = (soundPath, options) => playSound(ctx, soundPath, options);

  playSound(ctx, "missing.wav", {
    volume: 0.4,
    fallback: true,
  });

  assert.deepEqual(attempted, ["/shell/Assets/Sounds/missing.wav", "/shell/Assets/Sounds/notification.mp3"]);
  assert.equal(ctx.Logger.warnings.length, 2);
}

function testSoundServiceStopSoundStopsSpecificAndAllPlayers() {
  const stopSound = qmlFunction("stopSound", "soundPath");
  const first = {
    stopped: false,
    destroyed: false,
    stop() {
      this.stopped = true;
    },
    destroy() {
      this.destroyed = true;
    },
  };
  const second = {
    stopped: false,
    destroyed: false,
    stop() {
      this.stopped = true;
    },
    destroy() {
      this.destroyed = true;
    },
  };
  const ctx = createContext();
  ctx.activePlayers = {
    "/shell/Assets/Sounds/alarm.wav": first,
    "/tmp/other.wav": second,
  };

  stopSound(ctx, "alarm.wav");

  assert.equal(first.stopped, true);
  assert.equal(first.destroyed, true);
  assert.deepEqual(Object.keys(ctx.activePlayers), ["/tmp/other.wav"]);

  stopSound(ctx);

  assert.equal(second.stopped, true);
  assert.equal(second.destroyed, true);
  assert.deepEqual(ctx.activePlayers, {});
}

const tests = [
  testSoundServiceResolvePathHandlesEmptyRelativeFileAndAbsolutePaths,
  testSoundServicePlaySoundCreatesClampedPlayerAndStoresByResolvedPath,
  testSoundServicePlaySoundStopsExistingRepeatingPlayer,
  testSoundServicePlaySoundFallsBackWhenPlayerCreationFails,
  testSoundServiceStopSoundStopsSpecificAndAllPlayers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
