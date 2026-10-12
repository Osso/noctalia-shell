Time covers shared timestamp formatting, vague duration formatting, stopwatch/countdown state, and timer alarm behavior. Runtime source lives in `Commons/Time.qml`; implementation notes belong in [docs/wiki/systems/time.md](../wiki/systems/time.md).

## What it must do

### Formatting

- [x] `getFormattedTimestamp` types date input and declares string output.
- [x] `formatVagueHumanReadableDuration` types seconds input and declares string output.
- [x] `formatRelativeTime` types date input and declares string output.
- [x] Timestamp formatting defaults missing dates to the current time.
- [x] Timestamp formatting pads one-based month values.
- [x] Timestamp formatting returns the compact `yyyyMMdd-hhmmss` shape.
- [x] Timestamp formatting returns concrete zero-padded year, month, day, hour, minute, and second values.
- [x] Vague duration formatting fails closed to `0s` for invalid or negative durations.
- [x] Vague duration formatting floors decimal seconds.
- [x] Vague duration formatting splits durations into days, hours, minutes, and seconds.
- [x] Vague duration formatting shows seconds only for short durations.
- [x] Vague duration formatting joins readable duration parts with spaces.
- [x] Vague duration formatting returns concrete second, minute, hour, and day bucket strings.
- [x] Relative time formatting returns empty text for missing dates.
- [x] Relative time formatting returns translated now, one-minute, many-minutes, one-hour, many-hours, one-day, and many-days buckets.

### Update cadence

- [x] Shared Unix timestamps read current wall-clock time directly so they do not become stale when `Time.now` sleeps.
- [x] `Time.now` sleeps until the next minute boundary when no visible UI requires seconds and no timer is running.
- [x] Visible second-level clock consumers register and deregister second updates with ref-counted guards.
- [x] Bar clock formats request second updates only when the active format includes second tokens.
- [x] Analog/digital `NClock` requests second updates while visible for second-hand/progress rendering.
- [x] Analog hands paint and repaint from the supplied `NClock.now`, not an unrelated shared date.
- [x] Digital labels and seconds progress stay bound to the supplied date, including milliseconds, after shared Time updates.
- [x] Running stopwatch/countdown timers force second-level updates.

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
- [x] Timer pause, reset, and finish behavior execute the expected fake SoundService stop/play calls.

### Timer card

- [x] Timer card formatting functions use typed QML signatures for duration, digit-buffer, and string output values.
- [x] Timer card display formatting delegates to `TimerDigits` helpers.
- [x] Timer card digit parsing stores parsed seconds in shared timer state.
- [x] Timer card start, pause, and reset actions delegate to shared `Time` timer controls.
- [x] Timer card buffered input is parsed exactly once and cleared when non-empty.
- [x] Timer card empty buffered input leaves the existing timer value unchanged.

## How it works

- [docs/wiki/systems/time.md](../wiki/systems/time.md)

## Implementation inventory

- `Commons/Time.qml` - shared time singleton, timestamp/duration helpers, stopwatch state, countdown state, and timer alarm coordination.
- `Modules/Cards/TimerCard.qml` - timer UI consuming Time timer state.
- `Services/System/SoundService.qml` - alarm playback and stop helpers used by Time.
- `Services/Media/ScreenRecorderService.qml` - screen recording filenames generated from Time timestamps.
- `Commons/Logger.qml` - log timestamps generated from Time.

## Tests asserting this spec

- `Tests/datetime-tokens-layout-runtime.test.py` — offscreen date/time token geometry against fixed fixtures.
- `Tests/shortcuts-clock-warnings.test.py` — isolated ClockPanel display/month/card routing; also [ShortcutsCard](control-center.md).

- `Tests/nclock-datetime-warnings.test.py` (`lint` / `behavior`) with `Tests/Qml/NClockDateTimeWarningsHarness.qml` — at `63f0158f2`/`2ffe8adac`, NClock/NDateTimeTokens warnings drop 17→0/13→0. Five offscreen behavioral cases plus init/cleanup yield seven reported passes: analog supplied-date repaint/pixels, digital supplied-date labels/progress after a shared Time update, 12h/locale/style/font/color and registration lifecycle, injected shared midnight, and token examples/click payloads/locale/model rebuild/recreation. Time/settings/style are fixtures; injected dates and software pixels do not prove natural scheduling or live integration. Standalone gates and isolation: [testing](testing.md#nclock-and-date-time-tokens-isolated-runtime).

- `Tests/clock-warnings.test.py` (`lint` / `behavior`) with `Tests/Qml/ClockWarningsHarness.qml` — fifteen isolated production bar Clock transition rows at `1c6b00888`: 24h/12h and multiline/date formats, font/color and per-line sizing, injected second/midnight changes, horizontal/vertical active-format selection, seconds registration without duplication, hide/show, destruction, and recreation releasing all references. Time/settings/registry/UI services are fake; registration counters and injected dates do not prove real Time scheduling, natural cadence, desktop input/panels, persistence, or whole-shell integration. Clock-only lint drops 24→0 and requires zero warnings/exit status zero, not global warning-free acceptance. Standalone modes, isolation, and acceptance: [testing](testing.md#weathercard-and-bar-clock-isolated-runtime).
- `Tests/timer-card-isolation.test.py` — `33b49ea59`/`37fa86011` keep parent-owned synthetic settings/backup `0600` in a private `0700` root outside child `000` config directories. Checks denied config access and cleanup, behavior completion, four byte/mode tamper rejections, and clean/injected-warning harness lint. The behavior harness retains six phases; injected time is not natural elapsed-time proof.
- `Tests/timer-card-guards.test.js`
- `Tests/timer-card-runtime.test.py` (`lint` / `behavior`) with `Tests/Qml/TimerCardHarness.qml`: standalone targeted warning-free TimerCard lint and offscreen production TimerCard/Time integration (`behavior` also runs under `run-tests.sh`'s `deterministic-unit` gate). Assertions cover digit entry and limits, Backspace/Delete/Return/Escape, focus release, start/reset enabled states, mode switching, display/hour transitions, countdown ring, pause/resume/reset, scheduled updates, and repeating alarm requests through a fake SoundService. Countdown/stopwatch elapsed time is injected through `timerStartTimestamp`; this does not prove unassisted wall-clock progression.
- `Tests/remaining-layout-geometry.test.py behavior` - four offscreen production ClockSettings geometry/content cases at widths 480/1000 and scales 1/1.25, compared exactly with tracked pre-cleanup fixtures after token-highlight geometry settles. Assertions include `HH:mm`, `yyyy-MM-dd`, and nonempty list content; no token-click/edit interaction or time-progression proof. Shared isolation and lint limits: [testing](testing.md).
- `Tests/clock-settings-warnings.test.py behavior --artifacts <new-directory>` - isolated offscreen production ClockSettings/dialog/controls: seven behavior rows plus QtTest init/cleanup yield nine reported passes. Covers fixed-date 24h/12h/multiline previews, format switching, drag-selection/cut-paste reordering, focused token clicks/default insertion, trimmed copy-isolated serialization, font/color toggles, preview delegate rebuild/destruction/recreation, and Cancel/reopen versus Apply signal payloads. Settings/services/time are fixtures; no live persistence, natural time progression, physical desktop input, or whole-shell proof. Standalone `lint` requires zero ClockSettings warnings and exit status zero (29→0 in the cleanup audited through `f16faaa1a`), not global zero-warning acceptance. Safety/pass gates: [testing](testing.md).
- `Tests/residual-singleton-owners.test.py runtime` — at `159c2d307`, Time callback owner warnings drop 1→0. Offscreen actual Time proves scheduled `Time.now` advancement while a stopwatch runs, minute/second interval calculations, refcount floor, fixed-date timestamp formatting, and pause/reset with fixture SoundService; callback-local owner shadows are exercised. This does not prove natural elapsed countdown/stopwatch progression or canonical reload. Gates: [testing](testing.md#residual-singleton-owners).
- `Tests/time-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Prove unassisted `Time.timestamp` progression across scheduled timer updates. The isolated harness notes its cached `Date.now()` binding and injects elapsed start timestamps instead; natural countdown/stopwatch progression remains unverified.

## Out of scope

- Calendar event timestamp conversion is covered by [docs/specs/calendar.md](calendar.md).
- Sound playback internals are covered by [docs/specs/sound-service.md](sound-service.md).
