import QtQuick
import Quickshell
import qs.Modules.Panels.Audio
import qs.Services.Media

ShellRoot {
  id: testRoot

  property var panel: null
  property string stableSinkId: ""
  property int stableSinkTicks: 0
  property int exitCode: 0
  property bool finished: false

  function fail(message) {
    console.error("FAIL AudioPanelRegression:", message);
    exitCode = 1;
  }

  function verify(condition, message) {
    if (!condition) {
      fail(message);
    }
  }

  function approximatelyEqual(actual, expected) {
    return Math.abs(actual - expected) < 0.0001;
  }

  function findSinkVolumeConnection(object) {
    if (!object) {
      return null;
    }

    const handlesVolume = typeof object.onVolumeChanged === "function";
    if (handlesVolume && object.target === AudioService.sink.audio) {
      return object;
    }

    const objects = object.data;
    if (!objects) {
      return null;
    }
    for (let index = 0; index < objects.length; index++) {
      const match = findSinkVolumeConnection(objects[index]);
      if (match) {
        return match;
      }
    }
    return null;
  }

  function findActiveOutputRadio(item) {
    if (!item) {
      return null;
    }

    const hasRadioState = item.checked !== undefined && item.indicator !== undefined;
    const descriptionMatches = item.text === AudioService.sink.description;
    const idMatches = item.deviceId !== undefined && String(item.deviceId) === String(AudioService.sink.id);
    if (hasRadioState && (descriptionMatches || idMatches)) {
      return item;
    }

    const children = item.children;
    if (!children) {
      return null;
    }
    for (let index = 0; index < children.length; index++) {
      const match = findActiveOutputRadio(children[index]);
      if (match) {
        return match;
      }
    }
    return null;
  }

  function finish() {
    if (finished) {
      return;
    }
    finished = true;
    if (exitCode === 0) {
      console.log("PASS AudioPanelRegression");
    }
    Qt.exit(exitCode);
  }

  function verifyLiveVolumeSync() {
    const liveVolume = AudioService.volume;
    const staleVolume = liveVolume < 0.5 ? 0.9 : 0.1;
    panel.localOutputVolume = staleVolume;
    verify(approximatelyEqual(panel.localOutputVolume, staleVolume),
           "setup could not assign a guaranteed-different stale panel volume");

    const sinkVolumeConnection = findSinkVolumeConnection(panel);
    verify(sinkVolumeConnection !== null,
           "setup could not find the production sink-audio volume connection");
    if (sinkVolumeConnection) {
      sinkVolumeConnection.onVolumeChanged();
      verify(approximatelyEqual(panel.localOutputVolume, liveVolume),
             `stale output volume remained ${panel.localOutputVolume}; expected live service value ${liveVolume}`);
    }
  }

  function verifyActiveOutputSelector() {
    const outputRadio = findActiveOutputRadio(panel);
    verify(outputRadio !== null,
           `output radio for active sink ${AudioService.sink.description} (${AudioService.sink.id}) was not created`);
    if (!outputRadio) {
      return;
    }

    const indicator = outputRadio.indicator;
    verify(indicator !== null, "active output radio has no indicator item");
    if (indicator) {
      verify(indicator.visible, "active output radio indicator is not visible");
      verify(indicator.width > 0 && indicator.height > 0,
             `active output radio indicator has invalid geometry ${indicator.width}x${indicator.height}`);
    }
    verify(outputRadio.checked,
           `active output radio is unchecked: sink id ${AudioService.sink.id}, delegate id ${outputRadio.deviceId}`);
  }

  function verifyPanelState() {
    verifyLiveVolumeSync();
    verifyActiveOutputSelector();
    finish();
  }

  function createPanelAfterStableSink() {
    if (!AudioService.sink || !AudioService.sink.audio) {
      stableSinkId = "";
      stableSinkTicks = 0;
      return;
    }

    const currentSinkId = String(AudioService.sink.id);
    if (currentSinkId !== stableSinkId) {
      stableSinkId = currentSinkId;
      stableSinkTicks = 0;
      return;
    }

    stableSinkTicks++;
    if (stableSinkTicks < 4) {
      return;
    }

    sinkReadinessTimer.stop();
    panel = panelFactory.createObject(panelHost);
    if (!panel) {
      fail("production AudioPanel creation failed");
      finish();
      return;
    }
    panel.isPanelOpen = true;
    panelReadinessTimer.start();
  }

  function waitForPanelContent() {
    if (!panel || !panel.isPanelVisible) {
      return;
    }
    if (!findActiveOutputRadio(panel)) {
      return;
    }

    panelReadinessTimer.stop();
    Qt.callLater(verifyPanelState);
  }

  PanelWindow {
    id: owner
    visible: false
    implicitWidth: 800
    implicitHeight: 600

    Item {
      id: panelHost
      anchors.fill: parent
    }
  }

  Component {
    id: panelFactory

    AudioPanel {
      objectName: "audioPanelRegression"
      anchors.fill: parent
      screen: owner.screen
    }
  }

  Timer {
    id: sinkReadinessTimer
    interval: 50
    repeat: true
    running: true
    onTriggered: createPanelAfterStableSink()
  }

  Timer {
    id: panelReadinessTimer
    interval: 50
    repeat: true
    onTriggered: waitForPanelContent()
  }

  Timer {
    interval: 10000
    running: true
    repeat: false
    onTriggered: {
      fail("setup timeout waiting for stable host sink and loaded AudioPanel content");
      finish();
    }
  }
}
