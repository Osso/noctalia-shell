Settings covers persisted shell configuration, startup bootstrap and recovery, default settings generation, versioned migrations, widget-setting upgrades, the Settings panel navigation shell, and broad validation that QML settings references exist in defaults. Runtime source lives mainly in `Commons/Settings.qml` and `Modules/Panels/Settings/SettingsPanel.qml`; implementation notes belong in [docs/wiki/systems/settings.md](../wiki/systems/settings.md).

## What it must do

### Settings singleton

- [x] Settings bootstrap starts in a directory-preparation state; primary validation/default/hydration `FileView`s are lifecycle-scoped, and the full shell remains gated until `Settings.ready`.
- [x] Settings loading validates raw JSON, snapshots the original bytes in cache, verifies the snapshot by reading it back, and hydrates the primary `JsonAdapter` only from that verified snapshot; corrupt or non-object JSON must enter an explicit error state without writing the primary settings path.
- [x] Missing settings may create defaults only before the first successful load; later deletion or failure must not silently recreate configuration.
- [x] Validation, default creation, and hydration callbacks must ignore stale loader generations.
- [x] Successful snapshot hydration runs migrations, marks settings ready, and permits full-shell construction; ready-state persistence uses a write-only `FileView` and a separate raw-file watcher.
- [x] A settings file change after readiness is re-read and canonicalized with recursively sorted object keys before comparison; key-order-only differences and matching current-adapter or persisted content are ignored, save-owned watcher events defer to verified read-back, while divergent or invalid external content unloads the full shell and starts a new validation generation.
- [x] After an error, settings remains in the explicit error state until the user requests Retry; retry starts a new generation and performs read-only validation, except that a first-run missing file may trigger default creation and incomplete directory preparation may be retried.
- [x] Path preprocessing expands `~` and `~/...` using `$HOME`, leaves absolute/empty strings unchanged, and preserves non-string values.
- [x] Immediate saves write only the primary settings adapter; overlapping requests preserve the in-flight snapshot, queue one follow-up, and emit `settingsSaved` only after a current-generation read-back canonicalizes to the actual `JsonAdapter` serialization before processing the queued current adapter state.
- [x] Default settings generation converts the adapter to a plain object, base64-encodes it, and writes `Assets/settings-default.json` through a detached shell command.
- [x] Versioned migrations run only migrations newer than the current settings version.
- [x] Versioned migrations pass the root object, settings adapter, and logger to migration objects.
- [x] Versioned migrations destroy migration instances after use, log failed migrations, and log invalid migration objects.
- [x] Migration failures do not publish partially hydrated settings: all newer migrations are attempted and cleaned up, but any failed, invalid, or throwing migration leaves bootstrap in `Error` before `Ready`.
- [ ] `Settings.data` aliases a separate `SettingsData` `JsonAdapter`; persisted schema/default values live in `Commons/SettingsData.qml`, shared non-persisted constants live in `Helpers/SettingsDefaults.js`, and lifecycle, persistence, migration, and upgrade orchestration remain in `Commons/Settings.qml`.
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

- [x] The integrated inline `JsonObject` schema exposes declared fields in every settings group through the `Settings.data` alias, including enclosing `bar`, nested `bar.widgets`, and `controlCenter.shortcuts`.
- [x] Typed groups retain exact default and mutated JsonAdapter serialization, load/save/fresh-process reload behavior, unknown schema-key omission, and arbitrary nested widget and shortcut arrays.
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
- [x] Main screen settings panel placeholder references are typed as the Item-derived `Backgrounds.BackgroundRegion`, retaining geometry and four integer corner-state properties.

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

- `Commons/Settings.qml` - persisted settings singleton, bootstrap state machine, lifecycle-scoped primary file adapters, default generation, migrations, and settings upgrades.
- `Commons/SettingsData.qml` - declarative `JsonAdapter` schema and default settings values.
- `Helpers/SettingsDefaults.js` - shared non-persisted settings constants used by the singleton and adapter defaults.
- `Modules/Startup/SettingsLoadError.qml` - standalone settings-independent startup error surface.
- `shell.qml` - mutually exclusive startup error and full-shell activation.
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

- `9b40f9ff9`/`9a80fb4f7`: `Tests/settings-types.test.py lint-harness` checks its exact runtime stage with native FileView/JsonAdapter, private serialization and fail-closed semantic injection. The staged adapter metadata correction changes no persistence contract; [fixture audit and limits](testing.md#final-fixture-staging-audit).

- `Tests/settings-types-isolated.test.py` — settings-type entrypoint host-access denial, private subprocess completion and fixture byte/permission tamper rejection.

- `Tests/settings-types.test.py` — isolated offscreen production SettingsData contract: exact default/mutated/group JSON fixtures, load/save/fresh-process reload, unknown-key omission, nested arrays, and targeted qmllint alias probes; not canonical hot-reload coverage. At `d21cd2d27`, synthetic HOME contains fixture-owned `0600` settings checked for unchanged bytes/mode, with a separate private serialization file and no canonical settings read. Isolation and tamper-rejection regression: [testing](testing.md).
- `Tests/settings-singleton-warnings.test.py` — standalone `runtime` runs the actual Settings singleton offscreen: validated byte-preserving snapshots, overlapping immediate saves with verified read-back, external reload, malformed startup/watcher errors, explicit repaired retry, and first-run defaults. Logger/registry/OSD are fixtures; no full-shell or canonical hot-reload proof. Historical standalone `lint` accepted two residual warnings (46→2 at `e212e6081`); `159c2d307` removes the `saveTimer` owner warning. Current scoped residual acceptance is documented under [testing](testing.md#residual-singleton-owners); `Qt.application.font` metadata remains, not warning-free acceptance.
- `Tests/service-probes-settings.test.py` — five focused tests validate the defaults-derived representative private service-probe fixture with the unchanged key/shape predicates, including missing/extra keys and invalid shapes. At `cb08dc6c6`/`971b5575d`, this deliberately replaces canonical live-settings validation, not a silent skip; sandbox traces assert zero host-settings file-syscall attempts. Isolation, integrity, cleanup and failure coverage: [testing](testing.md#tests-asserting-this-spec).
- `Tests/settings-service-guards.test.js` — `64b6441d7`/`78bb2329f`/`38dbacc56` execute extracted production nested FileView handlers, bindings and bootstrap/save functions with mock adapters, generation properties and I/O. Checks snapshot hydration, stale callbacks, queued watcher reload/read/error ordering, no-op/overlapping saves and path preprocessing. Source/declaration checks remain structural; no real FileView, persistence or process-lifetime proof.
- `Tests/shell-setup-wizard-guards.test.js`
- `Tests/migration26-guards.test.js`
- `Tests/widget-registry.test.js`
- `Tests/settings-panel-guards.test.js`
- `Tests/settings-panel-warnings.test.py` — standalone `lint` requires zero SettingsPanel qmllint warnings and exit status zero (35→0 at `185ed644e`). Standalone `behavior --artifacts <new-directory>` runs actual SettingsPanel, SmartPanel, Settings/SettingsData, and panel controls offscreen with inert tab bodies/services. It visits all 21 tabs, checks ordered labels, loaded fixture content and sidebar selection/model roles, forward/backward wrap, page/small-step scroll movement, close-button teardown, delayed dirty-setting persistence/read-back, requested Audio-tab reopen, and Escape close. Final isolated JSON must contain only the expected font change. Direct helper/signal calls are not physical keyboard/pointer input; tab feature UIs, desktop services, whole-shell construction, canonical reload, and real-config persistence are not covered. Safety and pass gates: [testing](testing.md).
- `Tests/settings-references.test.js`
- `Tests/about-tab-warnings.test.py` — standalone `behavior` runs production AboutTab and controls under isolated offscreen `qmltestrunner`: five version/title rows with reactive updates, release/support/contributor navigation and toast arguments, contributor reorder/rename/empty-model rendering and cached local avatar, three synthetic commit-query paths, and disposal during delayed lookup followed by reopen. Four additional divider/contributor geometry rows at widths 600/800 and scales 1/1.5 check default-zero margin stability; they are not tracked pre-change snapshot comparisons. Fifteen behavior rows plus init/cleanup yield 17 reported passes after `afdaf56ab` (11 plus init/cleanup at `d42f61e1f`). Standalone `lint` now requires zero warnings and exit status zero (31→1→0); the undefined divider margin is no longer an accepted residual. Fixture services/Process/launch capture, direct signal invocation, and local image bytes do not prove real package/git queries, browser launches, network avatars, physical input, visible panel switching, or whole-shell behavior. Safety and invocation gates: [testing](testing.md).
- `Tests/clock-settings-warnings.test.py` — standalone isolated production ClockSettings/dialog coverage includes Cancel without mutation, reopen with original values, and Apply emitting trimmed settings for the expected section/index without mutating fixture settings. Seven behavior rows plus init/cleanup yield nine reported passes; format/token/delegate coverage: [time](time.md). ClockSettings-only lint requires zero warnings (29→0 through `f16faaa1a`); this does not resolve Settings singleton diagnostics or prove disk/live-config persistence. Safety and pass gates: [testing](testing.md).
- `Tests/display-tab-warnings.test.py` — standalone isolated production DisplayTab/control coverage: six behavioral rows plus init/cleanup (eight reported passes), immediate edits, fake schedule serialization, and destroy/reopen retaining fixture values. DisplayTab has no Save/Cancel transaction; destruction does not roll back edits. DisplayTab-only lint requires zero warnings and exit status zero (29→0 through `9d3ebd292`, `758202d4d`). Monitor/rendering coverage: [brightness](brightness.md#display-settings-tab). No real settings persistence, physical input, hardware mode/DDC writes, or whole-shell proof; safety and invocation gates: [testing](testing.md#display-settings-tab).
- `Tests/bar-tab-warnings.test.py` — standalone BarTab-only lint requires zero warnings/exit status zero (20→0 through `995514d7e`, `b675d1046`). Four isolated actual-tab behavioral cases plus init/cleanup yield six reported passes, including monitor/placement/density controls and dialog Cancel/Apply against fixture settings, with no immediate save request. Section/registry coverage: [bar](bar.md#tests-asserting-this-spec). Direct signals/helpers and fake registry/editor/services do not prove physical input/drag, real persistence, or whole-shell integration; safety and invocation: [testing](testing.md#bar-settings-tab).
- `Tests/settings-ui-helper-guards.test.js` — at `64b6441d7`, executes production AboutTab, BatterySettings, Changelog, ClockSettings, WallhavenSettings and scroll helpers with mock process/device/locale/input/search/flickable objects. Asserts outputs and state, not source shape as behavior; retained declaration checks are structural, not offscreen UI integration.
- `Tests/qml-type-annotations.test.js`

## Known gaps (current cycle)

- [x] Add executable JavaScript state-transition coverage for settings validation, stale callbacks, readiness, invalidation, and retry behavior.
- [ ] Verify typed settings integration across canonical hot auto-reload; isolated fresh-process fixtures do not cover this boundary. See [maintenance caveat](../local/maintenance.md#typed-settings-integration).
- [x] Add non-visible isolated actual-singleton `Process`/`FileView` coverage for bootstrap snapshots, load/save signals and read-back, file watching, malformed input, retry, and first-run defaults (`5e5dcd8af`, `e212e6081`); real settings remain unchanged.
- [ ] Extend lifecycle proof to full-shell construction/unloading gates, stale-generation races, and migration failures. The singleton harness uses fixture dependencies and immediate saves only; the isolated panel harness additionally proves delayed dirty-setting persistence across close/reopen, not arbitrary delayed-save races. Never point either at the real config or desktop runtime.
- [ ] Resolve residual `Qt.application.font` metadata (`missing-property`); `159c2d307` removes the cross-component `saveTimer` owner diagnostic (1→0).
- `Tests/residual-singleton-owners.test.py runtime` — offscreen actual-singleton deferred persistence and fresh-process hydration preserve `audio.volumeStep = 17` and `ui.fontDefault = "Owner Fixture Sans"`, including callback-local owner-shadow variants. Real settings access is denied, not audited by reading or backing up the file. Shared gates and limits: [testing](testing.md#residual-singleton-owners).
- [x] Add isolated offscreen actual-panel coverage for all 21 tab selections, scrolling, close/reopen, and dirty persistence (`185ed644e`), with inert tab bodies/services.
- [ ] Verify visible desktop rendering, physical input, and production tab-body/service integration; offscreen helper/signal-driven coverage does not establish these.
- [ ] Split feature-specific settings tab behavior into each feature spec when the tab has enough direct tests.

## Out of scope

- Bar widget add/remove/reorder settings behavior belongs in [bar.md](bar.md).
- Battery, wallpaper, changelog, and other feature-specific settings semantics belong in their feature specs when they are not shared settings-shell behavior.
