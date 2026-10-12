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

### Location settings tab

- [x] Location edits trim whitespace, retain unchanged names without resetting weather, use the default for empty input, and retain saved values on tab recreation.
- [x] First-day-of-week selections save immediately and survive tab recreation.
- [x] Calendar card toggles and reordering save to settings; the header remains enabled and saved order survives tab recreation.
- [x] Weather toggles synchronize weather-card state, availability, and dependent controls without resetting weather.
- [x] Opening the tab removes unknown cards, supplies missing cards, and disables the weather card when weather is disabled.

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

### Weather card precipitation effects

- [x] Disabled effects and clear weather leave the precipitation effect unloaded.
- [x] Rain and snow load their respective shaders with finite, continuously advancing time uniforms.
- [x] Rain hides the source content for distortion; snow leaves source content visible.
- [x] Disabling effects unloads them; enabling them again reloads an animating effect.
- [x] Switching from rain to snow updates the shader and source visibility while animation continues.

Lifecycle/uniform proof runs against the unchanged production card and widgets with fixed settings/location fixtures, isolated user paths, and an offscreen software backend. It does not prove GPU shader rendering or visual quality.

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

- `Tests/weather-card-warnings.test.py` (`lint` / `behavior`) with `Tests/Qml/WeatherCardWarningsHarness.qml` — eleven isolated production-card transition rows through `e270b67b9`/`18d5943a2`: missing-data busy state, city/current temperature/timezone, capped and expanded forecast dates, rounded Celsius/Fahrenheit extrema, current/forecast icons, location visibility, rain→snow shader/source visibility and advancing uniforms, effects unload/reload, cleared-data delegate removal, and weather-disabled visibility. Fake settings/location services supply fixed weather; no provider requests, natural refresh cadence, or GPU pixel proof. Targeted lint drops 25→9 and accepts only nine shader creation-context diagnostics, not warning-free analysis. Standalone modes, isolation, and acceptance: [testing](testing.md#weathercard-and-bar-clock-isolated-runtime).
- `Tests/weather-card-effects.test.py` with `Tests/Qml/WeatherCardEffectsHarness.qml` — offscreen production-card precipitation lifecycle and animation.
- `Tests/location-service-runtime.test.py` with `Tests/Qml/LocationServiceHarness.qml` and `Tests/Fixtures/LocationNetworkPlugin.cpp` — nine isolated cases against the unchanged production singleton, real FileView and asynchronous XMLHttpRequest callbacks; fixture replies cover loaded/missing-cache startup callbacks, timer-driven coordinate reuse, success, unresolved locations, parse failures, HTTP failures, in-flight refresh exclusion, and actual cache writes. Runs non-visible with isolated config/cache paths and network namespace; verifies the real settings hash remains unchanged.
- Runtime proof uses fixture Settings/Time/Logger singletons and synthetic provider replies, not live geocoding/Open-Meteo, real configuration integration, or whole-shell acceptance. The Python suite runs standalone; it is not wired into `run-tests.sh`.
- Targeted LocationService lint after `1a3fbecea` retains an installed `FileViewAdapter` metadata diagnostic; owner qualification does not establish warning-free or type-complete analysis.
- `Tests/location-tab-warnings.test.py` (`lint` / `behavior`) with `Tests/Qml/LocationTabWarningsHarness.qml` — at `b4b11e15c`, targeted LocationTab diagnostics drop 10→0; nine reported offscreen passes comprise seven behavioral rows plus QtTest init/cleanup. Production tab and controls exercise the location settings requirements above against synthetic in-memory settings and LocationService. Reopening proves fixture state retention, not disk persistence. No geolocation, provider network requests, live settings, or live desktop acceptance. Standalone modes and isolation: [testing](testing.md#locationtab-isolated-runtime).
- `Tests/location-service-guards.test.js` — `64b6441d7`/`78bb2329f` execute production lifecycle, scheduling and request callbacks with mocked XMLHttpRequest, cache and clock state: coordinate reuse/reset, in-flight exclusion, request parameters, success/error replies, cache retention and rescheduling. Retained source checks are structural; this Node fixture is not offscreen asynchronous networking or live-provider proof.
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [x] Add executable fixture coverage for geocoding success, unresolved-location, parse-error, and HTTP-error responses.
- [x] Add executable fixture coverage for Open-Meteo success, parse-error, and HTTP-error responses.
- [x] Add isolated WeatherCard visibility, current/forecast text and icon, and precipitation lifecycle/uniform coverage.
- [ ] Prove precipitation GPU pixel output and natural weather refresh cadence; isolated property/delegate assertions do not establish rendered visual quality.
- [x] Add isolated LocationTab coverage for location edits, selection, weather toggles, card ordering, and tab recreation.
- [ ] Prove LocationTab integration with real settings persistence, geolocation, and network providers; fixture settings and reset counters do not establish those boundaries.

## Out of scope

- Calendar provider behavior is covered by [docs/specs/calendar.md](calendar.md).
- Night light behavior belongs in a separate night-light spec.
- Dark mode behavior belongs in a separate dark-mode spec.
