Idle Inhibitor covers shell-managed idle inhibition, backend selection, manual keep-awake controls, timeout changes, and user feedback. Runtime source lives mainly in `Services/Power/IdleInhibitorService.qml`; implementation notes belong in [docs/wiki/systems/idle-inhibitor.md](../wiki/systems/idle-inhibitor.md).

## What it must do

### Startup and backend selection

- [x] Initialization logs service startup.
- [x] Initialization detects the inhibition backend.
- [x] Backend detection probes only in automatic mode.
- [x] Backend detection probes `systemd-inhibit` first.
- [x] Backend detection selects and logs the systemd strategy when available.
- [x] Backend detection probes `wayhibitor` as fallback.
- [x] Backend detection selects and logs the Wayland strategy when available.
- [x] Backend detection warns when probes fail.
- [x] Backend detection falls back to the systemd strategy when no backend is detected.

### Inhibitor registry and state

- [x] Adding an inhibitor rejects duplicate ids.
- [x] Adding an inhibitor records the id, updates system inhibition with the new reason, and reports success.
- [x] Removing an inhibitor rejects unknown ids.
- [x] Removing an inhibitor removes known ids and refreshes system inhibition.
- [x] Inhibition state derives from whether any active inhibitors remain.
- [x] State updates avoid redundant backend changes.
- [x] State updates start or stop inhibition based on active ids.
- [x] Starting inhibition stores the active reason.
- [x] Starting inhibition delegates to the selected systemd or Wayland backend.
- [x] Starting inhibition fails closed for unknown strategies.
- [x] Starting inhibition marks inhibition active after starting the backend.
- [x] Stopping inhibition is idempotent when already stopped.
- [x] Stopping inhibition terminates the backend process and marks inhibition inactive.

### Backend launchers and manual toggle

- [x] Systemd inhibition launches `systemd-inhibit --what=idle --mode=block sleep infinity` with the active reason.
- [x] Wayland inhibition launches `wayhibitor`.
- [x] Backend launchers start the inhibitor process.
- [x] Manual toggle clears any existing timeout.
- [x] Manual toggle disables existing manual inhibition and reports `false`.
- [x] Manual toggle enables untimed manual inhibition and reports `true`.

### Timeouts and manual helpers

- [x] Timeout changes ignore negative deltas when no timeout is active.
- [x] Timeout changes create timed manual inhibition when a positive delta arrives without an active timeout.
- [x] Timeout changes remove manual inhibition when the resulting timeout expires.
- [x] Timeout changes update existing positive timeouts.
- [x] Removing manual inhibition clears timeout state, stops the timeout timer, removes the manual inhibitor id, and notifies the user.
- [x] Adding manual inhibition adds the manual inhibitor id and notifies the user.
- [x] Adding manual inhibition leaves untimed inhibition untimed.
- [x] Adding manual inhibition starts the timer for a new timeout.
- [x] Adding manual inhibition updates an existing timeout.
- [x] Adding manual inhibition clears an existing timeout when changed back to untimed.

## How it works

- [docs/wiki/systems/idle-inhibitor.md](../wiki/systems/idle-inhibitor.md)

## Implementation inventory

- `Services/Power/IdleInhibitorService.qml` - backend detection, inhibitor registry, process launch/stop, manual keep-awake state, and timeout handling.
- `Modules/Bar/Widgets/KeepAwake.qml` - bar keep-awake widget that toggles manual inhibition and adjusts timeout by wheel input.
- `Modules/Panels/ControlCenter/Widgets/KeepAwake.qml` - control-center keep-awake button that toggles manual inhibition.

## Tests asserting this spec

- `Tests/idle-inhibitor-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for bar KeepAwake click and wheel interactions.
- [ ] Add executable coverage for control-center KeepAwake toggle behavior.
- [ ] Add executable coverage for inhibitor process exit handling.
- [ ] Add executable coverage for active timeout timer expiry.

## Out of scope

- Power profile selection belongs in [power-profile.md](power-profile.md).
- Host backend behavior belongs to `systemd-inhibit` and `wayhibitor`; this spec covers only shell command selection and state handling.
