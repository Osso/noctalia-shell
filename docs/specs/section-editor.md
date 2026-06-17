Section Editor covers the shared widget-section editor used by bar and control-center settings. Runtime source lives in `Widgets/NSectionEditor.qml`; implementation notes belong in [docs/wiki/systems/section-editor.md](../wiki/systems/section-editor.md).

## What it must do

### Widget palette and drag feedback

- [x] Widget color selection returns stable foreground/background palette pairs from widget identity.
- [x] Drop indicator updates hide the indicator and stop pulse animation when drag is inactive.
- [x] Drop indicator updates show a nearby insertion point beside the closest target widget.
- [x] Drop indicator updates set target index, x/y position, opacity, and pulse animation for valid nearby targets.
- [x] Drop indicator updates suppress the adjusted same-position target while dragging.
- [x] Drop indicator updates support insertion at the beginning of a section.
- [x] Drop indicator updates hide the indicator, clear target index, and stop pulse animation when no target is close.

### Typed delegates

- [x] Widget delegates declare typed `index`, `modelData`, and `id` roles.
- [x] Widget delegates expose a `widgetId` alias from the typed id role.
- [x] Widget delegates use `widgetId` for settings lookup, label text, and settings-dialog payloads.
- [x] Widget delegates avoid repeated `modelData.id` reads after role declaration.

## How it works

- [docs/wiki/systems/section-editor.md](../wiki/systems/section-editor.md)

## Implementation inventory

- `Widgets/NSectionEditor.qml` - shared widget-section editor, color selection, drag feedback, add/remove/reorder/move signals, and typed widget delegates.
- `Modules/Panels/Settings/Tabs/BarTab.qml` - bar settings section editor usage.
- `Modules/Panels/Settings/Tabs/ControlCenterTab.qml` - control-center settings section editor usage.
- `Widgets/NSearchableComboBox.qml` - add-widget selector used by the section editor.

## Tests asserting this spec

- `Tests/section-editor-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for add/remove/reorder/move signal emission from UI actions.
- [ ] Add executable coverage for settings dialog creation and error handling.
- [ ] Add executable coverage for full drag release reorder and cross-section move flows.

## Out of scope

- Bar-specific widget persistence is covered by [bar.md](bar.md).
- Control Center widget persistence is covered by [control-center.md](control-center.md).
- Searchable combo box behavior is covered by [searchable-combo-box.md](searchable-combo-box.md).
