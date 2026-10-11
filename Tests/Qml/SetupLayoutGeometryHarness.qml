import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Panels.SetupWizard

ShellRoot {
  id: harness
  property int caseIndex: 0
  property var snapshots: []
  property var cases: []
  property var step: null
  property var wizard: null

  Component {
    id: appearance
    SetupAppearanceStep {}
  }
  Component {
    id: customize
    SetupCustomizeStep {}
  }
  Component {
    id: dock
    SetupDockStep {}
  }
  Component {
    id: wizardComponent
    SetupWizard {}
  }

  // Only the offscreen platform may polish this window; no desktop connection exists.
  Window {
    id: window
    visible: true
    width: 1000
    height: 720
  }

  function startCase() {
    const scenario = cases[caseIndex];
    Settings.data.general.scaleRatio = scenario.scale;
    Settings.data.colorSchemes.useWallpaperColors = scenario.wallpaper;
    window.width = scenario.width;
    const dimensions = {
      width: scenario.width,
      height: 720
    };
    if (scenario.component === "wizard") {
      wizard = wizardComponent.createObject(window.contentItem);
      if (!wizard)
        throw new Error("SetupWizard did not instantiate");
      step = wizard.panelContent.createObject(window.contentItem, dimensions);
    } else {
      const component = scenario.component === "appearance" ? appearance : scenario.component === "customize" ? customize : dock;
      step = component.createObject(window.contentItem, dimensions);
    }
    if (!step)
      throw new Error("Production component did not instantiate: " + scenario.component);
  }

  function measure(item) {
    const geometry = {
      x: item.x,
      y: item.y,
      width: item.width,
      height: item.height,
      visible: item.visible,
      enabled: item.enabled
    };
    if (item.text !== undefined)
      geometry.text = item.text;
    if (item.radius !== undefined)
      geometry.radius = item.radius;
    if (item.color !== undefined)
      geometry.color = String(item.color);
    geometry.children = [];
    for (let i = 0; i < item.children.length; i++)
      geometry.children.push(measure(item.children[i]));
    return geometry;
  }

  Component.onCompleted: {
    if (Quickshell.env("QT_QPA_PLATFORM") !== "offscreen")
      throw new Error("Geometry harness requires offscreen platform");
    // Wallpaper content uses a stable inert directory label, not a random HOME path.
    Settings.data.wallpaper.directory = "/nonexistent/noctalia-geometry-wallpapers";
    Settings.data.ui.fontDefault = "DejaVu Sans";
    Settings.data.general.animationDisabled = true;
    for (const name of ["appearance", "customize", "dock", "wizard"]) {
      for (const width of [480, 1000]) {
        for (const scale of [1, 1.25]) {
          const wallpaperModes = name === "appearance" ? [false, true] : [false];
          for (const wallpaper of wallpaperModes)
            cases.push({
              component: name,
              width: width,
              scale: scale,
              wallpaper: wallpaper
            });
        }
      }
    }
    startCase();
  }

  Timer {
    interval: 500
    running: true
    repeat: true
    onTriggered: {
      try {
        snapshots.push({
          scenario: cases[caseIndex],
          tree: measure(step)
        });
        step.destroy();
        if (wizard) {
          wizard.destroy();
          wizard = null;
        }
        caseIndex++;
        if (caseIndex === cases.length) {
          console.log("SETUP_GEOMETRY " + JSON.stringify(snapshots));
          Qt.quit();
        } else {
          startCase();
        }
      } catch (error) {
        console.error("SETUP_GEOMETRY_FAIL " + error);
        Qt.exit(1);
      }
    }
  }
}
