Smart Panel covers the shared panel shell used by settings, changelog, control center, and other MainScreen panels. Runtime source lives in `Modules/MainScreen/SmartPanel.qml`; implementation notes belong in [docs/wiki/systems/smart-panel.md](../wiki/systems/smart-panel.md).

## What it must do

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

- `Tests/smart-panel-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for open lifecycle, open watchdog, and size/opacity animation finalization.
- [ ] Add executable coverage for vertical bar placement and explicit anchor combinations.
- [ ] Add executable coverage for keyboard shortcut forwarding and escape-to-close behavior.

## Out of scope

- Feature-specific panel content behavior belongs in each owning feature spec.
- Panel registration and lookup behavior is covered by [panel-service.md](panel-service.md).
