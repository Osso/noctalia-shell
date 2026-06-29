Location/weather covers configured location lookup, cached coordinate reuse, weather refresh lifecycle, Open-Meteo response handling, and weather formatting helpers. Runtime source lives mainly in `Services/Location/LocationService.qml`; implementation notes belong in [docs/wiki/systems/location-weather.md](../wiki/systems/location-weather.md).

## What it must do

### Refresh lifecycle

- [x] Initialization logs Location service startup.
- [x] Resetting weather marks coordinates as changing, clears stable display values, clears cached coordinates, clears cached weather, and triggers a weather refresh.
- [x] Weather refreshes stop immediately when weather is disabled in settings.
- [x] Weather refreshes avoid concurrent fetches and log that weather is still fetching.
- [x] Weather refreshes run when weather data, coordinates, location name, or fetch freshness requires it.
- [x] Weather refresh scheduling sleeps until the cache can expire instead of waking every few seconds while data is fresh.
- [x] Weather refresh scheduling uses a slower retry while a network fetch is already in progress.
- [x] Weather refreshes delegate actual work to the fresh-weather path.
- [x] Fresh-weather fetches mark weather as fetching before work starts.
- [x] Fresh-weather fetches detect configured location-name changes and clear coordinate readiness for changed locations.
- [x] Fresh-weather fetches geocode missing or changed locations using the configured location name.
- [x] Fresh-weather fetches persist geocoded coordinates and publish the display location name.
- [x] Fresh-weather fetches fetch weather after geocoding.
- [x] Fresh-weather fetches reuse cached coordinates when they are still valid.

### Network requests and error handling

- [x] Geocoding builds an encoded `assets.noctalia.dev` geocode URL.
- [x] Geocoding uses a typed string location-name input while keeping callbacks dynamic.
- [x] Geocoding waits for completed XMLHttpRequest state before processing.
- [x] Geocoding parses successful responses and calls back with resolved coordinates.
- [x] Geocoding reports unresolved locations, parse failures, and HTTP failures.
- [x] Geocoding sends a GET request.
- [x] Weather fetches build an Open-Meteo forecast URL from latitude and longitude.
- [x] Weather fetches parse successful responses, cache weather data, and stamp the fetch time.
- [x] Weather fetches publish stable coordinates and mark coordinates ready after successful weather data.
- [x] Weather fetches clear the fetch-in-progress state and schedule the next cache refresh after success.
- [x] Weather fetches report parse failures and HTTP failures.
- [x] Weather fetches send a GET request.
- [x] Shared error handling logs the error, clears the fetch-in-progress state, and schedules the next refresh.
- [x] Shared error handling types module and message inputs.

### Formatting helpers

- [x] Weather icon, description, and Celsius conversion helpers type their scalar inputs.
- [x] Weather icon mapping covers clear sky, partly cloudy, overcast, fog, drizzle, rain showers, snow, thunderstorms, and a cloud fallback.
- [x] Weather description mapping covers clear sky, mainly clear, partly cloudy, overcast, fog, drizzle, snow, rain showers, thunderstorms, and an Unknown fallback.
- [x] Celsius-to-Fahrenheit conversion returns `32 + celsius * 1.8`.

## How it works

- [docs/wiki/systems/location-weather.md](../wiki/systems/location-weather.md)

## Implementation inventory

- `Services/Location/LocationService.qml` - location coordinate cache, weather cache, geocoding, weather fetches, refresh lifecycle, and weather formatting helpers.
- `Modules/Cards/WeatherCard.qml` - weather card display backed by LocationService weather and coordinate state.
- `Modules/Panels/Settings/Tabs/LocationTab.qml` - location, weather, cards, night light, and dark mode settings surface.
- `Assets/settings-default.json` - default location/weather settings consumed by LocationService and LocationTab.

## Tests asserting this spec

- `Tests/location-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable fixture coverage for geocoding success, unresolved-location, parse-error, and HTTP-error responses.
- [ ] Add executable fixture coverage for Open-Meteo success, parse-error, and HTTP-error responses.
- [ ] Add UI-level coverage for WeatherCard visibility, current weather rendering, forecast rendering, and precipitation effects.
- [ ] Add settings-level coverage for LocationTab weather toggles, card ordering, and provider settings.

## Out of scope

- Calendar provider behavior is covered by [docs/specs/calendar.md](calendar.md).
- Night light behavior belongs in a separate night-light spec.
- Dark mode behavior belongs in a separate dark-mode spec.
