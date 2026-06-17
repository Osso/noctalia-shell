The tooltip module provides the shared popup tooltip used by sliders, buttons, menus, cards, and settings controls. Its source lives in [Modules/Tooltip/Tooltip.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Tooltip/Tooltip.qml).

## What it must do

Lifecycle:
- [x] Showing a tooltip with a missing target or empty text must leave the existing tooltip text unchanged.
- [x] Showing a tooltip must type required target and text inputs while keeping optional display inputs flexible.
- [x] TooltipService show must type required target and text inputs while keeping optional display inputs flexible.
- [x] Showing a valid tooltip must stop pending hide/show timers and hide animation, clear the outgoing state, process multiline text as rich text line breaks, set the target item, pick the target screen dimensions when available, initialize the hidden animation state, start the show timer, set direction, and apply the requested or default font family.
- [x] Positioning must fail closed when the target item or its parent is missing.
- [x] Hide must stop the show and hide timers, then either start the hide timer when a hide delay is active or start the hide animation immediately.
- [x] Starting hide animation must ignore already hidden or outgoing tooltips, mark the tooltip outgoing, stop show animation, and start hide animation.
- [x] Completing hide must clear visibility, outgoing state, text, positioned state, and restore container opacity/scale.
- [x] Immediate hide must stop show/hide timers and both animations, clear outgoing state, and complete the hide lifecycle.
- [x] Reset must stop show/hide timers and both animations, hide the tooltip, clear transient state, restore default direction and delays, and reset container opacity/scale.

Placement:
- [x] Auto placement must calculate tooltip dimensions, choose the first fitting direction in bottom/top/right/left order, clamp horizontally to the screen, set anchor coordinates, mark the tooltip positioned, show it, and start show animation.
- [x] Text updates on a visible tooltip must process multiline text as rich text line breaks, recalculate dimensions and anchor coordinates, clamp horizontally, and refresh the popup anchor on the next Qt tick.

## How it works

- [ ] See [docs/wiki/systems/tooltip.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/tooltip.md).

## Implementation inventory

- [Modules/Tooltip/Tooltip.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/Tooltip/Tooltip.qml) - shared popup window, timers, animations, placement, and lifecycle functions.
- [Widgets/NSlider.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NSlider.qml) - slider hover integration.
- [Widgets/NColorSlider.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Widgets/NColorSlider.qml) - color slider hover integration.

## Tests asserting this spec

- [Tests/tooltip-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/tooltip-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

## Known gaps (current cycle)

- [ ] Add function-level coverage before behavior/spec expansion if `code-index` reports any untested tooltip functions.

## Out of scope

- Theme-specific visual styling is covered by [docs/specs/theming.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/theming.md).
- Per-widget tooltip labels and translation strings are owned by the calling widget specs.
