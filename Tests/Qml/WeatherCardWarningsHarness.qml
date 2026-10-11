import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Services.Location
import qs.Modules.Cards

ShellRoot {
  id: harness

  Window {
    width: 480
    height: 320
    visible: true // Offscreen backend; runner removes all desktop connections.

    WeatherCard {
      id: card
      anchors.fill: parent
      showEffects: true
      forecastDays: 2
    }
  }

  function require(condition, message) {
    if (!condition) {
      console.error("WEATHER_CARD_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function items(item, predicate) {
    let found = predicate(item) ? [item] : [];
    for (const child of item.children || [])
      found = found.concat(harness.items(child, predicate));
    return found;
  }

  function texts() {
    return harness.items(card, item => item.visible && item.text !== undefined && item.icon === undefined).map(item => item.text);
  }

  function shader() {
    return harness.items(card, item => item.fragmentShader !== undefined)[0];
  }

  function setLocation(name, value) {
    const settings = JSON.parse(JSON.stringify(Settings.data));
    settings.location[name] = value;
    Settings.data = settings;
  }

  function publish(code) {
    LocationService.data = {
      weather: {
        current_weather: {
          weathercode: code,
          temperature: 12.6
        },
        timezone_abbreviation: "UTC",
        daily: {
          time: ["2026-10-11", "2026-10-12", "2026-10-13"],
          weathercode: [0, 61, 71],
          temperature_2m_max: [20.4, 14.6, -1],
          temperature_2m_min: [9.6, 4.2, -5]
        }
      }
    };
  }

  Timer {
    id: steps
    interval: 120
    running: true
    repeat: true
    property int step: 0
    property real sampledTime: 0

    onTriggered: {
      switch (steps.step) {
      case 0:
        harness.require(!card.weatherReady && harness.shader() === undefined, "missing data must not load precipitation");
        harness.require(harness.items(card, item => item.running !== undefined && item.running).length > 0, "missing data shows busy indicator");
        harness.setLocation("name", "Dallas, Texas, US");
        harness.publish(0);
        break;
      case 1:
        const clear = harness.texts();
        harness.require(clear.includes("Dallas") && clear.includes("13°C") && clear.includes("(UTC)"), "current city/temperature/timezone");
        harness.require(clear.includes("Sun") && clear.includes("Mon") && !clear.includes("Tue"), "forecastDays caps date delegates");
        harness.require(clear.includes("20°/10°") && clear.includes("15°/4°"), "forecast max/min rounding");
        harness.require(harness.shader() === undefined, "clear weather must not load effects");
        harness.setLocation("useFahrenheit", true);
        harness.publish(61);
        break;
      case 2:
        const rain = harness.texts();
        harness.require(rain.includes("55°F") && rain.includes("69°/49°") && rain.includes("58°/40°"), "current/forecast Fahrenheit conversion");
        harness.require(card.isRaining && !card.isSnowing, "rain condition code");
        harness.require(harness.shader().fragmentShader.toString().endsWith("weather_rain.frag.qsb") && harness.shader().source.hideSource, "rain shader hides source");
        steps.sampledTime = harness.shader().time;
        break;
      case 3:
        harness.require(harness.shader().time > steps.sampledTime, "rain uniform progresses");
        harness.publish(71);
        card.forecastDays = 6;
        card.showLocation = false;
        break;
      case 4:
        harness.require(card.isSnowing && !card.isRaining, "snow condition code");
        harness.require(harness.shader().fragmentShader.toString().endsWith("weather_snow.frag.qsb") && !harness.shader().source.hideSource, "snow shader preserves source");
        harness.require(harness.texts().includes("Tue") && harness.texts().includes("30°/23°"), "forecast expands up to available days");
        harness.require(!harness.texts().includes("Dallas") && !harness.texts().includes("(UTC)"), "location toggle hides city/timezone");
        steps.sampledTime = harness.shader().time;
        break;
      case 5:
        harness.require(harness.shader().time > steps.sampledTime, "snow uniform progresses after switch");
        card.showEffects = false;
        break;
      case 6:
        harness.require(harness.shader() === undefined, "effects disabled unloads shader");
        card.showEffects = true;
        break;
      case 7:
        harness.require(harness.shader() !== undefined, "effects reenabled reloads shader");
        harness.publish(0);
        break;
      case 8:
        harness.require(harness.shader() === undefined && !card.isRaining && !card.isSnowing, "clear condition unloads precipitation");
        LocationService.data = {
          weather: null
        };
        break;
      case 9:
        harness.require(!card.weatherReady && !harness.texts().includes("55°F") && !harness.texts().includes("Sun"), "cleared data removes weather and forecast delegates");
        harness.setLocation("weatherEnabled", false);
        break;
      case 10:
        harness.require(!card.visible, "weather setting hides card");
        console.log("WEATHER_CARD_BEHAVIOR_PASS", "11 transition rows");
        Qt.quit();
        break;
      }
      steps.step++;
    }
  }
}
