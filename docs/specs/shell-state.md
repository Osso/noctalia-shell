ShellState covers the small persisted state cache shared by services that need lightweight cross-reload data. Runtime source lives in `Commons/ShellState.qml`; implementation notes belong in [docs/wiki/systems/shell-state.md](../wiki/systems/shell-state.md).

## What it must do

### Adapter contract

- [x] ShellState exposes a JsonAdapter with exactly `display`, `notificationsState`, `changelogState`, and `colorSchemesList`.
- [x] Notification state defaults `lastSeenTs` to `0`.
- [x] Changelog state defaults `lastSeenVersion` to an empty string.
- [x] Color scheme list state defaults `schemes` to an empty list and `timestamp` to `0`.
- [x] Every adapter key is read or written through ShellState.
- [x] Display, notifications, changelog, and color scheme list state each expose setter and getter functions.

### Debounced persistence

- [x] Calling `save()` marks a save as queued and restarts the save timer.
- [x] `performSave()` does nothing when no save is queued.
- [x] `performSave()` keeps the save queued when the state file path is missing.
- [x] `performSave()` creates the cache directory, schedules the adapter write, clears the queued flag, writes the adapter, and logs success.

### Snapshot export

- [x] State snapshots include plain settings data.
- [x] State snapshots include do-not-disturb, performance mode, bar visibility, current wallpapers, display state, notifications state, changelog state, and color scheme list state.
- [x] Snapshot building fails closed with a logged error and returns null when object conversion fails.

## How it works

- [docs/wiki/systems/shell-state.md](../wiki/systems/shell-state.md)

## Implementation inventory

- `Commons/ShellState.qml` - singleton state cache, adapter defaults, getters/setters, debounced saves, and snapshot export.
- `Services/Compositor/CompositorService.qml` - display scale cache consumer.
- `Services/System/NotificationService.qml` - notification state consumer.
- `Services/Noctalia/UpdateService.qml` - changelog state consumer.
- `Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml` - color scheme list cache consumer.

## Tests asserting this spec

- `Tests/shell-state-contract.test.js`
- `Tests/shell-state-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for ShellState load success and load-failure paths.
- [ ] Add executable coverage for each setter emitting its matching change signal.
- [ ] Add executable coverage for cache consumers round-tripping through ShellState.

## Out of scope

- Settings file persistence belongs in [settings.md](settings.md).
- Individual consumer semantics belong in their feature specs: [compositor.md](compositor.md), [notifications.md](notifications.md), and [theming.md](theming.md).
