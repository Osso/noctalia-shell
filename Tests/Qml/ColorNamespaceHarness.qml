import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons

ShellRoot {
  id: root

  readonly property bool testReloadAfterCreation: Quickshell.env("COLOR_TEST_RELOAD_AFTER_CREATION") === "1"
  property bool waitingForExternalReload: false

  Connections {
    target: NColor
    function onFileLoaded() {
      // Let FileView finish clearing the completed operation before teardown.
      Qt.callLater(root.verifyPalette);
    }
  }

  Window {
    id: window
    width: 16
    height: 16
    visible: true // The runner forces the offscreen platform; no desktop surface.
    color: NColor.transparent

    Rectangle {
      id: paletteRectangle
      anchors.fill: parent
      color: NColor.mOnSurface
    }
  }

  function verifyPalette() {
    if (root.waitingForExternalReload) {
      root.verifyExternalColors();
      return;
    }
    console.log("COLOR_NAMESPACE_PROOF", "windowAlpha=" + window.color.a, "onSurface=" + NColor.mOnSurface, "transparentType=" + typeof NColor.transparent);
    const windowIsTransparent = window.color.a === 0;
    const defaults = {
      mPrimary: "#c7a1d8",
      mOnPrimary: "#1a151f",
      mSecondary: "#a984c4",
      mOnSecondary: "#f3edf7",
      mTertiary: "#e0b7c9",
      mOnTertiary: "#20161f",
      mError: "#e9899d",
      mOnError: "#1e1418",
      mSurface: "#1c1822",
      mOnSurface: "#e9e4f0",
      mSurfaceVariant: "#262130",
      mOnSurfaceVariant: "#a79ab0",
      mOutline: "#342c42",
      mShadow: "#120f18",
      mHover: "#e0b7c9",
      mOnHover: "#20161f"
    };
    for (const name of Object.keys(defaults)) {
      if (!Qt.colorEqual(NColor[name], defaults[name]) || NColor[name].a !== 1) {
        console.error("COLOR_NAMESPACE_FAIL", name, NColor[name]);
        Qt.exit(1);
        return;
      }
    }
    const defaultPaletteIsCorrect = Qt.colorEqual(NColor.black, "#000000") && Qt.colorEqual(NColor.white, "#ffffff");
    const transparentIsNotFunction = typeof NColor.transparent !== "function";
    const paletteResolved = windowIsTransparent && defaultPaletteIsCorrect && transparentIsNotFunction;
    if (!paletteResolved) {
      console.error("COLOR_NAMESPACE_FAIL: project palette must resolve and window must remain transparent");
      Qt.exit(1);
    } else {
      console.log("COLOR_NAMESPACE_PASS");
      if (root.testReloadAfterCreation) {
        root.waitingForExternalReload = true;
      } else {
        Qt.quit();
      }
    }
  }

  function verifyExternalColors() {
    const customColorsMatch = Qt.colorEqual(NColor.mPrimary, "#abcdef") && Qt.colorEqual(NColor.mOnSurface, "#40203040");
    if (!customColorsMatch) {
      return;
    }
    const unchangedDefaultMatches = Qt.colorEqual(NColor.mSecondary, "#a984c4");
    const absoluteColorsMatch = NColor.transparent.a === 0 && Qt.colorEqual(NColor.black, "#000000") && Qt.colorEqual(NColor.white, "#ffffff");
    const windowMatches = window.color.a === 0 && Qt.colorEqual(paletteRectangle.color, "#40203040");
    if (!unchangedDefaultMatches || !absoluteColorsMatch || !windowMatches) {
      console.error("COLOR_FILE_FAIL: defaults, transparency and rendering must survive formerly-missing reload");
      Qt.exit(1);
      return;
    }
    // Keep observing after reload so write loops cannot hide behind early exit.
    settledTimer.start();
  }

  Timer {
    id: settledTimer
    interval: 250
    onTriggered: {
      console.log("COLOR_MISSING_FILE_RELOAD_PASS");
      Qt.quit();
    }
  }

  Timer {
    interval: 10000
    running: true
    onTriggered: {
      console.error("COLOR_NAMESPACE_FAIL: timed out waiting for file load completion");
      Qt.exit(1);
    }
  }
}
