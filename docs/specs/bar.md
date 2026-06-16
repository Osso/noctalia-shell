Bar covers the multi-monitor shell bar, the bar widget registry, registered widget lookup, bar widget settings, and the bar settings tab. Runtime source lives mainly in `Modules/Bar/Bar.qml`, `Services/UI/BarService.qml`, and `Services/UI/BarWidgetRegistry.qml`; implementation notes belong in [docs/wiki/systems/bar.md](../wiki/systems/bar.md).

## What it must do

### Bar shell

- [x] Control Center toggling fails closed when the panel is unavailable.
- [x] Control Center toggling uses the bar-button anchor hint when settings request `close_to_bar_button`.
- [x] Control Center toggling falls back to the default panel toggle when the panel is configured away from the bar button.
- [x] Widget loader implicit size rounds visible item sizes.
- [x] Widget loader implicit size returns zero for missing or hidden items.
- [x] Bar widget loader screen references and widget-id delegate aliases are typed.

### Bar service

- [x] Bar registration marks each screen ready once and emits readiness changes.
- [x] Bar readiness lookup fails closed for unknown screens.
- [x] Widget registration uses a stable `screen|section|widget|index` key, stores widget metadata and instance, rescans visualizer state, and emits active widget changes.
- [x] Widget unregistration uses the same stable key, deletes the widget, and emits active widget changes.
- [x] Widget lookup supports exact screen/section/index matching, filtered fallback lookup, and returns `undefined` for misses.
- [x] Widget enumeration can filter by widget id, screen, and section while returning instances only.
- [x] Metadata lookup returns the full widget record or `undefined`.
- [x] Section lookup sorts widgets by stored index.
- [x] Registered-widget enumeration exposes key, widget id, section, screen name, and index for debug/settings consumers.
- [x] Widget presence checks support optional section and screen filters.
- [x] Pill direction, tooltip direction, and context menu position follow bar side/orientation and fail closed for missing anchors.
- [x] Widget settings dialogs use the target screen popup window, fail closed without it, load the shared settings dialog component, pass widget context, merge updates, save immediately, mark dialog ownership, clean up on close, and handle ready/error/async component states.

### Widget registry

- [x] Widget lookup returns declared widget components, preserves explicit null components, and returns null for unknown ids.
- [x] Widget presence reflects registry keys, including keys whose component is currently null.
- [x] Available-widget listing reflects registry key order.
- [x] User settings are enabled only when widget metadata explicitly sets `allowUserSettings: true`.
- [x] Registry metadata has unique widget ids, references declared components, keeps settings-map and metadata keys aligned, and includes expected local widgets.

### Bar settings

- [x] Adding a widget creates a widget entry with `id`, copies configurable widget metadata, skips `allowUserSettings`, and appends to the requested section.
- [x] Removing a widget validates bounds, replaces the section with a copied array, and warns when removing the last Control Center widget.
- [x] Reordering widgets validates bounds and replaces the section with a copied reordered array.
- [x] Moving widgets between sections validates source/target data, removes from a copied source array, and appends to a copied target array.
- [x] Available-widget model rebuilds from the registry with key, name, and compact location badges.
- [x] Widget location badges fail closed without BarService, read registered widgets, map left/center/right to `L`/`C`/`R`, and deduplicate locations.
- [x] Monitor delegates use typed aliases for screen name, model, width, and height before selection and scale actions.

### Bar pill

- [x] Vertical bar pill center offset tracks open direction.
- [x] Vertical bar pill delayed show ignores collapsed icon mode.
- [x] Vertical bar pill delayed show starts the show timer when closed.
- [x] Vertical bar pill delayed show restarts delayed hide when already open.

### Probe contract

- [x] Service probes reject invalid bar positions in settings fixtures.

## How it works

- [docs/wiki/systems/bar.md](../wiki/systems/bar.md)

## Implementation inventory

- `Modules/Bar/Bar.qml` - per-screen bar shell, orientation layout, and Control Center toggle behavior.
- `Modules/Bar/Extras/BarWidgetLoader.qml` - widget component loading and implicit-size reporting.
- `Modules/Bar/Extras/BarPillVertical.qml` - vertical pill animation and offset behavior.
- `Services/UI/BarService.qml` - bar readiness, widget instance registry, lookup helpers, context menu placement, and widget settings dialog wiring.
- `Services/UI/BarWidgetRegistry.qml` - available widget components, widget settings mapping, and registry metadata.
- `Modules/Panels/Settings/Tabs/BarTab.qml` - bar settings UI helpers for adding, removing, moving, and locating widgets.
- `Modules/Panels/Settings/Bar/BarWidgetSettingsDialog.qml` - shared per-widget settings dialog used by BarService.
- `Assets/settings-default.json` - default bar settings and widget layout.

## Tests asserting this spec

- `Tests/bar-helpers-guards.test.js`
- `Tests/bar-service-guards.test.js`
- `Tests/bar-widget-registry-guards.test.js`
- `Tests/bar-tab-guards.test.js`
- `Tests/bar-pill-vertical-guards.test.js`
- `Tests/widget-registry.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] Add executable coverage for horizontal bar pill animation behavior.
- [ ] Add executable coverage for full bar rendering across top, bottom, left, and right positions.
- [ ] Add executable coverage for widget settings dialog rendering and signal emission.
- [ ] Split widget-specific behavior into dedicated specs for widgets that do not already have one.

## Out of scope

- Individual audio, battery, Bluetooth, brightness, media, network, power profile, screen recorder, and wallpaper widget behavior belongs in their existing feature specs.
- Taskbar, tray, workspace, and custom button widget behavior should get separate specs because their tests cover feature-specific state beyond the shared bar contract.
