Active Window covers the bar widget that displays the focused window title and app icon. Runtime source lives mainly in `Modules/Bar/Widgets/ActiveWindow.qml`; implementation notes belong in [docs/wiki/systems/active-window.md](../wiki/systems/active-window.md).

## What it must do

### Sizing

- [x] Vertical dimension is derived from the scaled base widget size.
- [x] Content width includes text width, margins, and icon width when the icon is visible.
- [x] Content width omits icon width when icons are hidden.

### App icon lookup

- [x] App icon lookup prefers the focused window app id from the compositor.
- [x] Focused window app ids are normalized before icon lookup.
- [x] On Hyprland, icon lookup can fall back to the active toplevel app id.
- [x] Numeric toplevel app ids are converted to strings before icon lookup.
- [x] Icon lookup falls back to the configured fallback icon when app lookup fails.
- [x] Icon lookup logs ActiveWindow warnings when lookup throws.

## How it works

- [docs/wiki/systems/active-window.md](../wiki/systems/active-window.md)

## Implementation inventory

- `Modules/Bar/Widgets/ActiveWindow.qml` - bar widget sizing, focused window title/icon rendering, icon lookup fallback chain, context menu, and compositor event refresh.
- `Modules/Panels/Settings/Bar/WidgetSettings/ActiveWindowSettings.qml` - settings UI for icon visibility, hide mode, scrolling mode, max width, fixed width, and icon colorization.
- `Services/UI/BarWidgetRegistry.qml` - ActiveWindow widget registration and settings binding.
- `Services/Compositor/CompositorService.qml` - focused window title/app-id source and active-window change signal.

## Tests asserting this spec

- `Tests/active-window-widget-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for active window title rendering and hide modes.
- [ ] Add executable coverage for scrolling/fixed-width behavior.
- [ ] Add executable coverage for context-menu actions.
- [ ] Add executable coverage for ActiveWindow settings persistence.

## Out of scope

- Compositor backend focused-window parsing belongs in [compositor.md](compositor.md).
- General bar widget registration and placement belong in [bar.md](bar.md).
