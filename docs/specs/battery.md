Battery covers UPower battery selection, Bluetooth battery matching, low-battery warnings, battery panel display helpers, charge-threshold writes, battery IPC mode mapping, and battery probe parsing. Runtime source lives mainly in `Modules/Bar/Widgets/Battery.qml`, `Modules/Panels/Battery/BatteryPanel.qml`, and `Services/Hardware/BatteryService.qml`; implementation notes belong in [docs/wiki/systems/battery.md](../wiki/systems/battery.md).

## What it must do

### Battery and Bluetooth device selection

- [x] The battery widget uses the configured native path when it resolves to a battery device with a percentage.
- [x] The battery widget falls back to the UPower display device when the configured native path is missing, line power, missing, or blank.
- [x] Bluetooth device lookup extracts MAC addresses case-insensitively from the native path.
- [x] Bluetooth device lookup returns `null` for missing Bluetooth device lists or native paths without a MAC address.
- [x] Current battery percent prefers Bluetooth battery percentage when present.
- [x] Current battery percent falls back to UPower battery percentage or zero when no battery is available.

### Battery widget display

- [x] Battery widget initialization, charging/discharging icons, 90/50/25 percent icon boundaries, percentage text, colors, and collapsed text visibility remain covered by an offscreen production-widget regression.
- [x] Configured UPower paths and case-insensitive Bluetooth paths preserve percentage selection and disconnected-device state in the production-widget regression.

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
- [x] Battery settings preserve displayed state, threshold drag/release behavior, and progress-track/fill geometry at UI scales 1 and 1.25. The offscreen production-tab regression uses isolated fake UPower/sysfs/process/settings services and compares content/geometry with the pre-fix fixture; it never performs privileged writes.
- [x] Battery settings display the positive magnitude of signed UPower `changeRate` in watts to one decimal for charging and discharging; zero hides the power row, and battery state separately conveys direction.
- [x] Battery settings health uses the normal text color at 80% and above, the tertiary warning color from 50% to below 80%, and the error color below 50%.
- [x] Battery settings progress width uses the normal animation duration (300 ms at default speed with animations enabled).
- [x] The `batteryManager.cycle` IPC command delegates to the battery service cycle helper.
- [x] The `batteryManager.set` IPC command maps `full`, `balanced`, and `lifespan` strings to their charging modes.

### Types and probes

- [x] Battery service icon selection uses typed percentage, charging, and ready-state inputs.
- [x] Battery service icon selection returns exclamation when not ready, charging while charging, and threshold icons for 90/50/25/0 percent.
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
- `Services/Hardware/BatteryService.qml` - battery icon helper and charging mode service used by IPC.
- `Services/Control/IPCService.qml` - battery manager IPC command mapping.
- `Bin/dev/service-probes.sh` - read-only UPower probe parsing.

## Tests asserting this spec

- `Tests/battery-widget-guards.test.js`
- `Tests/battery-widget-warnings.test.py lint` checks only `Modules/Bar/Widgets/Battery.qml`, reports warning categories, and requires no warnings and qmllint exit status zero.
- `Tests/battery-widget-warnings.test.py behavior` runs `Tests/Qml/BatteryWidgetWarningsHarness.qml` with production Battery, BarPill layouts, NText/NIcon, and BatteryService; asserts initialization, icons, text, colors, visibility, device selection, and warning threshold/hysteresis without runtime warnings. Runs standalone and directly in `run-tests.sh`'s `deterministic-unit` gate after BatteryTab; lint remains standalone. Warning rejection covers this fixture runtime, not the full shell. Inert service fixtures record toast calls without delivery and replace popup windows with a non-surface item. HOME/XDG/Noctalia paths and DBus are isolated; a permission-locked real-settings backup and unchanged SHA are verified, and the child exits before cleanup.
- `Tests/battery-panel-guards.test.js`
- `Tests/battery-service-guards.test.js`
- `Tests/battery-tab-guards.test.js`
- `Tests/battery-tab-warnings.test.py` (`lint` checks only BatteryTab, requires qmllint exit status zero and no warnings; `behavior --snapshot <path>` checks signed watts (+12.5/-12.5/0), health colors (80/50/49%), normal progress animation, baseline geometry, and inert threshold writes in the production tab/controls with unchanged real-settings SHA).
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

### Per-widget battery settings isolated evidence

- At `5be8b91b2`/`e24cf960f`, `Modules/Panels/Settings/Bar/WidgetSettings/BatterySettings.qml` diagnostics drop **14→6**: eight lexical-owner warnings removed; six UPower `UntypedObjectModel` metadata diagnostics remain. The ineffective Quickshell import was removed; this is not zero-warning production lint.
- `Tests/battery-settings-warnings.test.py behavior --artifacts <new-directory>` runs `Tests/Qml/BatterySettingsWarningsHarness.qml` with production editor/controls and fixture UPower. Eight reported passes comprise six behavioral cases (including separate charging/discharging data rows) plus QtTest init/cleanup.
- Coverage: defaults; save-copy/source immutability and unknown-field preservation; clearing the default device path; device/display-mode selection and threshold clamping to 5–50%; same-count hotplug, add/remove, line-power filtering, name fallbacks, manual refresh, and retained selection. Charging and discharging fixtures both use positive `changeRate = 12.5`; assertions cover device listing/selection/save, not watts rendering (this editor has no power row).
- Real settings and the permission-locked, hash-verified backup remain unchanged. Offscreen fixture proof does not establish real UPower hotplug, hardware behavior, persistence, native input, or whole-shell acceptance. Runner/isolation details: [testing](testing.md#per-widget-battery-settings-isolated-runtime).

## Known gaps (current cycle)

- [ ] Add hardware and desktop integration coverage for the battery widget; its offscreen regression does not cover real UPower/Bluetooth hardware, visible popup interaction, desktop notifications, settings persistence, or whole-shell acceptance.
- [ ] Add executable tests for `Services/Hardware/BatteryService.qml` charging-mode cycling and command routing.
- [ ] Add executable tests for battery panel health/time display text.
- [ ] Resolve the six per-widget battery settings UPower `UntypedObjectModel` metadata diagnostics; the standalone `lint` mode still requires zero warnings and therefore remains failing.
- [ ] Add host integration coverage for privileged threshold writes; the isolated production-tab test checks command construction, drag/release timing, threshold bounds, and successful-write reload using inert process/sysfs fixtures, not actual writes.

## Out of scope

- Power profile switching belongs in [power-profile.md](power-profile.md).
- Bluetooth pairing and connection behavior belongs in a separate Bluetooth spec.
