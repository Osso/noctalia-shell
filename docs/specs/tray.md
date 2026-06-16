Tray covers the bar tray widget, tray menu popup, tray drawer panel, pinned/blacklisted item filtering, and typed tray menu references. Runtime source lives mainly in `Modules/Bar/Widgets/Tray.qml`, `Modules/Bar/Extras/TrayMenu.qml`, and `Modules/Panels/Tray/TrayDrawerPanel.qml`; implementation notes belong in [docs/wiki/systems/tray.md](../wiki/systems/tray.md).

## What it must do

### Tray widget filtering

- [x] Tray wildcard matching is case-insensitive, supports `*`, escapes literal regex characters, and fails closed for empty input or empty rules.
- [x] Tray filtering skips null items and blacklisted items.
- [x] When the drawer is disabled, all non-blacklisted tray items render inline.
- [x] When the drawer is enabled, pinned items render inline and unpinned items move to the dropdown list.
- [x] Without pinned rules, drawer mode keeps all non-blacklisted items in the dropdown.
- [x] Filter updates are debounced through the update timer.

### Drawer behavior

- [x] Toggling the drawer hides tooltips before opening.
- [x] Toggling the drawer closes any visible popup menu.
- [x] Toggling the drawer resolves `trayDrawerPanel` for the current screen, passes widget section/index metadata, and delegates panel toggle.
- [x] Tray drawer pinned matching accepts tooltip title, name, and id, uses wildcard rules, and fails closed for empty pinned lists or missing items.

### Tray menu popup

- [x] Tray menu show rejects missing anchors with a warning.
- [x] Tray menu show waits for menu children before positioning and retries later.
- [x] Tray menu show records anchor item and coordinates, updates the popup anchor, focuses the popup, and makes it visible.
- [x] Hiding the tray menu destroys nested submenus.
- [x] Pinning validates tray item identity, widget section/index, and Tray widget type before mutation.
- [x] Pinning persists the item name, saves settings immediately, and closes the tray drawer.
- [x] Invalid pin inputs log warnings and do not save settings.
- [x] Removing a pinned item filters every matching item name and saves settings immediately.

### Types

- [x] Tray menu item references are typed.
- [x] Tray submenu references are typed.
- [x] Tray menu loader references are typed in both the tray widget and tray drawer.
- [x] Tray popup menu window references are typed in both the tray widget and tray drawer.
- [x] Tray settings blacklist delegate roles are typed.

## How it works

- [docs/wiki/systems/tray.md](../wiki/systems/tray.md)

## Implementation inventory

- `Modules/Bar/Widgets/Tray.qml` - bar tray widget, item filtering, pinned/dropdown split, and drawer toggle.
- `Modules/Bar/Extras/TrayMenu.qml` - tray menu popup, nested submenu cleanup, and pin/unpin actions.
- `Modules/Panels/Tray/TrayDrawerPanel.qml` - drawer panel and pinned matching for dropdown items.
- `Modules/Panels/Settings/Bar/WidgetSettings/TraySettings.qml` - tray blacklist and drawer settings UI.
- `Services/UI/PanelService.qml` - tray drawer panel lookup.
- `Assets/settings-default.json` - tray widget defaults, pinned items, blacklist, and drawer settings.

## Tests asserting this spec

- `Tests/tray-widget-guards.test.js`
- `Tests/tray-menu-guards.test.js`
- `Tests/bar-action-helper-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for tray icon activation and right-click menu opening.
- [ ] Add executable coverage for tray drawer rendered grid dimensions.
- [ ] Add executable coverage for blacklist settings persistence from the settings UI.
- [ ] Add executable coverage for nested submenu positioning.

## Out of scope

- Bar widget registry and placement belong in [bar.md](bar.md).
- Individual status notifier item behavior belongs to Quickshell/system tray integration and is only covered here at the shell boundary.
