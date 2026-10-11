import QtQuick
import QtTest
import qs.Modules.Panels.Audio
import qs.Services.Media
import Quickshell.Services.Pipewire

Item {
  id: scene
  width: 800
  height: 600

  PwNode {
    id: output
    nodeId: 11
    description: "Speakers"
  }
  PwNode {
    id: input
    nodeId: 21
    description: "Microphone"
    isSink: false
    type: "Audio/Source"
  }
  PwNode {
    id: otherOutput
    nodeId: 12
    description: "Headphones"
  }
  PwNode {
    id: otherInput
    nodeId: 22
    description: "USB microphone"
    isSink: false
    type: "Audio/Source"
  }

  Component {
    id: factory
    AudioPanel {
      width: 800
      height: 600
    }
  }

  TestCase {
    name: "AudioPanel"
    when: windowShown
    property var panel
    property var sliders
    property var radios

    function collect(item, predicate) {
      let matches = predicate(item) ? [item] : [];
      for (const child of item.children)
        matches = matches.concat(collect(child, predicate));
      return matches;
    }

    function init() {
      Pipewire.ready = true;
      output.audio.volume = 0.4;
      input.audio.volume = 0.3;
      otherOutput.audio.volume = 0.7;
      otherInput.audio.volume = 0.6;
      AudioService.setAudioSink(output);
      AudioService.setAudioSource(input);
      Pipewire.nodes = {
        values: [output, input, otherOutput, otherInput]
      };
      panel = createTemporaryObject(factory, scene);
      verify(panel !== null);
      wait(0);
      sliders = collect(panel, item => item.textSize !== undefined && item.moved !== undefined);
      radios = collect(panel, item => item.deviceId !== undefined);
      compare(sliders.length, 2);
      compare(radios.length, 4);
    }

    function radio(id) {
      const matches = radios.filter(item => item.deviceId === String(id));
      compare(matches.length, 1);
      return matches[0];
    }

    function test_initial_and_external_volume() {
      compare(panel.localOutputVolume, 0.4);
      compare(panel.localInputVolume, 0.3);
      compare(radio(11).text, "Speakers");
      compare(radio(21).text, "Microphone");
      verify(radio(11).checked);
      verify(radio(11).indicator.visible);
      verify(radio(11).indicator.width > 0);
      output.audio.volume = 0.52;
      compare(panel.localOutputVolume, 0.52);
      compare(sliders[0].text, "52%");
    }

    function test_sink_source_selection_and_pending_sync() {
      sliders[0].moved(0.9);
      sliders[1].moved(0.8);
      radio(12).clicked();
      radio(22).clicked();
      compare(Pipewire.defaultAudioSink, otherOutput);
      compare(Pipewire.defaultAudioSource, otherInput);
      compare(panel.lastSinkId, 12);
      compare(panel.lastSourceId, 22);
      compare(panel.localOutputVolume, 0.7);
      compare(panel.localInputVolume, 0.6);
      verify(radio(12).checked);
      verify(!radio(11).checked);
      wait(150);
      compare(output.audio.volume, 0.4);
      compare(input.audio.volume, 0.3);
      compare(otherOutput.audio.volume, 0.7);
      compare(otherInput.audio.volume, 0.6);
      otherOutput.audio.volume = 0.65;
      otherInput.audio.volume = 0.55;
      compare(panel.localOutputVolume, 0.65);
      compare(panel.localInputVolume, 0.55);
    }

    function test_drag_debounce_release() {
      // Source guard is initialized by a source change, as in production.
      AudioService.setAudioSource(otherInput);
      AudioService.setAudioSource(input);
      sliders[0].pressedChanged(true, sliders[0].value);
      sliders[1].pressedChanged(true, sliders[1].value);
      sliders[0].moved(0.8);
      sliders[1].moved(0.65);
      verify(panel.localOutputVolumeChanging);
      verify(panel.localInputVolumeChanging);
      output.audio.volume = 0.45;
      input.audio.volume = 0.35;
      compare(panel.localOutputVolume, 0.8);
      compare(panel.localInputVolume, 0.65);
      compare(sliders[0].text, "80%");
      compare(sliders[1].text, "65%");
      wait(40);
      sliders[0].moved(0.9);
      sliders[1].moved(0.75);
      wait(40);
      compare(output.audio.volume, 0.45);
      compare(input.audio.volume, 0.35);
      sliders[0].pressedChanged(false, sliders[0].value);
      sliders[1].pressedChanged(false, sliders[1].value);
      verify(!panel.localOutputVolumeChanging);
      verify(!panel.localInputVolumeChanging);
      tryCompare(output.audio, "volume", 0.9);
      tryCompare(input.audio, "volume", 0.75);
    }

    function test_model_reorder_and_content_recreation() {
      Pipewire.nodes = {
        values: [otherInput, otherOutput, input, output]
      };
      wait(0);
      radios = collect(panel, item => item.deviceId !== undefined);
      compare(radios.length, 4);
      compare(radio(12).text, "Headphones");
      compare(radio(22).text, "USB microphone");
      radio(12).clicked();
      radio(22).clicked();
      compare(Pipewire.defaultAudioSink, otherOutput);
      compare(Pipewire.defaultAudioSource, otherInput);
      panel.isPanelOpen = false;
      wait(0);
      compare(collect(panel, item => item.deviceId !== undefined).length, 0);
      panel.isPanelOpen = true;
      wait(0);
      radios = collect(panel, item => item.deviceId !== undefined);
      compare(radios.length, 4);
      verify(radio(12).checked);
      compare(radio(22).text, "USB microphone");
    }

    function test_destroy_cancels_pending_sync() {
      sliders[0].moved(0.9);
      sliders[1].moved(0.8);
      panel.destroy();
      wait(150);
      compare(output.audio.volume, 0.4);
      compare(input.audio.volume, 0.3);
      output.audio.volume = 0.5;
      panel = createTemporaryObject(factory, scene);
      verify(panel !== null);
      compare(panel.localOutputVolume, 0.5);
      wait(150);
      compare(output.audio.volume, 0.5);
    }
  }
}
