The lock screen owns the session-lock UI, PAM authentication context, unlock lifecycle, and lock-screen-only status widgets. Runtime source lives mainly in [Modules/LockScreen/LockScreen.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockScreen.qml) and [Modules/LockScreen/LockContext.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockContext.qml).

## What it must do

Authentication:
- [x] Unlock attempts must fail closed when PAM is unavailable, show the failure state, set the error message to `PAM not available`, and leave unlock progress disabled.
- [x] Unlock attempts with PAM available must mark unlock in progress, clear previous error/failure state, log the authentication start, and start PAM authentication for the configured user.

Unlock lifecycle:
- [x] Scheduling unload after unlock must start the unload timer.

Typed contracts:
- [x] `PanelService.lockScreen` must be typed as a `Loader`.
- [x] Lock-screen forecast delegates must declare an integer `index` role before reading forecast arrays.

## How it works

- [ ] See [docs/wiki/systems/lock-screen.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/lock-screen.md).

## Implementation inventory

- [Modules/LockScreen/LockScreen.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockScreen.qml) - session-lock loader, lock surfaces, unlock scheduling, status widgets, and lock-screen UI.
- [Modules/LockScreen/LockContext.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockContext.qml) - PAM authentication state machine and unlock/failure signals.
- [Services/UI/PanelService.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Services/UI/PanelService.qml) - typed lock-screen reference used by shell services.

## Tests asserting this spec

- [Tests/panel-lock-palette-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/panel-lock-palette-helper-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

## Known gaps (current cycle)

- [ ] Add executable coverage for PAM completion success/failure signal handling.
- [ ] Add executable coverage for lock-screen rendering and compact-mode layout.

## Out of scope

- Battery rendering inside the lock screen is covered by [docs/specs/battery.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/battery.md).
- Keyboard layout display is covered by [docs/specs/keyboard-layout.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/keyboard-layout.md).
