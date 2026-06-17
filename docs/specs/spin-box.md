Spin Box covers the shared numeric input widget used by settings and color-editing surfaces. Runtime source lives in `Widgets/NSpinBox.qml`; implementation notes belong in [docs/wiki/systems/spin-box.md](../wiki/systems/spin-box.md).

## What it must do

### Value changes

- [x] Increment actions increase the value by the configured step.
- [x] Decrement actions decrease the value by the provided step when supplied.
- [x] Value changes use the widget `stepSize` when no explicit step is supplied.
- [x] Value change direction and explicit step inputs are typed while step omission still uses the widget default.
- [x] Increment actions clamp at the configured upper bound.
- [x] Decrement actions clamp at the configured lower bound.
- [x] Reaching either bound stops the repeat timer and restores the initial repeat delay.
- [x] Invalid directions leave the value and repeat timer unchanged.
- [x] Attempts to move past an existing bound leave the value and repeat timer unchanged.

### Repeat and text input

- [x] Stopping repeat clears the repeat direction, stops the timer, and restores the initial repeat delay.
- [x] Text input parses leading numeric content.
- [x] Text input clamps parsed numbers to configured bounds.
- [x] Non-numeric text input leaves the current value unchanged.

## How it works

- [docs/wiki/systems/spin-box.md](../wiki/systems/spin-box.md)

## Implementation inventory

- `Widgets/NSpinBox.qml` - shared spin box, bounds, repeat timer, button stepping, and text input parsing.
- `Widgets/NColorPickerDialog.qml` - color channel spin-box usage.
- `Modules/Panels/Settings/Tabs/SystemMonitorTab.qml` - system monitor numeric settings usage.
- `Modules/Panels/Settings/Tabs/DisplayTab.qml` - display numeric settings usage.
- `Modules/Panels/Settings/Tabs/AudioTab.qml` - audio numeric settings usage.
- `Modules/Panels/Settings/Bar/WidgetSettings/*.qml` - bar widget numeric settings usage.

## Tests asserting this spec

- `Tests/spin-box-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for hold-repeat acceleration and max multiplier behavior.
- [ ] Add executable coverage for mouse wheel stepping.
- [ ] Add executable coverage for prefix/suffix text display and focus commit/cancel behavior.

## Out of scope

- Feature-specific numeric setting ranges belong in each owning feature spec.
