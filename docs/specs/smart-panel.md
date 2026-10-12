Smart Panel covers the shared panel shell used by settings, changelog, control center, and other MainScreen panels. Runtime source lives in `Modules/MainScreen/SmartPanel.qml`; implementation notes belong in [docs/wiki/systems/smart-panel.md](../wiki/systems/smart-panel.md).

## What it must do

### Registration lifecycle

- [x] SmartPanel captures a stable registration key from `objectName` before registering with PanelService.
- [x] SmartPanel unregisters with the captured key and panel identity during destruction, even if screen-bound `objectName` changes during output teardown.

### Close lifecycle

- [x] Closing a panel starts the closing sequence.
- [x] Closing clears size-animation completion and close-finalized state.
- [x] Closing stops opacity and open-watchdog timers.
- [x] Closing starts the close watchdog.
- [x] Closing marks opacity fade complete immediately when the panel is already hidden.
- [x] Duplicate close finalization logs a warning and does not notify panel service or emit close.
- [x] Close finalization clears open/visible/closing state.
- [x] Close finalization stops the close watchdog and clears watchdog state.
- [x] Close finalization resets panel dimensions for the next open.
- [x] Close finalization notifies PanelService, emits the panel close signal, and logs completion.

### Positioning

- [x] Positioning retries later and leaves target size unset when root dimensions are missing.
- [x] Positioning applies preferred width and height as target panel size when no content or ratio override applies.
- [x] Button-positioned attached panels under a top bar are centered on the button and placed below the bar.
- [x] Detached standard placement centers the panel and offsets it below the top bar.
- [x] At 800×600 and 1920×1080, centered detached, button-attached, and floating edge-anchored panels preserve placement for all four bar edges as content dimensions change.

### Content lifecycle and animations

- [x] Panel content stays unloaded while closed, loads once on open, and retains its caller Component context.
- [x] Content dimension changes update panel geometry without recreating content.
- [x] Nonzero opening and closing animations settle with matching signals and cleared watchdog state.
- [x] Closing before opacity fade-in completes skips the opacity fade and unloads content after size animation.
- [x] Output teardown destroys loaded content and clears the opened-panel reference while unregistering the original key.

### Background path

- [x] Panel background fill containment follows position/size, rounded/square/inverted corners, and small-geometry radius clamping.
- [x] Hidden/null panels clear the path, panel-item replacement moves it, and background-color changes update fill color.

### Typed panel references

- [x] SmartPanel `buttonItem` is typed as `Item`.
- [x] SmartPanel `panelRegion` is typed as the real Item-derived `BackgroundRegion`, with four integer corner-state properties: top-left, top-right, bottom-right, and bottom-left (`-1` square, `0` inner curve, `1` X inversion, `2` Y inversion).
- [x] SmartPanel `panelRegion` exposes the live `panelBackground` geometry consumed by `AllBackgrounds`.
- [x] `PanelBackground` requires a `BackgroundRegion panel` and projects the visible region through readonly `BackgroundRegion panelBg`, or null for hidden/inactive geometry; no `panelItem` property is required.

## How it works

- [docs/wiki/systems/smart-panel.md](../wiki/systems/smart-panel.md)

## Implementation inventory

- `Modules/MainScreen/SmartPanel.qml` - shared panel lifecycle, sizing, positioning, masking, close/open watchdogs, and typed panel references.
- `Modules/MainScreen/MainScreen.qml` - SmartPanel host and panel placeholders.
- `Modules/MainScreen/AllScreens.qml` - per-screen host and bar/popup loader routing.
- `Modules/MainScreen/Backgrounds/PanelBackground.qml` - panel fill path and corner geometry.
- `Modules/MainScreen/Backgrounds/BackgroundRegion.qml` - shared Item-derived geometry and four-corner contract for bar, active panel, and inactive placeholder regions.
- `Services/UI/PanelService.qml` - panel registration and close notifications consumed by SmartPanel.
- `Modules/Panels/**/*.qml` - panel implementations built on SmartPanel.

## Tests asserting this spec

- `Tests/background-region-reload.test.py` — private cold-start/hot-reload checks of production MainScreen, SmartPanel and background regions; leaf panels/services are fixtures.

- `Tests/background-paths-warnings.test.py` / `Tests/Qml/BackgroundPathsHarness.qml` cover production panel/bar ShapePaths with fixture geometry, style, and visibility: 11 behavioral rows plus init/cleanup (13 reported passes) and four detected layout/rounding negative controls retained through `e8688d183`…`a5a892041`; PanelBackground lint drops 13→0 with the real shared region type. Private cold-start/source-reload evidence covers all 17 lazy callers per phase: [testing](testing.md#background-region-private-reload). This is offscreen containment/property evidence, not SmartPanel lifecycle or compositor visual proof. Invocation and isolation: [testing](testing.md#background-paths).

- `Tests/panel-service-guards.test.js`
- `Tests/Qml/PanelServiceLifecycleHarness.qml`
- `Tests/panel-service-lifecycle.test.sh` runs production SmartPanel/PanelService non-visibly: 24 geometry cases (two viewport sizes × four bar edges × three placement modes), one close-before-fade case, and one teardown-while-open case. Assertions cover nonzero animations, content resizing without recreation, Loader unloading, caller Component context, signal counts, and stable registry cleanup after output-name changes. Settings bootstrap is real but isolated; panel content is a fixture, not each consumer panel.
- Through `9684a5cbe`/`7ca59a588`, MainScreen static warnings drop 5→0. `Tests/Qml/MainScreenWarningsHarness.qml` / `Tests/main-screen-warnings.test.py runtime` report twelve offscreen QtTest passes: eight edge/floating geometry rows, one lifecycle/routing case exercising all 17 fixture panels, one reactive-screen case, and init/cleanup. Assertions cover one-pixel attachment overlap, mask geometry, loader registration/reuse/teardown, optional navigation, dim color and focus properties, monitor filtering, resize, foreign-screen rejection, and null/restored selection. Geometry, wrong-screen routing, and frozen-selection mutations are failing negative controls; the last freezes selection after loader registration. Screens, PanelWindow/Region/layer-shell transport, panels, backgrounds and services are synthetic. Reported real-config-denied execution is not visible compositor, native input, real SmartPanel animation, or consumer-panel proof. Invocation and isolation limits: [testing](testing.md#mainscreen-isolated-runtime).
- `Tests/smart-panel-guards.test.js` — at `b14c991c0`, attachment/close/placement helpers execute against owner-bound fixture settings, screens and timers; not compositor placement/input or runtime animation proof.
- `Tests/qml-type-annotations.test.js` — exact owner/type/modifier declaration inventory, including the shared region's four integer corner states. The full 44-row reconciliation at `64aba2111`/`f9bb567f8`/`cb3ec488c` reports 115 runner checks passing at `adea16df0`, not 115 runtime cases. Fourteen negative parser fixtures reject missing/wrong modifiers, types, owners, child/sibling-only declarations, duplicates and lookalike region names. Structural inventory and parser fixtures do not execute QML bindings or prove geometry, actions, persistence or native lifecycle; retained annotated runtime gates remain separately bounded. Helper metadata: [GitHub](github.md#tests-asserting-this-spec); proof classification: [testing](testing.md). External Wayland teardown remains unresolved; this result is not clean native-popup acceptance.
- `Tests/source-coverage.test.js`

### AllScreens isolated routing evidence

- At `ca9b9a618`, AllScreens warnings drop 5→0; one unused `Quickshell.Wayland` import informational notice remains. `Bound` delegates qualify screen ownership; this does not clear MainScreen's separate residual diagnostics.
- `Tests/all-screens-warnings.test.py runtime` / `Tests/Qml/AllScreensWarningsHarness.qml` report nine routing/lifecycle passes: initial two-screen routing, removal, re-addition (Bound delegate recreation), monitor filtering, panels without a bar, bar hiding, bar restoration, clearing the monitor filter, and final destruction with balanced create/destroy events. Assertions compare exact screen identities for MainScreen, BarContentWindow, BarExclusionZone and PopupMenuWindow fixtures.
- Reported `runtime --mutation` wrong-screen negative control forces first-screen routing on the private copy and fails; it is not an acceptance mode. Installed Variants and production Loader bindings remain real, while screens, services and window leaves are inert fixtures. No visible compositor, real config access, actual output hotplug or whole-shell acceptance is proven. Invocation/isolation: [testing](testing.md#allscreens-isolated-runtime).

## Known gaps (current cycle)

- [ ] MainScreen's staging fixture omits the new BackgroundRegion type; repair is separate. Scoped background evidence does not establish an entire unit-gate pass.
- [ ] Private region reload uses fixture leaf content and explicit close finalization; no live wallpaper or render-driven animation proof.

- [ ] Four dynamic Loader member diagnostics remain after the `05772415d` SmartPanel warning reduction (76 → 4); runtime lifecycle coverage is not zero-warning static-analysis acceptance.
- [ ] MainScreen's zero-warning lint and offscreen fixture coverage do not prove compositor pixels, native input delivery, or real-output routing.

- [ ] Add executable coverage for watchdog timeout recovery and zero-duration animation paths.
- [ ] Add executable coverage for remaining anchor combinations and constrained/oversized content.
- [ ] Add executable coverage for keyboard shortcut forwarding and escape-to-close behavior.

## Out of scope

- Feature-specific panel content behavior belongs in each owning feature spec.
- Panel registration and lookup behavior is covered by [panel-service.md](panel-service.md).
