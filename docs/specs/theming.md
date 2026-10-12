Theming covers color scheme discovery/application, wallpaper and predefined theme generation, Matugen template processing, template registry assets, and Color Scheme settings UI helpers. Runtime source lives mainly in `Services/Theming/ColorSchemeService.qml`, `Services/Theming/AppThemeService.qml`, `Services/Theming/TemplateProcessor.qml`, `Services/Theming/TemplateRegistry.qml`, and `Modules/Panels/Settings/Tabs/ColorScheme/`; implementation notes belong in [docs/wiki/systems/theming.md](../wiki/systems/theming.md).

## What it must do

### Project palette namespace

- [x] Project palette bindings resolve to `NColor`, distinct from QtQuick's `Color` singleton, including on Qt 6.12.
- [x] Transparent window bindings retain zero alpha and palette bindings retain their configured colors.
- [x] The namespace regression runs in `./run-tests.sh unit` offscreen with isolated writable paths and stubbed settings, without accessing the user's configuration or desktop.
- [x] The harness verifies zero window alpha, default `mOnSurface` color `#e9e4f0`, and a non-function `NColor.transparent`; success requires exit code zero and `COLOR_NAMESPACE_PASS` within 15 seconds.
- [x] Palette runtime cases (empty file, custom load/reload, missing-file creation, and fresh-process reload) reject every warning/error/fatal record; a success marker alone is insufficient.
- [x] Missing `colors.json` is created with default colors without runtime diagnostics. The harness waits for explicit save then load completion before exit and verifies a fresh process reload preserves file bytes.

### Color scheme service

- [x] Service initialization logs startup and triggers color scheme discovery.
- [x] Color scheme discovery resets scanning state, ensures the downloaded-schemes directory exists, scans preinstalled and downloaded scheme JSON files, and starts the finder process.
- [x] Scheme basenames fail closed for empty paths, strip directories and `.json`, and normalize built-in display names.
- [x] Scheme path resolution supports built-in and downloaded scheme locations.
- [x] Scheme application writes selected colors, updates settings, triggers template generation when templates are enabled, and reports success or missing schemes through toast/log channels.
- [x] Enabled-template detection returns true for any enabled template and false when none are enabled.
- [x] Color writes support material and plain key names with fallbacks for all required palette keys and force `colors.json` rewrite.

### App theme flow

- [x] App theme generation chooses predefined-scheme application unless wallpaper colors are enabled.
- [x] Wallpaper generation requires a wallpaper for the current screen, logs when missing, and passes wallpaper path plus dark/light mode to template processing.
- [x] Predefined scheme generation logs its flow and passes scheme data plus current dark/light mode to template processing.

### Template processing

- [x] Wallpaper-color processing builds a Matugen config, stops when no templates are enabled, escapes wallpaper paths, labels Matugen failures, and executes the generated script through bash.
- [x] Predefined-scheme processing installs predefined terminal themes, selects colors for the requested mode, processes application templates, appends user-template commands, and labels predefined failures.
- [x] Matugen config generation derives mode from dark-mode settings and includes wallpaper/application template sections based on enabled settings.
- [x] Template processing registers wallpaper and application templates from the registry.
- [x] Predefined template scripts replace colors for application templates.
- [x] Terminal theme handling and user-template commands quote paths, preserve shell variables where expected, and use Matugen `image` or `json` as appropriate.
- [x] Template error messages prefer stderr, fall back to stdout, then use translated generic descriptions and generator-specific titles.

### Template registry

- [x] User template TOML generation writes the default config header, templates section, user guidance, and placeholder example.
- [x] User template writes first check for an existing `user-templates.toml`.
- [x] User template creation makes the config directory, writes an escaped heredoc, and logs the output path.
- [x] Every Matugen template path referenced by the registry exists and is non-empty.
- [x] Every default template setting, except `enableUserTemplates`, has a registry entry.

### Color scheme assets and UI

- [x] Color scheme assets include the expected built-in scheme count.
- [x] Each built-in scheme defines dark and light palettes with the required material keys and hex colors.
- [x] Each built-in scheme ships non-empty terminal variants for Alacritty, Foot, Ghostty, Kitty, and WezTerm in dark and light modes.
- [x] Color Scheme tab caches loaded scheme JSON by name, falls back to an empty object for missing JSON, increments cache version, and delegates download popup opening to its loader.

### Scheme downloader

- [x] Scheme downloader cache loading reads ShellState, tolerates missing cached schemes, detects missing/expired cache, rate-limits API refresh, uses cached data when available, and logs cache failures.
- [x] Scheme downloader cache saving persists schemes with timestamp and logs save failures.
- [x] Scheme fetching avoids concurrent fetches, prefers loaded ShellState cache, and falls back to API when ShellState is unavailable.
- [x] Scheme tree resolution has tested fallback paths.
- [x] Scheme file download and installation checks are guarded.
- [x] Recursive sibling-directory listings retain independent request responses: reverse-order completion includes each directory's files exactly once, never completes while a sibling is pending, and invokes the final completion callback exactly once.
- [x] Scheme deletion only deletes from the downloaded scheme directory, detects active-scheme deletion, resets to the default scheme when needed, reloads schemes, notifies success/failure, and manages the delete process lifecycle.
- [x] Scheme color prefetch runs only while visible with available schemes, defers work, and skips already cached scheme colors.

### Color picker isolated evidence

- Through `90e6773e7`/`5cb2adc13`/`a4ad6de57`, `NColorPickerDialog` diagnostics drop from 12 `unqualified` plus one hoisting warning to zero. Recorded offscreen results are five passes: three behavioral tests plus QtTest init/cleanup.
- Production dialog/controls assert positive screen-bounded height, theme/named swatch selection and borders, Apply emitting exactly once, Cancel emitting nothing, and reopen updating color/RGB values.
- `Bound` ownership proof snapshots both palette models, empties/restores them to recreate delegates, and checks selection/borders remain attached to the first picker while a second retains `#654321`. Recreated tooltip enter/exit handlers are invoked directly and checked for exact name/uppercase color text and clearing; this is not physical hover proof.
- Fixtures replace services/settings/palette values; software/offscreen execution proves component lifecycle only, not live compositor placement/input, real persistence, or whole-shell rendering.

## How it works

- [docs/wiki/systems/theming.md](../wiki/systems/theming.md)

## Implementation inventory

- `Commons/NColor.qml` - project palette singleton, distinct from QtQuick's `Color`.
- `Services/Theming/ColorSchemeService.qml` - scheme discovery, selection, palette writing, and template triggering.
- `Services/Theming/AppThemeService.qml` - wallpaper/predefined theme generation coordinator.
- `Services/Theming/TemplateProcessor.qml` - Matugen config/script generation, terminal theme handling, user templates, and error reporting.
- `Services/Theming/TemplateRegistry.qml` - built-in template registry and user-template config bootstrap.
- `Modules/Panels/Settings/Tabs/ColorScheme/ColorSchemeTab.qml` - color scheme settings tab helpers and scheme cache.
- `Modules/Panels/Settings/Tabs/ColorScheme/SchemeDownloader.qml` - remote scheme cache, fetch, install, delete, and prefetch flows.
- `Assets/ColorScheme/` - built-in color scheme JSON and terminal variants.
- `Assets/MatugenTemplates/` - built-in Matugen template files.
- `Assets/settings-default.json` - template enablement defaults.

## Tests asserting this spec

- `Tests/color-picker-warnings.test.py` (`lint`, `lint-harness`, `runtime`) and `Tests/Qml/ColorPickerWarningsHarness.qml` — standalone warning/lifecycle coverage; isolation and acceptance gates: [testing](testing.md#color-picker-isolated-runtime).

- `Tests/color-namespace-runtime.test.py` - offscreen production palette/QColor binding regression, using `Tests/Qml/ColorNamespaceHarness.qml`.
- `Tests/color-scheme-service-guards.test.js`
- `Tests/color-scheme-service-behavior.test.js` - executes production service JavaScript with isolated QML boundary objects: sorted discovery and failure state, stored-name normalization, selection toasts, dark-mode reapplication, variant selection, palette writes, and template eligibility. No real settings, disk writes, processes, or desktop surfaces; not a QML runtime test.
- `Tests/app-theme-service-guards.test.js`
- `Tests/template-processor-guards.test.js`
- `Tests/template-registry-guards.test.js`
- `Tests/template-registry.test.js`
- `Tests/color-schemes.test.js`
- `Tests/color-scheme-tab-guards.test.js`
- `Tests/scheme-downloader-guards.test.js`
- `Tests/scheme-downloader-runtime.test.py runtime` - offscreen staged production downloader with synthetic XHR and file-only curl/wget fixtures; covers cache/color variants, concurrent-fetch prevention, metadata filtering/rate-limit/parse failures, branch/SHA/tree resolution, two concurrent directory responses delivered in reverse order with exact file and completion assertions, single-directory recursion, asynchronous download success/failure, delayed application, installed-path classification, and active-scheme deletion. Popup stays hidden; HOME/XDG paths and file writes are temporary, real settings are byte-checked unchanged, and no real network is used. Production Popup/Timer/Process remain real; services/widgets are fixtures, not whole-shell coverage.
- `Tests/scheme-downloader-runtime.test.py lint` - targeted production downloader analysis requires zero warnings and exit code zero; the final sibling-request hoisting warning is removed (1→0).
- `Tests/shell-state-consumer-roundtrip.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for real Matugen command success/failure parsing.
- [ ] Add executable coverage for rendered Color Scheme tab states.
- [ ] Add executable coverage for downloaded scheme archive/path sanitization.
- [ ] Add executable coverage for user-template TOML parsing beyond bootstrap file creation.

## Out of scope

- Wallpaper selection and wallpaper file scanning belong in [wallpaper.md](wallpaper.md).
- Theme icon lookup and desktop-entry icon fallbacks should get a separate icon/theme utility spec.
