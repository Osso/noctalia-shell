# Battery widget warning regression

Scoped extension of [battery](battery.md). No battery behavior changes.

## Contract

- [x] Battery bar widget owner qualification preserves initialization, charging/discharging icons, 90/50/25 percent icon boundaries, warning threshold/hysteresis, percentage text, colors, and collapsed text visibility.
- [x] Configured UPower paths and case-insensitive Bluetooth paths preserve percentage selection and disconnected-device state.
- [x] Tests instantiate production Battery, BarPill layouts, NText/NIcon, and BatteryService offscreen. UPower/Bluetooth/settings/services are inert fixtures; popup windows are replaced with a non-surface item and toast calls are recorded, never delivered.
- [x] Harness isolates HOME/XDG/Noctalia paths, disables desktop DBus access, verifies a permission-locked real-settings backup and unchanged SHA, and exits its child process before cleanup.

## Tests

- `Tests/battery-widget-warnings.test.py lint`: target only `Modules/Bar/Widgets/Battery.qml`; rejects unqualified/block-var warnings and reports any remaining categories.
- `Tests/battery-widget-warnings.test.py behavior`: executes `Tests/Qml/BatteryWidgetWarningsHarness.qml`; requires concrete state/icon/color/text/visibility assertions and no runtime warnings.

## Limits

No real UPower/Bluetooth hardware, visible popup interaction, desktop notifications, settings persistence, or whole-shell acceptance coverage.
