Reorder Checkboxes covers the shared checklist widget that toggles required/optional entries and reorders list entries. Runtime source lives in `Widgets/NReorderCheckboxes.qml`; implementation notes belong in [docs/wiki/systems/reorder-checkboxes.md](../wiki/systems/reorder-checkboxes.md).

## What it must do

### Toggle behavior

- [x] Toggle requests ignore negative and out-of-range indexes.
- [x] Toggle requests use a typed integer index input.
- [x] Toggle requests ignore required items.
- [x] Valid toggle requests copy the model array before mutating it.
- [x] Valid toggle requests copy the toggled item object before changing its enabled state.
- [x] Valid toggle requests invert the target item enabled state.
- [x] Valid toggle requests emit the toggled index and new enabled state.

### Reorder behavior

- [x] Reorder requests ignore no-op moves where source and target indexes match.
- [x] Reorder requests use typed integer source and target index inputs.
- [x] Reorder requests ignore negative and out-of-range source indexes.
- [x] Reorder requests ignore negative and out-of-range target indexes.
- [x] Valid reorder requests copy the model array before moving entries.
- [x] Valid reorder requests move the source item to the requested target index.
- [x] Valid reorder requests emit the source and target indexes.

### Typed delegates

- [x] Reorder checkbox delegates declare typed `index`, `id`, and `text` roles.
- [x] Reorder checkbox delegates expose readonly derived flags for item enabled state, required state, disabled state, and drag availability.
- [x] Reorder checkbox delegates avoid binding the model `enabled` role to `Item.enabled`.
- [x] Reorder checkbox delegates use typed roles instead of repeated `modelData.id` and `modelData.text` reads.

## How it works

- [docs/wiki/systems/reorder-checkboxes.md](../wiki/systems/reorder-checkboxes.md)

## Implementation inventory

- `Widgets/NReorderCheckboxes.qml` - shared toggle/reorder checklist, immutable model updates, drag state, and typed delegate roles.
- `Modules/Panels/Settings/Tabs/SessionMenuTab.qml` - session menu settings usage.
- `Modules/Panels/Settings/Bar/WidgetSettings/*.qml` - bar widget setting usage where ordered enabled entries are configured.

## Tests asserting this spec

- `Tests/reorder-checkboxes-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for drag-start, drag-target, and drag-end reorder flow.
- [ ] Add executable coverage for disabled item drag/toggle UI guards.
- [ ] Add executable coverage for required and disabled visual states.

## Out of scope

- Feature-specific ordered setting persistence belongs in each owning feature spec.
