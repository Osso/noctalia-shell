Bluetooth covers adapter state helpers, device ordering, device icons, connection eligibility, action helpers, status/signal/battery display helpers, typed device models, and Bluetooth device list roles. Runtime source lives mainly in `Services/Networking/BluetoothService.qml`; implementation notes belong in [docs/wiki/systems/bluetooth.md](../wiki/systems/bluetooth.md).

## What it must do

### Service lifecycle, probe resilience, and device ordering

- [x] Bluetooth service startup logs that the service started.
- [x] The read-only Bluetooth probe bounds each `bluetoothctl` query and fails with the query context and configured timeout instead of hanging.
- [x] The Bluetooth probe accepts an explicit `NOCTALIA_BLUETOOTHCTL` command for deterministic test execution; without it, it uses the host `bluetoothctl` diagnostic.
- [x] The rfkill Wi-Fi probe buffers stdout/stderr until process exit and only changes Wi-Fi for successful, parseable blocked-state output.
- [x] Nonzero exits, failed process starts, empty or malformed output, and adapter loss before completion preserve Wi-Fi state, log a diagnostic, and fall back to Bluetooth state feedback.
- [x] Normal exits are not finalized again by the process running-state transition.
- [x] Device sorting sorts the provided device array in place.
- [x] Device sorting falls back from `name` to `deviceName`.
- [x] Device sorting prefers human-readable names before short/opaque names.
- [x] Device sorting normalizes missing or non-positive signal strength to zero.
- [x] Device sorting orders devices within the same name-quality group by signal strength descending.

### Device icons and action eligibility

- [x] Missing devices use the generic Bluetooth device icon.
- [x] Device icon selection normalizes names and uses icon/name metadata to detect headphones, mice, keyboards, phones, watches, speakers, and displays.
- [x] Unknown device icon metadata falls back to the generic Bluetooth device icon.
- [x] Connect eligibility rejects missing devices and only allows idle, unblocked, disconnected devices.
- [x] Disconnect eligibility rejects missing devices and only allows idle, unblocked, connected devices.
- [x] Busy-state detection rejects missing devices and treats pairing, connecting, and disconnecting devices as busy.

### Status, signal, and battery helpers

- [x] Status text reports connecting, pairing, and blocked devices with translation keys.
- [x] Status text returns an empty string for normal devices.
- [x] Signal strength text reports unknown, excellent, good, fair, poor, and very poor states.
- [x] Signal icon selection maps missing/invalid, excellent, good, fair, poor, and very poor signals to antenna icons.
- [x] Battery helper rounds battery fractions into display percentages.

### Device actions and adapter state

- [x] Connect-with-trust ignores missing devices.
- [x] Connect-with-trust marks a device trusted before connecting it.
- [x] Disconnect ignores missing devices and calls device disconnect when present.
- [x] Forget ignores missing devices.
- [x] Forget marks a device untrusted before forgetting it.
- [x] Bluetooth enable/disable fails closed and logs when no adapter is available.
- [x] Bluetooth enable/disable logs the requested state and writes it to the adapter when available.

### Types and device-list roles

- [ ] Bluetooth device lists default to an empty array; an omitted model or empty device array produces zero rows without model-length errors.
- [ ] Bluetooth device lists use the caller-provided array and reflect its replacement, including replacement with an empty array.
- [x] Bluetooth service `devices` is typed as `ObjectModel`, not `var`.
- [x] Bluetooth device list delegates type `modelData` as `BluetoothDevice` and `index` as `int`.
- [x] Bluetooth device list delegates expose stable aliases for pairing, blocked, connected, connecting, display name, battery availability, connectability, disconnectability, and busy state.
- [x] Bluetooth device list delegates use those aliases for displayed text, battery visibility, and action availability.
- [x] Bluetooth device lists show no signal-strength row: the installed Quickshell `BluetoothDevice` contract has no signal-strength property. Name/status/battery rows retain the no-signal layout geometry even if a fixture adds a hypothetical signal-strength property.
- [x] Bluetooth device list content color uses primary color for pairing or connecting devices.
- [x] Bluetooth device list content color uses error color for blocked devices that are not pairing or connecting.
- [x] Bluetooth device list content color preserves the caller-provided default color for normal devices.

## How it works

- [docs/wiki/systems/bluetooth.md](../wiki/systems/bluetooth.md)

## Implementation inventory

- `Services/Networking/BluetoothService.qml` - adapter state, device ordering, icon/status/signal helpers, action helpers, and adapter enable/disable.
- `Modules/Panels/Bluetooth/BluetoothPanel.qml` - Bluetooth panel shell.
- `Modules/Panels/Bluetooth/BluetoothDevicesList.qml` - typed device list rows and action controls.
- `Modules/Bar/Widgets/Bluetooth.qml` - bar Bluetooth widget.
- `Modules/Panels/ControlCenter/Widgets/Bluetooth.qml` - control-center Bluetooth shortcut.
- `Modules/Panels/Settings/Tabs/NetworkTab.qml` - Bluetooth settings toggle.
- `Bin/dev/service-probes.sh` - bounded Bluetooth controller and connected-device probe, with optional injected `bluetoothctl` command.
- `Tests/fixtures/bluetoothctl` - deterministic controller-state fixture for automated Bluetooth probes.

## Tests asserting this spec

- `Tests/bar-controls-warnings.test.py` — isolated production bar-widget toggle dispatch, panel/context/settings routing, display modes, and vertical collapse. Cohort evidence: [bar](bar.md#bar-control-cohort); fixture limits: [testing](testing.md#bar-control-cohort).

- `Tests/root-service-warnings.test.py behavior` / `Tests/Qml/RootServiceHarness.qml` — production BluetoothService handles fixture enabling/enabled/blocked/disabled events, suppresses transitional toast feedback, starts discovery through its timer, and handles injected successful/failed rfkill completion. One of five behavioral cases at `8b1de9d34`; adapter, process, network, and toast boundaries are inert. Root-only lint retains eight `unresolved-type` and three `missing-property` warnings; no real adapter/radio effects or warning-free service claim. Cohort gates: [testing](testing.md#root-service-cohort).
- `Tests/bluetooth-service-warnings.test.py` — isolated service evidence at `858d93c35`: service-only warnings drop 11→8. Filtering through the typed `ObjectModel` removes three `values` member diagnostics; one adapter-type and seven enum-metadata diagnostics remain. Four behavioral cases pass, plus QtTest init/cleanup (six passes). The fake blocked-state event-ordering case failed and is excluded from the behavior claim; this is not full behavioral acceptance or warning-free lint. No radio, hardware, or network operations were performed. Evidence limits: [testing](testing.md#bluetooth-service-isolated-evidence).
- `Tests/bluetooth-service-guards.test.js`
- `Tests/bluetooth-devices-list-runtime.test.py` — nonvisible production-list default/empty models, caller array replacement, concrete device actions/state/battery, no-signal layout geometry, installed device metadata contract, and targeted lint (only the installed state-enum metadata warning remains).
- `Tests/qml-type-annotations.test.js`
- `Tests/widget-helper-guards.test.js`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] Add executable tests for Bluetooth panel row interactions and action dispatch.
- [ ] Add executable tests for control-center Bluetooth shortcut behavior and live adapter effects; isolated bar-widget dispatch does not exercise hardware.
- [ ] Add probe coverage for adapter/device discovery output beyond the deterministic controller fixture if a stable read-only probe is available.

## Out of scope

- Wi-Fi and airplane-mode network state belongs in [network.md](network.md).
- Bluetooth battery display inside battery widgets belongs in [battery.md](battery.md).
