Brightness covers monitor lookup, available brightness methods, global brightness adjustment, detected-display reporting, and brightness widget display helpers. Runtime source lives mainly in `Services/Hardware/BrightnessService.qml`; implementation notes belong in [docs/wiki/systems/brightness.md](../wiki/systems/brightness.md).

## What it must do

### Monitor discovery and lookup

- [x] Screen lookup returns the monitor whose `modelData` is the exact screen object.
- [x] Screen lookup does not match a different object just because it has the same shape.
- [x] Detected display reporting returns the current detected display list.

### Available methods

- [x] DDC support is reported only when DDC support is enabled and at least one DDC monitor exists.
- [x] Internal brightness support is reported when at least one non-DDC monitor exists.
- [x] Apple display support is reported when an Apple display is present.
- [x] DDC monitors are not reported as available when DDC support is disabled.

### Global adjustment

- [x] Increasing brightness delegates to every monitor instance.
- [x] Decreasing brightness delegates to every monitor instance.

### Widget helpers

- [x] Brightness widget display text uses the current monitor brightness percentage.
- [x] Brightness widget icon maps missing/zero brightness to off, low brightness to low, and higher brightness to high.

## How it works

- [docs/wiki/systems/brightness.md](../wiki/systems/brightness.md)

## Implementation inventory

- `Services/Hardware/BrightnessService.qml` - brightness monitor variants, method detection, display lookup, and global adjustment helpers.
- `Modules/Bar/Widgets/Brightness.qml` - bar widget display, icon, and interaction behavior.
- `Modules/Panels/Brightness/BrightnessPanel.qml` - brightness panel UI.
- `Modules/Panels/Settings/Tabs/DisplayTab.qml` - display settings for monitor brightness and DDC support.
- `Modules/OSD/OSD.qml` - brightness OSD display.

## Tests asserting this spec

- `Tests/brightness-service-guards.test.js`
- `Tests/brightness-widget-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for individual monitor `setBrightness`, debounce, and command routing.
- [ ] Add executable tests for DDC detection output parsing.
- [ ] Add spec coverage for brightness panel and display settings UI contracts.

## Out of scope

- Audio volume OSD behavior belongs in [audio.md](audio.md).
- Screen recorder display capture belongs in [screen-recorder.md](screen-recorder.md).
