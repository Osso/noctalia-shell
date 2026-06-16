Calendar covers local calendar availability checks, calendar/event loading, cache behavior, date formatting, month-grid event classification, and calendar helper scripts. Runtime source lives mainly in `Services/Location/CalendarService.qml`; implementation notes belong in [docs/wiki/systems/calendar.md](../wiki/systems/calendar.md).

## What it must do

### Cache and availability

- [x] Cache saves are debounced instead of written immediately.
- [x] Loading from cache copies cached events and calendars into service state when cached data exists.
- [x] Loading from cache logs cached event count, cached calendar count, and cache timestamp when present.
- [x] Availability checks no-op the process and mark the service unavailable when calendar events are disabled.
- [x] Availability checks start the availability process when calendar events are enabled.
- [x] Calendar loading starts the list-calendars process.

### Event loading

- [x] Event loading clears events, stops loading state, and does not start the process when calendar events are disabled.
- [x] Event loading ignores duplicate requests while already loading.
- [x] Event loading clears stale errors, marks the service loading, computes the requested start/end window, starts the process, and logs the requested window.
- [x] Date-time formatting delegates to Qt using the `yyyy-MM-dd hh:mm` format.

### Month grid helpers

- [x] ISO week number calculation handles year-boundary dates.
- [x] All-day event detection requires a 24-hour duration starting at local midnight.
- [x] Multi-day event detection excludes all-day events and detects non-all-day events crossing local day boundaries.
- [x] Events for a calendar date include events that start inside, end inside, or span the whole target day.
- [x] Events for a calendar date are hidden when the calendar service is unavailable.
- [x] Event indicator colors distinguish multi-day, all-day, and timed events, with a separate color for today.

### Helper scripts

- [x] Calendar availability script exits successfully, never prints a Python traceback, and prints either `available` or an `unavailable:` reason.
- [x] Calendar list script exits successfully, never prints a Python traceback, and prints a JSON array.
- [x] Calendar events script exits successfully for a wide timestamp range, never prints a Python traceback, and prints a JSON array.
- [x] Calendar event timestamp conversion fails closed for missing values, invalid dates, pre-epoch years, and calendar-library exceptions.
- [x] Calendar event timestamp conversion converts UTC date-times to Unix timestamps, date-only values to local midnight, and non-UTC values through UTC conversion.

## How it works

- [docs/wiki/systems/calendar.md](../wiki/systems/calendar.md)

## Implementation inventory

- `Services/Location/CalendarService.qml` - calendar service state, cache load/save, availability checks, calendar listing, event loading, and date formatting.
- `Modules/Cards/CalendarMonthCard.qml` - month grid, week-number helper, event overlap filtering, event classification, and event indicator colors.
- `Modules/Cards/CalendarHeaderCard.qml` - calendar header card.
- `Modules/Panels/Settings/Tabs/LocationTab.qml` - calendar settings, enabled cards, and calendar display preferences.
- `Modules/Bar/Widgets/Clock.qml` - clock widget calendar panel action.
- `Bin/check-calendar.py` - Evolution Data Server availability probe.
- `Bin/list-calendars.py` - calendar listing script.
- `Bin/calendar-events.py` - event listing script and timestamp conversion helper.

## Tests asserting this spec

- `Tests/calendar-service-guards.test.js`
- `Tests/calendar-month-card-guards.test.js`
- `Tests/calendar-scripts.test.sh`
- `Tests/calendar-events-safe-get-time.test.py`
- `Tests/qml-type-annotations.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for calendar process stdout/stderr parsing and cache fallback paths.
- [ ] Add executable tests for calendar header card rendering and settings-card ordering.
- [ ] Add executable tests for clock-widget calendar action routing.
- [ ] Add typed-QML coverage for calendar month week-number delegates and event indicator delegates if current aliases can be narrowed.

## Out of scope

- Weather/location provider behavior belongs in a separate location/weather spec.
- Time/date formatting outside calendar events belongs in a separate time spec.
