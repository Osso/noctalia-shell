import QtQuick
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.UI

ShellRoot {
  id: root

  readonly property var panelNames: ["audioPanel", "batteryPanel", "bluetoothPanel", "brightnessPanel", "clockPanel", "controlCenterPanel", "changelogPanel", "launcherPanel", "notificationHistoryPanel", "sessionMenuPanel", "settingsPanel", "setupWizardPanel", "trayDrawerPanel", "wallpaperPanel", "wifiPanel", "vpnPanel", "processPanel"]

  MainScreen {
    id: mainScreen
    screen: Quickshell.screens[0]
    visible: false
  }

  Connections {
    target: Quickshell
    function onReloadCompleted() {
      Quickshell.inhibitReloadPopup();
    }
  }

  Timer {
    id: probe
    property int panelIndex: 0
    property int phase: 0
    interval: 50
    running: true
    repeat: true

    function check(condition, message) {
      if (!condition)
        throw new Error("REGION_ASSERT: " + message);
    }

    function findPaths() {
      const container = mainScreen.contentItem.children[0];
      const backgrounds = container.children[0];
      return Array.from(backgrounds.children[0].children[0].data).filter(entry => entry.hasOwnProperty("backgroundColor"));
    }

    function updateBarSettings(changes) {
      // The fixture stores plain JSON; replace data to emit its notify signal.
      Settings.data = Object.assign({}, Settings.data, {
        bar: Object.assign({}, Settings.data.bar, changes)
      });
    }

    function checkBar(paths) {
      const bar = paths[0].bar;
      const corners = ["topLeftCornerState", "topRightCornerState", "bottomRightCornerState", "bottomLeftCornerState"];
      const expected = {
        top: [-1, -1, 2, 2],
        bottom: [2, 2, -1, -1],
        left: [-1, 1, 1, -1],
        right: [1, -1, -1, 1]
      };
      updateBarSettings({
        outerCorners: true
      });
      for (const position of ["top", "bottom", "left", "right"]) {
        updateBarSettings({
          position: position,
          floating: false
        });
        for (let index = 0; index < corners.length; index++)
          check(bar[corners[index]] === expected[position][index], position + " " + corners[index]);
        check(paths[0].barWidth === bar.width && paths[0].barHeight === bar.height, "bar geometry " + position);
        updateBarSettings({
          floating: true
        });
        for (const corner of corners)
          check(bar[corner] === 0, "floating " + corner);
      }
      updateBarSettings({
        position: "top",
        floating: false
      });
      console.log("REGION_BAR_STATES_PASS");
    }

    onTriggered: {
      const paths = findPaths();
      check(paths.length === 18, "bar and 17 panel paths");
      if (panelIndex === root.panelNames.length) {
        checkBar(paths);
        running = false;
        console.log("REGION_RESOLUTION_READY");
        return;
      }
      const name = root.panelNames[panelIndex];
      const key = name + "-" + mainScreen.screenName;
      const loader = PanelService.loaders[key];
      check(loader !== undefined, "registered " + name);
      if (phase === 0) {
        const inactive = mainScreen[name + "Placeholder"];
        check(!inactive.visible && inactive.width === 0 && inactive.height === 0, "inactive " + name);
        loader.active = true;
        loader.item.open();
        phase = 1;
        return;
      }
      if (phase === 1) {
        const panel = loader.item;
        if (!panel.isPanelVisible || panel.panelRegion.width === 0 || panel.panelRegion.height === 0)
          return;
        const region = mainScreen[name + "Placeholder"];
        check(region === panel.panelRegion, "active region identity " + name);
        const path = paths[panelIndex + 1];
        check(path.panel === region, "caller region identity " + name);
        check(path.panelWidth === region.width && path.panelHeight === region.height, "active geometry " + name);
        check(path.panelX === region.x && path.panelY === region.y, "active position " + name);
        check(path.tlRadius === path.effectiveRadius && path.tlMultX === -1, "top attachment inversion " + name);
        panel.close();
        // Hidden windows do not tick render-driven close animations.
        // Exercise the real completion boundary without claiming animation proof.
        panel.finalizeClose();
        phase = 2;
        return;
      }
      if (loader.item.isClosing || loader.item.isPanelOpen)
        return;
      check(paths[panelIndex + 1].panelWidth === 0, "closed geometry " + name);
      loader.active = false;
      check(!mainScreen[name + "Placeholder"].visible, "inactive after unload " + name);
      console.log("REGION_CALLER_PASS", name);
      panelIndex++;
      phase = 0;
    }
  }
}
