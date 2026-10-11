import QtQuick
import Quickshell
import qs.Commons

ShellRoot {
  id: root

  property bool initialColorsLoaded: false

  Timer {
    interval: 50
    repeat: true
    running: true
    onTriggered: {
      if (!root.initialColorsLoaded) {
        const initialColorsMatch = Qt.colorEqual(NColor.mPrimary, "#123456") && Qt.colorEqual(NColor.mOnSurface, "#80402010");
        if (initialColorsMatch) {
          root.initialColorsLoaded = true;
          console.log("COLOR_FILE_LOAD_PASS");
        }
        return;
      }

      const reloadedColorsMatch = Qt.colorEqual(NColor.mPrimary, "#abcdef") && Qt.colorEqual(NColor.mOnSurface, "#40203040");
      if (!reloadedColorsMatch) {
        return;
      }
      const unchangedDefaultMatches = Qt.colorEqual(NColor.mSecondary, "#a984c4");
      const absoluteColorsMatch = NColor.transparent.a === 0 && Qt.colorEqual(NColor.black, "#000000") && Qt.colorEqual(NColor.white, "#ffffff");
      if (!unchangedDefaultMatches || !absoluteColorsMatch) {
        console.error("COLOR_FILE_FAIL: defaults and absolute colors must survive custom reload");
        Qt.exit(1);
        return;
      }
      console.log("COLOR_FILE_RELOAD_PASS");
      Qt.quit();
    }
  }

  Timer {
    interval: 10000
    running: true
    onTriggered: {
      console.error("COLOR_FILE_FAIL: timed out loading or reloading custom colors");
      Qt.exit(1);
    }
  }
}
