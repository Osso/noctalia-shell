Control Center covers the panel card loader, shortcut widget registry, shortcut/card settings helpers, IPC opening behavior, and typed delegate contracts. Runtime source lives mainly in `Modules/Panels/ControlCenter/`, `Services/UI/ControlCenterWidgetRegistry.qml`, and `Modules/Panels/Settings/Tabs/ControlCenterTab.qml`; implementation notes belong in [docs/wiki/systems/control-center.md](../wiki/systems/control-center.md).

## What it must do

### Panel cards

- [x] Default Control Center cards in settings must be loadable by `ControlCenterPanel`.
- [x] Default Control Center cards must have matching height switch entries.
- [x] Control Center card delegates expose typed card id and enabled aliases before activation and source selection.
- [x] Card delegates use typed aliases instead of repeated dynamic `modelData.id` and `modelData.enabled` reads.

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

- `Tests/control-center-tab-guards.test.js`
- `Tests/control-center-widget-registry-guards.test.js`
- `Tests/widget-registry.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for Control Center panel rendered card ordering.
- [ ] Add executable coverage for Control Center widget loader failure states.
- [ ] Add executable coverage for individual Control Center shortcut widget activation paths not already covered by feature specs.
- [ ] Add executable coverage for Control Center panel placement across bar positions.

## Out of scope

- Bar button toggling behavior belongs in [bar.md](bar.md).
- Feature-specific shortcut behavior belongs in the corresponding specs, such as [bluetooth.md](bluetooth.md), [power-profile.md](power-profile.md), [screen-recorder.md](screen-recorder.md), [network.md](network.md), and [wallpaper.md](wallpaper.md).
