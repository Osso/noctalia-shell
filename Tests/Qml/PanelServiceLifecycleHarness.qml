import QtQuick
import Quickshell
import qs.Commons
import qs.Modules.MainScreen
import qs.Services.UI

ShellRoot {
  id: testRoot

  readonly property string initialPanelKey: "launcherPanel-eDP-1"
  property var screenOwner: null
  property int exitCode: 0
  property int phase: 0
  property int caseIndex: 0
  property int createdContent: 0
  property int destroyedContent: 0
  property int openedCount: 0
  property int closedCount: 0
  property int phaseTicks: 0
  property real contentWidth: 280
  property real contentHeight: 180
  property var cases: []
  property var currentCase: null

  function verify(condition, message) {
    if (!condition) {
      console.error("FAIL PanelServiceLifecycle:", caseIndex, phase, message);
      exitCode = 1;
      Qt.exit(exitCode);
    }
  }

  function near(actual, expected, message) {
    verify(Math.abs(actual - expected) < 1, message + ": " + actual + " != " + expected);
  }

  function findLoader(item) {
    if (item.sourceComponent !== undefined)
      return item;
    for (const child of item.children) {
      const found = findLoader(child);
      if (found)
        return found;
    }
    return null;
  }

  function buildCases() {
    // Exercise branch-local positioning variables in both axes, including floating insets.
    for (const size of [[800, 600], [1920, 1080]]) {
      for (const bar of ["top", "bottom", "left", "right"]) {
        cases.push({
          width: size[0],
          height: size[1],
          bar: bar,
          mode: "center",
          attached: false,
          floating: false
        });
        cases.push({
          width: size[0],
          height: size[1],
          bar: bar,
          mode: "button",
          attached: true,
          floating: false
        });
        cases.push({
          width: size[0],
          height: size[1],
          bar: bar,
          mode: "edge",
          attached: true,
          floating: true
        });
      }
    }
    cases.push({
      width: 800,
      height: 600,
      bar: "top",
      mode: "earlyClose",
      attached: false,
      floating: false
    });
    cases.push({
      width: 800,
      height: 600,
      bar: "top",
      mode: "teardownOpen",
      attached: false,
      floating: false
    });
  }

  function beginCase() {
    currentCase = cases[caseIndex];
    Settings.data.bar.position = currentCase.bar;
    Settings.data.bar.floating = currentCase.floating;
    Settings.data.bar.marginHorizontal = 1;
    Settings.data.bar.marginVertical = 1;
    Settings.data.bar.backgroundOpacity = 1;
    Settings.data.bar.monitors = [];
    Settings.data.ui.panelsAttachedToBar = currentCase.attached;
    contentWidth = 280;
    contentHeight = 180;
    screenOwner = screenOwnerFactory.createObject(testRoot);
    const panel = screenOwner.panel;
    verify(PanelService.registeredPanels[initialPanelKey] === panel, "initial registration missing");
    verify(!panel.isPanelOpen && !panel.isPanelVisible, "initial state not closed");
    verify(findLoader(panel).item === null, "content loaded while closed");
    verify(createdContent === caseIndex, "unexpected eager content creation");
    panel.panelAnchorHorizontalCenter = currentCase.mode === "center";
    panel.panelAnchorVerticalCenter = currentCase.mode === "center";
    panel.panelAnchorLeft = currentCase.mode === "edge" && currentCase.bar === "left";
    panel.panelAnchorRight = currentCase.mode === "edge" && currentCase.bar !== "left";
    panel.panelAnchorTop = currentCase.mode === "edge" && currentCase.bar !== "bottom";
    panel.panelAnchorBottom = currentCase.mode === "edge" && currentCase.bar === "bottom";
    panel.open(currentCase.mode === "button" ? screenOwner.button : null);
    verify(panel.isPanelOpen && PanelService.openedPanel === panel, "open request not delivered");
    phase = 1;
    phaseTicks = 0;
  }

  function checkGeometry() {
    const panel = screenOwner.panel;
    const region = panel.panelRegion;
    const c = currentCase;
    const vertical = c.bar === "left" || c.bar === "right";
    const marginH = c.floating ? Style.marginXL : 0;
    const marginV = c.floating ? Style.marginXL : 0;
    let x;
    let y;
    if (c.mode === "center") {
      x = vertical ? (c.width - Style.barHeight - contentWidth) / 2 + (c.bar === "left" ? Style.barHeight : 0) : (c.width - contentWidth) / 2;
      y = vertical ? (c.height - contentHeight) / 2 : (c.height - Style.barHeight - contentHeight) / 2 + (c.bar === "top" ? Style.barHeight : 0);
    } else if (c.mode === "button") {
      x = vertical ? (c.bar === "left" ? Style.barHeight : c.width - Style.barHeight - contentWidth) : c.width / 2 + 20 - contentWidth / 2;
      y = vertical ? c.height / 2 + 10 - contentHeight / 2 : (c.bar === "top" ? Style.barHeight : c.height - Style.barHeight - contentHeight);
    } else {
      x = c.bar === "left" ? marginH + Style.barHeight : c.width - contentWidth - (vertical ? marginH + Style.barHeight : marginH + Style.radiusL * 2);
      y = c.bar === "bottom" ? c.height - marginV - Style.barHeight - contentHeight : (c.bar === "top" ? marginV + Style.barHeight : 0);
    }
    near(region.width, contentWidth, "content width");
    near(region.height, contentHeight, "content height");
    near(region.x, x, "horizontal placement");
    near(region.y, y, "vertical placement");
  }

  function closeCase() {
    const panel = screenOwner.panel;
    panel.close();
    verify(panel.isClosing && !panel.sizeAnimationComplete && !panel.closeFinalized, "closing state not entered");
    verify(panel.closeWatchdogActive && !panel.openWatchdogActive, "close watchdog state");
    phase = 3;
    phaseTicks = 0;
  }

  function teardownCase() {
    const panel = screenOwner.panel;
    screenOwner.screenName = "unknown";
    panel.screen = null;
    verify(panel.objectName === "launcherPanel-unknown", "screen-bound name did not change");
    if (currentCase.mode === "teardownOpen") {
      verify(panel.isPanelOpen && PanelService.openedPanel === panel, "teardown did not exercise an open panel");
      verify(findLoader(panel).item.contextMarker === "unknown", "loaded caller context did not follow screen name");
    }
    verify(panel.registrationKey === initialPanelKey, "registration key changed with output name");
    verify(PanelService.registeredPanels[initialPanelKey] === panel, "stable registration lost before teardown");
    screenOwner.destroy();
    screenOwner = null;
    phase = 4;
    phaseTicks = 0;
  }

  function advance() {
    if (!Settings.isLoaded)
      return;
    phaseTicks++;
    verify(phaseTicks < 500, "phase timeout");
    if (phase === 0) {
      Settings.data.general.animationDisabled = false;
      Settings.data.general.animationSpeed = 2;
      verify(Style.animationNormal > 0 && Style.animationFast > 0, "animations disabled in fixture");
      buildCases();
      beginCase();
      return;
    }
    if (phase === 4) {
      verify(PanelService.registeredPanels[initialPanelKey] === undefined, "original key leaked after output teardown");
      verify(PanelService.registeredPanels["launcherPanel-unknown"] === undefined, "changed key registered");
      verify(PanelService.openedPanel === null, "opened panel leaked");
      verify(destroyedContent === createdContent, "loaded content survived teardown");
      caseIndex++;
      if (caseIndex === cases.length) {
        verify(openedCount === cases.length && closedCount === cases.length - 1, "open/close signal counts");
        console.log("PASS PanelServiceLifecycle", cases.length, "animation/geometry/Loader cases plus output teardown");
        Qt.exit(exitCode);
      } else {
        beginCase();
      }
      return;
    }
    const panel = screenOwner.panel;
    const loader = findLoader(panel);
    if (phase === 1) {
      if (!panel.isPanelVisible)
        return;
      verify(loader.item !== null && createdContent === caseIndex + 1, "content not created exactly once");
      verify(loader.item.contextMarker === "eDP-1", "caller component context lost");
      verify(loader.sourceComponent === panel.panelContent, "public content Component shadowed");
      if (currentCase.mode === "earlyClose") {
        verify(panel.opacity === 0 && panel.isOpening, "early-close boundary not exercised");
        closeCase();
        verify(panel.opacityFadeComplete, "hidden close did not skip opacity fade");
        return;
      }
      if (panel.opacity < 0.999 || panel.openWatchdogActive || panel.panelRegion.width !== contentWidth || panel.panelRegion.height !== contentHeight)
        return;
      verify(panel.sizeAnimationComplete && !panel.isOpening && !panel.isClosing, "opening never settled");
      if (currentCase.mode === "teardownOpen") {
        teardownCase();
        return;
      }
      checkGeometry();
      contentWidth = 320;
      contentHeight = 210;
      phase = 2;
      phaseTicks = 0;
      return;
    }
    if (phase === 2) {
      if (panel.panelRegion.width !== contentWidth || panel.panelRegion.height !== contentHeight)
        return;
      checkGeometry();
      verify(createdContent === caseIndex + 1, "content recreated on resize");
      closeCase();
      return;
    }
    if (phase === 3 && !panel.isPanelOpen) {
      verify(!panel.isPanelVisible && !panel.isClosing && panel.closeFinalized, "close did not finalize");
      verify(!panel.opacityFadeComplete && !panel.closeWatchdogActive && panel.opacity === 0, "close animation residue");
      verify(loader.item === null && destroyedContent === createdContent, "Loader not unloaded after close");
      verify(!panel.panelRegion.dimensionsInitialized, "dimensions not reset for reopen");
      teardownCase();
    }
  }

  Timer {
    interval: 10
    running: true
    repeat: true
    onTriggered: testRoot.advance()
  }

  Timer {
    interval: 40000
    running: true
    onTriggered: testRoot.verify(false, "setup/test timeout")
  }

  Component {
    id: screenOwnerFactory

    PanelWindow {
      id: owner
      property string screenName: "eDP-1"
      property alias panel: panel
      property alias button: button
      visible: false
      implicitWidth: 1
      implicitHeight: 1

      Item {
        width: testRoot.currentCase.width
        height: testRoot.currentCase.height

        Item {
          id: button
          x: parent.width / 2
          y: parent.height / 2
          width: 40
          height: 20
        }

        SmartPanel {
          id: panel
          objectName: "launcherPanel-" + owner.screenName
          screen: Quickshell.screens[0]
          onOpened: testRoot.openedCount++
          onClosed: testRoot.closedCount++
          panelContent: Item {
            readonly property string contextMarker: owner.screenName
            readonly property real contentPreferredWidth: testRoot.contentWidth
            readonly property real contentPreferredHeight: testRoot.contentHeight
            Component.onCompleted: testRoot.createdContent++
            Component.onDestruction: testRoot.destroyedContent++
          }
        }
      }
    }
  }
}
