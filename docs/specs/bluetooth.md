Bluetooth covers adapter state helpers, device ordering, device icons, connection eligibility, action helpers, status/signal/battery display helpers, typed device models, and Bluetooth device list roles. Runtime source lives mainly in `Services/Networking/BluetoothService.qml`; implementation notes belong in [docs/wiki/systems/bluetooth.md](../wiki/systems/bluetooth.md).

## What it must do

### Service lifecycle and device ordering

- [x] Bluetooth service startup logs that the service started.
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

- [x] Bluetooth service `devices` is typed as `ObjectModel`, not `var`.
- [x] Bluetooth device list delegates type `modelData` as `BluetoothDevice` and `index` as `int`.
- [x] Bluetooth device list delegates expose stable aliases for pairing, blocked, connected, connecting, display name, signal strength, battery availability, connectability, disconnectability, and busy state.
- [x] Bluetooth device list delegates use those aliases for displayed text, signal/battery visibility, and action availability.
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

## Tests asserting this spec

- `Tests/bluetooth-service-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/widget-helper-guards.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for rfkill/Wi-Fi blocked detection and airplane-mode toast behavior.
- [ ] Add executable tests for Bluetooth panel row interactions and action dispatch.
- [ ] Add executable tests for bar/control-center Bluetooth widget behavior.
- [ ] Add probe coverage for adapter/device discovery output if a stable read-only probe is available.

## Out of scope

- Wi-Fi and airplane-mode network state belongs in [network.md](network.md).
- Bluetooth battery display inside battery widgets belongs in [battery.md](battery.md).
