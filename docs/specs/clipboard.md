Clipboard covers cliphist availability, wl-paste watcher lifecycle, history listing, decode/base64 image decode, and mutation commands. Runtime source lives mainly in `Services/Keyboard/ClipboardService.qml`; implementation notes belong in [docs/wiki/systems/clipboard.md](../wiki/systems/clipboard.md).

## What it must do

### Dependency and watcher lifecycle

- [x] Cliphist availability is probed only once with `which cliphist`.
- [x] Watchers start only when clipboard history is active, auto-watch is enabled, watchers are not already started, and cliphist is available.
- [x] Watchers start separate text and image `wl-paste --watch cliphist store` processes.
- [x] Stopping watchers is idempotent and stops both watcher processes.

### Listing

- [x] Listing fails closed when clipboard history is inactive or cliphist is unavailable.
- [x] Listing skips work while the list process is already running.
- [x] Listing marks the service loading and runs `cliphist list -preview-width <width>`.
- [x] Listing defaults preview width to `100` when no width is supplied.
- [x] List output parsing supports space and tab separated ids, preserves previews, detects image entries, guesses image MIME types, and records first-seen timestamps for new ids.

### Decode and image data

- [x] Text decode calls back with empty content when cliphist is unavailable.
- [x] Text decode stores the callback and starts `cliphist decode <id>`.
- [x] Data-url decode calls back with empty content when cliphist is unavailable.
- [x] Data-url decode returns cached image data immediately.
- [x] Data-url decode queues uncached work, defaults missing mime types to `image/*`, and starts base64 decode work when idle.
- [x] Base64 decode work runs through `cliphist decode <id> | base64 -w 0`.
- [x] Base64 decode work does not start while cliphist is unavailable.
- [x] Image lookup returns `null` for undefined ids and cached data for known ids.

### Mutations

- [x] Copy fails closed when cliphist is unavailable.
- [x] Copy decodes the selected entry and pipes it to `wl-copy`.
- [x] Delete fails closed when cliphist is unavailable.
- [x] Delete runs `cliphist delete <id>`, bumps revision, and refreshes the list later.
- [x] Wipe fails closed when cliphist is unavailable.
- [x] Wipe runs `cliphist wipe`, bumps revision, and refreshes the list later.

## How it works

- [docs/wiki/systems/clipboard.md](../wiki/systems/clipboard.md)

## Implementation inventory

- `Services/Keyboard/ClipboardService.qml` - cliphist wrapper, watchers, list/decode commands, image data cache, and mutation commands.
- `Modules/Panels/Launcher/Plugins/ClipboardPlugin.qml` - launcher plugin UI for clipboard search, copy, image previews, and clear action.
- `Modules/Panels/Settings/Tabs/LauncherTab.qml` - clipboard-history settings toggle.
- `Services/Control/IPCService.qml` - launcher IPC mode for clipboard search.

## Tests asserting this spec

- `Tests/clipboard-service-guards.test.js`
- `Tests/clipboard-plugin-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [x] Add executable tests for list-process output parsing into clipboard items.
- [ ] Add executable tests for decode process completion callbacks and base64 cache writes.
- [ ] Add spec coverage for clipboard launcher result rendering and activation.

## Out of scope

- General launcher navigation/search behavior belongs in the launcher spec.
- Emoji clipboard copy behavior belongs in the emoji spec.
