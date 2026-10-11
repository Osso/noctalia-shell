Brightness covers monitor lookup, available brightness methods, global brightness adjustment, detected-display reporting, and brightness widget display helpers. Runtime source lives mainly in `Services/Hardware/BrightnessService.qml`; implementation notes belong in [docs/wiki/systems/brightness.md](../wiki/systems/brightness.md).

## What it must do

### Monitor discovery and lookup

- [x] Screen lookup returns the monitor whose `modelData` is the exact screen object.
- [x] Screen lookup does not match a different object just because it has the same shape.
- [x] Detected display reporting returns the current detected display list.
- [x] DDC detection output parsing handles blank output, supported monitors, invalid displays, unsupported monitors, and missing model/bus fields.
- [x] DDC process output is buffered until exit determines success or failure.
- [x] Successful valid detection atomically replaces the prior DDC monitor list; malformed DDC-capable exit-zero output, non-zero exits, and failed `ddcutil` starts preserve the last known monitors and log a concrete error.
- [x] Legitimate unsupported-display output is not classified as malformed and may replace stale DDC monitors with an empty list.
- [x] Detection generations ignore stale completions, including a process completing after DDC support was disabled.
- [x] Requests arriving during any in-flight detection, including the initial detection and disable/re-enable transitions, are coalesced and trigger one restart after the process fully stops.
- [x] Normal exits and failed starts finalize detection exactly once.

### Available methods

- [x] DDC support is reported only when DDC support is enabled and at least one DDC monitor exists.
- [x] Internal brightness support is reported when at least one non-DDC monitor exists.
- [x] Apple display support is reported when an Apple display is present.
- [x] DDC monitors are not reported as available when DDC support is disabled.

### Global adjustment

- [x] Increasing brightness delegates to every monitor instance.
- [x] Decreasing brightness delegates to every monitor instance.

### Per-monitor adjustment

- [x] Individual monitor brightness clamps to the configured minimum and 100% maximum before publishing.
- [x] Internal displays route brightness changes through `brightnessctl`.
- [x] DDC displays route brightness changes through `ddcutil` with the monitor bus number and restart the DDC debounce timer.
- [x] Apple displays route brightness changes through `asdbctl`.
- [x] Brightness changes queue without publishing or executing commands while the monitor debounce timer is running.

### Widget helpers

- [x] Brightness widget display text uses the current monitor brightness percentage.
- [x] Brightness widget icon maps missing/zero brightness to off, low brightness to low, and higher brightness to high.

### Display settings tab

- [x] DisplayTab shows monitor names and scaled descriptions, brightness percentages, unavailable-control state, and hides brightness controls when no monitor is found.
- [x] Brightness slider move/release routes values to the matching monitor; screen reorder/repopulation preserves monitor ownership.
- [x] Brightness-step and enforce-minimum edits update settings immediately; DisplayTab has no Save/Cancel transaction or rollback on close.

## How it works

- [docs/wiki/systems/brightness.md](../wiki/systems/brightness.md)

## Implementation inventory

- `Services/Hardware/BrightnessService.qml` - brightness monitor variants, method detection, display lookup, and global adjustment helpers.
- `Modules/Bar/Widgets/Brightness.qml` - bar widget display, icon, and interaction behavior.
- `Modules/Panels/Brightness/BrightnessPanel.qml` - brightness panel UI.
- `Modules/Panels/Settings/Tabs/DisplayTab.qml` - display settings for monitor brightness and DDC support.
- `Modules/OSD/OSD.qml` - brightness OSD display.

## Tests asserting this spec

- `Tests/bar-controls-warnings.test.py` — isolated production bar-widget panel/display-settings routing, wheel adjustment and unavailable-monitor guard, first-update suppression/subsequent pill reveal, and display modes. Cohort evidence: [bar](bar.md#bar-control-cohort); no direct widget OSD dispatch or real monitor changes: [testing](testing.md#bar-control-cohort).

### DisplayTab coverage

- `Tests/display-tab-warnings.test.py` — standalone production DisplayTab and controls under isolated offscreen `qmltestrunner`; settings, screens, compositor scale, brightness/night-light services, Process, and toasts are fixtures. DisplayTab lint requires zero warnings and exit status zero (29→0 through `9d3ebd292`, `758202d4d`).
- Six behavioral rows plus init/cleanup yield eight reported passes: monitor rendering at UI scales 1/1.5; brightness move/release and screen repopulation; selection/immediate-edit/destroy-reopen; synthetic night-light availability/toasts; temperature release and schedule visibility. Rendering covers four fixture monitors, scaled descriptions, percentages, unavailable and missing brightness controls, and card geometry. The schedule row checks 48 half-hour options, fake JSON serialization, and retained fixture edits after reopening, not Save/Cancel or disk persistence.
- Reported before/after rendered PNG bytes match at both scales. The standalone runner captures PNGs and checks their signature/dimensions; it does not enforce pre-change byte equality itself. This is bounded fixture rendering, not live desktop pixel acceptance.
- Direct control signals and synthetic Process exits do not prove physical input, installed `wlsunset`, actual night-light application, hardware mode/DDC writes, real persistence, or whole-shell behavior. Safety and pass gates: [testing](testing.md#display-settings-tab).

- `Tests/brightness-service-guards.test.js`
- `Tests/brightness-widget-guards.test.js`
- `Tests/helpers.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [x] Add executable tests for individual monitor `setBrightness`, debounce, and command routing.
- [x] Add bounded DisplayTab UI contract coverage with inert monitor/settings/service boundaries.
- [ ] Add brightness panel UI coverage and live display-settings integration proof; fixture DisplayTab coverage does not establish hardware mode/DDC writes or real persistence.

## Out of scope

- Audio volume OSD behavior belongs in [audio.md](audio.md).
- Screen recorder display capture belongs in [screen-recorder.md](screen-recorder.md).
