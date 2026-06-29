#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function testLocationServiceLifecycleAndRefreshGuards() {
  const source = readQml("Services/Location/LocationService.qml");
  const initBody = extractFunctionBody(source, "init");
  const resetBody = extractFunctionBody(source, "resetWeather");
  const updateBody = extractFunctionBody(source, "updateWeather");
  const freshBody = extractFunctionBody(source, "getFreshWeather");

  assert.match(initBody, /Logger\.i\("Location", "Service started"\)/, "init must log service startup");
  assert.match(resetBody, /root\.coordinatesReady = false/, "resetWeather must mark coordinates changing");
  assert.match(resetBody, /root\.stableLatitude = ""[\s\S]*root\.stableLongitude = ""[\s\S]*root\.stableName = ""/, "resetWeather must clear stable display values");
  assert.match(resetBody, /adapter\.latitude = ""[\s\S]*adapter\.longitude = ""[\s\S]*adapter\.name = ""/, "resetWeather must clear cached location coordinates");
  assert.match(resetBody, /adapter\.weatherLastFetch = 0[\s\S]*adapter\.weather = null/, "resetWeather must clear cached weather");
  assert.match(resetBody, /updateWeather\(\)/, "resetWeather must trigger a weather refresh");
  assert.match(updateBody, /if \(!Settings\.data\.location\.weatherEnabled\)[\s\S]*return;/, "updateWeather must respect disabled weather setting");
  assert.match(updateBody, /if \(isFetchingWeather\)[\s\S]*Logger\.w\("Location", "Weather is still fetching"\)[\s\S]*return;/, "updateWeather must avoid concurrent fetches");
  assert.match(updateBody, /if \(root\.shouldRefreshWeather\(\)\)[\s\S]*getFreshWeather\(\)/, "updateWeather must refresh only when weather data is missing, changed, or expired");
  assert.match(freshBody, /isFetchingWeather = true/, "getFreshWeather must mark fetch in progress");
  assert.match(freshBody, /const locationChanged = data\.name !== Settings\.data\.location\.name/, "getFreshWeather must detect location name changes");
  assert.match(freshBody, /if \(locationChanged\)[\s\S]*root\.coordinatesReady = false/, "getFreshWeather must clear coordinate readiness when location changes");
  assert.match(freshBody, /if \(\(adapter\.latitude === ""\) \|\| \(adapter\.longitude === ""\) \|\| locationChanged\)/, "getFreshWeather must geocode missing or changed locations");
  assert.match(freshBody, /_geocodeLocation\(Settings\.data\.location\.name, function \(latitude, longitude, name, country\)/, "getFreshWeather must geocode configured location names");
  assert.match(freshBody, /adapter\.name = Settings\.data\.location\.name[\s\S]*adapter\.latitude = latitude\.toString\(\)[\s\S]*adapter\.longitude = longitude\.toString\(\)/, "getFreshWeather must persist geocoded coordinates");
  assert.match(freshBody, /root\.stableName = `\$\{name\}, \$\{country\}`/, "getFreshWeather must publish display location name");
  assert.match(freshBody, /_fetchWeather\(latitude, longitude, errorCallback\)/, "getFreshWeather must fetch weather after geocoding");
  assert.match(freshBody, /else[\s\S]*_fetchWeather\(adapter\.latitude, adapter\.longitude, errorCallback\)/, "getFreshWeather must reuse cached coordinates when valid");
}

function testLocationServiceSchedulingGuards() {
  const source = readQml("Services/Location/LocationService.qml");
  const shouldRefreshWeather = new Function("ctx", `with (ctx) { return (function() ${extractFunctionBody(source, "shouldRefreshWeather")}).call(ctx); }`);
  const nextWeatherUpdateIntervalMs = new Function("ctx", `with (ctx) { return (function() ${extractFunctionBody(source, "nextWeatherUpdateIntervalMs")}).call(ctx); }`);
  const scheduleWeatherUpdate = new Function("ctx", `with (ctx) { return (function() ${extractFunctionBody(source, "scheduleWeatherUpdate")}).call(ctx); }`);

  assert.match(source, /property int weatherTimerIntervalMs:/, "LocationService must store the next weather timer interval");
  assert.match(source, /interval: root\.weatherTimerIntervalMs/, "weather update timer must use scheduled intervals instead of a fixed 20s loop");
  assert.match(source, /onRunningChanged:[\s\S]*root\.scheduleWeatherUpdate\(\)/, "weather timer must reschedule when enabled");
  assert.match(source, /onTriggered:[\s\S]*updateWeather\(\)[\s\S]*root\.scheduleWeatherUpdate\(\)/, "weather timer must reschedule after each check");

  const ctx = {
    weatherUpdateFrequency: 1800,
    weatherTimerIntervalMs: 0,
    isFetchingWeather: false,
    adapter: {
      weatherLastFetch: 1000,
      weather: { current_weather: {} },
      latitude: "32.0",
      longitude: "-96.0",
      name: "Dallas, TX",
    },
    Settings: {
      data: {
        location: {
          name: "Dallas, TX",
        },
      },
    },
    Time: {
      timestamp: 1100,
    },
  };
  ctx.root = ctx;
  ctx.shouldRefreshWeather = () => shouldRefreshWeather(ctx);
  ctx.nextWeatherUpdateIntervalMs = () => nextWeatherUpdateIntervalMs(ctx);

  assert.equal(shouldRefreshWeather(ctx), false);
  assert.equal(nextWeatherUpdateIntervalMs(ctx), 1700000);
  scheduleWeatherUpdate(ctx);
  assert.equal(ctx.weatherTimerIntervalMs, 1700000);

  ctx.isFetchingWeather = true;
  assert.equal(nextWeatherUpdateIntervalMs(ctx), 60000);
  ctx.isFetchingWeather = false;

  ctx.Time.timestamp = 2800;
  assert.equal(shouldRefreshWeather(ctx), true);
  assert.equal(nextWeatherUpdateIntervalMs(ctx), 1000);

  ctx.adapter.weather = null;
  assert.equal(shouldRefreshWeather(ctx), true);
  assert.equal(nextWeatherUpdateIntervalMs(ctx), 1000);
}

function testLocationServiceNetworkRequestGuards() {
  const source = readQml("Services/Location/LocationService.qml");
  const geocodeBody = extractFunctionBody(source, "_geocodeLocation");
  const fetchBody = extractFunctionBody(source, "_fetchWeather");
  const errorBody = extractFunctionBody(source, "errorCallback");

  assert.match(source, /function _geocodeLocation\(locationName, callback, errorCallback\)/, "_geocodeLocation must type the required location name input while keeping callbacks dynamic");
  assert.match(source, /function errorCallback\(module, message\)/, "errorCallback must type module and message inputs");
  assert.match(geocodeBody, /var geoUrl = "https:\/\/assets\.noctalia\.dev\/geocode\.php\?city=" \+ encodeURIComponent\(locationName\) \+ "&language=en&format=json"/, "_geocodeLocation must build encoded geocode URLs");
  assert.match(geocodeBody, /if \(xhr\.readyState === XMLHttpRequest\.DONE\)/, "_geocodeLocation must wait for request completion");
  assert.match(geocodeBody, /if \(xhr\.status === 200\)[\s\S]*var geoData = JSON\.parse\(xhr\.responseText\)/, "_geocodeLocation must parse successful responses");
  assert.match(geocodeBody, /if \(geoData\.lat != null\)[\s\S]*callback\(geoData\.lat, geoData\.lng, geoData\.name, geoData\.country\)/, "_geocodeLocation must callback with resolved coordinates");
  assert.match(geocodeBody, /else[\s\S]*errorCallback\("Location", "could not resolve location name"\)/, "_geocodeLocation must report unresolved locations");
  assert.match(geocodeBody, /catch \(e\)[\s\S]*errorCallback\("Location", "Failed to parse geocoding data: " \+ e\)/, "_geocodeLocation must report parse errors");
  assert.match(geocodeBody, /errorCallback\("Location", "Geocoding error: " \+ xhr\.status\)/, "_geocodeLocation must report HTTP errors");
  assert.match(geocodeBody, /xhr\.open\("GET", geoUrl\)[\s\S]*xhr\.send\(\)/, "_geocodeLocation must send GET requests");
  assert.match(fetchBody, /var url = "https:\/\/api\.open-meteo\.com\/v1\/forecast\?latitude=" \+ latitude \+ "&longitude=" \+ longitude/, "_fetchWeather must build Open-Meteo URLs");
  assert.match(fetchBody, /if \(xhr\.status === 200\)[\s\S]*var weatherData = JSON\.parse\(xhr\.responseText\)/, "_fetchWeather must parse successful weather responses");
  assert.match(fetchBody, /data\.weather = weatherData[\s\S]*data\.weatherLastFetch = Time\.timestamp/, "_fetchWeather must cache weather and fetch time");
  assert.match(fetchBody, /root\.stableLatitude = data\.latitude = weatherData\.latitude\.toString\(\)[\s\S]*root\.stableLongitude = data\.longitude = weatherData\.longitude\.toString\(\)[\s\S]*root\.coordinatesReady = true/, "_fetchWeather must publish stable coordinates on success");
  assert.match(fetchBody, /isFetchingWeather = false[\s\S]*root\.scheduleWeatherUpdate\(\)/, "_fetchWeather must clear fetch state and reschedule on success");
  assert.match(fetchBody, /catch \(e\)[\s\S]*errorCallback\("Location", "Failed to parse weather data"\)/, "_fetchWeather must report parse errors");
  assert.match(fetchBody, /errorCallback\("Location", "Weather fetch error: " \+ xhr\.status\)/, "_fetchWeather must report HTTP errors");
  assert.match(fetchBody, /xhr\.open\("GET", url\)[\s\S]*xhr\.send\(\)/, "_fetchWeather must send GET requests");
  assert.match(errorBody, /Logger\.e\(module, message\)/, "errorCallback must log errors");
  assert.match(errorBody, /isFetchingWeather = false[\s\S]*root\.scheduleWeatherUpdate\(\)/, "errorCallback must clear fetch state and reschedule");
}

function testLocationServiceWeatherFormattingHelpers() {
  const source = readQml("Services/Location/LocationService.qml");
  const symbolBody = extractFunctionBody(source, "weatherSymbolFromCode");
  const descriptionBody = extractFunctionBody(source, "weatherDescriptionFromCode");
  const fahrenheitBody = extractFunctionBody(source, "celsiusToFahrenheit");

  assert.match(source, /function weatherSymbolFromCode\(code\)/, "weatherSymbolFromCode must type weather-code input");
  assert.match(source, /function weatherDescriptionFromCode\(code\)/, "weatherDescriptionFromCode must type weather-code input");
  assert.match(source, /function celsiusToFahrenheit\(celsius\)/, "celsiusToFahrenheit must type Celsius input");
  assert.match(symbolBody, /if \(code === 0\)\s+return "weather-sun"/, "weatherSymbolFromCode must map clear sky");
  assert.match(symbolBody, /if \(code === 1 \|\| code === 2\)\s+return "weather-cloud-sun"/, "weatherSymbolFromCode must map partly cloudy");
  assert.match(symbolBody, /if \(code === 3\)\s+return "weather-cloud"/, "weatherSymbolFromCode must map overcast");
  assert.match(symbolBody, /if \(code >= 45 && code <= 48\)\s+return "weather-cloud-haze"/, "weatherSymbolFromCode must map fog");
  assert.match(symbolBody, /if \(code >= 51 && code <= 67\)\s+return "weather-cloud-rain"/, "weatherSymbolFromCode must map drizzle");
  assert.match(symbolBody, /if \(code >= 80 && code <= 82\)\s+return "weather-cloud-rain"/, "weatherSymbolFromCode must map rain showers");
  assert.match(symbolBody, /if \(code >= 71 && code <= 77\)\s+return "weather-cloud-snow"/, "weatherSymbolFromCode must map snow");
  assert.match(symbolBody, /if \(code >= 95 && code <= 99\)\s+return "weather-cloud-lightning"/, "weatherSymbolFromCode must map thunderstorms");
  assert.match(symbolBody, /return "weather-cloud"/, "weatherSymbolFromCode must fall back to cloud icon");
  assert.match(descriptionBody, /if \(code === 0\)\s+return "Clear sky"/, "weatherDescriptionFromCode must describe clear sky");
  assert.match(descriptionBody, /if \(code === 1\)\s+return "Mainly clear"/, "weatherDescriptionFromCode must describe mainly clear");
  assert.match(descriptionBody, /if \(code === 2\)\s+return "Partly cloudy"/, "weatherDescriptionFromCode must describe partly cloudy");
  assert.match(descriptionBody, /if \(code === 3\)\s+return "Overcast"/, "weatherDescriptionFromCode must describe overcast");
  assert.match(descriptionBody, /if \(code === 45 \|\| code === 48\)\s+return "Fog"/, "weatherDescriptionFromCode must describe fog");
  assert.match(descriptionBody, /if \(code >= 51 && code <= 67\)\s+return "Drizzle"/, "weatherDescriptionFromCode must describe drizzle");
  assert.match(descriptionBody, /if \(code >= 71 && code <= 77\)\s+return "Snow"/, "weatherDescriptionFromCode must describe snow");
  assert.match(descriptionBody, /if \(code >= 80 && code <= 82\)\s+return "Rain showers"/, "weatherDescriptionFromCode must describe rain showers");
  assert.match(descriptionBody, /if \(code >= 95 && code <= 99\)\s+return "Thunderstorm"/, "weatherDescriptionFromCode must describe thunderstorms");
  assert.match(descriptionBody, /return "Unknown"/, "weatherDescriptionFromCode must fall back to Unknown");
  assert.match(fahrenheitBody, /return 32 \+ celsius \* 1\.8/, "celsiusToFahrenheit must convert Celsius to Fahrenheit");
}

const tests = [
  testLocationServiceLifecycleAndRefreshGuards,
  testLocationServiceSchedulingGuards,
  testLocationServiceNetworkRequestGuards,
  testLocationServiceWeatherFormattingHelpers,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}
