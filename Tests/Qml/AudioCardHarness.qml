import QtQuick
import QtTest
import qs.Modules.Cards
import qs.Services.Media
import Quickshell.Services.Pipewire

Item {
  id: scene
  width: 640
  height: 160

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
    AudioCard {
      width: 640
      height: 160
    }
  }

  TestCase {
    name: "AudioCard"
    when: windowShown
    property var card
    property var sliders
    property var buttons

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
      output.audio.muted = false;
      input.audio.muted = false;
      AudioService.setAudioSink(output);
      AudioService.setAudioSource(input);
      Pipewire.nodes = {
        values: [output, input, otherOutput, otherInput]
      };
      wait(0);
      card = createTemporaryObject(factory, scene);
      verify(card !== null);
      sliders = collect(card, item => item.from !== undefined && item.moved !== undefined);
      buttons = collect(card, item => item.clicked !== undefined && item.icon !== undefined);
      compare(sliders.length, 2);
      compare(buttons.length, 2);
      wait(0);
    }

    function move(slider, value) {
      slider.value = value;
      slider.moved();
    }

    function test_initial_and_external_volume() {
      compare(card.localOutputVolume, 0.4);
      compare(card.localInputVolume, 0.3);
      compare(sliders[0].value, 0.4);
      compare(sliders[1].value, 0.3);
      output.audio.volume = 0.52;
      input.audio.volume = 0.42;
      compare(card.localOutputVolume, 0.52);
      compare(card.localInputVolume, 0.42);
      compare(sliders[0].tooltipText, "52%");
      compare(sliders[1].tooltipText, "42%");
      wait(150);
      compare(output.audio.volume, 0.52);
      compare(input.audio.volume, 0.42);
    }

    function test_drag_debounce_release() {
      sliders[0].pressed = true;
      sliders[1].pressed = true;
      move(sliders[0], 0.8);
      move(sliders[1], 0.65);
      compare(card.localOutputVolumeChanging, true);
      compare(card.localInputVolumeChanging, true);
      compare(output.audio.volume, 0.4);
      compare(input.audio.volume, 0.3);
      output.audio.volume = 0.45;
      input.audio.volume = 0.35;
      compare(card.localOutputVolume, 0.8);
      compare(card.localInputVolume, 0.65);
      wait(40);
      move(sliders[0], 0.9);
      move(sliders[1], 0.75);
      wait(40);
      compare(output.audio.volume, 0.45);
      compare(input.audio.volume, 0.35);
      sliders[0].pressed = false;
      sliders[1].pressed = false;
      compare(card.localOutputVolumeChanging, false);
      compare(card.localInputVolumeChanging, false);
      tryCompare(output.audio, "volume", 0.9);
      tryCompare(input.audio, "volume", 0.75);
      wait(0);
    }

    function test_mute_and_volume_unmute() {
      buttons[0].clicked();
      buttons[1].clicked();
      compare(output.audio.muted, true);
      compare(input.audio.muted, true);
      compare(buttons[0].icon, "volume-off");
      compare(buttons[1].icon, "microphone-off");
      buttons[0].clicked();
      buttons[1].clicked();
      compare(output.audio.muted, false);
      compare(input.audio.muted, false);
      buttons[0].clicked();
      buttons[1].clicked();
      move(sliders[0], 0.55);
      move(sliders[1], 0.45);
      tryCompare(output.audio, "volume", 0.55);
      tryCompare(input.audio, "volume", 0.45);
      compare(output.audio.muted, false);
      compare(input.audio.muted, false);
    }

    function test_device_switch_during_pending_sync() {
      move(sliders[0], 0.9);
      move(sliders[1], 0.8);
      AudioService.setAudioSink(otherOutput);
      AudioService.setAudioSource(otherInput);
      compare(Pipewire.defaultAudioSink, otherOutput);
      compare(Pipewire.defaultAudioSource, otherInput);
      compare(card.lastSinkId, 12);
      compare(card.lastSourceId, 22);
      compare(card.localOutputVolume, 0.7);
      compare(card.localInputVolume, 0.6);
      const labels = collect(card, item => item.text === "Headphones" || item.text === "USB microphone");
      compare(labels.length, 2);
      wait(150);
      compare(output.audio.volume, 0.4);
      compare(input.audio.volume, 0.3);
      compare(otherOutput.audio.volume, 0.7);
      compare(otherInput.audio.volume, 0.6);
      output.audio.volume = 0.2;
      input.audio.volume = 0.1;
      compare(card.localOutputVolume, 0.7);
      compare(card.localInputVolume, 0.6);
      otherOutput.audio.volume = 0.65;
      otherInput.audio.volume = 0.55;
      compare(card.localOutputVolume, 0.65);
      compare(card.localInputVolume, 0.55);
    }

    function test_disconnect_before_sync() {
      move(sliders[0], 0.9);
      move(sliders[1], 0.8);
      Pipewire.ready = false;
      compare(card.lastSinkId, -1);
      compare(card.lastSourceId, -1);
      compare(card.localOutputVolume, 0);
      compare(card.localInputVolume, 0);
      compare(sliders[0].enabled, false);
      compare(sliders[1].enabled, false);
      wait(150);
      compare(output.audio.volume, 0.4);
      compare(input.audio.volume, 0.3);
    }

    function test_destroy_cancels_pending_sync() {
      move(sliders[0], 0.9);
      move(sliders[1], 0.8);
      card.destroy();
      wait(150);
      compare(output.audio.volume, 0.4);
      compare(input.audio.volume, 0.3);
      output.audio.volume = 0.5;
      input.audio.volume = 0.45;
      card = createTemporaryObject(factory, scene);
      verify(card !== null);
      compare(card.localOutputVolume, 0.5);
      compare(card.localInputVolume, 0.45);
      wait(150);
      compare(output.audio.volume, 0.5);
      compare(input.audio.volume, 0.45);
    }
  }
}
