The lock screen owns the session-lock UI, PAM authentication context, unlock lifecycle, and lock-screen-only status widgets. Runtime source lives mainly in [Modules/LockScreen/LockScreen.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockScreen.qml) and [Modules/LockScreen/LockContext.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockContext.qml).

## What it must do

Authentication:
- [x] Unlock attempts must fail closed when PAM is unavailable, show the failure state, set the error message to `PAM not available`, and leave unlock progress disabled.
- [x] Unlock attempts with PAM available must mark unlock in progress, clear previous error/failure state, log the authentication start, and start PAM authentication for the configured user.

Unlock lifecycle:
- [x] Scheduling unload after unlock must start the unload timer.
- [x] On an injected unlock signal, release the session-lock fixture and clear the password before delayed Loader unload; reactivation must create a locked, password-masked instance.
- [x] Destroying an instance with pending unload must not unload a replacement instance.

Password UI:
- [x] Mask passwords by default, route edits to the authentication context, and reveal plaintext only after the visibility toggle.
- [x] Submission must route to the context and disable input, reveal, and submit controls while unlock is in progress; an injected failure must clear input without unloading.

Typed contracts:
- [x] `PanelService.lockScreen` must be typed as a `Loader`.
- [x] Lock-screen forecast delegates must declare an integer `index` role before reading forecast arrays.
- [x] Forecast rows must preserve weekday, symbol, and temperature ordering for four days, reduced to three with playable media; wallpaper lookup must receive the surface screen name.

## How it works

- [ ] See [docs/wiki/systems/lock-screen.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/wiki/systems/lock-screen.md).

## Implementation inventory

- [Modules/LockScreen/LockScreen.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockScreen.qml) - session-lock loader, lock surfaces, unlock scheduling, status widgets, and lock-screen UI.
- [Modules/LockScreen/LockContext.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Modules/LockScreen/LockContext.qml) - PAM authentication state machine and unlock/failure signals.
- [Services/UI/PanelService.qml](/syncthing/Sync/Projects/apps/noctalia-shell/Services/UI/PanelService.qml) - typed lock-screen reference used by shell services.

## Tests asserting this spec

- [Tests/panel-lock-palette-helper-guards.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/panel-lock-palette-helper-guards.test.js)
- [Tests/qml-type-annotations.test.js](/syncthing/Sync/Projects/apps/noctalia-shell/Tests/qml-type-annotations.test.js)

- `Tests/lock-screen-warnings.test.py` — standalone lint and isolated production-UI runtime coverage. At `c9ebda0fc`/`b90b5c861`/`a00e603ed`, warnings fall 22→10; four behavioral cases plus QtTest init/cleanup report six passes, zero failures and no runtime warnings. Password-exposure (`visibility`) and delayed-unload (`unload`) mutations produced RED failures. Isolation and proof limits: [testing](testing.md#lock-screen-isolated-runtime).
- The remaining ten `unqualified` warnings are implicit cross-component `lockContext` captures at lines 433 (two), 448, 940, 946, 947, 951, 1052, 1089, and 1103 at `b90b5c861`. Deliberately retained to preserve security behavior pending exact proof; not a zero-warning claim.

## Known gaps (current cycle)

- [ ] Add executable coverage for PAM completion success/failure signal handling.
- [ ] Verify real compositor session locking, PAM authentication, physical input, and live rendering; offscreen fixtures are not live-lock proof.
- [ ] Add executable coverage for compact-mode layout and remaining context-capture changes.

## Out of scope

- Battery rendering inside the lock screen is covered by [docs/specs/battery.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/battery.md).
- Keyboard layout display is covered by [docs/specs/keyboard-layout.md](/syncthing/Sync/Projects/apps/noctalia-shell/docs/specs/keyboard-layout.md).
