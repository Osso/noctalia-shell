Wallpaper covers local wallpaper model setup, monitor-specific wallpaper lookup and randomization, recursive wallpaper scans, wallpaper panel helpers, settings interval helpers, Wallhaven search/download helpers, and typed monitor delegates. Runtime source lives mainly in `Services/UI/WallpaperService.qml`, `Services/UI/WallhavenService.qml`, and `Modules/Panels/Wallpaper/WallpaperPanel.qml`; implementation notes belong in [docs/wiki/systems/wallpaper.md](../wiki/systems/wallpaper.md).

## What it must do

### Service initialization and models

- [x] Wallpaper service startup logs that the service started.
- [x] Wallpaper service startup translates UI models, defers cache path setup until settings are available, and schedules the initial scan.
- [x] Model translation retries after translations load if translations are not ready.
- [x] Fill-mode model includes center, crop, fit, and stretch with their uniform values.
- [x] Transition model includes none, random, fade, disc, stripes, and wipe.
- [x] Fill-mode lookup scans the fill-mode model, returns the configured mode uniform, and falls back to crop.

### Monitor lookup, wallpaper selection, and scanning

- [x] Monitor config lookup returns the matching named monitor config and returns `undefined` for unknown screens.
- [x] Monitor config lookup uses a typed string screen-name input.
- [x] Wallpaper-list lookup returns cached screen lists and fails closed to an empty list for unknown screens.
- [x] Random wallpaper selection updates only screens that have cached wallpapers in multi-monitor-directory mode.
- [x] Random wallpaper selection updates all screens through an undefined screen name in single-directory mode.
- [x] Recursive scan setup parses successful scan output, sorts cached files, emits list changes, clears lists after failed scans, cleans process references, and starts the scan process.

### Wallpaper panel and settings helpers

- [x] Current wallpaper view lookup returns `null` without panel content.
- [x] Current wallpaper view lookup returns the current screen repeater item.
- [x] Current grid lookup returns the current wallpaper view grid and fails closed to `null` without a current grid.
- [x] Wallpaper interval preset selection persists the selected interval, restarts the random wallpaper timer, and hides the custom interval control.
- [x] Wallpaper interval selection reports selected state only for the current interval.

### Wallhaven search and download

- [x] Wallhaven wallpaper and thumbnail URL helpers declare string return types.
- [x] Wallhaven thumbnail URL helper uses a typed string size input.
- [x] Wallhaven search ignores duplicate requests while fetching.
- [x] Wallhaven search clears scheduled initial search state, resets public request state, encodes query text, includes base filters, conditionally includes `topRange` and `seed`, includes the page, and issues a GET request.
- [x] Wallhaven search clears fetching only after request completion and handles response state through the request completion path.
- [x] Wallhaven URL helpers choose usable source URLs and thumbnail URLs, including thumbnail fallback from wallpaper id.
- [x] Wallhaven download fails the callback when no wallpaper URL exists, resolves the configured directory with default fallback, normalizes a trailing slash, builds a stable local path, emits success, calls the callback, and cleans up the process.
- [x] Wallhaven reset clears search state.
- [x] Wallhaven pagination advances or retreats only within bounds and while idle.

### Types and IPC

- [x] Wallpaper background, overview, panel, tab, and scanner delegates use typed screen/model aliases instead of repeated dynamic screen access.
- [x] Wallpaper tab interval preset delegates type numeric `modelData`.
- [x] Wallpaper IPC random action delegates to `WallpaperService.setRandomWallpaper`.
- [x] Wallpaper IPC set action passes normalized path and screen values to `WallpaperService.changeWallpaper`.

## How it works

- [docs/wiki/systems/wallpaper.md](../wiki/systems/wallpaper.md)

## Implementation inventory

- `Services/UI/WallpaperService.qml` - wallpaper models, cache path setup, monitor directories, random wallpaper selection, wallpaper lists, and recursive scanning.
- `Services/UI/WallhavenService.qml` - Wallhaven search, URL construction, download, reset, and pagination helpers.
- `Modules/Panels/Wallpaper/WallpaperPanel.qml` - wallpaper panel views, current view/grid helpers, local wallpapers, and Wallhaven UI.
- `Modules/Panels/Settings/Tabs/WallpaperTab.qml` - wallpaper settings, monitor directory aliases, and random interval presets.
- `Modules/Background/Background.qml` - rendered wallpaper background per screen.
- `Modules/Background/Overview.qml` - overview wallpaper background per screen.
- `Services/Control/IPCService.qml` - wallpaper IPC actions.
- `Bin/dev/service-probes.sh` - wallpaper/settings probe shape checks.

## Tests asserting this spec

- `Tests/wallpaper-service-guards.test.js`
- `Tests/wallhaven-service-guards.test.js`
- `Tests/wallpaper-panel-guards.test.js`
- `Tests/wallpaper-tab-guards.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] Add executable tests for actual wallpaper file acceptance/rejection and image-extension filtering.
- [ ] Add executable tests for rendered wallpaper background transition behavior.
- [ ] Add executable tests for Wallhaven response parsing with concrete success and error JSON fixtures.
- [ ] Add executable tests for wallpaper panel local/Wallhaven user actions beyond current view helper lookup.

## Out of scope

- Theme color extraction from wallpapers belongs in a separate theme/color spec.
- Shell background layout outside wallpaper-specific behavior belongs in a separate background spec if it grows beyond wallpaper rendering.
