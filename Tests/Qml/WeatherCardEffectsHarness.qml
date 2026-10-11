import QtQuick
import QtQuick.Window
import Quickshell
import qs.Modules.Cards

ShellRoot {
  Window {
    width: 400
    height: 300
    visible: true // Runner requires offscreen; no desktop connection exists.

    WeatherCard {
      id: card
      anchors.fill: parent
      showEffects: false
    }
  }

  // Inspect live objects without adding test-only APIs to WeatherCard.
  function findProperty(item, propertyName) {
    if (item[propertyName] !== undefined) {
      return item;
    }
    for (const child of item.children) {
      const found = findProperty(child, propertyName);
      if (found !== null) {
        return found;
      }
    }
    return null;
  }

  function effect() {
    return findProperty(card, "fragmentShader");
  }

  function require(condition, message) {
    if (!condition) {
      console.error("WEATHER_EFFECTS_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  Timer {
    interval: 100
    running: true
    repeat: true
    property int step: 0
    property int conditionIndex: 0
    property real sampledTime: 0
    readonly property string condition: conditionIndex === 0 ? "rain" : "snow"

    onTriggered: {
      switch (step) {
      case 0:
        card.testEffects = condition;
        require(effect() === null, "disabled effects must not load");
        card.showEffects = true;
        break;
      case 1:
        const shader = effect();
        require(shader !== null, condition + " effect must load");
        require(shader.fragmentShader.toString().endsWith("weather_" + condition + ".frag.qsb"), "wrong shader");
        require(shader.source.hideSource === (condition === "rain"), "wrong content hiding");
        require(shader.source.sourceItem !== null, "content source must exist");
        require(shader.width > 0 && shader.height > 0, "effect must have dimensions");
        require(isFinite(shader.time), "uniform must be finite");
        sampledTime = shader.time;
        break;
      case 2:
      case 3:
        require(effect().time > sampledTime, condition + " shader uniform must keep advancing");
        console.log("WEATHER_EFFECT_PROOF", condition, sampledTime, effect().time);
        sampledTime = effect().time;
        if (step === 3) {
          card.showEffects = false;
        }
        break;
      case 4:
        require(effect() === null, "disabling effects must unload");
        card.showEffects = true;
        break;
      case 5:
        require(effect() !== null, "effect must reload");
        sampledTime = effect().time;
        break;
      case 6:
        require(effect().time > sampledTime, "reloaded effect must animate");
        card.testEffects = "";
        break;
      case 7:
        require(effect() === null, "clear weather must unload");
        if (conditionIndex === 0) {
          card.showEffects = false;
          conditionIndex = 1;
          step = -1;
        } else {
          card.testEffects = "rain";
        }
        break;
      case 8:
        require(effect() !== null, "rain must load before switching to snow");
        card.testEffects = "snow";
        break;
      case 9:
        require(effect().fragmentShader.toString().endsWith("weather_snow.frag.qsb"), "rain-to-snow must update shader");
        require(effect().source.hideSource === false, "snow must not hide content");
        sampledTime = effect().time;
        break;
      case 10:
        require(effect().time > sampledTime, "switched effect must animate");
        console.log("WEATHER_EFFECTS_PASS");
        Qt.quit();
        break;
      }
      step++;
    }
  }
}
