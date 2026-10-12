import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons

ShellRoot {
  id: root

  Connections {
    target: NColor
    function onFileLoaded() {
      // Let FileView finish clearing the completed operation before teardown.
      Qt.callLater(root.verifyPalette);
    }
    function onFileSaved() {
      // Creation completes at saved; watcher reload may run during the write.
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
      anchors.fill: parent
      color: NColor.mOnSurface
    }
  }

  function verifyPalette() {
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
      Qt.quit();
    }
  }

  Timer {
    interval: 10000
    running: true
    onTriggered: {
      console.error("COLOR_NAMESPACE_FAIL: timed out waiting for file load or save completion");
      Qt.exit(1);
    }
  }
}
