import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Panels.SetupWizard

ShellRoot {
  id: harness
  property var step: null
  property int caseIndex: 0
  property bool reordered: false
  property var positions: []
  property var ratios: []
  readonly property var cases: [
    {
      width: 480,
      scale: 1
    },
    {
      width: 480,
      scale: 1.25
    },
    {
      width: 1000,
      scale: 1
    },
    {
      width: 1000,
      scale: 1.25
    }
  ]

  Window {
    id: window
    visible: true
    width: 1000
    height: 720
  }

  Component {
    id: customize
    SetupCustomizeStep {}
  }

  function assertValue(actual, expected, label) {
    if (actual !== expected)
      throw new Error(label + ": " + actual + " != " + expected);
  }

  function findItems(item, predicate) {
    let result = predicate(item) ? [item] : [];
    for (const child of item.children)
      result = result.concat(findItems(child, predicate));
    return result;
  }

  function click(item) {
    const mice = findItems(item, child => child.containsMouse !== undefined && typeof child.clicked === "function");
    assertValue(mice.length, 1, "click target count");
    mice[0].clicked(null);
  }

  function assertSelection(keys, selected, label) {
    const tiles = findItems(step, item => keys.includes(item.key));
    assertValue(tiles.length, 4, label + " delegate count");
    for (const tile of tiles) {
      assertValue(tile.isActive, tile.key === selected, label + " active " + tile.key);
      const texts = findItems(tile, item => item.text === tile.name);
      assertValue(texts.length, 1, label + " label " + tile.key);
      assertValue(String(texts[0].color), String(tile.isActive ? NColor.mOnPrimary : NColor.mOnSurface), label + " text color " + tile.key);
    }
    return tiles;
  }

  function exerciseSelections() {
    const positionKeys = ["top", "bottom", "left", "right"];
    const densityKeys = ["mini", "compact", "default", "comfortable"];
    const positionTiles = assertSelection(positionKeys, step.selectedBarPosition, "position");
    for (const tile of positionTiles) {
      const count = positions.length;
      click(tile);
      assertValue(step.selectedBarPosition, tile.key, "position click value");
      assertValue(positions.length, count + 1, "position signal count");
      assertValue(positions[count], tile.key, "position signal payload");
      assertSelection(positionKeys, tile.key, "position click");
    }
    const densityTiles = assertSelection(densityKeys, Settings.data.bar.density, "density");
    for (const tile of densityTiles) {
      click(tile);
      assertValue(Settings.data.bar.density, tile.key, "density setting");
      assertSelection(densityKeys, tile.key, "density click");
    }
    step.selectedBarPosition = "left";
    Settings.data.bar.density = "compact";
    assertSelection(positionKeys, "left", "external position");
    assertSelection(densityKeys, "compact", "external density");
    assertValue(Settings.saveRequests, 0, "no persistence");
  }

  function exerciseForm() {
    const sliders = findItems(step, item => item.textSize !== undefined && typeof item.moved === "function");
    assertValue(sliders.length, 3, "slider count");
    const scale = sliders.find(item => item.from === 0.8);
    assertValue(scale.value, 1, "initial scale");
    for (const value of [0.8, 1.05, 1.2]) {
      const count = ratios.length;
      scale.moved(value);
      assertValue(step.selectedScaleRatio, value, "scale selection");
      assertValue(scale.value, value, "scale binding");
      assertValue(scale.text, Math.floor(value * 100) + "%", "scale text");
      assertValue(ratios.length, count + 1, "scale signal count");
      assertValue(ratios[count], value, "scale signal payload");
    }
    assertValue(Settings.data.general.scaleRatio, cases[caseIndex].scale, "scale stays draft");
    const opacity = sliders.filter(item => item.from === 0);
    assertValue(opacity.length, 2, "opacity slider count");
    for (const value of [0, 0.37, 1]) {
      opacity[0].moved(value);
      assertValue(Settings.data.bar.backgroundOpacity, value, "background setting");
      assertValue(opacity[0].value, value, "background binding");
      assertValue(opacity[0].text, Math.floor(value * 100) + "%", "background text");
      opacity[1].moved(value);
      assertValue(Settings.data.general.dimmerOpacity, value, "dimmer setting");
      assertValue(opacity[1].value, value, "dimmer binding");
      assertValue(opacity[1].text, Math.floor(value * 100) + "%", "dimmer text");
    }
    const toggles = findItems(step, item => typeof item.toggled === "function" && item.baseSize !== undefined);
    assertValue(toggles.length, 2, "toggle count");
    for (const checked of [true, false, true]) {
      click(toggles[0]);
      assertValue(Settings.data.bar.floating, checked, "floating setting");
      assertValue(toggles[0].checked, checked, "floating binding");
      click(toggles[1]);
      assertValue(Settings.data.general.enableShadows, checked, "shadows setting");
      assertValue(toggles[1].checked, checked, "shadows binding");
    }
  }

  function reorderModels() {
    const repeaters = findItems(step, item => typeof item.itemAt === "function" && item.model !== undefined);
    assertValue(repeaters.length, 2, "repeater count");
    for (const repeater of repeaters)
      repeater.model = Array.from(repeater.model).reverse();
  }

  function assertReorderedModels() {
    const repeaters = findItems(step, item => typeof item.itemAt === "function" && item.model !== undefined);
    const orders = [["right", "left", "bottom", "top"], ["comfortable", "default", "compact", "mini"]];
    for (let group = 0; group < repeaters.length; group++) {
      for (let index = 0; index < orders[group].length; index++)
        assertValue(repeaters[group].itemAt(index).key, orders[group][index], "reordered key " + group + ":" + index);
    }
  }

  function startCase() {
    const scenario = cases[caseIndex];
    Settings.data.general.scaleRatio = scenario.scale;
    Settings.data.general.animationDisabled = true;
    Settings.data.bar.density = "default";
    Settings.data.bar.floating = false;
    Settings.data.general.enableShadows = false;
    positions = [];
    ratios = [];
    window.width = scenario.width;
    step = customize.createObject(window.contentItem, {
      width: scenario.width,
      height: 720
    });
    if (!step)
      throw new Error("Customization component did not instantiate");
    step.barPositionChanged.connect(position => positions.push(position));
    step.scaleRatioChanged.connect(ratio => ratios.push(ratio));
    reordered = false;
  }

  Component.onCompleted: {
    if (Quickshell.env("QT_QPA_PLATFORM") !== "offscreen")
      throw new Error("Customization harness requires offscreen platform");
    startCase();
  }

  Timer {
    interval: 300
    running: true
    repeat: true
    onTriggered: {
      try {
        if (!harness.reordered) {
          harness.exerciseSelections();
          harness.exerciseForm();
          harness.reorderModels();
          harness.reordered = true;
          return;
        }
        harness.assertReorderedModels();
        harness.assertSelection(["top", "bottom", "left", "right"], "left", "reordered position");
        harness.assertSelection(["mini", "compact", "default", "comfortable"], "compact", "reordered density");
        harness.exerciseSelections();
        harness.step.destroy();
        harness.caseIndex++;
        if (harness.caseIndex === harness.cases.length) {
          console.log("PASS customize: 4 width/scale cases");
          Qt.quit();
        } else {
          harness.startCase();
        }
      } catch (error) {
        console.error(error.message + "\n" + error.stack);
        Qt.quit();
      }
    }
  }
}
