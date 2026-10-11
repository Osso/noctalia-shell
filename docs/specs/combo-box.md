Combo Box covers the shared non-searchable `NComboBox` settings widget used for small option lists. Runtime source lives in [Widgets/NComboBox.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NComboBox.qml).

## What it must do

Model helpers:
- [x] `itemCount()` must return `0` when the model is missing.
- [x] `itemCount()` must return `model.count` when the model exposes a numeric `count`.
- [x] `itemCount()` must return array length for array-backed models.
- [x] `itemCount()` must reject plain length-shaped objects that are not arrays.
- [x] `getItem(index)` must type the index input, return items from `model.get(index)` or array-backed models, and return `null` for missing or unsupported models.
- [x] `findIndexByKey(key)` must type the key input, return the first matching item index, and return `-1` when no item matches.

Typed delegate contract:
- [x] Combo box item delegates must type the parent combo box reference as `ComboBox`.
- [x] Combo box item delegates must declare an integer `index` role before deriving `itemIndex`.

Activation and popup behavior:
- [x] Combo box activation emits the selected key for the current item and ignores missing-key or out-of-range items.
- [x] Delegate clicks select the item, update the parent combo-box index, and close the popup.
- [x] Delegate clicks defer selection while the list is flicking or moving, cancel the flick, and start a retry timer.
- [x] Pending click retries restart while the list is still moving, then select once and clear the pending flag when the list settles.

## How it works

- [ ] See [docs/wiki/systems/combo-box.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/combo-box.md).

## Implementation inventory

- [Widgets/NComboBox.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NComboBox.qml) - shared combo box model helpers, selected signal, delegate, and popup behavior.

## Tests asserting this spec

- [Tests/widget-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/widget-helper-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

- `Tests/shared-ui-widgets-warnings.test.py behavior` / `Tests/Qml/SharedUiWidgetsWarningsHarness.qml`: actual offscreen keyboard activation/focus border, pointer delegate selection, popup close/reopen and closed-list clearing, source clear, missing key, array/null/unsupported models, and invalid activation. A real moving list receives a direct delegate `clicked()` signal and emits exactly one deferred selection before closing (through `92726d66a`).

## Known gaps (current cycle)

- [ ] Moving-list coverage injects the click signal, not a physical pointer click during a flick; repeated retry while movement persists is not separately forced.
- [ ] Selected keyboard/popup paths do not establish exhaustive keyboard navigation, desktop input, or real settings persistence.

## Out of scope

- Search filtering behavior belongs in [docs/specs/searchable-combo-box.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/searchable-combo-box.md).
