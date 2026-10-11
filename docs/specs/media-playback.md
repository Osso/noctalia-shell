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
- [x] MPRIS player add/remove, playback-state, playing-state, and title changes trigger active-player updates without always-on player polling.

### Transport controls

- [x] `playPause` ignores missing players.
- [x] `playPause` reads playback state from a virtual player's state source and sends commands to its control target.
- [x] `play`, `pause`, `next`, and `previous` require their matching MPRIS capability before sending commands.
- [x] `stop` sends to the resolved control target when present.

### Position updates and seeking

- [x] Live position polling is gated behind visible media progress UI.
- [x] Detailed media cards request 1s position updates; compact bar media widgets request 5s updates.
- [x] Visible media progress consumers register/deregister with ref-counted guards.
- [x] Position update deregistration clamps at zero to avoid stale negative refs.
- [x] Seek helpers resolve a virtual player's control target.
- [x] Seek helpers type absolute position, relative offset, and ratio inputs.
- [x] Absolute seek updates backend position and local `currentPosition`.
- [x] Relative seek requires a seekable target with a positive length and adds the requested offset.
- [x] Ratio seek requires a seekable target with a positive length and converts ratio to absolute position.
- [x] Seek helpers skip non-seekable targets.

### Media mini widget

- [x] Media mini title formatting supports artist-first display with `Artist - Title`.
- [x] Media mini title formatting supports title-first display with `Title - Artist`.
- [x] Media mini title formatting omits the separator when artist metadata is empty.
- [x] With no player, the widget shows its placeholder and settings-only menu; playback clicks do nothing.
- [x] Left click and the menu toggle playback subject to capabilities; middle click selects the previous track and the menu can select the next track.
- [x] Playback state and metadata changes update title, menu icons, artwork fallback, tooltips, and progress; progress clamps at the track duration.
- [x] Album art and playback icons follow bar orientation; linear, mirrored, and wave visualizers receive spectrum data, have nonzero dimensions, and unload when disabled.
- Spectrum rendering contracts and isolated component proof belong in [audio](audio.md#spectrum-visualization); those cases do not extend MediaMini integration coverage.
- [x] Fixed width honors its configured limit; always-scroll mode advances overflowing titles after its delay.
- [x] Idle hide mode hides paused playback and releases position updates; resuming playback shows the widget and registers updates again.

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

- `Tests/widget-settings-cohort-warnings.test.py` / `Tests/Qml/WidgetSettingsCohortHarness.qml` — MediaMiniSettings: five toggles, visualizer-dependent controls, hide/visualizer/scrolling selections, width 315 and invalid empty/non-numeric/zero values resolving to 240. Fixture defaults include `hideMode: "hidden"`; this does not verify live MPRIS or visualizer output. Each editor also exercises fixture defaults, save-copy isolation, cancel/reopen, and apply-close. Completed isolated assertions do not close the RED shared-control runtime warning gate. Cohort counts/lint evidence: [bar](bar.md#tests-asserting-this-spec); isolation and limits: [testing](testing.md#widget-settings-cohort).

- `Tests/media-service-guards.test.js`
- `Tests/media-mini-warnings.test.py` and `Tests/Qml/MediaMiniWarningsHarness.qml` - standalone isolated offscreen production-widget coverage with fixture services and real artwork/visualizer widgets; requires completed behavior assertions and no runtime WARN/ERROR/FATAL logs.
- `Tests/widget-helper-guards.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`

## Known gaps (current cycle)

- [ ] Extend metadata-consumer runtime coverage beyond MediaMini to the media card.
- [ ] Add spec coverage for IPC media action contracts.

## Out of scope

- PipeWire volume, mute, device selection, and audio OSD behavior belong in [audio.md](audio.md).
- Screen recording audio/video capture belongs in a separate screen recording spec.
