import QtQuick
import Quickshell
import LocationNetwork
import qs.Commons
import qs.Services.Location

ShellRoot {
  id: root
  property string scenario: Quickshell.env("LOCATION_SCENARIO")
  property int step: 0
  readonly property LocationService service: LocationService
  readonly property var expectedErrors: ({
      "geo-http-error": "Geocoding error: 503",
      "geo-unresolved-error": "could not resolve location name",
      "geo-parse-error": "Failed to parse geocoding data:",
      "weather-http-error": "Weather fetch error: 503",
      "weather-parse-error": "Failed to parse weather data"
    })

  function require(condition: bool, message: string): void {
    if (!condition) {
      console.error("LOCATION_FAIL", root.scenario, message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  Timer {
    interval: 100
    running: true
    repeat: true
    onTriggered: {
      const service = root.service;
      if (root.step++ === 0) {
        if (root.scenario === "missing")
          return; // Enabled startup refresh comes from the real FileView load failure.
        root.require(!service.isFetchingWeather, "disabled weather must not fetch on cache load");
        if (root.scenario === "cached") {
          root.require(service.coordinatesReady, "cache must publish coordinates");
          root.require(service.displayCoordinates === "32.0000, -96.0000", "cache display coordinates");
          root.require(service.stableName === "Fixture City", "cache name");
        }
        Settings.data.location.weatherEnabled = true;
        if (root.scenario === "reuse")
          return; // Exercise the production update Timer, not a manual refresh.
        service.updateWeather();
        if (root.scenario !== "cached") {
          root.require(service.isFetchingWeather, "refresh must enter fetching state");
          service.updateWeather(); // In-flight refresh must not issue another request.
        }
        return;
      }
      const saveFinished = root.step >= (root.scenario === "reuse" ? 25 : 14);
      if (service.isFetchingWeather || (!root.scenario.endsWith("error") && !saveFinished))
        return; // Allow the real one-second adapter save timer to finish.
      if (root.scenario.endsWith("error")) {
        root.require(!service.coordinatesReady, "failure must not publish coordinates");
        root.require(Logger.errors.length === 1, "provider failure must be logged once");
        const expected = root.expectedErrors[root.scenario];
        root.require(Logger.errors[0].startsWith(expected), "wrong provider error: " + Logger.errors[0]);
        root.require(service.weatherTimerIntervalMs === 1000, "failure retry interval");
      } else {
        root.require(Logger.errors.length === 0, "unexpected provider error");
        root.require(service.coordinatesReady, "success must publish coordinates");
        root.require(service.displayCoordinates === "32.0000, -96.0000", "stable display");
        root.require(service.data.latitude === "32" && service.data.longitude === "-96", "adapter provider coordinates");
        root.require(service.data.weatherLastFetch === 1000, "fetch timestamp");
        root.require(service.data.weather.current_weather.temperature === 21, "provider JSON cached");
        root.require(service.weatherTimerIntervalMs === 1800000, "fresh cache expiry scheduling");
        root.require(service.stableName === (root.scenario === "geocode" || root.scenario === "missing" ? "Fixture City, ZZ" : "Fixture City"), "stable location name");
      }
      console.log("LOCATION_PASS", root.scenario);
      Qt.exit(0);
    }
  }
  Timer {
    interval: 4000
    running: true
    onTriggered: root.require(false, "fixture timed out")
  }
}
