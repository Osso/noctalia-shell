pragma ComponentBehavior: Bound
import QtMultimedia
import QtQuick
import Quickshell
import qs.Commons
import qs.Services.System

Scope {
  id: harness

  property QtObject firstPlayer
  property QtObject fallbackPlayer
  property QtObject stoppedPlayer
  property QtObject replacedPlayer
  property QtObject repeatPlayer
  property QtObject stopAllFirst
  property QtObject stopAllSecond
  property int phase: 0
  property int ticks: 0
  property var createdPaths: []
  property var errors: []

  function require(condition, message) {
    if (!condition) {
      throw new Error(message);
    }
  }

  function volumeEquals(player, expected) {
    return Math.abs(player.soundVolume - expected) < 0.000001 && Math.abs(player.audioOutput.volume - expected) < 0.000001;
  }

  function observePlayer(path) {
    const player = SoundService.activePlayers[path];
    harness.require(player !== null && player !== undefined, "creation must register player before logging");
    harness.createdPaths.push(path);
    harness.require(player.source.toString() === "file://" + path, "source must use resolved path");
    if (path.endsWith("missing.wav")) {
      harness.firstPlayer = player;
      harness.require(harness.volumeEquals(player, 0.4), "requested volume reaches real AudioOutput");
      harness.require(player.shouldFallback && player.loops === 1, "one-shot fallback options");
    } else if (path.endsWith("notification.mp3")) {
      harness.fallbackPlayer = player;
      harness.require(harness.volumeEquals(player, 0.4), "fallback preserves volume");
      harness.require(!player.shouldFallback && player.loops === 1, "fallback cannot recurse");
    }
  }

  function testVolumeAndStopping() {
    SoundService.playSound("stopped.wav", {
                             volume: -0.5
                           });
    const stopped = SoundService.activePlayers[SoundService.resolvePath("stopped.wav")];
    harness.stoppedPlayer = stopped;
    harness.require(harness.volumeEquals(stopped, 0), "low volume clamp");
    stopped.soundVolume = 0.25;
    harness.require(harness.volumeEquals(stopped, 0.25), "nested binding follows player volume");
    stopped.playbackStateChanged(MediaPlayer.StoppedState);
    harness.require(Object.keys(SoundService.activePlayers).length === 0, "stopped one-shot removes registration");

    SoundService.playSound("repeat.wav", {
                             volume: 1.5,
                             repeat: true,
                             fallback: true
                           });
    const repeating = SoundService.activePlayers[SoundService.resolvePath("repeat.wav")];
    harness.replacedPlayer = repeating;
    harness.require(harness.volumeEquals(repeating, 1), "high volume clamp");
    harness.require(repeating.loops === MediaPlayer.Infinite && !repeating.shouldFallback, "repeat disables fallback");
    repeating.playbackStateChanged(MediaPlayer.StoppedState);
    harness.require(Object.keys(SoundService.activePlayers).length === 1, "stopped repeating player remains registered");
    SoundService.playSound("repeat.wav", {
                             volume: 0.7,
                             repeat: true
                           });
    harness.repeatPlayer = SoundService.activePlayers[SoundService.resolvePath("repeat.wav")];
    harness.require(harness.repeatPlayer !== harness.replacedPlayer, "repeat replaces old player");
    SoundService.stopSound("repeat.wav");
    harness.require(Object.keys(SoundService.activePlayers).length === 0, "specific stop clears registration");

    SoundService.playSound("all-a.wav", {
                             repeat: true
                           });
    harness.stopAllFirst = SoundService.activePlayers[SoundService.resolvePath("all-a.wav")];
    SoundService.playSound("all-b.wav", {
                             repeat: true
                           });
    harness.stopAllSecond = SoundService.activePlayers[SoundService.resolvePath("all-b.wav")];
    SoundService.stopSound();
    harness.require(Object.keys(SoundService.activePlayers).length === 0, "stop all clears registrations");
  }

  Component.onCompleted: {
    Logger.observe = path => harness.observePlayer(path);
    Logger.observeError = path => harness.errors.push(path.toString());
    SoundService.playSound("missing.wav", {
                             volume: 0.4,
                             fallback: true
                           });
    harness.require(harness.firstPlayer !== null, "real MediaPlayer created synchronously");
  }

  Timer {
    interval: 50
    running: true
    repeat: true
    onTriggered: {
      try {
        harness.ticks++;
        harness.require(harness.ticks < 100, "timed out awaiting asynchronous media errors/destruction");
        if (harness.phase === 0 && harness.errors.length === 2) {
          harness.require(harness.createdPaths.length === 2, "exactly one fallback created");
          harness.require(harness.errors[0].endsWith("missing.wav") && harness.errors[1].endsWith("notification.mp3"), "real backend errors occur original then fallback");
          harness.require(Object.keys(SoundService.activePlayers).length === 0, "errors clean active map");
          harness.require(harness.firstPlayer === null && harness.fallbackPlayer === null, "errored players destroyed");
          harness.testVolumeAndStopping();
          harness.phase = 1;
        } else if (harness.phase === 1) {
          harness.require(harness.stoppedPlayer === null && harness.replacedPlayer === null && harness.repeatPlayer === null, "stopped/replaced players destroyed");
          harness.require(harness.stopAllFirst === null && harness.stopAllSecond === null, "stop all destroys players");
          console.log("SOUND_SERVICE_PASS: creation, asynchronous errors, bounded fallback, cleanup, volume binding, repeat replacement, stop all");
          Qt.quit();
        }
      } catch (error) {
        console.error("SOUND_SERVICE_FAIL:", error.message);
        Qt.quit();
      }
    }
  }
}
