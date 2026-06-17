Searchable Combo Box covers the shared searchable list selector used by settings and widget editing surfaces. Runtime source lives in `Widgets/NSearchableComboBox.qml`; implementation notes belong in [docs/wiki/systems/searchable-combo-box.md](../wiki/systems/searchable-combo-box.md).

## What it must do

### Key lookup

- [x] Base-model key lookup returns the first matching item index.
- [x] Base-model key lookup returns `-1` when no item matches.
- [x] Filtered-model key lookup searches only the filtered model.
- [x] Filtered-model key lookup returns `-1` for keys present only in the unfiltered source model.
- [x] Key lookup helpers use typed string key inputs.

### Filtering

- [x] Filtering clears stale filtered results before rebuilding the filtered model.
- [x] Filtering returns an empty filtered model when the source model is missing.
- [x] Filtering returns an empty filtered model when the source model has no count.
- [x] Blank search text copies all source items into the filtered model in source order.
- [x] Case-insensitive fallback search matches item names when fuzzy search is unavailable.
- [x] Fuzzy search uses item `name`, threshold `-1000`, and limit `50`.
- [x] Fuzzy search appends results in returned relevance order.

### Selection

- [x] Activation emits the selected key for the current filtered item.
- [x] Activation ignores invalid current indexes.
- [x] External `currentKey` changes sync the combo index to the matching filtered item or `-1`.

### Popup lifecycle

- [x] Opening the popup refreshes the filtered model immediately.
- [x] Opening the popup schedules focus for the search input when its input item exists.

### Types

- [x] The default popup delegate declares typed `index`, `key`, and `name` roles.
- [x] Badge repeaters in the default popup delegate declare typed string badge text.

## How it works

- [docs/wiki/systems/searchable-combo-box.md](../wiki/systems/searchable-combo-box.md)

## Implementation inventory

- `Widgets/NSearchableComboBox.qml` - shared searchable combo box, filtered model, key lookup helpers, and search filtering.
- `Helpers/FuzzySort.js` - fuzzy search helper consumed by the widget.
- `Widgets/NSectionEditor.qml` - section editor usage.
- `Modules/Panels/Settings/Tabs/GeneralTab.qml` - settings tab usage.
- `Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml` - clock widget setting usage.

## Tests asserting this spec

- `Tests/searchable-combo-box-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)
None.

## Out of scope

- Section editor behavior is covered by its own spec when direct behavior tests exist.
- Settings tab behavior belongs in each owning feature spec.
