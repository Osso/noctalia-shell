The view wrapper widgets provide shared `NGridView` and `NListView` components that expose selected native view properties while keeping Noctalia scrollbar styling and wrapper behavior in one place. Their source lives in [Widgets/NGridView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NGridView.qml) and [Widgets/NListView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NListView.qml).

## What it must do

Shared forwarding:
- [x] `NGridView` and `NListView` must expose the wrapped view `model`, `delegate`, and `currentIndex` through property aliases.
- [x] `NGridView` and `NListView` must report vertical scrollbar activity from wrapped content height relative to wrapped view height.
- [x] `positionViewAtIndex(index, mode)` must forward to the wrapped view with the same arguments.
- [x] `positionViewAtBeginning()` and `positionViewAtEnd()` must forward to the wrapped view.
- [x] `forceLayout()` and `cancelFlick()` must forward to the wrapped view.
- [x] `flick(xVelocity, yVelocity)` must forward both velocity arguments to the wrapped view.
- [x] `incrementCurrentIndex()` and `decrementCurrentIndex()` must forward to the wrapped view.
- [x] `indexAt(x, y)`, `itemAt(x, y)`, and `itemAtIndex(index)` must return the wrapped view results.

Grid wrapper:
- [x] `NGridView` must forward methods to its internal `gridView`.
- [x] `NGridView` must expose the internal `GridView` model, delegate, and current index aliases.

List wrapper:
- [x] `NListView` must forward methods to its internal `listView`.
- [x] `NListView` must expose the internal `ListView` model, delegate, and current index aliases.

## How it works

- [ ] See [docs/wiki/systems/view-wrapper.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/view-wrapper.md).

## Implementation inventory

- [Widgets/NGridView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NGridView.qml) - styled `GridView` wrapper with aliases, forwarding methods, and scrollbar state.
- [Widgets/NListView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NListView.qml) - styled `ListView` wrapper with aliases, forwarding methods, wheel handling, and scrollbar state.
- [Modules/Panels/Launcher/Launcher.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Launcher/Launcher.qml) - launcher consumer for list/grid result views.
- [Widgets/NIconPicker.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NIconPicker.qml) - icon picker consumer of `NGridView`.

## Tests asserting this spec

- [Tests/view-wrapper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/view-wrapper-guards.test.js)

## Known gaps (current cycle)

- [ ] Add function-level coverage before behavior/spec expansion if `code-index` reports any untested view wrapper functions.

## Out of scope

- Per-feature result navigation and selection behavior is owned by the consuming launcher, picker, or panel specs.
- Visual scrollbar styling beyond the asserted activity state is owned by theming and widget rendering coverage.
