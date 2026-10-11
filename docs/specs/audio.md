Audio covers PipeWire-backed output/input volume state, device selection, OSD suppression, and audio-facing UI contracts. Runtime source lives mainly in `Services/Media/AudioService.qml`; implementation notes belong in [docs/wiki/systems/audio.md](../wiki/systems/audio.md).

## What it must do

### OSD suppression

- [x] Output OSD suppression stores an absolute deadline.
- [x] Input OSD suppression stores an absolute deadline.
- [x] A shorter suppression request must not shrink an existing OSD suppression window.
- [x] OSD suppression consumers report active state before the deadline and inactive state at/after expiry.

### Output volume

- [x] Output volume increase/decrease fail closed when PipeWire or sink audio is unavailable.
- [x] Output volume increase respects the configured overdrive maximum.
- [x] Output volume decrease clamps at zero.
- [x] Setting output volume fails closed when the sink is missing or not ready.
- [x] Setting output volume clamps requested values, skips tiny changes, unmutes the sink, applies the clamped value, and clears the feedback-loop guard later.
- [x] Output mute changes fail closed when PipeWire or sink audio is unavailable.
- [x] Output icons distinguish muted, near-zero, low, and high volume states.

### Input volume

- [x] Input volume increase/decrease fail closed when PipeWire or source audio is unavailable.
- [x] Input volume increase respects the configured overdrive maximum.
- [x] Input volume decrease clamps at zero.
- [x] Setting input volume fails closed when the source is missing or not ready.
- [x] Setting input volume clamps requested values, skips tiny changes, unmutes the source, applies the clamped value, and clears the feedback-loop guard later.
- [x] Input mute changes fail closed when PipeWire or source audio is unavailable.
- [x] Input icons distinguish muted/silent and active microphone states.

### Device selection

- [x] Setting the default sink or source fails closed until PipeWire is ready.
- [x] Setting the default sink updates PipeWire's preferred default audio sink.
- [x] Setting the default source updates PipeWire's preferred default audio source.
- [x] The active output device selector visibly marks the current default sink.

### UI volume controls

- [x] Audio card and audio panel volume sliders use on-demand debounce timers instead of permanent 100ms polling loops.
- [x] Slider movement schedules pending output/input volume sync.
- [x] Slider release flushes pending output/input volume sync.
- [x] Pending sync preserves device-id guards before writing output/input volume.
- [x] An audio panel opened after a default sink already exists immediately reflects that sink's volume and stays synchronized with later live volume changes.

### Spectrum visualization

- [x] Linear and mirrored spectra reflect normalized frame amplitudes in horizontal/vertical bar geometry, including minimum signal, reduced-quality settings, frame clearing/reassignment, and resizing.
- [x] Wave pixels reflect horizontal/vertical frames and minimum signal; clearing removes the wave, and inactive→active transitions repaint reassigned data.

### Typed UI contracts

- [x] Audio panel sink/source delegates expose typed `PwNode` model data and stable device id/description aliases.
- [x] Audio tab sink/source delegates expose typed `PwNode` model data and stable device id/description aliases.

## How it works

- [docs/wiki/systems/audio.md](../wiki/systems/audio.md)

## Implementation inventory

- `Services/Media/AudioService.qml` - PipeWire audio singleton, device lists, volume/mute controls, OSD suppression, and icon helpers.
- `Modules/Panels/Audio/AudioPanel.qml` - audio panel UI for sink/source controls.
- `Modules/Panels/Settings/Tabs/AudioTab.qml` - settings UI for audio device controls.
- `Modules/Bar/Widgets/Volume.qml` - output volume bar widget.
- `Modules/Bar/Widgets/Microphone.qml` - input microphone bar widget.
- `Modules/OSD/OSD.qml` - OSD consumer for audio state changes.
- `Modules/Cards/AudioCard.qml` - control-center audio card.
- `Modules/Bar/Widgets/AudioVisualizer.qml` - audio visualizer widget.
- `Services/Media/CavaService.qml` - audio visualizer data service.

## Tests asserting this spec

- At `8b1de9d34`, the existing AudioCard behavior suite rerun against the root-qualified AudioService records six behavioral cases plus QtTest init/cleanup (eight passes). AudioService is not exercised by the new root-service behavior harness, which substitutes an audio fixture. `Tests/root-service-warnings.test.py lint` removes eligible root-owner diagnostics but retains two AudioService `missing-property` warnings; no warning-free service claim. Cohort limits: [testing](testing.md#root-service-cohort).
- `Tests/audio-service-guards.test.js`
- `Tests/audio-ui-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/qml-runtime-guards.test.js`
- `Tests/Qml/AudioPanelRegressionHarness.qml`
- `Tests/audio-panel-regression.test.sh` delegates to `Tests/audio-panel-warnings.test.py behavior`. The standalone Python `behavior` mode runs production AudioPanel/AudioService and slider/radio controls under isolated offscreen `qmltestrunner`: initial/output external volume and selected-output indicator, sink/source selection during pending sync, guarded drag/debounce/release, reordered device models and content recreation, and destruction/recreation with pending sync. Five behavioral cases plus QtTest init/cleanup yield seven reported passes. PipeWire nodes, SmartPanel host, and bootstrap services are fixtures; signals are invoked directly. Standalone `lint` requires zero AudioPanel warnings and exit status zero (39 → 0 across `9f2f66140` and `5f7553f10`). This is bounded component evidence, not whole-shell acceptance.
- `Tests/Qml/AudioCardHarness.qml` and `Tests/audio-card-warnings.test.py behavior` exercise production AudioCard, AudioService, and supporting controls under isolated offscreen `qmltestrunner`: initial/external output and input volume, drag/debounce/release, mute and volume-driven unmute, device switching during pending sync, disconnect before sync, and destruction/recreation with pending sync. Six behavioral cases plus QtTest init/cleanup yield eight reported passes. PipeWire nodes and bootstrap/UI services are fixtures; actions invoke signals directly, not physical input. Standalone `lint` requires zero AudioCard warnings and exit status zero (41 → 0 at `755150f52`); neither mode claims runner integration or whole-shell acceptance.

- `Tests/audio-spectrum-warnings.test.py` / `Tests/Qml/AudioSpectrumHarness.qml` — five production-QML behavioral cases: horizontal bar amplitudes; vertical minimum/reduced-quality updates; clear/reassign/resize; Wave frame/orientation/clear/reassign pixels; Wave minimum/visibility. At `4ee4fb340`, Mirrored/Linear/Wave lint warnings drop 34+33+4→0 and the reproduced Wave inactive→active repaint gap is fixed. Isolation, acceptance, and proof limits: [testing](testing.md#audio-spectrum-isolated-runtime).

## Known gaps (current cycle)

- [ ] Live Cava/audio input and GPU rendering remain unverified by the isolated spectrum suite; media controls belong in [media playback](media-playback.md), recording in [screen recorder](screen-recorder.md).
- [ ] Add behavior tests for UI consumers that call `AudioService.suppressOutputOSD` and `AudioService.suppressInputOSD`.
- [ ] Real PipeWire integration and physical slider/button input remain untested by the AudioCard and AudioPanel fixture suites; mocked node setter paths are covered.
- [ ] AudioPanel source-radio checked state remains unverified: the unchanged comparison uses integer source id `===` string `deviceId`; source-selection assertions do not verify its indicator.
- [ ] AudioPanel's initial source-id guard remains unchanged and unverified: completion initializes only the sink guard. Input drag coverage first changes the source away and back; it does not prove input sync before the first source change.

## Out of scope

- Media player metadata and controls belong in a separate media playback spec.
- Screen recording audio capture flags belong in a separate screen recording spec.
