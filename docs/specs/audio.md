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

### UI volume controls

- [x] Audio card and audio panel volume sliders use on-demand debounce timers instead of permanent 100ms polling loops.
- [x] Slider movement schedules pending output/input volume sync.
- [x] Slider release flushes pending output/input volume sync.
- [x] Pending sync preserves device-id guards before writing output/input volume.

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

- `Tests/audio-service-guards.test.js`
- `Tests/audio-ui-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Extract separate specs for media playback, screen recording, and Cava visualization so this audio spec stays focused on core audio control.
- [ ] Add behavior tests for UI consumers that call `AudioService.suppressOutputOSD` and `AudioService.suppressInputOSD`.
- [ ] Add executable tests for volume setter command paths with mocked PipeWire node objects.

## Out of scope

- Media player metadata and controls belong in a separate media playback spec.
- Screen recording audio capture flags belong in a separate screen recording spec.
