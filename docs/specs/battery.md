Battery covers UPower battery selection, Bluetooth battery matching, low-battery warnings, battery panel display helpers, charge-threshold writes, battery IPC mode mapping, and battery probe parsing. Runtime source lives mainly in `Modules/Bar/Widgets/Battery.qml`, `Modules/Panels/Battery/BatteryPanel.qml`, and `Services/Hardware/BatteryService.qml`; implementation notes belong in [docs/wiki/systems/battery.md](../wiki/systems/battery.md).

## What it must do

### Battery and Bluetooth device selection

- [x] The battery widget uses the configured native path when it resolves to a battery device with a percentage.
- [x] The battery widget falls back to the UPower display device when the configured native path is missing, line power, missing, or blank.
- [x] Bluetooth device lookup extracts MAC addresses case-insensitively from the native path.
- [x] Bluetooth device lookup returns `null` for missing Bluetooth device lists or native paths without a MAC address.
- [x] Current battery percent prefers Bluetooth battery percentage when present.
- [x] Current battery percent falls back to UPower battery percentage or zero when no battery is available.

### Battery panel display

- [x] Battery panel device-path selection prefers a right-section battery widget over left and center sections.
- [x] Battery panel device-path selection falls back from left to center sections.
- [x] Battery panel device-path selection ignores missing device paths and non-battery widgets.
- [x] Battery panel device names require ready state.
- [x] Battery panel device names suppress laptop battery names.
- [x] Battery panel device names prefer Bluetooth names, then non-laptop battery models, then an empty string.

### Low-battery warnings

- [x] Low-battery warning shows once when discharging below the configured warning threshold.
- [x] Low-battery warning does not repeat while still below threshold.
- [x] Low-battery warning resets only after recovery above threshold plus hysteresis.
- [x] Charging suppresses low-battery warnings and clears the notification state.

### Settings and IPC

- [x] Battery settings start the write-threshold process with `start` and the requested value for start-threshold changes.
- [x] Battery settings start the write-threshold process with `end` and the requested value for stop-threshold changes.
- [x] The `batteryManager.cycle` IPC command delegates to the battery service cycle helper.
- [x] The `batteryManager.set` IPC command maps `full`, `balanced`, and `lifespan` strings to their charging modes.

### Types and probes

- [x] Battery references in bar widget, lock screen, battery panel, and battery tab are typed as `UPowerDevice`, not `var`.
- [x] UPower percentage probe parsing accepts valid percentage rows and rejects invalid, prefixed, malformed, and out-of-range rows.
- [x] UPower battery-state probe parsing accepts valid battery states and rejects invalid, prefixed, and malformed rows.
- [x] Physical UPower battery probe parsing requires a non-empty native path and `rechargeable: yes` without malformed or prefixed rows.

## How it works

- [docs/wiki/systems/battery.md](../wiki/systems/battery.md)

## Implementation inventory

- `Modules/Bar/Widgets/Battery.qml` - bar battery widget, UPower/Bluetooth device lookup, percentage selection, and low-battery warnings.
- `Modules/Panels/Battery/BatteryPanel.qml` - battery panel device selection and display-name helpers.
- `Modules/Panels/Settings/Tabs/BatteryTab.qml` - battery settings and charge-threshold write helpers.
- `Modules/Panels/Settings/Bar/WidgetSettings/BatterySettings.qml` - per-widget battery settings UI.
- `Modules/LockScreen/LockScreen.qml` - lock-screen battery display.
- `Services/Hardware/BatteryService.qml` - battery charging mode service used by IPC.
- `Services/Control/IPCService.qml` - battery manager IPC command mapping.
- `Bin/dev/service-probes.sh` - read-only UPower probe parsing.

## Tests asserting this spec

- `Tests/battery-widget-guards.test.js`
- `Tests/battery-panel-guards.test.js`
- `Tests/battery-tab-guards.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] Add executable tests for `Services/Hardware/BatteryService.qml` charging-mode cycling and command routing.
- [ ] Add executable tests for battery panel health/time display text.
- [ ] Add executable tests for per-widget battery settings device list filtering.
- [ ] Add runtime/probe coverage for actual threshold write command construction.

## Out of scope

- Power profile switching belongs in [power-profile.md](power-profile.md).
- Bluetooth pairing and connection behavior belongs in a separate Bluetooth spec.
