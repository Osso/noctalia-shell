Sound Service covers resolving sound asset paths, playing sounds through media players, replacing repeat players, fallback sound playback, and stopping active players. Runtime source lives in `Services/System/SoundService.qml`; implementation notes belong in [docs/wiki/systems/sound-service.md](../wiki/systems/sound-service.md).

## What it must do

### Path resolution

- [x] Empty and null sound paths resolve to an empty path.
- [x] Bare filenames resolve inside the shell `Assets/Sounds` directory.
- [x] Relative `Assets/Sounds/...` paths resolve inside the shell directory.
- [x] Absolute filesystem paths are preserved.
- [x] `file://` URLs resolve to filesystem paths.

### Playback

- [x] Playing a sound creates a media player with resolved path and `file://` source.
- [x] Playback volume is clamped to the supported range and reaches the player's AudioOutput; later player-volume changes update that output.
- [x] Repeating playback uses infinite loops.
- [x] Newly created players are stored by resolved path.
- [x] Playing a repeating sound stops and destroys any existing player for the same resolved path.
- [x] Player creation failures warn and can retry through the fallback notification sound.

- [x] Asynchronous media errors remove and destroy the failed player; fallback preserves volume, attempts the notification sound once, and cannot recurse if that sound also fails.
- [x] Repeating playback disables fallback and remains registered on a stopped-state signal; stopped one-shot playback removes and destroys its player.

### Stopping

- [x] Stopping a specific sound resolves its path, stops and destroys the matching player, and removes it from active players.
- [x] Stopping without a sound path stops and destroys every active player and clears active players.

## How it works

- [docs/wiki/systems/sound-service.md](../wiki/systems/sound-service.md)

## Implementation inventory

- `Services/System/SoundService.qml` - sound path resolution, MediaPlayer creation, active-player tracking, fallback playback, and stop helpers.
- `Assets/Sounds/alarm-beep.wav` - bundled sound asset used by shell features.

## Tests asserting this spec

- `Tests/sound-service-guards.test.js`
- `Tests/sound-service-runtime.test.py` and `Tests/Qml/SoundServiceHarness.qml` - standalone offscreen production MediaPlayer coverage in a bubblewrap sandbox without host audio/devices or session sockets: missing-file asynchronous errors, bounded fallback, volume binding, repeat replacement, explicit stopped-state signals, and stop-one/stop-all destruction. Does not decode valid audio or prove natural end-of-media cleanup.
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for natural end-of-media cleanup with valid audio.
- [ ] Add coverage for every shell feature that triggers SoundService playback.

## Out of scope

- PipeWire device and volume behavior is covered by [docs/specs/audio.md](audio.md).
- Notification display behavior is covered by [docs/specs/notifications.md](notifications.md).
