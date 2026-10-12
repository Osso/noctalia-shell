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
- [x] Monitor directory, wallpaper, and wallpaper-list lookups use typed string screen-name inputs.
- [x] Monitor directory updates use typed screen-name and directory inputs.
- [x] Wallpaper-list lookup returns cached screen lists and fails closed to an empty list for unknown screens.
- [x] Wallpaper changes type the required path input while keeping the target screen optional for all-screen updates.
- [x] Internal wallpaper updates type the resolved screen name and path inputs.
- [x] Random wallpaper selection updates only screens that have cached wallpapers in multi-monitor-directory mode.
- [x] Random wallpaper selection updates all screens through an undefined screen name in single-directory mode.
- [x] Recursive scan setup parses successful scan output, sorts cached files, emits list changes, clears lists after failed scans, cleans process references, and starts the scan process.
- [x] Recursive scan setup uses typed screen-name and directory inputs.

### Rendered background resource use

- [x] Wallpaper backgrounds request a monitor-sized decode before assigning image sources.
- [x] Wallpaper backgrounds render the settled wallpaper through a plain `Image` instead of an always-loaded transition shader.
- [x] Wallpaper transition shaders load only while a transition image is pending or animating.
- [x] Wallpaper background fill-mode settings are mapped to matching `Image` fill modes for idle rendering.

### Wallpaper panel and settings helpers

- [x] Current wallpaper view lookup returns `null` without panel content.
- [x] Current wallpaper view lookup returns the current screen repeater item.
- [x] Current grid lookup returns the current wallpaper view grid and fails closed to `null` without a current grid.
- [x] Local and Wallhaven grids recreate delegates after model clearing and reassignment, preserving model paths/IDs, selection, navigation, and monitor options.
- [x] Local and Wallhaven vertical scrollbars follow their grid's effective layout mirroring, moving left when mirrored and right when restored.
- [x] Wallpaper interval preset selection persists the selected interval, restarts the random wallpaper timer, and hides the custom interval control.
- [x] Wallpaper interval selection reports selected state only for the current interval.

### Wallhaven search and download

- [x] Wallhaven wallpaper and thumbnail URL helpers declare string return types.
- [x] Wallhaven thumbnail URL helper uses a typed string size input.
- [x] Wallhaven search uses typed query string and page integer inputs.
- [x] Wallhaven search ignores duplicate requests while fetching.
- [x] Wallhaven search clears scheduled initial search state, resets public request state, encodes query text, includes base filters, conditionally includes `topRange` and `seed`, includes the page, and issues a GET request.
- [x] Wallhaven search clears fetching only after request completion and handles response state through the request completion path.
- [x] Wallhaven search handles concrete success, invalid-shape, parse-failure, rate-limit, and generic API-error fixtures.
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

- `Tests/layer-bar-owner-warnings.test.py backgrounds` covers unified bar/panel backgrounds, not wallpaper rendering: after `ead749abf`, AllBackgrounds owner warnings drop 17→0 with zero target lint warnings. Two offscreen behavioral cases assert panel/bar color and geometry updates, canvas sizing, uncovered transparent-canvas samples revealing a changed underlay, and synthetic pointer pass-through. The input-region assertion checks only an inert fixture property; no compositor pixel/input-region or wallpaper resource proof. Invocation and safety: [testing](testing.md#background-and-widget-loader-owners).
- Setup wallpaper scanner/selection evidence at `9d8cac1b3`: seven isolated cases and 7→0 target warnings. Real Process/StdioCollector consumes synthetic stdout, not wallpaper files; no real wallpaper load/application, config access, network, or resource proof. Exact coverage and wrong-collector negative-control limits: [setup wizard](setup-wizard.md#setup-wallpaper-isolated-evidence); sandbox/gates: [testing](testing.md#setup-wallpaper-isolated-runtime).
- `Tests/overview-warnings.test.py` and `Tests/Qml/OverviewWarningsHarness.qml` — at `482c044af`/`86a50071b`, Background Overview warnings drop 5→0. The nonexistent destruction-time `timerDisableFx.stop()` is removed; the delegate uses required `ShellScreen modelData`, a typed monitor name, and explicit panel ownership for wallpaper callbacks/image source. Three isolated behavioral cases cover two screen sizes and resize, namespace/image/overlay geometry and dark-mode color, matching/unmatched monitor signals, all three enable gates, Loader recreation, and screen-list removal/readdition. Cover-anchor, overview-enable, and image-geometry mutations must fail their designated cases. Production Loader/bindings/callbacks run; Variants uses Qt Instantiator, PanelWindow is invisible, and image decoding/layer-shell are inert. Commands, sandbox and gates: [testing](testing.md#background-overview-isolated-runtime). No real wallpaper resources, config persistence, compositor routing, blur pixels, memory/resource-use or canonical-runtime proof; no live wallpaper retest.
- `Tests/background-resource-guards.test.js`
- `Tests/background-warnings.test.py` — standalone `lint` retains exactly 46 diagnostics (42 unqualified Component captures, four missing-property), down from 58 at `6c7c733ca`; rejects known-owner unqualified accesses and block-scoped `var`. Five isolated offscreen `runtime` cases cover size/fill-mode calculations, decode-size assignment before source, shader Component context, transition completion without decoding, and settings/random-selection helpers. Production layer-shell declarations are removed and PanelWindow is an invisible fixture Window; services/settings are inert and writable paths isolated. Requires exit status zero, `0 failed`, no logged `QWARN`, `QFATAL`, `ReferenceError`, `TypeError`, or `Binding loop`, and unchanged real settings after a permission-locked, hash-verified backup. No shader-pixel, actual image-decode, output-routing, or live memory proof. Idle shader unload remains unproved: the existing empty URL/string strict comparison keeps the shader active; the harness reports this blocker rather than failing or fixing it.
- `Tests/wallpaper-service-guards.test.js`
- `Tests/wallpaper-service-warnings.test.py` and `Tests/Qml/WallpaperServiceHarness.qml` — through `6160beab3`, `2367970a8`, and `0d9a94fc5`, six isolated behavioral cases cover random-timer routing, changed/unchanged/empty/all-screen wallpaper signals and debounced cache state, scanner Loading/Ready/Null list updates, screen removal/recreation with directory-signal routing after disposal, recursive scan replacement/success/failure cleanup, and cache load/failure. Staged `--mutation signal` and `--mutation list` controls omit notification or list updates and must fail; they are negative controls, not acceptance modes. Service-only JSON diagnostic scope retains 18 `unqualified`, 30 hoisting, and one unresolved-type warning; lint gates proven lexical-owner accesses, not zero warnings or exact residual counts. Harness lint is a separate zero-warning fixture gate. Safety, invocation, and proof limits: [testing](testing.md#wallpaper-service-isolated-runtime).
- `Tests/wallhaven-service-guards.test.js`
- `Tests/wallpaper-panel-guards.test.js`
- `Tests/wallpaper-panel-warnings.test.py` and `Tests/Qml/WallpaperPanelWarningsHarness.qml` — at `fa33b0937`/`69c3fbbc4`, WallpaperPanel warnings drop 6→0 with `ComponentBehavior: Bound`; panel-only lint requires zero warnings and exit status zero. Seven offscreen behavioral cases plus QtTest setup/cleanup cover fuzzy filtering, refresh/screen roles, model clear/reassignment, local keyboard/tap selection, navigation, monitor/filename options, scrollbar mirroring, Wallhaven search/resolution/download/pagination/error state, and disposal with pending debounce. Two panel instances recreate content and verify their own screen routing, columns, filters, tabs, settings and close actions. `--mode runtime --mutation` forces both grid screen bindings to the first screen: a wrong-screen failing negative control, not acceptance. Images are inert and wallpaper paths nonexistent; downloads are synchronous fixtures. Commands, diagnostic gates and config/resource/network isolation: [testing](testing.md#wallpaper-panel-isolated-runtime). No real wallpaper loading/application, persistence, network service, compositor, resource-use or whole-shell proof; no live wallpaper retest.
- `Tests/wallpaper-tab-guards.test.js`
- `Tests/wallpaper-tab-warnings.test.py` and `Tests/Qml/WallpaperTabWarningsHarness.qml` — at `4484e33f0`, WallpaperTab diagnostics drop 11→1; the outer `screen` owner at line 77 remains unqualified and unproved. Five behavioral cases plus QtTest init/cleanup yield seven reported offscreen passes: management/overview/random visibility, selections across reopen, preset clicks and valid/invalid custom intervals, two-instance delegate ownership, and main/monitor folder routing with empty selections. The inverted management-switch mutation is a reported failing negative control, not acceptance. Real controls run with fixture settings/services and a non-enumerating picker; no real persistence, wallpaper application, image/resource, compositor, or live memory proof. Audit and bubblewrap isolation, commands, and gates: [testing](testing.md#wallpaper-tab-isolated-runtime). No live wallpaper retest.
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] Add executable tests for actual wallpaper file acceptance/rejection and image-extension filtering.
- [ ] Extend isolated background helper/transition coverage to actual image decoding, shader pixels, and output routing; transition completion with empty sources is not rendered-transition proof.
- [ ] Prove idle shader unloading; current isolated case is blocked by the existing empty URL/string strict comparison. Wallpaper memory testing remains closed without new evidence reopening it; neither wallpaper warning cleanup nor unified-background owner cleanup supplies such evidence.
- [ ] Extend wallpaper panel action coverage to real styled-control interaction and asynchronous download completion after disposal; current isolated coverage uses fixture controls and synchronous fake downloads.

## Out of scope

- Theme color extraction from wallpapers belongs in a separate theme/color spec.
- Shell background layout outside wallpaper-specific behavior belongs in a separate background spec if it grows beyond wallpaper rendering.
