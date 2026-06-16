Screen recorder covers gpu-screen-recorder source discovery, start/stop state, portal preflight, command construction, and recording shutdown. Runtime source lives mainly in `Services/Media/ScreenRecorderService.qml`; implementation notes belong in [docs/wiki/systems/screen-recorder.md](../wiki/systems/screen-recorder.md).

## What it must do

### Source discovery

- [x] Refreshing capture sources starts both `gpu-screen-recorder --list-capture-options` and `gpu-screen-recorder --list-monitors`.

### Toggle and start

- [x] Toggle starts recording when neither recording nor pending.
- [x] Toggle stops recording when recording or pending.
- [x] Starting recording fails closed when gpu-screen-recorder is unavailable.
- [x] Starting recording ignores requests while already recording or pending.
- [x] Starting recording marks the session pending and clears active-recording state.
- [x] Starting recording closes the currently opened panel when it is not already closing.
- [x] Portal capture runs an xdg-desktop-portal preflight instead of launching immediately.
- [x] Direct capture skips the portal preflight and launches immediately.

### Command construction

- [x] Launching builds an output path from the configured directory and formatted timestamp.
- [x] Launching starts the pending timer and runs the recorder through a monitored shell command.
- [x] Focused capture includes the primary monitor resolution as a `-s` size flag when available.
- [x] The combined audio source emits `-a "default_output|default_input"`.
- [x] System-output and microphone-only audio sources are passed directly.
- [x] Empty output directory keeps the filename relative.
- [x] Non-focused capture omits the focused size flag.

### Stop

- [x] Stop fails closed when no recording is active or pending.
- [x] Stop shows a stopping toast, sends SIGINT to native/Flatpak recorder processes, clears recording and pending state, stops pending/monitor timers, clears active-recording state, and arms the force-kill timer.

## How it works

- [docs/wiki/systems/screen-recorder.md](../wiki/systems/screen-recorder.md)

## Implementation inventory

- `Services/Media/ScreenRecorderService.qml` - capture source discovery, recording state, command construction, portal preflight, process monitoring, and shutdown.
- `Modules/Bar/Widgets/ScreenRecorder.qml` - bar widget for capture source selection and toggle.
- `Modules/Panels/ControlCenter/Widgets/ScreenRecorder.qml` - control-center screen recorder toggle.
- `Modules/Panels/Settings/Tabs/ScreenRecorderTab.qml` - screen recorder settings UI.
- `Services/UI/ControlCenterWidgetRegistry.qml` - control-center widget registration.

## Tests asserting this spec

- `Tests/screen-recorder-service-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for capture-source and monitor-list parsing.
- [ ] Add executable tests for recorder process exit handling and pending/monitor timer transitions.
- [ ] Add spec coverage for settings UI source/codec/quality controls.

## Out of scope

- PipeWire volume and audio device selection belong in [audio.md](audio.md).
- Notification/toast display internals belong in notification/toast specs.
