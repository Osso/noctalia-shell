Dark Mode covers automatic dark-mode scheduling from manual sunrise/sunset times or weather sunrise/sunset data. Runtime source lives in `Services/Location/DarkModeService.qml`; implementation notes belong in [docs/wiki/systems/dark-mode.md](../wiki/systems/dark-mode.md).

## What it must do

### Schedule inputs

- [x] Time parsing reads `HH:mm` strings into hour and minute values.
- [x] Manual scheduling builds yesterday sunset, today sunrise, today sunset, and tomorrow sunrise changes from configured manual times.
- [x] Manual scheduling marks sunset changes as dark mode enabled and sunrise changes as disabled.
- [x] Weather scheduling includes a pre-sunrise dark-mode state when current time is before sunrise.
- [x] Weather scheduling maps sunrise to dark mode disabled and sunset to dark mode enabled.
- [x] Service init uses manual schedule changes in manual mode, weather schedule changes in location mode when weather exists, and leaves init incomplete when location weather is missing.

### Applying state

- [x] Applying current mode chooses the latest change in the past.
- [x] Applying current mode writes the selected dark-mode state to color-scheme settings.
- [x] Applying current mode logs the reset state.
- [x] Applying current mode leaves settings unchanged when there is no past change.

### Scheduling next change

- [x] Next-mode scheduling chooses the first change in the future.
- [x] Next-mode scheduling stores the next dark-mode state.
- [x] Next-mode scheduling sets the timer interval to the delay until the next change.
- [x] Next-mode scheduling restarts the timer and logs the scheduled state.
- [x] Next-mode scheduling leaves the timer untouched when there is no future change.
- [x] Timer-triggered dark-mode changes apply the pending state and reschedule from weather data when weather exists.

## How it works

- [docs/wiki/systems/dark-mode.md](../wiki/systems/dark-mode.md)

## Implementation inventory

- `Services/Location/DarkModeService.qml` - dark-mode schedule collection, current-state application, next-change scheduling, and settings updates.
- `Services/Location/LocationService.qml` - weather sunrise/sunset data source used by weather scheduling.
- `Modules/Bar/Widgets/DarkMode.qml` - bar control for toggling dark mode.
- `Modules/Panels/Settings/Tabs/LocationTab.qml` - location/settings surface for dark-mode scheduling options.

## Tests asserting this spec

- `Tests/dark-mode-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add settings-level coverage for LocationTab dark-mode controls.
- [ ] Add bar-widget coverage for manual dark-mode toggling.

## Out of scope

- Weather fetch behavior is covered by [docs/specs/location-weather.md](location-weather.md).
- Matugen/template dark-mode rendering is covered by [docs/specs/theming.md](theming.md).
