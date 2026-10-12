Tray covers the bar tray widget, tray menu popup, tray drawer panel, pinned/blacklisted item filtering, and typed tray menu references. Runtime source lives mainly in `Modules/Bar/Widgets/Tray.qml`, `Modules/Bar/Extras/TrayMenu.qml`, and `Modules/Panels/Tray/TrayDrawerPanel.qml`; implementation notes belong in [docs/wiki/systems/tray.md](../wiki/systems/tray.md).

## What it must do

### Tray widget filtering

- [x] Tray wildcard matching is case-insensitive, supports `*`, escapes literal regex characters, and fails closed for empty input or empty rules.
- [x] Tray wildcard matching uses typed string inputs.
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
- [ ] Tray popup menu window references have concrete popup types in both the tray widget and tray drawer; the widget retains generic QtObject typing because the concrete import creates a cycle.
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

- `Tests/tray-drawer-resolution.test.py` and `Tests/tray-widget-resolution.test.py` — private real Quickshell resolver cold start, reload and failed-reload recovery without desktop surfaces.
- `Tests/tray-drawer-warnings.test.py` — targeted production lint and offscreen drawer Loader/delegate/icon/mouse behavior with fixture notifier/popup/settings boundaries; includes strict harness lint and private reload regression.
- `Tests/timer-tray-wallpaper-isolation.test.py` — drawer/widget runtime and lint entrypoints deny host config, preserve private fixture integrity and reject mutations.

- `Tests/tray-widget-guards.test.js`
- `Tests/tray-widget-warnings.test.py`, `Tests/Qml/TrayWidgetWarningsHarness.qml` and `Tests/tray-widget-reload.test.py`: [isolated Tray widget evidence](#tray-widget-isolated-evidence).
- `Tests/tray-menu-guards.test.js`
- `Tests/tray-menu-warnings.test.py` and `Tests/Qml/TrayMenuWarningsHarness.qml`: [isolated TrayMenu evidence](#tray-menu-isolated-evidence).
- `Tests/bar-action-helper-guards.test.js` — at `ce976459e`, drawer pin matching, pin/unpin, absent-owner and two-owner isolation execute the production helper with owner-bound fixture settings; not source-regex or live tray proof.
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

### Tray widget isolated evidence

- Through `8a1636052`/`b9b8785c8`, widget warnings drop 20→13 through a truthful `TrayMenu` binding for the loaded menu, not fixture-only metadata or warning suppression. Standalone `--mode lint` rejects unqualified accesses and QQuickLoader.item metadata warnings; it accepts exactly 12 `missing-property` and one `incompatible-type` diagnostic, with exit status 0 or 255. Concrete popup typing remains blocked by an import cycle; generic popup/Repeater metadata and external `UntypedObjectModel.values` metadata remain visible.
- `--mode runtime` and `--mode runtime --shadow` each report eight passes: six behavioral cases (two tests plus four menu-position rows) and QtTest init/cleanup. Production Tray and installed IconImage run offscreen with inert notifier/popup/settings boundaries. Coverage includes Ready/Null opacity, primary/secondary activation, only-menu inhibition, blacklist/pinned filtering, model reorder/clear/reassignment, all four menu positions, Loader recreation, popup reassignment, tooltip ownership and drawer metadata. Shadow members test owner resolution; SystemTray ordering is preserved.
- The private reload runner uses actual Tray/TrayMenu, installed Quickshell resolution and PopupWindow with an invisible owner, synthetic services/notifiers and inert controls. Reported cold-start, source reload and recovery after an intentionally invalid reload cover two owners, menu teardown/recreation, screen handoff, popup unregister/re-register and drawer routing. The failed reload is a negative control, not acceptance.
- Private HOME/XDG paths, settings-access guards and sandbox isolation exclude real config and desktop connections. Runtime retains permission-locked synthetic fixture/backup integrity checks; reload tracing requires zero settings.json attempts and termination of the private process group. Real settings are not accessed or backed up; no canonical restart/reload, native notifier/menu DBus actions, compositor placement/focus/input, real persistence or whole-shell acceptance is proven.

### Tray settings isolated evidence

- At `3a0c2e2dc`, TraySettings diagnostics drop 5→0; standalone lint requires zero warnings and exit status zero.
- `Tests/tray-settings-warnings.test.py` and `Tests/Qml/TraySettingsWarningsHarness.qml` cover the production editor offscreen. Three behavioral tests plus QtTest init/cleanup yield five reported passes: defaults/metadata and toggle save; blacklist removal, trimmed addition, duplicate/empty rejection and preserved order; copy-save retaining unrelated fields without mutating input or sharing the saved blacklist; positive row widths equal to the list width, labels and reactive toggles.
- Settings/services/controls are synthetic fixtures. Audited open/stat/lstat/readlink denial and sandbox masks make real config inaccessible, not read or backed up. No live panel, real persistence, compositor interaction or whole-shell acceptance is proven.

### Tray menu isolated evidence

- At `149effda0`/`2970c1957`, TrayMenu diagnostics drop 9→1 after enabling `ComponentBehavior: Bound`; the installed `PopupAnchor.updateAnchor` `missing-property` metadata warning remains unsuppressed. Standalone lint accepts exactly that diagnostic and exit status 0 or 255, not zero-warning acceptance.
- Four offscreen behavioral tests plus QtTest init/cleanup yield six reported passes; six existing tray-menu guard passes are separately reported. Production delegates/layout/handlers cover handle order, reorder/clear, newline normalization, disabled/separator inhibition, activation and owner drawer closure, anchor bindings, reopen/recreation after destruction, and independent popup owners with model replacement. Activation and owner mutations are reported failing negative controls, not acceptance modes.
- Popup transport, notifier handles, settings, services and leaf widgets are fixtures. Real settings are never accessed, resolved, hashed or backed up; sandbox and access audits deny access. These results do not prove native menu transport, compositor placement/focus/input, real persistence, nested submenus or whole-shell acceptance.

## Known gaps (current cycle)

- [x] Add isolated executable coverage for tray icon activation and right-click menu opening.
- [ ] Add executable coverage for tray drawer rendered grid dimensions.
- [x] Add isolated executable coverage for blacklist editing and copy-save output from the settings UI.
- [ ] Verify real blacklist persistence through the live settings panel.
- [ ] Add executable coverage for nested submenu positioning.

## Out of scope

- Bar widget registry and placement belong in [bar.md](bar.md).
- Individual status notifier item behavior belongs to Quickshell/system tray integration and is only covered here at the shell boundary.
