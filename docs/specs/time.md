Time covers shared timestamp formatting, vague duration formatting, stopwatch/countdown state, and timer alarm behavior. Runtime source lives in `Commons/Time.qml`; implementation notes belong in [docs/wiki/systems/time.md](../wiki/systems/time.md).

## What it must do

### Formatting

- [x] `getFormattedTimestamp` declares string output.
- [x] `formatVagueHumanReadableDuration` declares string output.
- [x] Timestamp formatting defaults missing dates to the current time.
- [x] Timestamp formatting pads one-based month values.
- [x] Timestamp formatting returns the compact `yyyyMMdd-hhmmss` shape.
- [x] Vague duration formatting fails closed to `0s` for invalid or negative durations.
- [x] Vague duration formatting floors decimal seconds.
- [x] Vague duration formatting splits durations into days, hours, minutes, and seconds.
- [x] Vague duration formatting shows seconds only for short durations.
- [x] Vague duration formatting joins readable duration parts with spaces.

### Timer lifecycle

- [x] Starting in stopwatch mode resumes from elapsed seconds and records the current timestamp.
- [x] Starting in countdown mode ignores empty countdowns.
- [x] Starting in countdown mode snapshots the countdown total and resets pause state.
- [x] Pausing preserves stopwatch or countdown pause state.
- [x] Pausing stops timer state, clears start timestamp, stops the alarm sound, and marks sound inactive.
- [x] Resetting stops the timer and clears start timestamp.
- [x] Resetting clears stopwatch and countdown state.
- [x] Resetting stops the alarm sound and marks sound inactive.
- [x] Finishing a countdown stops the countdown, clears remaining seconds, marks alarm sound active, and plays the repeating low-volume alarm.

## How it works

- [docs/wiki/systems/time.md](../wiki/systems/time.md)

## Implementation inventory

- `Commons/Time.qml` - shared time singleton, timestamp/duration helpers, stopwatch state, countdown state, and timer alarm coordination.
- `Modules/Cards/TimerCard.qml` - timer UI consuming Time timer state.
- `Services/System/SoundService.qml` - alarm playback and stop helpers used by Time.
- `Services/Media/ScreenRecorderService.qml` - screen recording filenames generated from Time timestamps.
- `Commons/Logger.qml` - log timestamps generated from Time.

## Tests asserting this spec

- `Tests/time-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable value tests for timestamp and duration formatting outputs.
- [ ] Add fake SoundService coverage for timer alarm start and stop calls.
- [ ] Add TimerCard behavior coverage for stopwatch/countdown display and controls.
- [ ] Add coverage for `formatRelativeTime`.

## Out of scope

- Calendar event timestamp conversion is covered by [docs/specs/calendar.md](calendar.md).
- Sound playback internals are covered by [docs/specs/sound-service.md](sound-service.md).
