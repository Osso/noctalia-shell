import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Panels.SetupWizard
import qs.Services.UI

ShellRoot {
  id: harness
  property int caseIndex: 0
  property var snapshots: []
  property var cases: []
  property var step: null
  property var wizard: null
  readonly property bool transitions: Quickshell.env("NOCTALIA_TEST_TRANSITIONS") === "1"
  readonly property var route: [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4]
  property int routeIndex: 0

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
      if (transitions) {
        routeIndex = 0;
        Settings.data.bar.position = "top";
        wizard.opened();
        assertValue(wizard.selectedScaleRatio, scenario.scale, "opened scale");
        assertValue(wizard.selectedBarPosition, "top", "opened bar");
      }
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

  function assertValue(actual, expected, label) {
    if (actual !== expected)
      throw new Error(label + ": " + actual + " != " + expected);
  }

  function findItem(item, predicate) {
    if (predicate(item))
      return item;
    for (const child of item.children) {
      const found = findItem(child, predicate);
      if (found)
        return found;
    }
    return null;
  }

  function clickButton(label) {
    const button = findItem(step, item => item.text === label && typeof item.clicked === "function");
    if (!button || !button.visible)
      throw new Error("Missing visible button: " + label);
    button.clicked();
  }

  function exerciseValues() {
    if (wizard.currentStep === 1) {
      const wallpaper = findItem(step, item => item.selectedDirectory !== undefined);
      wallpaper.directoryChanged("/nonexistent/noctalia-transition-wallpapers");
      const image = Quickshell.shellDir + "/Assets/noctalia.svg";
      wallpaper.wallpaperChanged(image);
      assertValue(wizard.selectedWallpaperDirectory, "/nonexistent/noctalia-transition-wallpapers", "directory handoff");
      assertValue(Settings.data.wallpaper.directory, wizard.selectedWallpaperDirectory, "directory applied");
      assertValue(wizard.selectedWallpaper, image, "wallpaper handoff");
      assertValue(WallpaperService.appliedWallpaper, image, "wallpaper applied");
    }
    if (wizard.currentStep === 3) {
      const customizeStep = findItem(step, item => item.selectedBarPosition !== undefined);
      customizeStep.scaleRatioChanged(cases[caseIndex].scale);
      customizeStep.barPositionChanged("bottom");
      assertValue(wizard.selectedScaleRatio, cases[caseIndex].scale, "scale handoff");
      assertValue(Settings.data.general.scaleRatio, wizard.selectedScaleRatio, "scale applied");
      assertValue(wizard.selectedBarPosition, "bottom", "bar handoff");
      assertValue(Settings.data.bar.position, "bottom", "bar applied");
    }
  }

  function exerciseCompletion() {
    const saves = Settings.saveRequests;
    wizard.onEscapePressed();
    assertValue(Settings.saveRequests, saves, "escape does not save");
    assertValue(wizard.isCompleting, false, "escape does not complete");
    wizard.close();
    assertValue(Settings.saveRequests, saves, "cancel does not save");
    wizard.opened();
    clickButton("All Done!");
    assertValue(Settings.saveRequests, saves + 1, "finish saves once");
    assertValue(wizard.isCompleting, true, "finish waits for confirmation");
    wizard.completeSetup();
    assertValue(Settings.saveRequests, saves + 1, "duplicate finish ignored");
    Settings.settingsSaved();
    assertValue(wizard.isCompleting, false, "confirmation clears completion");
    wizard.currentStep = 0;
    clickButton("Skip Setup");
    assertValue(Settings.saveRequests, saves + 2, "skip saves once");
    Settings.settingsSaved();
    assertValue(wizard.isCompleting, false, "skip confirmation clears completion");
  }

  Component.onCompleted: {
    if (Quickshell.env("QT_QPA_PLATFORM") !== "offscreen")
      throw new Error("Geometry harness requires offscreen platform");
    // Wallpaper content uses a stable inert directory label, not a random HOME path.
    Settings.data.wallpaper.directory = "/nonexistent/noctalia-geometry-wallpapers";
    Settings.data.ui.fontDefault = "DejaVu Sans";
    Settings.data.general.animationDisabled = true;
    for (const name of transitions ? ["wizard"] : ["appearance", "customize", "dock", "wizard"]) {
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
        if (transitions) {
          assertValue(wizard.currentStep, route[routeIndex], "navigation step");
          exerciseValues();
          snapshots.push({
            scenario: cases[caseIndex],
            step: wizard.currentStep,
            tree: measure(step)
          });
          if (routeIndex < route.length - 1) {
            const next = route[routeIndex + 1];
            clickButton(next > wizard.currentStep ? "Continue →" : "← Back");
            assertValue(wizard.currentStep, next, "button transition");
            routeIndex++;
            return;
          }
          exerciseCompletion();
        } else {
          snapshots.push({
            scenario: cases[caseIndex],
            tree: measure(step)
          });
        }
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
