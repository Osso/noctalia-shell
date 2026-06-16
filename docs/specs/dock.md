Dock covers the shell dock and dock context menu for running and pinned app actions. Runtime source lives mainly in `Modules/Dock/Dock.qml` and `Modules/Dock/DockMenu.qml`; implementation notes belong in [docs/wiki/systems/dock.md](../wiki/systems/dock.md).

## What it must do

### Dock menu sizing and items

- [x] Menu width calculation starts from zero, tolerates empty item lists, includes horizontal margins, includes icon width/spacing, measures text width, and enforces a minimum width.
- [x] Menu item initialization detects running toplevels and pinned apps.
- [x] Running apps expose a focus action.
- [x] All app menus expose a pin or unpin action with translated text.
- [x] Running apps expose a close action.
- [x] Desktop entry ids can be resolved through DesktopEntries heuristic lookup when available.

### Pin state

- [x] Pinned app lookup tolerates missing pinned-app settings.
- [x] Pin toggling copies pinned-app settings before mutation.
- [x] Pin toggling persists the updated pinned-app list.
- [x] Pin action toggles the current toplevel app and requests menu close.

### Actions and hover

- [x] Hover lookup computes item index from menu-relative Y position and clamps outside-menu positions to `-1`.
- [x] Focus action activates focusable toplevels and requests menu close.
- [x] Close action validates the toplevel against ToplevelManager before closing.
- [x] Close action closes valid toplevels, schedules dock refresh callback, hides the menu, and requests close.

### Types

- [x] Dock `currentContextMenu` is typed as `DockMenu`.
- [x] DockMenu `toplevel` is typed as `Toplevel`.
- [x] DockMenu item delegates use typed inputs instead of dynamic field access.

## How it works

- [docs/wiki/systems/dock.md](../wiki/systems/dock.md)

## Implementation inventory

- `Modules/Dock/Dock.qml` - dock shell and current context menu owner.
- `Modules/Dock/DockMenu.qml` - dock app context menu, item generation, pin/focus/close actions, and hover handling.
- `Assets/settings-default.json` - dock defaults, including pinned apps.
- `Modules/Panels/Settings/Tabs/DockTab.qml` - dock monitor and placement settings.
- `Modules/Panels/SetupWizard/SetupDockStep.qml` - setup-time dock monitor settings.

## Tests asserting this spec

- `Tests/dock-menu-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for `Dock.qml` app list and pinned app rendering.
- [ ] Add executable coverage for dock context menu show/hide timing.
- [ ] Add executable coverage for dock monitor settings in setup/settings flows.
- [ ] Add executable coverage for launching pinned apps without running toplevels.

## Out of scope

- Compositor toplevel models and focus/close backend behavior belong in [compositor.md](compositor.md).
- Setup wizard flow behavior belongs in a future setup/onboarding spec.
