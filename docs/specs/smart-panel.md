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
- [x] SmartPanel `panelRegion` is typed as `Item`.
- [x] SmartPanel `panelRegion` exposes the live `panelBackground` geometry consumed by `AllBackgrounds`.
- [x] Panel background exposes its `panelItem` as an `Item`.

## How it works

- [docs/wiki/systems/smart-panel.md](../wiki/systems/smart-panel.md)

## Implementation inventory

- `Modules/MainScreen/SmartPanel.qml` - shared panel lifecycle, sizing, positioning, masking, close/open watchdogs, and typed panel references.
- `Modules/MainScreen/MainScreen.qml` - SmartPanel host and panel placeholders.
- `Modules/MainScreen/Backgrounds/PanelBackground.qml` - panel fill path and corner geometry.
- `Services/UI/PanelService.qml` - panel registration and close notifications consumed by SmartPanel.
- `Modules/Panels/**/*.qml` - panel implementations built on SmartPanel.

## Tests asserting this spec

- `Tests/background-paths-warnings.test.py` / `Tests/Qml/BackgroundPathsHarness.qml` cover production panel/bar ShapePaths with fixture geometry, style, and visibility: 11 behavioral rows plus init/cleanup (13 reported passes) and four detected layout/rounding negative controls through `7c8e74ea2`/`23b32ca34`/`f16acbc36`. This is offscreen containment/property evidence, not SmartPanel lifecycle or compositor visual proof. Invocation and isolation: [testing](testing.md#background-paths).

- `Tests/panel-service-guards.test.js`
- `Tests/Qml/PanelServiceLifecycleHarness.qml`
- `Tests/panel-service-lifecycle.test.sh` runs production SmartPanel/PanelService non-visibly: 24 geometry cases (two viewport sizes × four bar edges × three placement modes), one close-before-fade case, and one teardown-while-open case. Assertions cover nonzero animations, content resizing without recreation, Loader unloading, caller Component context, signal counts, and stable registry cleanup after output-name changes. Settings bootstrap is real but isolated; panel content is a fixture, not each consumer panel.
- `Tests/Qml/MainScreenWarningsHarness.qml` and `Tests/main-screen-warnings.test.py runtime` run production MainScreen non-visibly on private headless Cage. Seventeen fixture-panel cases cover loader registration, unloaded placeholders, caller context/name and screen routing, loaded region handoff, open/close/reopen reuse, keyboard-focus properties, and destruction unregistering every loader once. Closed/closing color is transparent; open color is black with configured dim alpha. With the bar hidden, closed/closing mask construction has zero-sized subtract regions. Panels, backgrounds, and services are inert fixtures; animations are disabled. These are QML color/Region/layer-shell property assertions, not compositor pixels, input delivery, real SmartPanel animations, or consumer-panel acceptance.
- `Tests/smart-panel-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] PanelBackground retains 13 unsuppressed `missing-property` diagnostics: `panelItem` and corner-state fields live on anonymous Items, outside static Item metadata. Exact-count lint acceptance leaves the shared typed metadata blocker unresolved.

- [ ] Four dynamic Loader member diagnostics remain after the `05772415d` SmartPanel warning reduction (76 → 4); runtime lifecycle coverage is not zero-warning static-analysis acceptance.
- [ ] MainScreen retains 11 `missing-property` diagnostics after `8a689c0bc` (48 → 11): five installed screen-metadata diagnostics and six optional SmartPanel key-handler diagnostics. Its standalone lint gate accepts exactly that count with exit status zero; no compositor pixel or desktop input-delivery proof is provided by its nonvisible fixture suite.

- [ ] Add executable coverage for watchdog timeout recovery and zero-duration animation paths.
- [ ] Add executable coverage for remaining anchor combinations and constrained/oversized content.
- [ ] Add executable coverage for keyboard shortcut forwarding and escape-to-close behavior.

## Out of scope

- Feature-specific panel content behavior belongs in each owning feature spec.
- Panel registration and lookup behavior is covered by [panel-service.md](panel-service.md).
