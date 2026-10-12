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

### Background path

- [x] Bar background fill containment follows position/size, rounded/square/inverted corners, and radius clamping for small geometry.
- [x] Bar background hides for hidden bars, excluded monitors, and null bar references; monitor selection and fill-color changes update the path.
- [x] Bar background consumes the real Item-derived `BackgroundRegion` four-corner contract; private cold-start/reload checks all four bar sides and floating corner states.

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
- `Modules/MainScreen/Backgrounds/BackgroundRegion.qml` - shared typed geometry/corner contract; [panel contract](smart-panel.md#typed-panel-references).
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

- `Tests/audio-notification-settings-warnings.test.py` — isolated defaults, toggle/save, copy ownership and cancel/apply for [audio](audio.md) and [notification](notifications.md) widget editors.
- `Tests/bar-multiline-var-warnings.test.py` — isolated CustomButton, KeepAwake, KeyboardLayout and Spacer property, interaction and lifetime cases.
- `Tests/low-count-widget-settings-warnings.test.py` — isolated Brightness, KeyboardLayout, Microphone, Spacer and Volume editor controls with synthetic settings.

- `Tests/bar-widget-metadata-runtime.test.py` — offscreen Loader construction checks ActiveWindow/MediaMini metadata before instance IDs, late settings, width caps, vertical scaling and hidden dimensions.
- `Tests/qml-static-bar-fixtures.test.py` — metadata/grouped-taskbar harnesses are counted once by the static checker; injected genuine warnings remain visible and fail.
- `Tests/taskbar-fixture-lint.test.py` — actual Taskbar runtime fixture lint accepts clean diagnostics and rejects an injected missing property.
- `Tests/downloader-sound-monitor-taskbar-isolation.test.py` — grouped-taskbar parent CLI denies host config, preserves private settings/backup bytes and rejects fixture mutations.

### Optional dynamic widget loader contract

- At `985a57a53`, BarWidgetLoader diagnostics remain 3→3 (`screen`, `scaling`, `onLoaded`); production is unchanged. Inspection of all 40 registered widget types across both registries found no truthful shared contract for these optional members. Exact-count acceptance is not zero-warning analysis.
- `Tests/Qml/BarWidgetLoaderHarness.qml` covers filtered props, screen/scaling assignment and registration before callback, independent owners/reload, optional-member absence, owner-bound density scaling, rounded/hidden geometry and transparent hide mode, missing-registry handling, and destruction unregistration. Six behavioral cases plus init/cleanup report eight passes each in normal and owner-shadow offscreen runs. Shared dedicated-test accounting, nine negative controls, and isolation limits: [testing](testing.md#control-center-widget-loader-isolated-runtime).

### Bar control cohort

- `Tests/bar-controls-warnings.test.py` covers production ControlCenter, Brightness, Microphone, Volume, Bluetooth, VPN, LockKeys, and SessionMenu. Through `1fa24f0b0`, owner qualification reduces cohort unqualified-access warnings 62→0 and block-scoped-variable warnings 10→0; standalone lint requires zero warnings per widget. No intended user-facing behavior change.
- Offscreen behavior reports 19 passes: eight click/context rows, three wheel/update rows, five display-mode rows, one ControlCenter shader-binding case, plus initialization/cleanup. Synthetic mouse events exercise panel routing, popup positioning, settings dispatch, ControlCenter launcher/settings actions and centered anchoring, SessionMenu toggling, Bluetooth toggling, VPN connect/disconnect and visibility polling references, and audio mute/mixer dispatch. Wheel signals exercise brightness availability, audio delta accumulation, first-update suppression, subsequent pill reveal, tooltip clearing, and microphone mute reveal. Display modes include vertical Bluetooth/VPN collapse; shader colors follow colorization and dark-mode settings.
- LockKeys coverage here is construction/geometry and context/settings routing, not lock-state transitions or per-key rendering. Widgets make no direct OSD dispatch; pill reveal is not OSD proof. Invocation, fake-service boundaries, and remaining integration limits: [testing](testing.md#bar-control-cohort).

### Bar status cohort

- At `c14da3540`, NotificationHistory/ScreenRecorder/WiFi/AudioVisualizer owner fixes remove 6+2+6+9 warnings. `Tests/bar-status-warnings.test.py` retains exact per-file residual diagnostics rather than claiming warning-free cohort analysis.
- Eight isolated behavioral cases exercise production buttons/pills, badge and spectrum Loaders, geometry, routing, and timed spinner/size transitions; QtTest init/cleanup add two reported passes. Feature assertions: [notifications](notifications.md#tests-asserting-this-spec), [screen recorder](screen-recorder.md#tests-asserting-this-spec), [network](network.md#tests-asserting-this-spec), [audio](audio.md#tests-asserting-this-spec). Invocation, residual counts, and integration limits: [testing](testing.md#bar-status-cohort).

### Bar content window isolated evidence

- At `4d9c52ccc`, `Tests/bar-content-window-warnings.test.py` retains BarContentWindow diagnostics 8→8: one PanelWindow creatability diagnostic, four opaque Margins fields (`top`, `bottom`, `left`, `right`), and three opaque screen fields (`name`, `width`, `height`). Exact-count lint acceptance is not zero-warning analysis; production source is unchanged.
- Offscreen runtime reports four passes: two behavioral cases plus QtTest init/cleanup. Production bindings with synthetic PanelWindow transport and Bar content cover four-side anchors/dimensions, floating margins, rotation, empty-position default, two-screen routing/reassignment, reactive screen/style dimensions, namespace, transparent color, and creation logging. `routing`, `rotation`, and `margins` staged-copy negative controls exercise those failure boundaries.
- No real compositor, layer-surface placement/input, production Bar rendering, persistence, or whole-shell proof. Invocation and settings-denied isolation: [testing](testing.md#bar-content-window-isolated-runtime).

### Other bar coverage

- At `2a73a4c4f`, BrightnessSettings/KeyboardLayoutSettings/MicrophoneSettings/SpacerSettings/VolumeSettings warnings each drop 2→0. Four display-mode rows and one Spacer row exercise production editors and real controls. Spacer covers initial/default width, keyboard edits, zero/invalid-width metadata handling, copy-save retention/nonmutation, control geometry, and reopen from saved values. No shared-dialog Apply/Cancel, BarService popup, or real persistence proof. Seven-pass accounting, owner-shadow mode and isolation: [testing](testing.md#small-widget-settings-isolated-runtime).

- At `5a3d4be9d`, AudioVisualizerSettings and NotificationHistorySettings warnings each drop 4→0. Shared-dialog offscreen coverage checks cancel without updates, reopening with original values, and one Apply update to the requested section/index while preserving unrelated fixture fields. Editor assertions: [audio](audio.md#tests-asserting-this-spec), [notifications](notifications.md#tests-asserting-this-spec); eight-pass accounting and config-denied isolation: [testing](testing.md#audionotification-settings-isolated-runtime). No BarService popup ownership or real persistence proof.

- ActiveWindowSettings warning reduction 6→0 and six reported offscreen passes through `40d1f6391`/`a5322cf4b`/`9f3c50289` cover editor options, pending/copy-save isolation, and shared-dialog cancel/reopen/apply with synthetic settings. This does not prove BarService popup ownership, real persistence, or resolution of reload-time ActiveWindow warnings. Coverage: [active window](active-window.md#tests-asserting-this-spec); invocation/isolation: [testing](testing.md#activewindow-settings-isolated-runtime).

- `Tests/background-paths-warnings.test.py` / `Tests/Qml/BackgroundPathsHarness.qml` cover production bar/panel paths retained through `e8688d183`…`a5a892041`: 11 offscreen behavioral rows plus init/cleanup (13 reported passes), with four detected layout/rounding negative controls. Shape containment and fill-color properties are not compositor visual proof. BarBackground lint drops 12→0 with the shared region type. Invocation and isolation: [testing](testing.md#background-paths); private cold-start/source-reload: [testing](testing.md#background-region-private-reload).

- `Tests/layer-bar-owner-warnings.test.py loader` covers production BarWidgetLoader offscreen after `097536acb`: owner warnings 15→0, with three unsuppressed dynamic-widget `missing-property` diagnostics (`screen`, `scaling`, `onLoaded`) retained. One behavioral case covers two-screen property assignment, registration before widget callback, rounded/hidden sizes, density scaling, opacity/hide mode, resize propagation, ordered teardown, and recreation. Synthetic clicks reach an underlying receiver; the unchanged input region is only a fixture property, not compositor proof. Invocation and isolation: [testing](testing.md#background-and-widget-loader-owners).
- Unified bar/panel backgrounds after `ead749abf` have offscreen color/geometry, transparent-canvas sample, and pointer pass-through coverage, not compositor-rendered pixels or live input-region proof: [testing](testing.md#background-and-widget-loader-owners).

- `Tests/simple-service-warnings.test.py` / `Tests/Qml/SimpleServiceHarness.qml` — production BarService registry changes drive its real rescan timer: AudioVisualizer enables visualizer state, removal and non-visualizing MediaMini clear it, visualizing MediaMini restores it, and enumeration retains both MediaMini instances. No popup/dialog or whole-shell proof; cohort invocation and lint counts: [testing](testing.md#simple-service-cohort).

- `Tests/widget-settings-cohort-warnings.test.py` with `Tests/Qml/WidgetSettingsCohortHarness.qml` — after `c9fd2feed` and `eac48e27a`, standalone editor lint counts are LockKeys 21→0, ControlCenter 20→0, SystemMonitor 20→0, MediaMini 17→0, Workspace 10→0. Isolated production editors and shared dialog exercise three parameterized cases per editor (toggle/save copy isolation, cancel/reopen/apply-close, fixture metadata defaults), plus one combined dependent-control/validation case: 16 behavioral cases plus QtTest init/cleanup, 18 reported passes. Apply emits one update with section/index/settings and closes; cancel emits none, preserves fixture state, and reopening restores initial values. Signals are invoked directly, not physical input. After `6c946f837` explicitly preserves NButton/NTextInput `enabled` overrides, the saved cohort run passes strict runtime no-warning acceptance. This is bounded fixture runtime proof, not warning-free whole-shell or shared-control static analysis. Isolation, invocation, and remaining limits: [testing](testing.md#widget-settings-cohort).

- `Tests/bar-warnings.test.py` - standalone `behavior` runs production Bar/BarWidgetLoader offscreen with fixture screens, widgets, services, and style: seven behavior rows plus QtTest init/cleanup yield nine reported passes. Covers delayed screen assignment, monitor selection, registration/teardown, section order/spacing and hidden sizes on all four sides across two fixture screens, right-click routing, corner/orientation replacement, and Control Center modes. Isolated HOME/XDG paths, a permission-locked hash-verified real-settings backup, and unchanged-byte checks protect settings; success requires exit status zero, `0 failed`, and no `QWARN`, `QFATAL`, `ReferenceError`, `TypeError`, or `Binding loop`. Standalone `lint` accepts exactly two `missing-property` warnings (39→2 at `a83e8408d`), not zero. Neither mode is registered in `run-tests.sh`.
- `Tests/custom-button-bar-settings-warnings.test.py` - standalone production-editor coverage and zero-warning lint (41→0 at `1a1c35375`), not a bar feature change. Four behavior cases plus init/cleanup produce six reported passes; serialization, controls, copy isolation, and component discard/reopen coverage belong in [custom button](custom-button.md). This does not cover shared dialog save/cancel, widget reorder, or persistence.
- `Tests/bar-helpers-guards.test.js`
- `Tests/bar-service-guards.test.js`
- `Tests/bar-widget-registry-guards.test.js`
- `Tests/bar-tab-warnings.test.py` / `Tests/Qml/BarTabWarningsHarness.qml` — standalone BarTab lint requires zero warnings/exit status zero (20→0 through `995514d7e`, `b675d1046`). Isolated actual tab, shared controls, and widget dialog cover four behavioral cases plus init/cleanup (six reported passes): registry badges/refresh; monitor selection, placement and density; section add/remove/reorder/move/update and invalid bounds/last-ControlCenter warning; dialog Cancel preserving fixture values and Apply updating the target entry with no immediate save request. Settings, screens, registry/services, and CustomButton editor are fixtures; direct signals/helpers prove neither physical drag/input nor real persistence or whole-shell behavior. Safety and invocation: [testing](testing.md#bar-settings-tab).
- `Tests/bar-tab-guards.test.js` — at `b78dcaba1`, four executable production-function checks cover add/remove/reorder/update/move and available-widget models with fixture settings; not regex proof or real persistence.
- `Tests/bar-pill-vertical-guards.test.js`
- `Tests/bar-pill-warnings.test.py` - nine isolated production-widget behavior cases: four orientation/density geometry cases, two hover/input cases, two auto-hide cases, and one Loader replacement/force-close case; 11 reported passes including init/cleanup. Through `3569081f8`/`b645aea04`/`56d317612`, these pass via the config-denied sandbox runner. `Tests/bar-pill-owner-warnings.test.py runtime` separately reports three passes (one behavioral case plus init/cleanup), covering two-instance label/color/density/screen ownership across all four sides, Loader size propagation, and show/hide/delayed show. Bound fixture runtime is not whole-shell or settings-persistence proof. Isolation and invocation: [testing](testing.md#bar-pill-isolated-owner-evidence).
- `Tests/bar-pill-owner-isolation.test.py` — public core/horizontal/vertical behavior and two-owner runtime under masked host/read-only private HOME; rejects owner mutations and injected fixture warnings, verifies parent/Qt-child permission denial and cleanup. Fixture services exclude real persistence, native input and whole-shell proof; [isolation evidence](testing.md#bar-pill-isolated-owner-evidence).
- `Tests/bar-pill-vertical-warnings.test.py` - seven offscreen production-widget cases: four density/direction/rotation geometry rows, hover/input routing, delayed auto-hide/cancellation, and force-closed/locked-open behavior. Standalone lint requires zero warnings after `70f90a4bc` (46→0).
- `Tests/bar-pill-horizontal-warnings.test.py` - 12 offscreen cases through production BarPill's horizontal Loader: geometry, hover/press-release/input, and auto-hide across default/compact density at scales 1/1.25. Geometry emits eight records spanning both open directions; standalone lint requires zero horizontal warnings after `32d56b877` (38→0).
- All three BarPill Python harnesses run `behavior` in `deterministic-unit`, ordered core → horizontal → vertical after wallpaper-panel runtime coverage and before color coverage. Both modes remain runnable standalone; lint modes are not added to this gate. Exact arguments, once-only ordering, success continuation, and fail-closed exit-status propagation are runner meta evidence: [testing](testing.md#runner-contract).
- `Tests/widget-registry.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

- `1611de2ad`: CustomButton/KeepAwake/KeyboardLayout/Spacer scoped hoisting warnings 11→0; 20 reported offscreen cases cover settings lifetimes, commands/scroll branches, awake actions, keyboard context and spacer layout. Inert process/power/keyboard/panel boundaries; no live backend or compositor proof. [Runner limits](testing.md#bar-and-slidertextdialog-lexical-local-evidence).

## Known gaps (current cycle)

- [ ] Offscreen typed-region coverage proves neither compositor pixels nor live input regions, wallpaper, or render-driven panel animations. MainScreen's separate staging omission prevents an entire unit-gate claim; [testing limits](testing.md#background-region-private-reload).

- [ ] Extend isolated pill endpoint/delay coverage to intermediate animation frames and whole-shell integration; current fixtures use controlled style values and stub tooltip/bar services. Horizontal's eight geometry records were reported unchanged for `32d56b877`, but the harness has no tracked snapshot-equality comparator.
- [ ] Eight BarPill Loader.item metadata `missing-property` diagnostics remain: width, height, show, hide, and showDelayed. After `705973eb2` reduced warnings 52→8, `3569081f8`/`b645aea04`/`56d317612` retain 8→8; exact-count lint acceptance is not zero-warning analysis. No intended user-facing behavior change.
- [ ] Extend isolated four-side Bar geometry coverage to full-shell rendering and real output/input delivery; fixture screens share one offscreen window and do not prove compositor input regions or pixel rendering.
- [ ] Two Bar `missing-property` static diagnostics remain after `a83e8408d`; isolated behavior success is not warning-free whole-shell acceptance. BarWidgetLoader separately retains three unsuppressed dynamic-widget type diagnostics after `097536acb`; zero owner warnings does not mean zero total warnings.
- [ ] Extend widget settings coverage to pixel rendering, physical input/drag reorder, BarService popup ownership, and real persistence; isolated BarTab now covers helper-driven section reorder/move and dialog Apply/Cancel, but uses fixture settings/registry/services and directly invoked signals.
- [ ] Split widget-specific behavior into dedicated specs for widgets that do not already have one.

## Out of scope

- Individual audio, battery, Bluetooth, brightness, media, network, power profile, screen recorder, and wallpaper widget behavior belongs in their existing feature specs.
- Workspace and grouped/ungrouped Taskbar behavior and isolated runtime coverage belong in [compositor.md](compositor.md), not the shared bar contract. Ungrouped Taskbar's `60c64807d` coverage records 37→0 warnings and seven offscreen QtTest cases (five behavioral plus initialization/cleanup); it proves no Firefox notification cursor-flicker fix and leaves input regions and icon sizing untouched.
- Taskbar, tray, and custom button widget behavior should get separate specs because their tests cover feature-specific state beyond the shared bar contract.
