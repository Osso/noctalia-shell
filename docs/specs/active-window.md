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

### Title, visibility, and actions

- [x] Window title rendering uses the compositor title when present and falls back to `No active window`.
- [x] Hidden mode hides the widget when there is no focused window, but keeps it visible while fading out.
- [x] Transparent mode keeps the widget visible but transparent when there is no focused window.
- [x] Visible mode stays fully opaque even when there is no focused window.
- [x] The context-menu settings action closes the popup menu window before opening widget settings with the current widget identity.
- [x] Right clicking the widget opens its context menu at the BarService-provided widget position.

## How it works

- [docs/wiki/systems/active-window.md](../wiki/systems/active-window.md)

## Implementation inventory

- `Modules/Bar/Widgets/ActiveWindow.qml` - bar widget sizing, focused window title/icon rendering, icon lookup fallback chain, context menu, and compositor event refresh.
- `Modules/Panels/Settings/Bar/WidgetSettings/ActiveWindowSettings.qml` - settings UI for icon visibility, hide mode, scrolling mode, max width, fixed width, and icon colorization.
- `Services/UI/BarWidgetRegistry.qml` - ActiveWindow widget registration and settings binding.
- `Services/Compositor/CompositorService.qml` - focused window title/app-id source and active-window change signal.

## Tests asserting this spec

- `Tests/active-window-warnings.test.py` - standalone `lint` requires exit status zero and zero ActiveWindow static warnings (48→0 at `381ab5330`). Standalone `behavior` exercises direct production widgets and the production registry/BarWidgetLoader before delayed fixture Settings hydration. Four startup variants cross empty/focused startup with fixture/production Style; two soft-reload variants use empty/focused startup with production Style and visible focused widgets at reload (`164f2a3d7`, `32aad541d`, `3da5b0cca`, `9d89b21b9`). Assertions cover pre-ready metadata/settled dimensions, title and width cap, fixed width, vertical density, visible/transparent/hidden modes, production fade timing, and close-before-settings context arguments. Reload uses `Quickshell.reload(false)`, persistent generation state, and two configuration-loaded markers. Success requires exit status zero, `ACTIVE_WINDOW_BEHAVIOR_PASS`, and no logged `WARN`, `ERROR`, or `FATAL` in either space- or colon-prefixed forms. Offscreen runs isolate writable paths, make a permission-locked hash-verified real-settings backup, and check original bytes unchanged. Neither mode is registered in `run-tests.sh`; fixture Settings/compositor/services do not prove canonical bootstrap or reload.
- `Tests/active-window-settings-warnings.test.py` — through `40d1f6391`/`a5322cf4b`/`9f3c50289`, ActiveWindowSettings static warnings drop 6→0. Four offscreen behavioral cases plus QtTest init/cleanup yield six reported passes: option/default selection, pending edits and copy-save isolation, width validation/reactive controls, and shared-dialog cancel/reopen/apply against synthetic settings. Apply preserves unrelated fields and records one targeted update; cancel preserves fixture state. Invocation and config-denied isolation: [testing](testing.md#activewindow-settings-isolated-runtime). No real persistence or canonical reload proof.
- `Tests/active-window-widget-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [x] Add executable coverage for active window title rendering and hide modes.
- [x] Add isolated executable coverage for fixed-width geometry and dynamic title width caps.
- [ ] Add executable coverage for scrolling motion; selecting `scrollingMode: "always"` in the isolated harness does not prove motion.
- [x] Add executable coverage for context-menu actions.
- [ ] Add executable coverage for real ActiveWindow settings persistence; isolated editor copy-save and dialog apply/cancel cover synthetic state only.
- [ ] Canonical LIVE runtime still emits four undefined-assignment warnings before Settings loads. Root cause remains unproved; zero static warnings and six isolated startup/reload variants do not establish zero canonical runtime warnings or a live fix.

## Out of scope

- Compositor backend focused-window parsing belongs in [compositor.md](compositor.md).
- General bar widget registration and placement belong in [bar.md](bar.md).
