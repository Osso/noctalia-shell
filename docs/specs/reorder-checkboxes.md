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
- `Tests/shared-ui-widgets-warnings.test.py behavior` / `Tests/Qml/SharedUiWidgetsWarningsHarness.qml`: actual offscreen checklist toggle, immutable source preservation, required/disabled input guards, pointer drag start→move→release and reorder signals, invalid/no-op moves, model clear and reassignment. `e32bd53ce` adds forward/reverse drag geometry, stacking, clear during an active grab, and reassigned-list recovery. Saved isolated actual-QML proof through `a3b2fab58` reports seven passes (five behavioral cases plus initialization/cleanup), zero failures.
- `Tests/shared-ui-widgets-warnings.test.py lint`: through `a3b2fab58`, checklist target warnings are zero; the final four block-scope declaration warnings drop 4→0. Remaining unused-import Info is not a warning.

## Known gaps (current cycle)

- [ ] Required/disabled visual appearance and disabled-item physical interaction are not asserted; input enabled properties and direct required-toggle guards are checked.
- [ ] Offscreen synthetic pointer input does not prove desktop drag behavior or settings persistence.

## Out of scope

- Feature-specific ordered setting persistence belongs in each owning feature spec.
