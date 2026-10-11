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
- `Services/UI/PanelService.qml` - panel registration and close notifications consumed by SmartPanel.
- `Modules/Panels/**/*.qml` - panel implementations built on SmartPanel.

## Tests asserting this spec

- `Tests/panel-service-guards.test.js`
- `Tests/Qml/PanelServiceLifecycleHarness.qml`
- `Tests/panel-service-lifecycle.test.sh` runs production SmartPanel/PanelService non-visibly: 24 geometry cases (two viewport sizes × four bar edges × three placement modes), one close-before-fade case, and one teardown-while-open case. Assertions cover nonzero animations, content resizing without recreation, Loader unloading, caller Component context, signal counts, and stable registry cleanup after output-name changes. Settings bootstrap is real but isolated; panel content is a fixture, not each consumer panel.
- `Tests/smart-panel-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Four dynamic Loader member diagnostics remain after the `05772415d` SmartPanel warning reduction (76 → 4); runtime lifecycle coverage is not zero-warning static-analysis acceptance.

- [ ] Add executable coverage for watchdog timeout recovery and zero-duration animation paths.
- [ ] Add executable coverage for remaining anchor combinations and constrained/oversized content.
- [ ] Add executable coverage for keyboard shortcut forwarding and escape-to-close behavior.

## Out of scope

- Feature-specific panel content behavior belongs in each owning feature spec.
- Panel registration and lookup behavior is covered by [panel-service.md](panel-service.md).
