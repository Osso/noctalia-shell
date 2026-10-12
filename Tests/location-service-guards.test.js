#!/usr/bin/env node

const assert = require("assert/strict");
const { extractFunctionBody, readQml } = require("./qml-test-utils");

function locationFunction(name) {
  const body = extractFunctionBody(readQml("Services/Location/LocationService.qml"), name);
  return new Function("ctx", `with (ctx) { return (function() ${body}).call(ctx); }`);
}

function testLocationServiceLifecycleAndRefreshGuards() {
  const logs = [];
  const fetches = [];
  const geocodes = [];
  const ctx = {
    coordinatesReady: true,
    stableLatitude: "32",
    stableLongitude: "-96",
    stableName: "Dallas, US",
    cacheData: { latitude: "32", longitude: "-96", name: "Dallas", weatherLastFetch: 1000, weather: {} },
    Settings: { data: { location: { name: "Dallas", weatherEnabled: true } } },
    isFetchingWeather: false,
    Time: { timestamp: 1100 },
    weatherUpdateFrequency: 1800,
    Logger: {
      i(...args) {
        logs.push(args);
      },
      d() {},
      w(...args) {
        logs.push(args);
      },
    },
    errorCallback() {
      throw new Error("unexpected weather error");
    },
    _fetchWeather(latitude, longitude, error) {
      assert.equal(error, ctx.errorCallback);
      fetches.push([latitude, longitude]);
    },
    _geocodeLocation(name, callback, error) {
      assert.equal(error, ctx.errorCallback);
      geocodes.push(name);
      assert.equal(ctx.isFetchingWeather, true);
      callback(48.85, 2.35, "Paris", "France");
    },
  };
  ctx.root = ctx;
  ctx.data = ctx.cacheData;
  ctx.shouldRefreshWeather = () => locationFunction("shouldRefreshWeather")(ctx);
  ctx.getFreshWeather = () => locationFunction("getFreshWeather")(ctx);
  ctx.updateWeather = () => locationFunction("updateWeather")(ctx);

  locationFunction("init")(ctx);
  assert.deepEqual(logs, [["Location", "Service started"]]);
  ctx.updateWeather();
  assert.deepEqual(fetches, [], "fresh cache must not fetch");

  ctx.Settings.data.location.weatherEnabled = false;
  let resetSnapshot;
  const updateWeather = ctx.updateWeather;
  ctx.updateWeather = () => {
    resetSnapshot = { ...ctx.cacheData };
    assert.equal(ctx.coordinatesReady, false);
    assert.deepEqual([ctx.stableLatitude, ctx.stableLongitude, ctx.stableName], ["", "", ""]);
    updateWeather();
  };
  locationFunction("resetWeather")(ctx);
  assert.deepEqual(resetSnapshot, { latitude: "", longitude: "", name: "", weatherLastFetch: 0, weather: null });
  assert.deepEqual(fetches, [], "disabled weather must not fetch even after reset");
  ctx.updateWeather = updateWeather;

  ctx.Settings.data.location.weatherEnabled = true;
  ctx.isFetchingWeather = true;
  ctx.updateWeather();
  assert.deepEqual(fetches, [], "in-flight fetch must not start another");
  assert.deepEqual(logs.at(-1), ["Location", "Weather is still fetching"]);
  ctx.isFetchingWeather = false;
  ctx.updateWeather();
  assert.deepEqual(geocodes, ["Dallas"]);
  assert.deepEqual(fetches, [[48.85, 2.35]]);
  assert.deepEqual(ctx.cacheData, { latitude: "48.85", longitude: "2.35", name: "Dallas", weatherLastFetch: 0, weather: null });
  assert.equal(ctx.stableName, "Paris, France");
  assert.equal(ctx.isFetchingWeather, true);

  ctx.isFetchingWeather = false;
  ctx.getFreshWeather();
  assert.deepEqual(fetches.at(-1), ["48.85", "2.35"], "unchanged location reuses cached coordinates");
  assert.deepEqual(geocodes, ["Dallas"]);
  ctx.coordinatesReady = true;
  ctx.Settings.data.location.name = "Paris";
  ctx.getFreshWeather();
  assert.equal(ctx.coordinatesReady, false);
  assert.deepEqual(geocodes, ["Dallas", "Paris"]);
  assert.equal(ctx.cacheData.name, "Paris");
  assert.deepEqual(fetches.at(-1), [48.85, 2.35]);

  for (const coordinate of ["latitude", "longitude"]) {
    ctx.cacheData[coordinate] = "";
    ctx.getFreshWeather();
    assert.equal(geocodes.length, coordinate === "latitude" ? 3 : 4);
    assert.equal(ctx.cacheData[coordinate], coordinate === "latitude" ? "48.85" : "2.35");
  }
}

function testLocationServiceSchedulingGuards() {
  const source = readQml("Services/Location/LocationService.qml");
  const shouldRefreshWeather = new Function(
    "ctx",
    `with (ctx) { return (function() ${extractFunctionBody(source, "shouldRefreshWeather")}).call(ctx); }`,
  );
  const nextWeatherUpdateIntervalMs = new Function(
    "ctx",
    `with (ctx) { return (function() ${extractFunctionBody(source, "nextWeatherUpdateIntervalMs")}).call(ctx); }`,
  );
  const scheduleWeatherUpdate = new Function(
    "ctx",
    `with (ctx) { return (function() ${extractFunctionBody(source, "scheduleWeatherUpdate")}).call(ctx); }`,
  );

  assert.match(source, /property int weatherTimerIntervalMs:/, "LocationService must store the next weather timer interval");
  assert.match(
    source,
    /interval: root\.weatherTimerIntervalMs/,
    "weather update timer must use scheduled intervals instead of a fixed 20s loop",
  );
  assert.match(source, /onRunningChanged:[\s\S]*root\.scheduleWeatherUpdate\(\)/, "weather timer must reschedule when enabled");
  assert.match(
    source,
    /onTriggered:[\s\S]*updateWeather\(\)[\s\S]*root\.scheduleWeatherUpdate\(\)/,
    "weather timer must reschedule after each check",
  );

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
  ctx.cacheData = ctx.adapter;
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
  const execute = (name, ...args) => new Function("ctx", ...args, `with (ctx) ${extractFunctionBody(source, name)}`);
  const requests = [];
  const errors = [];
  const resolved = [];
  let reschedules = 0;
  const ctx = {
    isFetchingWeather: true,
    Time: { timestamp: 1234 },
    data: { latitude: "old", longitude: "old", weather: null, weatherLastFetch: 0 },
    coordinatesReady: false,
    stableLatitude: "old",
    stableLongitude: "old",
    Logger: {
      d() {},
      e(...args) {
        errors.push(args);
      },
    },
    scheduleWeatherUpdate() {
      reschedules += 1;
    },
    XMLHttpRequest: class {
      static DONE = 4;
      constructor() {
        this.readyState = 1;
        requests.push(this);
      }
      open(method, url) {
        this.method = method;
        this.url = url;
      }
      send() {
        this.sent = true;
      }
      respond(status, responseText, readyState = 4) {
        this.status = status;
        this.responseText = responseText;
        this.readyState = readyState;
        this.onreadystatechange();
      }
    },
  };
  ctx.root = ctx;
  const error = (module, message) => execute("errorCallback", "module", "message")(ctx, module, message);
  const geocode = execute("_geocodeLocation", "locationName", "callback", "errorCallback");
  const fetchWeather = execute("_fetchWeather", "latitude", "longitude", "errorCallback");

  geocode(ctx, "Paris & suburbs", (...coordinates) => resolved.push(coordinates), error);
  const geoRequest = requests.at(-1);
  assert.equal(geoRequest.method, "GET");
  assert.equal(geoRequest.url, "https://assets.noctalia.dev/geocode.php?city=Paris%20%26%20suburbs&language=en&format=json");
  assert.equal(geoRequest.sent, true);
  geoRequest.respond(200, '{"lat":48.85,"lng":2.35,"name":"Paris","country":"France"}', 3);
  assert.deepEqual(resolved, [], "incomplete geocoding response must not publish coordinates");
  geoRequest.respond(200, '{"lat":48.85,"lng":2.35,"name":"Paris","country":"France"}');
  assert.deepEqual(resolved, [[48.85, 2.35, "Paris", "France"]]);
  assert.deepEqual(errors, []);

  for (
    const [status, payload, expected] of [
      [200, "{}", "could not resolve location name"],
      [200, "invalid json", /^Failed to parse geocoding data:/],
      [503, "{}", "Geocoding error: 503"],
    ]
  ) {
    ctx.isFetchingWeather = true;
    geocode(ctx, "Paris", (...coordinates) => resolved.push(coordinates), error);
    requests.at(-1).respond(status, payload);
    assert.equal(errors.at(-1)[0], "Location");
    if (expected instanceof RegExp) assert.match(errors.at(-1)[1], expected);
    else assert.equal(errors.at(-1)[1], expected);
    assert.equal(ctx.isFetchingWeather, false);
  }
  assert.equal(resolved.length, 1, "geocoding failures must not publish coordinates");
  assert.equal(reschedules, 3);

  ctx.isFetchingWeather = true;
  fetchWeather(ctx, 48.85, 2.35, error);
  const weatherRequest = requests.at(-1);
  assert.equal(weatherRequest.method, "GET");
  assert.equal(weatherRequest.sent, true);
  const url = new URL(weatherRequest.url);
  assert.equal(url.origin + url.pathname, "https://api.open-meteo.com/v1/forecast");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    latitude: "48.85",
    longitude: "2.35",
    current_weather: "true",
    current: "relativehumidity_2m,surface_pressure",
    daily: "temperature_2m_max,temperature_2m_min,weathercode,sunset,sunrise",
    timezone: "auto",
  });
  const weather = { latitude: 48.85, longitude: 2.35, current_weather: { temperature: 23 } };
  weatherRequest.respond(200, JSON.stringify(weather));
  assert.deepEqual(ctx.data.weather, weather);
  assert.equal(ctx.data.weatherLastFetch, 1234);
  assert.deepEqual([ctx.data.latitude, ctx.data.longitude], ["48.85", "2.35"]);
  assert.deepEqual([ctx.stableLatitude, ctx.stableLongitude], ["48.85", "2.35"]);
  assert.equal(ctx.coordinatesReady, true);
  assert.equal(ctx.isFetchingWeather, false);
  assert.equal(reschedules, 4);

  for (
    const [status, payload, expected] of [
      [200, "invalid json", "Failed to parse weather data"],
      [503, "{}", "Weather fetch error: 503"],
    ]
  ) {
    ctx.isFetchingWeather = true;
    fetchWeather(ctx, 48.85, 2.35, error);
    requests.at(-1).respond(status, payload);
    assert.deepEqual(errors.at(-1), ["Location", expected]);
    assert.equal(ctx.isFetchingWeather, false);
    assert.deepEqual(ctx.data.weather, weather, "failed requests must preserve cached weather");
    assert.equal(ctx.data.weatherLastFetch, 1234);
  }
  assert.equal(reschedules, 6);
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
  assert.match(
    symbolBody,
    /if \(code === 1 \|\| code === 2\)\s+return "weather-cloud-sun"/,
    "weatherSymbolFromCode must map partly cloudy",
  );
  assert.match(symbolBody, /if \(code === 3\)\s+return "weather-cloud"/, "weatherSymbolFromCode must map overcast");
  assert.match(symbolBody, /if \(code >= 45 && code <= 48\)\s+return "weather-cloud-haze"/, "weatherSymbolFromCode must map fog");
  assert.match(symbolBody, /if \(code >= 51 && code <= 67\)\s+return "weather-cloud-rain"/, "weatherSymbolFromCode must map drizzle");
  assert.match(symbolBody, /if \(code >= 80 && code <= 82\)\s+return "weather-cloud-rain"/, "weatherSymbolFromCode must map rain showers");
  assert.match(symbolBody, /if \(code >= 71 && code <= 77\)\s+return "weather-cloud-snow"/, "weatherSymbolFromCode must map snow");
  assert.match(
    symbolBody,
    /if \(code >= 95 && code <= 99\)\s+return "weather-cloud-lightning"/,
    "weatherSymbolFromCode must map thunderstorms",
  );
  assert.match(symbolBody, /return "weather-cloud"/, "weatherSymbolFromCode must fall back to cloud icon");
  assert.match(descriptionBody, /if \(code === 0\)\s+return "Clear sky"/, "weatherDescriptionFromCode must describe clear sky");
  assert.match(descriptionBody, /if \(code === 1\)\s+return "Mainly clear"/, "weatherDescriptionFromCode must describe mainly clear");
  assert.match(descriptionBody, /if \(code === 2\)\s+return "Partly cloudy"/, "weatherDescriptionFromCode must describe partly cloudy");
  assert.match(descriptionBody, /if \(code === 3\)\s+return "Overcast"/, "weatherDescriptionFromCode must describe overcast");
  assert.match(descriptionBody, /if \(code === 45 \|\| code === 48\)\s+return "Fog"/, "weatherDescriptionFromCode must describe fog");
  assert.match(descriptionBody, /if \(code >= 51 && code <= 67\)\s+return "Drizzle"/, "weatherDescriptionFromCode must describe drizzle");
  assert.match(descriptionBody, /if \(code >= 71 && code <= 77\)\s+return "Snow"/, "weatherDescriptionFromCode must describe snow");
  assert.match(
    descriptionBody,
    /if \(code >= 80 && code <= 82\)\s+return "Rain showers"/,
    "weatherDescriptionFromCode must describe rain showers",
  );
  assert.match(
    descriptionBody,
    /if \(code >= 95 && code <= 99\)\s+return "Thunderstorm"/,
    "weatherDescriptionFromCode must describe thunderstorms",
  );
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
