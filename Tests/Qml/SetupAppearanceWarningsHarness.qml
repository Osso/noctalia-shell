import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import qs.Modules.Panels.SetupWizard
import qs.Services.Theming

ShellRoot {
  id: harness
  property var step: null
  property int caseIndex: 0
  property int phase: 0
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
    id: appearance
    SetupAppearanceStep {}
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

  function startCase() {
    const scenario = cases[caseIndex];
    Settings.data.general.scaleRatio = scenario.scale;
    Settings.data.general.animationDisabled = true;
    Settings.data.colorSchemes.useWallpaperColors = false;
    Settings.data.colorSchemes.darkMode = true;
    window.width = scenario.width;
    step = appearance.createObject(window.contentItem, {
                                     width: scenario.width,
                                     height: 720
                                   });
    if (!step)
      throw new Error("Appearance component did not instantiate");
    phase = 0;
  }

  function assertSchemes(surface, primary) {
    const tiles = findItems(step, item => item.schemeName !== undefined);
    assertValue(tiles.length, 4, "scheme delegate count");
    for (const name of ["Rose Pine", "Nord", "Catppuccin"]) {
      const tile = tiles.find(item => item.schemeName === name);
      if (!tile)
        throw new Error("Missing scheme delegate: " + name);
      assertValue(String(tile.color), surface, "loaded tile surface " + name);
      assertValue(step.getSchemeColor(name, "mPrimary"), primary, "cache primary " + name);
      const swatches = findItems(tile, item => item.width === 14 && item.color !== undefined);
      assertValue(swatches.length, 4, "swatch count " + name);
      assertValue(String(swatches[0].color), primary, "primary swatch " + name);
      const labels = findItems(tile, item => item.text === name);
      assertValue(labels.length, 1, "scheme label " + name);
    }
    assertValue(Object.keys(step.schemeColorsCache.Broken).length, 0, "invalid JSON empty cache");
  }

  function exerciseSchemeClicks() {
    const tiles = findItems(step, item => item.schemeName !== undefined);
    for (const tile of tiles) {
      const mouse = findItems(tile, item => item.containsMouse !== undefined && typeof item.clicked === "function")[0];
      mouse.clicked(null);
      assertValue(Settings.data.colorSchemes.predefinedScheme, tile.schemeName, "scheme click setting");
      assertValue(ColorSchemeService.appliedScheme, tile.schemeName, "scheme click application");
      assertValue(Settings.data.colorSchemes.useWallpaperColors, false, "scheme click color source");
    }
  }

  function exerciseMatugenClicks() {
    const tiles = findItems(step, item => item.key !== undefined && item.name !== undefined);
    assertValue(tiles.length, 8, "matugen delegate count");
    const generations = AppThemeService.generations;
    for (const tile of tiles) {
      const mouse = findItems(tile, item => item.cursorShape !== undefined && typeof item.clicked === "function")[0];
      mouse.clicked(null);
      assertValue(Settings.data.colorSchemes.matugenSchemeType, tile.key, "matugen click key");
      assertValue(tile.isActive, true, "matugen active state");
      assertValue(findItems(tile, item => item.text === tile.name).length, 1, "matugen label");
    }
    assertValue(AppThemeService.generations, generations + 8, "generation count");
    const version = step.cacheVersion;
    ColorSchemeService.schemes = ColorSchemeService.schemes.slice();
    assertValue(step.cacheVersion, version + 1, "cache invalidation version");
    assertValue(Object.keys(step.schemeColorsCache).length, 0, "cache invalidation contents");
  }

  Component.onCompleted: {
    if (Quickshell.env("QT_QPA_PLATFORM") !== "offscreen")
      throw new Error("Appearance harness requires offscreen platform");
    startCase();
  }

  Timer {
    interval: 500
    running: true
    repeat: true
    onTriggered: {
      try {
        if (harness.phase === 0) {
          harness.assertSchemes("#123456", "#abcdef");
          Settings.data.colorSchemes.darkMode = false;
          harness.phase = 1;
          return;
        }
        if (harness.phase === 1) {
          harness.assertSchemes("#654321", "#fedcba");
          harness.exerciseSchemeClicks();
          Settings.data.colorSchemes.useWallpaperColors = true;
          harness.phase = 2;
          return;
        }
        harness.exerciseMatugenClicks();
        harness.step.destroy();
        harness.caseIndex++;
        if (harness.caseIndex === harness.cases.length) {
          console.log("PASS appearance: 4 width/scale cases");
          Qt.quit();
        } else {
          harness.startCase();
        }
      } catch (error) {
        console.error(error.stack);
        Qt.quit();
      }
    }
  }
}
