Bar covers the multi-monitor shell bar, the bar widget registry, registered widget lookup, bar widget settings, and the bar settings tab. Runtime source lives mainly in `Modules/Bar/Bar.qml`, `Services/UI/BarService.qml`, and `Services/UI/BarWidgetRegistry.qml`; implementation notes belong in [docs/wiki/systems/bar.md](../wiki/systems/bar.md).

## What it must do

### Bar shell

- [x] Control Center toggling fails closed when the panel is unavailable.
- [x] Control Center toggling uses the bar-button anchor hint when settings request `close_to_bar_button`.
- [x] Control Center toggling falls back to the default panel toggle when the panel is configured away from the bar button.
- [x] Widget loader implicit size rounds visible item sizes.
- [x] Widget loader implicit size returns zero for missing or hidden items.
- [x] Bar widget loader screen references and widget-id delegate aliases are typed.
- [x] Bar background consumers accept the exposed bar item as a typed `Item` while keeping the owning panel window dynamic.

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
- [x] Bar widget registry lookup, presence, and user-settings helpers type widget id inputs as strings.
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

- [x] Shared pill preserves label/suffix, icon, density-dependent sizing, custom/hover colors, and expanded/collapsed geometry across horizontal and vertical orientations.
- [x] Shared pill forwards hover, tooltip, three mouse buttons, wheel delta, and shown/hidden signals; delayed opening, auto-hide, and cancellation preserve visibility and opacity in both orientations.
- [x] Orientation changes replace the loaded pill while retaining screen, label, open state, and size bindings; force-close, opposite direction, and rotated vertical text remain functional.
- [x] Horizontal pill preserves expanded/collapsed geometry, both open directions, density-dependent label/icon sizing, delayed hover cancellation, release-only three-button callbacks, wheel forwarding, force-close, and auto-hide at UI scales 1 and 1.25.
- [x] Vertical pill preserves expanded/collapsed geometry, both open directions, rotated text, default/compact sizing, custom/hover colors, tooltip/input forwarding, delayed auto-hide/cancellation, force-close, and locked-open behavior.
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
- `Modules/MainScreen/Backgrounds/AllBackgrounds.qml` - unified background container that receives the exposed bar item.
- `Modules/MainScreen/Backgrounds/BarBackground.qml` - bar shape path consumer of the exposed bar item.
- `Modules/Bar/Extras/BarWidgetLoader.qml` - widget component loading and implicit-size reporting.
- `Modules/Bar/Extras/BarPill.qml` - shared pill bindings, input forwarding, and orientation-dependent loading.
- `Modules/Bar/Extras/BarPillHorizontal.qml` - horizontal pill animation and geometry.
- `Modules/Bar/Extras/BarPillVertical.qml` - vertical pill animation and offset behavior.
- `Services/UI/BarService.qml` - bar readiness, widget instance registry, lookup helpers, context menu placement, and widget settings dialog wiring.
- `Services/UI/BarWidgetRegistry.qml` - available widget components, widget settings mapping, and registry metadata.
- `Modules/Panels/Settings/Tabs/BarTab.qml` - bar settings UI helpers for adding, removing, moving, and locating widgets.
- `Modules/Panels/Settings/Bar/BarWidgetSettingsDialog.qml` - shared per-widget settings dialog used by BarService.
- `Assets/settings-default.json` - default bar settings and widget layout.

## Tests asserting this spec

### Bar control cohort

- `Tests/bar-controls-warnings.test.py` covers production ControlCenter, Brightness, Microphone, Volume, Bluetooth, VPN, LockKeys, and SessionMenu. Through `1fa24f0b0`, owner qualification reduces cohort unqualified-access warnings 62→0 and block-scoped-variable warnings 10→0; standalone lint requires zero warnings per widget. No intended user-facing behavior change.
- Offscreen behavior reports 19 passes: eight click/context rows, three wheel/update rows, five display-mode rows, one ControlCenter shader-binding case, plus initialization/cleanup. Synthetic mouse events exercise panel routing, popup positioning, settings dispatch, ControlCenter launcher/settings actions and centered anchoring, SessionMenu toggling, Bluetooth toggling, VPN connect/disconnect and visibility polling references, and audio mute/mixer dispatch. Wheel signals exercise brightness availability, audio delta accumulation, first-update suppression, subsequent pill reveal, tooltip clearing, and microphone mute reveal. Display modes include vertical Bluetooth/VPN collapse; shader colors follow colorization and dark-mode settings.
- LockKeys coverage here is construction/geometry and context/settings routing, not lock-state transitions or per-key rendering. Widgets make no direct OSD dispatch; pill reveal is not OSD proof. Invocation, fake-service boundaries, and remaining integration limits: [testing](testing.md#bar-control-cohort).

### Other bar coverage

- `Tests/widget-settings-cohort-warnings.test.py` with `Tests/Qml/WidgetSettingsCohortHarness.qml` — after `c9fd2feed` and `eac48e27a`, standalone editor lint counts are LockKeys 21→0, ControlCenter 20→0, SystemMonitor 20→0, MediaMini 17→0, Workspace 10→0. Isolated production editors and shared dialog exercise three parameterized cases per editor (toggle/save copy isolation, cancel/reopen/apply-close, fixture metadata defaults), plus one combined dependent-control/validation case: 16 behavioral cases plus QtTest init/cleanup, 18 reported passes. Apply emits one update with section/index/settings and closes; cancel emits none, preserves fixture state, and reopening restores initial values. Signals are invoked directly, not physical input. Strict runtime no-warning acceptance remains **RED** on a shared-control `enabled` redeclaration despite completed behavior assertions; editor lint is not warning-free runtime proof. Isolation, invocation, and remaining limits: [testing](testing.md#widget-settings-cohort).

- `Tests/bar-warnings.test.py` - standalone `behavior` runs production Bar/BarWidgetLoader offscreen with fixture screens, widgets, services, and style: seven behavior rows plus QtTest init/cleanup yield nine reported passes. Covers delayed screen assignment, monitor selection, registration/teardown, section order/spacing and hidden sizes on all four sides across two fixture screens, right-click routing, corner/orientation replacement, and Control Center modes. Isolated HOME/XDG paths, a permission-locked hash-verified real-settings backup, and unchanged-byte checks protect settings; success requires exit status zero, `0 failed`, and no `QWARN`, `QFATAL`, `ReferenceError`, `TypeError`, or `Binding loop`. Standalone `lint` accepts exactly two `missing-property` warnings (39→2 at `a83e8408d`), not zero. Neither mode is registered in `run-tests.sh`.
- `Tests/custom-button-bar-settings-warnings.test.py` - standalone production-editor coverage and zero-warning lint (41→0 at `1a1c35375`), not a bar feature change. Four behavior cases plus init/cleanup produce six reported passes; serialization, controls, copy isolation, and component discard/reopen coverage belong in [custom button](custom-button.md). This does not cover shared dialog save/cancel, widget reorder, or persistence.
- `Tests/bar-helpers-guards.test.js`
- `Tests/bar-service-guards.test.js`
- `Tests/bar-widget-registry-guards.test.js`
- `Tests/bar-tab-guards.test.js`
- `Tests/bar-pill-vertical-guards.test.js`
- `Tests/bar-pill-warnings.test.py` - nine isolated production-widget behavior cases: four orientation/density geometry cases, two hover/input cases, two auto-hide cases, and one Loader replacement/force-close case. Exercises Bound component context; fixture services do not prove whole-shell behavior.
- `Tests/bar-pill-vertical-warnings.test.py` - seven offscreen production-widget cases: four density/direction/rotation geometry rows, hover/input routing, delayed auto-hide/cancellation, and force-closed/locked-open behavior. Standalone lint requires zero warnings after `70f90a4bc` (46→0).
- `Tests/bar-pill-horizontal-warnings.test.py` - 12 offscreen cases through production BarPill's horizontal Loader: geometry, hover/press-release/input, and auto-hide across default/compact density at scales 1/1.25. Geometry emits eight records spanning both open directions; standalone lint requires zero horizontal warnings after `32d56b877` (38→0).
- All three BarPill Python harnesses run `behavior` in `deterministic-unit`, ordered core → horizontal → vertical after wallpaper-panel runtime coverage and before color coverage. Both modes remain runnable standalone; lint modes are not added to this gate. `Tests/test-runner-categories.test.sh` checks exact arguments, once-only ordering, success continuation, and fail-closed exit-status propagation. Runner contract: [testing](testing.md).
- `Tests/widget-registry.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] Extend isolated pill endpoint/delay coverage to intermediate animation frames and whole-shell integration; current fixtures use controlled style values and stub tooltip/bar services. Horizontal's eight geometry records were reported unchanged for `32d56b877`, but the harness has no tracked snapshot-equality comparator.
- [ ] Eight BarPill Loader/QObject `missing-property` typing diagnostics remain after `705973eb2` reduced warnings from 52 to 8. Standalone lint expects exactly those eight, not warning-free analysis; owner qualification introduces no intended user-facing behavior change.
- [ ] Extend isolated four-side Bar geometry coverage to full-shell rendering and real output/input delivery; fixture screens share one offscreen window and do not prove compositor input regions or pixel rendering.
- [ ] Two Bar `missing-property` static diagnostics remain after `a83e8408d`; isolated behavior success is not warning-free whole-shell acceptance.
- [ ] Resolve the shared-control `enabled` redeclaration before claiming strict runtime acceptance for the five-editor cohort. Its isolated dialog assertions cover save/cancel/reopen/apply-close, not warning-free runtime.
- [ ] Extend widget settings coverage to pixel rendering, physical input, widget reorder, BarService popup ownership, and real persistence; the cohort uses fixture settings/registry/services and directly invoked control signals.
- [ ] Split widget-specific behavior into dedicated specs for widgets that do not already have one.

## Out of scope

- Individual audio, battery, Bluetooth, brightness, media, network, power profile, screen recorder, and wallpaper widget behavior belongs in their existing feature specs.
- Workspace and grouped/ungrouped Taskbar behavior and isolated runtime coverage belong in [compositor.md](compositor.md), not the shared bar contract. Ungrouped Taskbar's `60c64807d` coverage records 37→0 warnings and seven offscreen QtTest cases (five behavioral plus initialization/cleanup); it proves no Firefox notification cursor-flicker fix and leaves input regions and icon sizing untouched.
- Taskbar, tray, and custom button widget behavior should get separate specs because their tests cover feature-specific state beyond the shared bar contract.
