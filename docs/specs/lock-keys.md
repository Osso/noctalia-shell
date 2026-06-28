Lock keys covers Caps Lock, Num Lock, and Scroll Lock state publication for bar widgets and OSD notifications. Runtime source lives mainly in `Services/Keyboard/LockKeysService.qml` and `Modules/Bar/Widgets/LockKeys.qml`; implementation notes belong in [docs/wiki/systems/lock-keys.md](../wiki/systems/lock-keys.md).

## What it must do

### State polling

- [x] Lock-key state checks must avoid periodic shell pipelines.
- [x] Lock-key state checks must read LED brightness files directly.
- [x] Lock-key polling must not run at the old 200ms interval.
- [x] Startup state synchronization must avoid emitting lock-key changed signals before the initial state is known.

### Published state

- [x] The service must publish Caps Lock, Num Lock, and Scroll Lock boolean state.
- [x] The service must emit per-key change signals after initial state synchronization.

## How it works

- [ ] See [docs/wiki/systems/lock-keys.md](../wiki/systems/lock-keys.md).

## Implementation inventory

- `Services/Keyboard/LockKeysService.qml` - lock-key LED discovery, polling, state publication, and change signals.
- `Modules/Bar/Widgets/LockKeys.qml` - bar widget rendering for lock-key states.
- `Modules/OSD/OSD.qml` - OSD signal consumers for lock-key changes.

## Tests asserting this spec

- `Tests/lock-keys-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable behavior coverage for multi-device LED aggregation if multiple keyboards expose the same lock key.

## Out of scope

- Keyboard layout display is covered by [docs/specs/keyboard-layout.md](keyboard-layout.md).
- Lock-screen authentication is covered by [docs/specs/lock-screen.md](lock-screen.md).
