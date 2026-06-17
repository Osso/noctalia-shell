Media playback covers MPRIS player discovery, virtual player pairing, active-player selection, transport controls, and seek controls. Runtime source lives mainly in `Services/Media/MediaService.qml`; implementation notes belong in [docs/wiki/systems/media-playback.md](../wiki/systems/media-playback.md).

## What it must do

### Player discovery

- [x] Player discovery fails closed when MPRIS player values are unavailable.
- [x] Generic browser MPRIS players are separated from specific application players.
- [x] Configured MPRIS blacklist entries remove matching player identities.
- [x] Matching generic/specific players are paired by compatible track titles.
- [x] Virtual paired players keep the specific player identity and control target.
- [x] Virtual paired players use the richer metadata/state source when available.
- [x] Matched generic players are not duplicated.
- [x] Unmatched generic players remain available.
- [x] Discovery returns only controllable players.

### Active-player selection

- [x] Active-player lookup returns `null` when no filtered players exist.
- [x] Actively playing players take priority and update `selectedPlayerIndex`.
- [x] Preferred player identity is used when no player is actively playing.
- [x] Valid manual selections are preserved.
- [x] Invalid manual selections reset to the first player.
- [x] Manual switching bounds-checks the requested index, updates the current player/index, and syncs position.
- [x] Automatic updates apply the selected active player and sync position.

### Transport controls

- [x] `playPause` ignores missing players.
- [x] `playPause` reads playback state from a virtual player's state source and sends commands to its control target.
- [x] `play`, `pause`, `next`, and `previous` require their matching MPRIS capability before sending commands.
- [x] `stop` sends to the resolved control target when present.

### Seeking

- [x] Seek helpers resolve a virtual player's control target.
- [x] Absolute seek updates backend position and local `currentPosition`.
- [x] Relative seek requires a seekable target with a positive length and adds the requested offset.
- [x] Ratio seek requires a seekable target with a positive length and converts ratio to absolute position.
- [x] Seek helpers skip non-seekable targets.

### Media mini widget

- [x] Media mini title formatting supports artist-first display with `Artist - Title`.
- [x] Media mini title formatting supports title-first display with `Title - Artist`.
- [x] Media mini title formatting omits the separator when artist metadata is empty.

### Media card

- [x] Media card wallpaper change handling uses typed wallpaper signal payloads.

## How it works

- [docs/wiki/systems/media-playback.md](../wiki/systems/media-playback.md)

## Implementation inventory

- `Services/Media/MediaService.qml` - MPRIS player discovery, active-player selection, transport controls, and seek state.
- `Modules/Cards/MediaCard.qml` - media card UI consuming current player metadata and controls.
- `Modules/Bar/Widgets/MediaMini.qml` - compact bar widget consuming media title/artist metadata.
- `Services/Control/IPCService.qml` - IPC routes for media actions.

## Tests asserting this spec

- `Tests/media-service-guards.test.js`
- `Tests/widget-helper-guards.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`

## Known gaps (current cycle)

- [ ] Add behavior tests for UI consumers of `MediaService` player metadata.
- [ ] Add spec coverage for IPC media action contracts.

## Out of scope

- PipeWire volume, mute, device selection, and audio OSD behavior belong in [audio.md](audio.md).
- Screen recording audio/video capture belongs in a separate screen recording spec.
