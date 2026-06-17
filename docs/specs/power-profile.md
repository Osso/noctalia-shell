Power profile covers UPower profile labeling, icon selection, profile mutation, IPC commands, and Noctalia performance mode. Runtime source lives mainly in `Services/Power/PowerProfileService.qml`; implementation notes belong in [docs/wiki/systems/power-profile.md](../wiki/systems/power-profile.md).

## What it must do

### Profile labels and icons

- [x] Profile names fail closed to `Unknown` when power profiles are unavailable.
- [x] Profile names default to the active profile when no explicit profile is supplied.
- [x] Profile names map performance, balanced, and power-saver profile values to display labels.
- [x] Unknown profile values are displayed as `Unknown`.
- [x] Profile icons fail closed to the balanced icon when power profiles are unavailable.
- [x] Profile icons default to the active profile when no explicit profile is supplied.
- [x] Profile icons map performance, balanced, and power-saver profile values to icon names.
- [x] Unknown profile values use the balanced icon.

### Profile mutation

- [x] Service startup logs that the power profile service started.
- [x] Setting a profile no-ops when power profiles are unavailable.
- [x] Setting a profile uses a typed profile value input.
- [x] Setting a profile writes the requested value to the UPower profile object when available.
- [x] Profile assignment failures are logged.
- [x] Cycling profiles no-ops when power profiles are unavailable.
- [x] Cycling reads the live UPower profile and maps performance to power saver, balanced to performance, and power saver to balanced.
- [x] Default-state detection treats unavailable profiles as default.
- [x] Balanced is the default profile.

### IPC surface

- [x] The `powerProfile.cycle` IPC command delegates to the power profile service cycle helper.
- [x] The `powerProfile.set` IPC command maps `performance`, `balanced`, and `powersaver` strings to their profile values.
- [x] The `powerProfile` IPC surface exposes Noctalia performance toggle, enable, and disable commands.

### Noctalia performance mode

- [x] Noctalia performance toggle inverts the mode.
- [x] Noctalia performance setter uses a typed boolean input.
- [x] Noctalia performance setter assigns the requested mode.
- [x] Enabling Noctalia performance mode shows the enabled toast with the rocket icon.
- [x] Disabling Noctalia performance mode shows the disabled toast with the rocket-off icon.

## How it works

- [docs/wiki/systems/power-profile.md](../wiki/systems/power-profile.md)

## Implementation inventory

- `Services/Power/PowerProfileService.qml` - UPower profile state, profile labels/icons, mutation helpers, profile-change toasts, and Noctalia performance mode.
- `Services/Control/IPCService.qml` - power profile and Noctalia performance IPC commands.
- `Modules/Panels/ControlCenter/Widgets/PowerProfile.qml` - control-center profile button.
- `Modules/Bar/Widgets/PowerProfile.qml` - bar power-profile widget.
- `Modules/Bar/Widgets/NoctaliaPerformance.qml` - bar Noctalia performance toggle.
- `Services/UI/BarWidgetRegistry.qml` - widget registry entries for power profile and Noctalia performance widgets.

## Tests asserting this spec

- `Tests/power-profile-service-guards.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/qml-type-annotations.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for the profile-change toast handler.
- [ ] Add executable tests for control-center and bar power-profile widget bindings.
- [ ] Add executable tests for Noctalia performance consumers that disable expensive UI effects.

## Out of scope

- Battery charging mode and battery panel behavior belong in a separate battery spec.
- Idle inhibition belongs in a separate idle-inhibitor spec.
