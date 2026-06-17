Settings covers persisted shell configuration, default settings generation, versioned migrations, widget-setting upgrades, the Settings panel navigation shell, and broad validation that QML settings references exist in defaults. Runtime source lives mainly in `Commons/Settings.qml` and `Modules/Panels/Settings/SettingsPanel.qml`; implementation notes belong in [docs/wiki/systems/settings.md](../wiki/systems/settings.md).

## What it must do

### Settings singleton

- [x] Path preprocessing expands `~` and `~/...` using `$HOME`, leaves absolute/empty strings unchanged, and preserves non-string values.
- [x] Immediate saves write the primary settings adapter, write the fallback adapter only when `NOCTALIA_SETTINGS_FALLBACK` is configured, and emit `settingsSaved`.
- [x] Default settings generation converts the adapter to a plain object, base64-encodes it, and writes `Assets/settings-default.json` through a detached shell command.
- [x] Versioned migrations run only migrations newer than the current settings version.
- [x] Versioned migrations pass the root object, settings adapter, and logger to migration objects.
- [x] Versioned migrations destroy migration instances after use, log failed migrations, and log invalid migration objects.
- [x] Widget upgrades prune stale keys, preserve existing valid values, add missing metadata defaults, and report whether a mutation happened.
- [x] Settings-data upgrade defers with a warning until the BarWidgetRegistry is ready.
- [x] Settings-data upgrade removes invalid bar widgets, upgrades valid widgets, guarantees a Control Center widget exists, and logs the mutations.

### Versioned calendar migration

- [x] Migration 26 replaces legacy `banner-card` and `calendar-card` entries with `calendar-header-card` and `calendar-month-card`.
- [x] Migration 26 preserves non-calendar cards and their enabled state.
- [x] Migration 26 enables both split calendar cards when any legacy calendar card was enabled.
- [x] Migration 26 disables both split calendar cards when all legacy calendar cards were disabled.
- [x] Migration 26 leaves adapters without calendar card settings otherwise untouched.
- [x] Migration 26 logs the migration start and legacy-card replacement.
- [x] Default calendar card ids must either be loadable by the current calendar panel or handled by Migration 26.

### Settings references and defaults

- [x] QML `Settings.data.*` references outside `Commons/Settings.qml` must exist in `Assets/settings-default.json`.
- [x] Settings reference coverage must stay broad enough to catch project-wide drift, not only a small fixture set.

### Settings panel shell

- [x] Settings panel tab model builds an ordered list containing General, User Interface, Bar, Control Center, Session Menu, System Monitor, and About tabs, then publishes it.
- [x] Settings panel scroll helpers require an active vertical scrollbar.
- [x] Settings panel small-step scrolling moves 10 percent of viewport height and clamps to scrollbar boundaries.
- [x] Settings panel page scrolling moves one page and clamps to top/bottom boundaries.
- [x] Settings panel keyboard handlers route Tab/BackTab/PageDown/PageUp to the shared tab and scroll helpers.
- [x] Settings tab navigation wraps next/previous tab selection and ignores empty tab models.
- [x] Settings panel active scroll view and tab delegates are typed.

### Monitor and delegate typing

- [x] Shared monitor settings repeaters type `modelData` as `ShellScreen`.
- [x] BarTab monitor delegates expose typed aliases for screen name, model, width, and height before label, scale, description, selection, and add/remove actions.
- [x] Settings-related combo box delegates type parent and index roles.
- [x] Main screen settings panel placeholder references are typed as `Item`.

### Settings UI helpers

- [x] About tab git commit lookup skips missing shell directories and starts the process in the shell directory when present.
- [x] Battery widget settings device models filter line-power devices.
- [x] Changelog release-date formatting handles empty, invalid, and valid dates.
- [x] Clock widget settings token insertion defaults to the horizontal input.
- [x] Clock widget settings token insertion uses a typed token input.
- [x] Date/time token picker category color selection uses a typed category input.
- [x] Wallhaven settings resolution updates exact/minimum resolution state and optionally triggers search.
- [x] Scroll view setup updates only flickable children and applies bounds, direction, and content-width binding.

## How it works

- [docs/wiki/systems/settings.md](../wiki/systems/settings.md)

## Implementation inventory

- `Commons/Settings.qml` - persisted settings singleton, file adapters, default generation, migrations, and settings upgrades.
- `Commons/Migrations/MigrationRegistry.qml` - version-to-migration component registry.
- `Commons/Migrations/Migration26.qml` - legacy calendar card migration.
- `Assets/settings-default.json` - canonical default settings shape used by reference validation.
- `Modules/Panels/Settings/SettingsPanel.qml` - Settings panel shell, tab model, keyboard navigation, and scrolling helpers.
- `Modules/Panels/Settings/Tabs/*.qml` - settings tab UIs backed by `Settings.data`.
- `Modules/Panels/Settings/Bar/WidgetSettings/*.qml` - per-widget settings panes opened from bar/widget settings flows.
- `Modules/Panels/Changelog/ChangelogPanel.qml` - changelog date formatting used by settings-adjacent UI.
- `Modules/Panels/Wallpaper/WallhavenSettingsPopup.qml` - Wallhaven settings popup helper behavior.
- `Widgets/NScrollView.qml` - shared scroll-view setup used by settings panels.

## Tests asserting this spec

- `Tests/settings-service-guards.test.js`
- `Tests/migration26-guards.test.js`
- `Tests/widget-registry.test.js`
- `Tests/settings-panel-guards.test.js`
- `Tests/settings-references.test.js`
- `Tests/settings-ui-helper-guards.test.js`
- `Tests/qml-type-annotations.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for settings file load failure and recovery behavior.
- [ ] Add executable coverage for fallback settings file loading, not only fallback writes.
- [ ] Add executable coverage for visible Settings panel rendering and tab switching.
- [ ] Split feature-specific settings tab behavior into each feature spec when the tab has enough direct tests.

## Out of scope

- Bar widget add/remove/reorder settings behavior belongs in [bar.md](bar.md).
- Battery, wallpaper, changelog, and other feature-specific settings semantics belong in their feature specs when they are not shared settings-shell behavior.
