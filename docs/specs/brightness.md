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

### Brightness panel

- [x] Panel monitor labels and scaled descriptions follow screen metadata; provider updates refresh brightness percentages and icons without writing brightness.
- [x] Slider press/move/release routes brightness to the current monitor; screen replacement does not write to the removed monitor.
- [x] Unavailable and missing providers disable adjustment; even directly emitted slider signals do not write to them. Missing providers display `N/A`.
- [x] Close dispatch targets the panel owner.

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

- At `2a73a4c4f`, BrightnessSettings warnings drop 2→0. The isolated editor case checks all display modes, metadata defaults, keyboard selection, copy-save retaining unrelated fields without source mutation, independent instances, and reopen from saved values. Shared accounting and limits: [testing](testing.md#small-widget-settings-isolated-runtime); no real brightness adjustment or persistence proof.

- `Tests/bar-controls-warnings.test.py` — isolated production bar-widget panel/display-settings routing, wheel adjustment and unavailable-monitor guard, first-update suppression/subsequent pill reveal, and display modes. Cohort evidence: [bar](bar.md#bar-control-cohort); no direct widget OSD dispatch or real monitor changes: [testing](testing.md#bar-control-cohort).

### Isolated service signal/order evidence

- At `919e77989`/`5d0857b06`, `Tests/brightness-keyboard-services-warnings.test.py` reports BrightnessService diagnostics 6→5: undeclared `detectedDisplays` and four cross-component `root` references remain. This is not zero-warning production acceptance.
- Two of the three shared behavioral cases cover DDC enable/collector/exit/stop ordering, coalesced restart and stale completion after disable; and monitor publication before recorded command dispatch, refresh signals, unchanged-value suppression and screen removal. `ddc-signal` is a failing negative control. Harness lint is zero-warning; isolation and shared proof limits: [testing](testing.md#brightnesskeyboard-services-isolated-runtime).

### Brightness panel coverage

- `Tests/brightness-panel-warnings.test.py` — standalone panel-only lint and offscreen production BrightnessPanel/NValueSlider/NSlider/NScrollView behavior. Owner diagnostics drop 20→0 through `e1fb713f0`, `5fb28925d`; seven exposed generic `QtObject` member diagnostics drop 7→0 at `4b0aea12d` using the confirmed `BrightnessService.Monitor` type. Current lint requires zero warnings and exit status zero, not whole-project warning-free acceptance.
- Five behavioral cases plus init/cleanup yield seven reported passes: monitor metadata/scaled descriptions and provider-driven percentage/icon updates without writes; synthetic mouse press/drag/release through the actual slider; screen replacement routing only to the new provider; disabled/missing-provider guards including directly emitted signals; close-owner dispatch.
- Screens, monitors/service, SmartPanel host, settings, compositor scale, and leaf presentation widgets are inert fixtures. DDC is disabled; recorded fixture writes are not hardware writes. No real monitor service/command routing, desktop input, rendered pixel acceptance, persistence, or whole-shell integration is established. Isolation and acceptance gates: [testing](testing.md#brightness-panel-isolated-runtime).

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
- [x] Add bounded brightness panel UI coverage with inert providers and actual offscreen slider events.
- [ ] Add live brightness-panel/display-settings integration proof; fixture coverage does not establish hardware mode/DDC writes or real persistence.

## Out of scope

- Audio volume OSD behavior belongs in [audio.md](audio.md).
- Screen recorder display capture belongs in [screen-recorder.md](screen-recorder.md).
