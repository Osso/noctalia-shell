Night Light covers wlsunset command generation, manual and automatic scheduling, forced all-day night mode, coordinate readiness, and runner lifecycle. Runtime source lives in `Services/Location/NightLightService.qml`; implementation notes belong in [docs/wiki/systems/night-light.md](../wiki/systems/night-light.md).

## What it must do

### Command generation

- [x] Manual scheduling builds a `wlsunset` command with night temperature, day temperature, manual sunrise, manual sunset, and a 900-second transition duration.
- [x] Automatic scheduling builds a `wlsunset` command with night temperature, day temperature, stable latitude, stable longitude, and a 900-second transition duration.
- [x] Forced night mode builds a `wlsunset` command with configured night/day temperatures, all-day night schedule boundaries, and a 1-second transition duration.

### Applying state

- [x] Applying automatic schedule waits for location coordinates before building or restarting the runner.
- [x] Applying changed commands stores the new command, updates the runner command, and starts the runner.
- [x] Applying the same command leaves the running runner unchanged.
- [x] Applying disabled settings stops the runner.
- [x] Settings signal handlers reapply night light state and emit enabled/disabled or forced/normal notices where applicable.
- [x] Location coordinate readiness applies night light state only after coordinates become ready.

## How it works

- [docs/wiki/systems/night-light.md](../wiki/systems/night-light.md)

## Implementation inventory

- `Services/Location/NightLightService.qml` - wlsunset command generation, LocationService coordinate dependency, setting-change application, and runner lifecycle.
- `Services/Location/LocationService.qml` - stable latitude/longitude source for automatic schedule mode.
- `Modules/Bar/Widgets/NightLight.qml` - bar control for night light state and settings access.
- `Modules/Panels/ControlCenter/Widgets/NightLight.qml` - Control Center night light shortcut.
- `Modules/Panels/Settings/Tabs/LocationTab.qml` - night light settings surface.

## Tests asserting this spec

- `Tests/night-light-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add fake Process coverage for runner start and exit logging.
- [ ] Add settings-level coverage for LocationTab night light controls.
- [ ] Add widget coverage for bar and Control Center night light toggles.

## Out of scope

- Location/weather fetch behavior is covered by [docs/specs/location-weather.md](location-weather.md).
- Dark-mode scheduling is covered by [docs/specs/dark-mode.md](dark-mode.md).
