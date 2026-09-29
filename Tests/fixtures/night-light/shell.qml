import QtQuick
import Quickshell
import qs.Commons
import qs.Services.Location

ShellRoot {
  id: root
  Component.onCompleted: {
    NightLightService.apply();
    if ("TEST_MODE" === "disabled") {
      disableTimer.start();
    }
    if ("TEST_MODE" === "latest") {
      latestTimer.start();
    }
    if ("TEST_MODE" === "unchanged") {
      unchangedTimer.start();
    }
  }

  Timer {
    id: disableTimer
    interval: 75
    onTriggered: Settings.data.nightLight.enabled = false
  }
  Timer {
    id: latestTimer
    interval: 75
    onTriggered: {
      Settings.data.nightLight.nightTemp = 4200;
      Settings.data.nightLight.nightTemp = 3200;
    }
  }
  Timer {
    id: unchangedTimer
    interval: 900
    onTriggered: NightLightService.apply()
  }
}
