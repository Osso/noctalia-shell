The shape corner helper defines the typed corner math used by bar and panel backgrounds for normal, flat, and inverted corner rendering. Its source lives in [Modules/MainScreen/Backgrounds/ShapeCornerHelper.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/MainScreen/Backgrounds/ShapeCornerHelper.qml).

## What it must do

Typed API:
- [x] `getMultX(cornerState)` must take an `int` corner state and return an `int` multiplier.
- [x] `getMultY(cornerState)` must take an `int` corner state and return an `int` multiplier.
- [x] `getArcDirection(multX, multY)` must take typed integer multipliers and return an integer arc direction.
- [x] `getArcDirectionFromState(cornerState)` must take an `int` corner state and return an integer arc direction.
- [x] `getFlattenedRadius(dimension, requestedRadius)` must take real dimensions/radius values and return a real radius.
- [x] `shouldFlatten(width, height, radius)` must take real dimensions/radius values and return a boolean.

Corner math:
- [x] X-axis multiplier must invert only horizontal corner state `1`; every other state returns `1`.
- [x] Y-axis multiplier must invert only vertical corner state `2`; every other state returns `1`.
- [x] Arc direction must use XOR-style multiplier inversion: exactly one negative multiplier maps to `PathArc.Counterclockwise`, otherwise `PathArc.Clockwise`.
- [x] Arc direction from state must compose `getMultX`, `getMultY`, and `getArcDirection`.

Flattening:
- [x] Flattened radius must clamp to half the dimension when the dimension is smaller than the requested diameter.
- [x] Flattened radius must preserve the requested radius when the dimension can fit the requested diameter.
- [x] `shouldFlatten` must return true when either width or height is smaller than the requested diameter.

Background consumers:
- [x] Bar background corner radius must map flat corner state `-1` to `0`.
- [x] Bar background corner radius must map non-flat corner states to the effective radius.
- [x] Panel background corner radius must map flat corner state `-1` to `0`.
- [x] Panel background corner radius must map non-flat corner states to the effective radius.

## How it works

- [ ] See [docs/wiki/systems/shape-corner-helper.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/shape-corner-helper.md).

## Implementation inventory

- [Modules/MainScreen/Backgrounds/ShapeCornerHelper.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/MainScreen/Backgrounds/ShapeCornerHelper.qml) - singleton helper for corner multipliers, arc direction, and radius flattening.
- [Modules/MainScreen/Backgrounds/BarBackground.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/MainScreen/Backgrounds/BarBackground.qml) - bar background consumer of corner state helpers.
- [Modules/MainScreen/Backgrounds/PanelBackground.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/MainScreen/Backgrounds/PanelBackground.qml) - panel background consumer of corner state helpers.

## Tests asserting this spec

- [Tests/shape-corner-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/shape-corner-helper-guards.test.js)
- [Tests/widget-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/widget-helper-guards.test.js)

## Known gaps (current cycle)

- [ ] Add function-level coverage before behavior/spec expansion if `code-index` reports any untested shape corner helper functions.

## Out of scope

- Full visual rendering of generated background paths is covered by bar/panel background behavior, not this helper contract.
