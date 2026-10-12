The view wrapper widgets provide shared `NGridView` and `NListView` components that expose selected native view properties while keeping Noctalia scrollbar styling and wrapper behavior in one place. `NScrollView` also provides a padded, clipped scrolling viewport with styled horizontal and vertical scrollbars. Their source lives in [Widgets/NGridView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NGridView.qml) and [Widgets/NListView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NListView.qml).

## What it must do

Shared forwarding:
- [x] `NGridView` and `NListView` must expose the wrapped view `model`, `delegate`, and `currentIndex` through property aliases.
- [x] `NGridView` and `NListView` must report vertical scrollbar activity from wrapped content height relative to wrapped view height.
- [x] `positionViewAtIndex(index, mode)` must forward to the wrapped view with the same arguments.
- [x] `positionViewAtIndex(index, mode)` must type index and mode as integers.
- [x] `positionViewAtBeginning()` and `positionViewAtEnd()` must forward to the wrapped view.
- [x] `forceLayout()` and `cancelFlick()` must forward to the wrapped view.
- [x] `flick(xVelocity, yVelocity)` must forward both velocity arguments to the wrapped view.
- [x] `flick(xVelocity, yVelocity)` must type both velocity inputs as real numbers.
- [x] `incrementCurrentIndex()` and `decrementCurrentIndex()` must move selection within model bounds, wrap when `keyNavigationWraps` is enabled, and leave empty-model selection at -1.
- [x] `indexAt(x, y)`, `itemAt(x, y)`, and `itemAtIndex(index)` must return the wrapped view results.
- [x] `indexAt(x, y)`, `itemAt(x, y)`, and `itemAtIndex(index)` must type coordinate and index inputs.

Grid wrapper:
- [x] `NGridView` must forward view operations to its internal `gridView`; index increment/decrement must update its selection directly.
- [x] `NGridView` must expose the internal `GridView` model, delegate, and current index aliases.

List wrapper:
- [x] `NListView` must forward methods to its internal `listView`.
- [x] `NListView` must expose the internal `ListView` model, delegate, and current index aliases.

Scroll view (isolated assertions at `d3e94d7c0`):
- [x] `NScrollView` must preserve padded viewport and scrollbar geometry for small, exact-fit, tall, wide, and two-axis overflow content.
- [x] Content offsets must translate content and advance both scrollbar positions; resizing must update viewport and scrollbar dimensions.
- [x] `AlwaysOff` horizontal policy must constrain content width to the viewport, use vertical-only flicking with stopped bounds, and preserve vertical overflow after resizing.
- [x] Scrolled content must render inside the viewport without painting outside it.
- [x] Both scrollbar handles must use normal/pressed colors and restore normal color on release; `AlwaysOn` and active `AsNeeded` must expose handle/track opacity 1/0.3, while inactive `AsNeeded` hides both.

## How it works

- [ ] See [docs/wiki/systems/view-wrapper.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/view-wrapper.md).

## Implementation inventory

- [Widgets/NScrollView.qml](../../Widgets/NScrollView.qml) - padded scroll viewport with clipping, policies, and styled scrollbars.

- [Widgets/NGridView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NGridView.qml) - styled `GridView` wrapper with aliases, forwarding methods, and scrollbar state.
- [Widgets/NListView.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NListView.qml) - styled `ListView` wrapper with aliases, forwarding methods, wheel handling, and scrollbar state.
- [Modules/Panels/Launcher/Launcher.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Panels/Launcher/Launcher.qml) - launcher consumer for list/grid result views.
- [Widgets/NIconPicker.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NIconPicker.qml) - icon picker consumer of `NGridView`.

## Tests asserting this spec

- [Tests/view-wrapper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/view-wrapper-guards.test.js)

### Grid/list isolated evidence

- At `00178bc6e`/`5bf3a9d00`, GridView-only warnings drop 9→0 and ListView-only warnings 7→0 without suppression. [Runner](../../Tests/grid-list-warnings.test.py) and [harness](../../Tests/Qml/GridListWarningsHarness.qml) cover thirteen behavioral rows plus QtTest init/cleanup: fifteen reported offscreen cases.
- Both wrappers exercise repeated empty/small/exact-fit/overflow model changes, content/delegate geometry, scrollbar activity, selection and index lookup, beginning/end/index scrolling, cancel-flick state, index boundaries/wrapping, RTL→LTR scrollbar placement and resize, clipped pixels, and normal/pressed/released colors with policy opacity. List-only wheel events assert repeated movement and upper/lower bounds. Grid scrollbar placement remains relative to the wrapper so attached-view auto-positioning cannot replace RTL geometry.
- Staged-copy `palette`, `selection`, and `scrollbar-parent` mutations are expected-failing negative controls. Hover color, positive flick velocity, native input and live compositor rendering are not proven. Real-config access is denied/audited, not backed up or read; isolation and gates: [testing](testing.md#gridlist-isolated-runtime). This docs-only audit inspected source without rerunning tests.

### Scroll view isolated evidence

- At `d3e94d7c0`, NScrollView-only diagnostics drop 12→0 through explicit scrollbar-owner references, without suppression. [Runner](../../Tests/scrollview-warnings.test.py) and [harness](../../Tests/Qml/ScrollViewWarningsHarness.qml) assert ten behavioral cases (five geometry rows, offsets/resize, horizontal disable, clipped pixels, two palette rows), plus QtTest init/cleanup: twelve reported cases.
- The staged `runtime --mutation palette` negative control replaces pressed colors with normal colors and is expected to fail the pressed-color assertions. Hover color and native pointer interaction are not asserted. Isolation and acceptance gates: [testing](testing.md#scroll-view-isolated-runtime). This audit inspected source; it did not rerun proof commands.

### Busy indicator/divider isolated evidence

- At `627eb5599`, NBusyIndicator and NDivider each drop 1→0 unqualified warnings through explicit outer-owner references; Divider retains two unused-import informational notices. [Runner](../../Tests/busy-divider-warnings.test.py) and [harness](../../Tests/Qml/BusyDividerWarningsHarness.qml) cover four behavioral tests plus init/cleanup: six reported normal and six owner-shadow offscreen passes.
- Assertions cover busy-indicator default/reactive geometry and style, an arc pixel using the outer stroke width, animation stop/resume with a changed duration, and divider orientation, parent resizing and border thickness. Shadow fixtures collide with Canvas `strokeWidth` and Gradient `vertical`; reported owner-collision RED establishes the failure boundary before qualification.
- Private config masking and proof limits: [testing](testing.md#busy-indicatordivider-isolated-runtime). Native/compositor rendering and whole-shell acceptance remain unproven. This docs-only audit inspected source without rerunning tests.

### Tab buttons isolated evidence

- At `3f3e0be41`, NIconTabButton and NTabButton each drop 2→0 warnings without suppression. Both expose `property NTabBar tabBar: null`; the containing NTabBar assigns itself to button children. Clicks emit `clicked` before updating that explicit owner's `currentIndex`, without discovering ownership through ancestor properties. Unused QtQuick.Controls imports are removed from all three widgets; NIconTabButton also drops Quickshell.
- [Runner](../../Tests/tab-button-warnings.test.py) and [QtTest harness](../../Tests/Qml/TabButtonWarningsHarness.qml) cover text/icon selection and text/icon owner-shadow rows: four behavioral rows plus init/cleanup, six reported isolated cases. Selection asserts independent bars, checked bindings, pre-update click observation, fixture-provided left/right keyboard navigation, and delegate destruction/recreation. Shadow rows reparent buttons beneath conflicting `currentIndex` and `tabBar` members and assert the original explicit owner still changes.
- [Private Quickshell harness](../../Tests/Qml/TabButtonReloadHarness.qml) checks assigned owners, independent selection and recreated delegates at cold start and after a private source reload. Isolation, acceptance gates and limits: [testing](testing.md#tab-buttons-isolated-runtime). This docs-only audit inspected source; no proof commands were rerun.

## Known gaps (current cycle)

- [ ] Add function-level coverage before behavior/spec expansion if `code-index` reports any untested view wrapper functions.

## Out of scope

- Per-feature result navigation and selection behavior is owned by the consuming launcher, picker, or panel specs.
- Scrollbar styling beyond the scroll-view assertions above is owned by theming and widget rendering coverage; real compositor/input and whole-shell acceptance are not proven here.
