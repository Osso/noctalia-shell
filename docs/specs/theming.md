Theming covers color scheme discovery/application, wallpaper and predefined theme generation, Matugen template processing, template registry assets, and Color Scheme settings UI helpers. Runtime source lives mainly in `Services/Theming/ColorSchemeService.qml`, `Services/Theming/AppThemeService.qml`, `Services/Theming/TemplateProcessor.qml`, `Services/Theming/TemplateRegistry.qml`, and `Modules/Panels/Settings/Tabs/ColorScheme/`; implementation notes belong in [docs/wiki/systems/theming.md](../wiki/systems/theming.md).

## What it must do

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
- [x] Scheme deletion only deletes from the downloaded scheme directory, detects active-scheme deletion, resets to the default scheme when needed, reloads schemes, notifies success/failure, and manages the delete process lifecycle.
- [x] Scheme color prefetch runs only while visible with available schemes, defers work, and skips already cached scheme colors.

## How it works

- [docs/wiki/systems/theming.md](../wiki/systems/theming.md)

## Implementation inventory

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

- `Tests/color-scheme-service-guards.test.js`
- `Tests/app-theme-service-guards.test.js`
- `Tests/template-processor-guards.test.js`
- `Tests/template-registry-guards.test.js`
- `Tests/template-registry.test.js`
- `Tests/color-schemes.test.js`
- `Tests/color-scheme-tab-guards.test.js`
- `Tests/scheme-downloader-guards.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for real Matugen command success/failure parsing.
- [ ] Add executable coverage for rendered Color Scheme tab states.
- [ ] Add executable coverage for downloaded scheme archive/path sanitization.
- [ ] Add executable coverage for user-template TOML parsing beyond bootstrap file creation.

## Out of scope

- Wallpaper selection and wallpaper file scanning belong in [wallpaper.md](wallpaper.md).
- Theme icon lookup and desktop-entry icon fallbacks should get a separate icon/theme utility spec.
