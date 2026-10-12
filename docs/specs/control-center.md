Control Center covers the panel card loader, shortcut widget registry, shortcut/card settings helpers, IPC opening behavior, and typed delegate contracts. Runtime source lives mainly in `Modules/Panels/ControlCenter/`, `Services/UI/ControlCenterWidgetRegistry.qml`, and `Modules/Panels/Settings/Tabs/ControlCenterTab.qml`; implementation notes belong in [docs/wiki/systems/control-center.md](../wiki/systems/control-center.md).

## What it must do

### Panel cards

- [x] Default Control Center cards in settings must be loadable by `ControlCenterPanel`.
- [x] Default Control Center cards must have matching height switch entries.
- [x] Control Center card delegates expose typed card id and enabled aliases before activation and source selection.
- [x] Card delegates use typed aliases instead of repeated dynamic `modelData.id` and `modelData.enabled` reads.
- [x] Card loaders are active only while the Control Center panel is open, so hidden cards do not retain media/system resources after close.

### Shortcut registry

- [x] Control Center widget ids are unique.
- [x] Control Center widget registry entries reference declared components.
- [x] CustomButton is the only widget metadata entry that allows user settings.
- [x] Notifications and WallpaperSelector are present in the Control Center widget registry.
- [x] Every default Control Center shortcut id exists in `ControlCenterWidgetRegistry`.
- [x] Shortcut widget registry lookup, presence, available-list, and user-settings helpers preserve registry behavior and type widget id inputs as strings.

### Shortcut settings

- [x] Saving cards persists only card id and enabled state.
- [x] Adding a shortcut appends a widget entry to the target section.
- [x] Adding a configurable shortcut copies widget metadata except the user-settings marker.
- [x] Removing shortcuts validates index bounds and leaves invalid removes unchanged.
- [x] Reordering shortcuts validates index bounds and leaves invalid reorders unchanged.
- [x] Moving shortcuts between sections validates bounds and appends to the target section.
- [x] Updating shortcut settings replaces the indexed shortcut entry and saves immediately.
- [x] Shortcut settings dialog cancel leaves the entry unchanged; apply updates the entry and requests an immediate save.
- [x] `ShortcutsCard` left and right shortcut delegates type the shortcut id role and use it for widget loading/settings.

### IPC and placement

- [x] Control Center IPC resolves the target screen before opening the panel.
- [x] Control Center IPC respects the `close_to_bar_button` position setting.
- [x] Control Center IPC opens near the bar button anchor when configured.

### Loader typing

- [x] Control Center widget loader screen references are typed.
- [x] MainScreen Control Center panel placeholder is typed as an `Item`.

## How it works

- [docs/wiki/systems/control-center.md](../wiki/systems/control-center.md)

## Implementation inventory

- `Modules/Panels/ControlCenter/ControlCenterPanel.qml` - Control Center panel layout, cards, and card loader.
- `Modules/Panels/ControlCenter/ControlCenterWidgetLoader.qml` - shortcut widget loading and typed screen/props plumbing.
- `Modules/Panels/ControlCenter/Widgets/` - Control Center shortcut widget implementations.
- `Modules/Cards/ShortcutsCard.qml` - left/right shortcut delegates and widget loader usage.
- `Services/UI/ControlCenterWidgetRegistry.qml` - shortcut widget component registry and metadata.
- `Modules/Panels/Settings/Tabs/ControlCenterTab.qml` - settings helpers for cards and shortcut sections.
- `Services/Control/IPCService.qml` - Control Center IPC target-screen and anchor behavior.
- `Assets/settings-default.json` - default Control Center cards and shortcuts.

## Tests asserting this spec

- At `985a57a53`, ControlCenterWidgetLoader lint remains 2→2 after the earlier 6→2 reduction at `3325e0c65`: generic QObject `screen`/`onLoaded` metadata retains two `missing-property` warnings. Production is unchanged; inspection of all 40 registered widget types across both registries found no truthful shared contract for optional screen/scaling/onLoaded members, not warning-free acceptance. `Tests/Qml/ControlCenterWidgetLoaderHarness.qml` covers property filtering and screen-before-callback order, current owner values on reload (existing widgets are not updated in place), independent owners and optional-member absence, section bindings, visibility/size geometry, missing-registry warning/zero size, and destruction clearing props. Six behavioral tests plus QtTest init/cleanup yield eight reported passes each in normal and owner-shadow offscreen runs. Synthetic widgets/screens do not prove real shortcut activation or live panel behavior. Dedicated-test accounting, nine negative controls, isolation and acceptance: [testing](testing.md#control-center-widget-loader-isolated-runtime).

- At `1e05e0ef7`, ProfileCard lint drops 6→4; four `unqualified` screen references retain caller-context lookup, not an explicit card screen contract or warning-free acceptance. `Tests/Qml/VisualizerProfileHarness.qml` asserts avatar fallback/geometry, changing display name, synthetic uptime completion and refresh, settings General-tab routing, session-menu open/control-center close ordering, close action, and resizing. The fixture supplies the caller screen; uptime Process and services are inert. No real uptime process, live desktop or persistence proof. Shared accounting and isolation: [testing](testing.md#visualizerprofile-isolated-runtime).

- Production Control Center `WidgetSettings/CustomButtonSettings.qml` editor coverage through `bb8611429`/`b0cc0dc20`: targeted lint 20→0 and four isolated command/icon/state-list/serialization-discard cases. This is not the bar ControlCenterSettings editor or outer settings dialog. Exact coverage and limits: [custom button](custom-button.md#control-center-settings-editor); diagnostic/isolation contract: [testing](testing.md#control-center-custom-button-settings-editor).

- `Tests/bar-controls-warnings.test.py` — production bar-button toggle/anchor, launcher/settings/context routing, and shader target-color bindings under colorization and dark-mode changes. This is not rendered shader pixel or panel-placement proof. Cohort evidence and limits: [bar](bar.md#bar-control-cohort), [testing](testing.md#bar-control-cohort).

- `Tests/widget-settings-cohort-warnings.test.py` / `Tests/Qml/WidgetSettingsCohortHarness.qml` — ControlCenterSettings (bar widget editor, not ControlCenterTab): distro-logo and colorization toggles, conditional color selection, and browse-button enablement. No real file-picker or image-selection proof. Each editor also exercises fixture defaults, save-copy isolation, cancel/reopen, and apply-close. Completed isolated assertions do not close the RED shared-control runtime warning gate. Cohort counts/lint evidence: [bar](bar.md#tests-asserting-this-spec); isolation and limits: [testing](testing.md#widget-settings-cohort).

- `Tests/control-center-panel-warnings.test.py` / `Tests/Qml/ControlCenterPanelWarningsHarness.qml` — at `b55847897`, panel-only static warnings drop 12→0. Four offscreen behavioral cases cover card routing/order, row geometry/scaling, independent weather-height owners, disable/weather filtering and reload, screen/position anchor bindings, and open/close loader disposal plus media/VPN fixture interactions. SmartPanel and leaf cards are inert fixtures; this is not production card rendering, compositor placement/input, or backend proof. Isolation and acceptance: [testing](testing.md#control-center-panel-isolated-runtime).
- `Tests/control-center-panel-guards.test.js`
- `Tests/control-center-tab-warnings.test.py` / `Tests/Qml/ControlCenterTabWarningsHarness.qml` — `e304d4747` reduces ControlCenterTab-only lint 22→0. Four behavioral cases plus QtTest initialization/cleanup yield six cases: initial card completion/sorted registry/section geometry at widths 600/900, card toggle/reorder/weather notification, position selection and shortcut add/remove/reorder/move with invalid-index no-ops, and dialog cancel/apply with an inert editor/save counter. Initial card rows have zero height until model replacement; this is an asserted unchanged limitation, not new behavior or rendered card-order proof. Direct control/helper/signal calls do not establish physical input or real settings persistence. Isolation and acceptance: [testing](testing.md#controlcentertab-isolated-runtime).
- `Tests/control-center-tab-guards.test.js`
- `Tests/control-center-widget-registry-guards.test.js`
- `Tests/widget-registry.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/source-coverage.test.js`
- AudioCard isolated volume/mute/device-switch/disposal coverage and fixture limits: [audio](audio.md#tests-asserting-this-spec).
- `Tests/main-screen-warnings.test.py runtime` includes the Control Center loader among 17 production MainScreen lifecycle cases: registration, unloaded placeholder, caller context/name and screen routing, region handoff, open/closing state, keyboard focus, reopen reuse, and destruction cleanup. Panel content and PanelService are fixtures; this does not test Control Center cards or placement. Shared host coverage and residual diagnostics: [smart panel](smart-panel.md#tests-asserting-this-spec).

## Known gaps (current cycle)

- [ ] Add executable coverage for Control Center panel rendered card ordering.
- [ ] Add executable coverage for Control Center widget loader component-load failures beyond the covered missing-registry case.
- [ ] Add executable coverage for individual Control Center shortcut widget activation paths not already covered by feature specs.
- [ ] Add executable coverage for Control Center panel placement across bar positions.

## Out of scope

- Bar button toggling behavior belongs in [bar.md](bar.md).
- Custom button state-check validation, debounce, stale async result handling, and isolated synthetic coverage belong in [custom-button.md](custom-button.md).
- Feature-specific shortcut behavior belongs in the corresponding specs, such as [bluetooth.md](bluetooth.md), [power-profile.md](power-profile.md), [screen-recorder.md](screen-recorder.md), [network.md](network.md), and [wallpaper.md](wallpaper.md).
