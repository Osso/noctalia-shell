import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons

ShellRoot {
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

  Timer {
    interval: 100
    running: true
    onTriggered: {
      console.log("COLOR_NAMESPACE_PROOF", "windowAlpha=" + window.color.a, "onSurface=" + NColor.mOnSurface, "transparentType=" + typeof NColor.transparent);
      const windowIsTransparent = window.color.a === 0;
      const defaultPaletteIsCorrect = Qt.colorEqual(NColor.mOnSurface, "#e9e4f0");
      const transparentIsNotFunction = typeof NColor.transparent !== "function";
      if (!windowIsTransparent || !defaultPaletteIsCorrect || !transparentIsNotFunction) {
        console.error("COLOR_NAMESPACE_FAIL: project palette must resolve and window must remain transparent");
        Qt.exit(1);
      } else {
        console.log("COLOR_NAMESPACE_PASS");
        Qt.quit();
      }
    }
  }
}
