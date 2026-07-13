Screen recorder covers gpu-screen-recorder source discovery, start/stop state, portal preflight, command construction, and recording shutdown. Runtime source lives mainly in `Services/Media/ScreenRecorderService.qml`.

## What it must do

### Source discovery

- [x] Refreshing capture sources starts both `gpu-screen-recorder --list-capture-options` and `gpu-screen-recorder --list-monitors`.
- [x] Capture-source parsing skips v4l2 devices, keeps monitor resolutions, maps region capture, and appends the portal picker.
- [x] Monitor-list parsing inserts missing monitors before the portal picker, avoids duplicate monitor keys, and records the first monitor resolution.
- [x] The read-only host probe accepts one or more valid `NAME|WIDTHxHEIGHT` monitor rows and rejects empty or partly malformed lists.

### Host probe

- [x] The read-only screen-recorder probe requires `gpu-screen-recorder` and `pidof`, validates monitor and capture-option enumeration, and fails closed on missing or malformed output.
- [x] The probe requires `xdg-desktop-portal` and at least one supported portal backend (`wlr`, `hyprland`, `gnome`, `kde`, or `gtk`).

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
- [x] Launching disarms any force-kill timer left by a previous stop, starts the pending timer, and runs the recorder through a monitored shell command.
- [x] Focused capture includes the primary monitor resolution as a `-s` size flag when available.
- [x] The combined audio source emits `-a "default_output|default_input"`.
- [x] System-output and microphone-only audio sources are passed directly.
- [x] Empty output directory keeps the filename relative.
- [x] Non-focused capture omits the focused size flag.

### Process and timer lifecycle

- [x] A recorder exit while pending cancels the pending timer and reports missing binaries or startup failures from buffered output.
- [x] A successful recorder exit while active clears recording and active-recording state, stops monitoring, and reports the saved output; failure reports a concrete diagnostic.
- [x] The pending timer promotes a still-running process to active recording and clears a pending session whose process already exited.
- [x] The monitor timer stops polling when the recorder process disappears but leaves terminal recording state to the authoritative process-exit handler, so save/failure reporting is not suppressed.

### Settings UI

- [x] Settings expose output-directory text/folder-picker writeback and cursor-visibility toggle writeback.
- [x] The video-source selector uses discovered capture sources and falls back to `portal` and `screen`, then writes `videoSource`.
- [x] Frame-rate options are `30`, `60`, `100`, `120`, `144`, `165`, and `240`; string option keys convert to and from the numeric persisted setting type-safely.
- [x] Quality options are `medium`, `high`, `very_high`, and `ultra`; video codecs are `h264`, `hevc`, `av1`, `vp8`, and `vp9`; color ranges are `limited` and `full`.
- [x] Audio-source options are `default_output`, `default_input`, and `both`; audio codecs are `opus` and `aac`; each control writes its matching setting.

### Stop

- [x] Stop fails closed when no recording is active or pending.
- [x] Stop shows a stopping toast, sends SIGINT to native/Flatpak recorder processes, clears recording and pending state, stops pending/monitor timers, clears active-recording state, and arms the force-kill timer.

## How it works

- Runtime behavior is implemented in `Services/Media/ScreenRecorderService.qml` and covered by the tests listed below.

## Implementation inventory

- `Services/Media/ScreenRecorderService.qml` - capture source discovery, recording state, command construction, portal preflight, process monitoring, and shutdown.
- `Modules/Bar/Widgets/ScreenRecorder.qml` - bar widget for capture source selection and toggle.
- `Modules/Panels/ControlCenter/Widgets/ScreenRecorder.qml` - control-center screen recorder toggle.
- `Modules/Panels/Settings/Tabs/ScreenRecorderTab.qml` - screen recorder settings UI.
- `Services/UI/ControlCenterWidgetRegistry.qml` - control-center widget registration.
- `Bin/dev/service-probes.sh` - read-only monitor/source enumeration and portal availability probe.

## Tests asserting this spec

- `Tests/screen-recorder-service-guards.test.js`
- `Tests/screen-recorder-settings-ui.test.js`
- `Tests/service-probes-parsing.test.sh`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

None.

## Out of scope

- PipeWire volume and audio device selection belong in [audio.md](audio.md).
- Notification/toast display internals belong in notification/toast specs.
