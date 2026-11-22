pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

// Weather logic and caching with stable UI properties
Singleton {
  id: root

  property string locationFile: Quickshell.env("NOCTALIA_WEATHER_FILE") || (Settings.cacheDir + "location.json")
  property int weatherUpdateFrequency: 30 * 60 // 30 minutes expressed in seconds
  property int weatherTimerIntervalMs: 1000
  property bool isFetchingWeather: false
  property bool isFetchingLocation: false

  readonly property alias data: adapter // Public cached weather data.
  readonly property alias cacheData: adapter

  // Stable UI properties - only updated when location is fully resolved
  property bool coordinatesReady: false
  property string stableLatitude: ""
  property string stableLongitude: ""
  property string stableName: ""
  property string stableTimezone: ""

  FileView {
    id: locationFileView
    path: root.locationFile
    printErrors: false
    onAdapterUpdated: saveTimer.start()
    onLoaded: {
      Logger.d("Location", "Loaded cached data");
      // Initialize stable properties on load
      if (root.cacheData.latitude !== "" && root.cacheData.longitude !== "" && root.cacheData.name === Settings.data.location.name) {
        root.stableLatitude = root.cacheData.latitude;
        root.stableLongitude = root.cacheData.longitude;
        root.stableName = root.cacheData.name;
        root.stableTimezone = root.cacheData.timezone || "";
        if (root.stableTimezone !== "") {
          Time.setLocationTimezone(root.stableTimezone);
        }
        if (root.cacheData.weatherLastFetch > 0 || !Settings.data.location.weatherEnabled) {
          root.coordinatesReady = true;
          Logger.i("Location", "Coordinates ready");
        }
      }
      root.updateWeather();
      root.scheduleWeatherUpdate();
    }
    onLoadFailed: function (error) {
      root.updateWeather();
      root.scheduleWeatherUpdate();
    }

    JsonAdapter {
      id: adapter

      // Core data properties
      property string latitude: ""
      property string longitude: ""
      property string name: ""
      property string timezone: ""
      property int weatherLastFetch: 0
      property var weather: null
    }
  }

  // Helper property for UI components (outside JsonAdapter to avoid binding loops)
  readonly property string displayCoordinates: {
    if (!root.coordinatesReady || root.stableLatitude === "" || root.stableLongitude === "") {
      return "";
    }
    const lat = parseFloat(root.stableLatitude).toFixed(4);
    const lon = parseFloat(root.stableLongitude).toFixed(4);
    return `${lat}, ${lon}`;
  }

  // Wake when the weather cache can actually expire instead of polling every few seconds.
  Timer {
    id: updateTimer
    interval: root.weatherTimerIntervalMs
    running: Settings.data.location.weatherEnabled || Settings.data.colorSchemes.schedulingMode == "location"
    repeat: true
    onRunningChanged: {
      if (running) {
        root.scheduleWeatherUpdate();
      }
    }
    onTriggered: {
      root.updateWeather();
      root.scheduleWeatherUpdate();
    }
  }

  Timer {
    id: saveTimer
    running: false
    interval: 1000
    onTriggered: locationFileView.writeAdapter()
  }

  // --------------------------------
  function init() {
    // does nothing but ensure the singleton is created
    // do not remove
    Logger.i("Location", "Service started");
  }

  // --------------------------------
  function resetWeather() {
    Logger.i("Location", "Resetting weather data");

    // Mark as changing to prevent UI updates
    root.coordinatesReady = false;
    // Reset stable properties
    root.stableLatitude = "";
    root.stableLongitude = "";
    root.stableName = "";
    root.stableTimezone = "";

    // Reset core data
    root.cacheData.latitude = "";
    root.cacheData.longitude = "";
    root.cacheData.name = "";
    root.cacheData.timezone = "";
    root.cacheData.weatherLastFetch = 0;
    root.cacheData.weather = null;

    // Try to fetch immediately
    updateWeather();
  }

  // --------------------------------
  function needsLocationGeocode() {
    return (root.cacheData.latitude === "") || (root.cacheData.longitude === "") || (root.cacheData.name !== Settings.data.location.name) || (root.cacheData.timezone === "");
  }

  // --------------------------------
  function resolveLocation() {
    if (root.isFetchingLocation || !Settings.data.location.name || !root.needsLocationGeocode()) {
      return;
    }

    root.isFetchingLocation = true;
    root.coordinatesReady = false;
    _geocodeLocation(Settings.data.location.name, function (latitude, longitude, name, country, timezone) {
      Logger.d("Location", "Geocoded", Settings.data.location.name, "to:", latitude, "/", longitude);
      root.cacheData.name = Settings.data.location.name;
      root.cacheData.latitude = latitude.toString();
      root.cacheData.longitude = longitude.toString();
      root.cacheData.timezone = timezone || "";
      root.stableLatitude = root.cacheData.latitude;
      root.stableLongitude = root.cacheData.longitude;
      root.stableName = `${name}, ${country}`;
      root.stableTimezone = root.cacheData.timezone;
      root.coordinatesReady = true;
      if (root.stableTimezone !== "") {
        Time.setLocationTimezone(root.stableTimezone);
      }
      root.isFetchingLocation = false;
    }, function (module, message) {
      Logger.e(module, message);
      root.isFetchingLocation = false;
    });
  }

  // --------------------------------
  function updateWeather() {
    if (!Settings.data.location.weatherEnabled) {
      root.resolveLocation();
      return;
    }

    if (isFetchingWeather) {
      Logger.w("Location", "Weather is still fetching");
      return;
    }

    if (root.shouldRefreshWeather()) {
      getFreshWeather();
    }
  }

  function shouldRefreshWeather() {
    return (root.cacheData.weatherLastFetch === "") || (root.cacheData.weather === null) || (root.cacheData.latitude === "") || (root.cacheData.longitude === "") || (root.cacheData.name !== Settings.data.location.name) || (Time.timestamp >= root.cacheData.weatherLastFetch + weatherUpdateFrequency);
  }

  function nextWeatherUpdateIntervalMs() {
    if (isFetchingWeather) {
      return 60000;
    }

    if (root.shouldRefreshWeather()) {
      return 1000;
    }

    const nextFetchTimestamp = root.cacheData.weatherLastFetch + weatherUpdateFrequency;
    return Math.max(1000, (nextFetchTimestamp - Time.timestamp) * 1000);
  }

  function scheduleWeatherUpdate() {
    weatherTimerIntervalMs = nextWeatherUpdateIntervalMs();
  }

  // --------------------------------
  function getFreshWeather() {
    isFetchingWeather = true;

    // Check if location name has changed
    const locationChanged = data.name !== Settings.data.location.name;
    if (locationChanged) {
      root.coordinatesReady = false;
      Logger.d("Location", "Location changed from", root.cacheData.name, "to", Settings.data.location.name);
    }

    if (root.needsLocationGeocode()) {
      _geocodeLocation(Settings.data.location.name, function (latitude, longitude, name, country, timezone) {
        Logger.d("Location", "Geocoded", Settings.data.location.name, "to:", latitude, "/", longitude);

        // Save location name
        root.cacheData.name = Settings.data.location.name;

        // Save GPS coordinates and timezone
        root.cacheData.latitude = latitude.toString();
        root.cacheData.longitude = longitude.toString();
        root.cacheData.timezone = timezone || "";

        root.stableName = `${name}, ${country}`;
        root.stableTimezone = root.cacheData.timezone;
        if (root.stableTimezone !== "") {
          Time.setLocationTimezone(root.stableTimezone);
        }

        _fetchWeather(latitude, longitude, errorCallback);
      }, errorCallback);
    } else {
      if (root.cacheData.timezone && root.cacheData.timezone !== "") {
        root.stableTimezone = root.cacheData.timezone;
        Time.setLocationTimezone(root.stableTimezone);
      }
      _fetchWeather(root.cacheData.latitude, root.cacheData.longitude, errorCallback);
    }
  }

  // --------------------------------
  function _geocodeLocation(locationName, callback, errorCallback) {
    Logger.d("Location", "Geocoding location name");
    var geoUrl = "https://geocoding-api.open-meteo.com/v1/search?name=" + encodeURIComponent(locationName) + "&count=1&language=en&format=json";
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
      if (xhr.readyState === XMLHttpRequest.DONE) {
        if (xhr.status === 200) {
          try {
            const geoData = JSON.parse(xhr.responseText);
            const first = geoData.results && geoData.results.length > 0 ? geoData.results[0] : null;
            if (first && first.latitude != null && first.longitude != null) {
              callback(first.latitude, first.longitude, first.name, first.country, first.timezone || "");
            } else {
              errorCallback("Location", "could not resolve location name");
            }
          } catch (e) {
            errorCallback("Location", "Failed to parse geocoding data: " + e);
          }
        } else {
          errorCallback("Location", "Geocoding error: " + xhr.status);
        }
      }
    };
    xhr.open("GET", geoUrl);
    xhr.send();
  }

  // --------------------------------
  function _fetchWeather(latitude, longitude, errorCallback) {
    Logger.d("Location", "Fetching weather from api.open-meteo.com");
    var url = "https://api.open-meteo.com/v1/forecast?latitude=" + latitude + "&longitude=" + longitude + "&current_weather=true&current=relativehumidity_2m,surface_pressure&daily=temperature_2m_max,temperature_2m_min,weathercode,sunset,sunrise&timezone=auto";
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
      if (xhr.readyState === XMLHttpRequest.DONE) {
        if (xhr.status === 200) {
          try {
            const weatherData = JSON.parse(xhr.responseText);
            //console.log(JSON.stringify(weatherData))

            // Save core data
            data.weather = weatherData;
            data.weatherLastFetch = Time.timestamp;

            // Update stable display values only when complete and successful
            root.stableLatitude = data.latitude = weatherData.latitude.toString();
            root.stableLongitude = data.longitude = weatherData.longitude.toString();
            root.coordinatesReady = true;

            isFetchingWeather = false;
            root.scheduleWeatherUpdate();
            Logger.d("Location", "Cached weather to disk - stable coordinates updated");
          } catch (e) {
            errorCallback("Location", "Failed to parse weather data");
          }
        } else {
          errorCallback("Location", "Weather fetch error: " + xhr.status);
        }
      }
    };
    xhr.open("GET", url);
    xhr.send();
  }

  // --------------------------------
  function errorCallback(module, message) {
    Logger.e(module, message);
    isFetchingWeather = false;
    root.scheduleWeatherUpdate();
  }

  // --------------------------------
  function weatherSymbolFromCode(code) {
    if (code === 0)
      return "weather-sun";
    if (code === 1 || code === 2)
      return "weather-cloud-sun";
    if (code === 3)
      return "weather-cloud";
    if (code >= 45 && code <= 48)
      return "weather-cloud-haze";
    if (code >= 51 && code <= 67)
      return "weather-cloud-rain";
    if (code >= 80 && code <= 82)
      return "weather-cloud-rain";
    if (code >= 71 && code <= 77)
      return "weather-cloud-snow";
    if (code >= 71 && code <= 77)
      return "weather-cloud-snow";
    if (code >= 85 && code <= 86)
      return "weather-cloud-snow";
    if (code >= 95 && code <= 99)
      return "weather-cloud-lightning";
    return "weather-cloud";
  }

  // --------------------------------
  function weatherDescriptionFromCode(code) {
    if (code === 0)
      return "Clear sky";
    if (code === 1)
      return "Mainly clear";
    if (code === 2)
      return "Partly cloudy";
    if (code === 3)
      return "Overcast";
    if (code === 45 || code === 48)
      return "Fog";
    if (code >= 51 && code <= 67)
      return "Drizzle";
    if (code >= 71 && code <= 77)
      return "Snow";
    if (code >= 80 && code <= 82)
      return "Rain showers";
    if (code >= 95 && code <= 99)
      return "Thunderstorm";
    return "Unknown";
  }

  // --------------------------------
  function celsiusToFahrenheit(celsius) {
    return 32 + celsius * 1.8;
  }
}
