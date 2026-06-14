pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.Pipewire
import qs.Commons

Singleton {
  id: root

  // Devices
  readonly property PwNode sink: Pipewire.ready ? Pipewire.defaultAudioSink : null
  readonly property PwNode source: validatedSource
  readonly property PwNodeAudio sinkAudio: sink ? sink.audio : null
  readonly property PwNodeAudio sourceAudio: source ? source.audio : null
  readonly property bool hasInput: !!source
  readonly property var sinks: deviceNodes.sinks
  readonly property var sources: deviceNodes.sources

  readonly property real epsilon: 0.005

  // Output Volume - read directly from device
  readonly property real volume: {
    if (!sinkAudio)
      return 0;
    const vol = sinkAudio.volume;
    if (vol === undefined || isNaN(vol))
      return 0;
    const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
    return Math.max(0, Math.min(maxVolume, vol));
  }
  readonly property bool muted: sinkAudio ? sinkAudio.muted : true

  // Input Volume - read directly from device
  readonly property real inputVolume: {
    if (!sourceAudio)
      return 0;
    const vol = sourceAudio.volume;
    if (vol === undefined || isNaN(vol))
      return 0;
    const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
    return Math.max(0, Math.min(maxVolume, vol));
  }
  readonly property bool inputMuted: sourceAudio ? sourceAudio.muted : true

  // Allow callers to skip the next OSD notification when they are already
  // presenting volume state (e.g. the Audio Panel UI). We track this as a short
  // time window so suppression applies to every monitor, not just the first one
  // that receives the signal.
  property double outputOSDSuppressedUntilMs: 0
  property double inputOSDSuppressedUntilMs: 0

  function suppressOutputOSD(durationMs = 400) {
    const target = Date.now() + durationMs;
    outputOSDSuppressedUntilMs = Math.max(outputOSDSuppressedUntilMs, target);
  }

  function suppressInputOSD(durationMs = 400) {
    const target = Date.now() + durationMs;
    inputOSDSuppressedUntilMs = Math.max(inputOSDSuppressedUntilMs, target);
  }

  function consumeOutputOSDSuppression(): bool {
    return Date.now() < outputOSDSuppressedUntilMs;
  }

  function consumeInputOSDSuppression(): bool {
    return Date.now() < inputOSDSuppressedUntilMs;
  }

  readonly property real stepVolume: Settings.data.audio.volumeStep / 100.0

  // Filtered device nodes (non-stream sinks and sources)
  readonly property var deviceNodes: Pipewire.ready ? Pipewire.nodes.values.reduce((acc, node) => {
                                                                                     if (!node.isStream) {
                                                                                       if (node.isSink) {
                                                                                         acc.sinks.push(node);
                                                                                       } else if (node.audio) {
                                                                                         acc.sources.push(node);
                                                                                       }
                                                                                     }
                                                                                     return acc;
                                                                                   }, {
                                                                                     "sources": [],
                                                                                     "sinks": []
                                                                                   }) : {
                                                        "sources": [],
                                                        "sinks": []
                                                      }

  // Validated source (ensures it's a proper audio source, not a sink)
  readonly property PwNode validatedSource: {
    if (!Pipewire.ready) {
      return null;
    }
    const raw = Pipewire.defaultAudioSource;
    if (!raw || raw.isSink || !raw.audio) {
      return null;
    }
    // Optional: check type if available (type reflects media.class per docs)
    if (raw.type && typeof raw.type === "string" && !raw.type.startsWith("Audio/Source")) {
      return null;
    }
    return raw;
  }

  // Internal state for feedback loop prevention
  property bool isSettingOutputVolume: false
  property bool isSettingInputVolume: false

  // Bind default sink and source to ensure their properties are available
  PwObjectTracker {
    id: sinkTracker
    objects: root.sink ? [root.sink] : []
  }

  PwObjectTracker {
    id: sourceTracker
    objects: root.source ? [root.source] : []
  }

  // Bind all devices to ensure their properties are available
  PwObjectTracker {
    objects: [...root.sinks, ...root.sources]
  }

  // Watch output device changes for clamping
  Connections {
    target: sinkAudio

    function onVolumeChanged() {
      // Ignore volume changes if we're the one setting it (to prevent feedback loop)
      if (root.isSettingOutputVolume) {
        return;
      }

      if (!root.sinkAudio) {
        return;
      }

      const vol = root.sinkAudio.volume;
      if (vol === undefined || isNaN(vol)) {
        return;
      }

      const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;

      // If volume exceeds max, clamp it (but only if we didn't just set it)
      if (vol > maxVolume) {
        root.isSettingOutputVolume = true;
        Qt.callLater(() => {
                       if (root.sinkAudio && root.sinkAudio.volume > maxVolume) {
                         root.sinkAudio.volume = maxVolume;
                       }
                       root.isSettingOutputVolume = false;
                     });
      }
    }
  }

  // Watch input device changes for clamping
  Connections {
    target: sourceAudio

    function onVolumeChanged() {
      // Ignore volume changes if we're the one setting it (to prevent feedback loop)
      if (root.isSettingInputVolume) {
        return;
      }

      if (!root.sourceAudio) {
        return;
      }

      const vol = root.sourceAudio.volume;
      if (vol === undefined || isNaN(vol)) {
        return;
      }

      const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;

      // If volume exceeds max, clamp it (but only if we didn't just set it)
      if (vol > maxVolume) {
        root.isSettingInputVolume = true;
        Qt.callLater(() => {
                       if (root.sourceAudio && root.sourceAudio.volume > maxVolume) {
                         root.sourceAudio.volume = maxVolume;
                       }
                       root.isSettingInputVolume = false;
                     });
      }
    }
  }

  // Output Control
  function increaseVolume() {
    if (!Pipewire.ready || !sinkAudio) {
      return;
    }
    const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
    if (volume >= maxVolume) {
      return;
    }
    setVolume(Math.min(maxVolume, volume + stepVolume));
  }

  function decreaseVolume() {
    if (!Pipewire.ready || !sinkAudio) {
      return;
    }
    if (volume <= 0) {
      return;
    }
    setVolume(Math.max(0, volume - stepVolume));
  }

  function setVolume(newVolume: real) {
    if (!Pipewire.ready || !sink || !sink.ready || !sinkAudio) {
      Logger.w("AudioService", "No sink available or not ready");
      return;
    }

    const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
    const clampedVolume = Math.max(0, Math.min(maxVolume, newVolume));
    const delta = Math.abs(clampedVolume - sinkAudio.volume);
    if (delta < root.epsilon) {
      return;
    }

    // Set flag to prevent feedback loop, then set the actual volume
    isSettingOutputVolume = true;
    sinkAudio.muted = false;
    sinkAudio.volume = clampedVolume;

    // Clear flag after a short delay to allow external changes to be detected
    Qt.callLater(() => {
                   isSettingOutputVolume = false;
                 });
  }

  function setOutputMuted(muted: bool) {
    if (!Pipewire.ready || !sinkAudio) {
      Logger.w("AudioService", "No sink available or Pipewire not ready");
      return;
    }

    sinkAudio.muted = muted;
  }

  function getOutputIcon() {
    if (muted)
      return "volume-mute";

    const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
    const clampedVolume = Math.max(0, Math.min(volume, maxVolume));

    // Show volume-x icon when volume is effectively 0% (within rounding threshold)
    if (clampedVolume < root.epsilon) {
      return "volume-x";
    }
    if (clampedVolume <= 0.5) {
      return "volume-low";
    }
    return "volume-high";
  }

  // Input Control
  function increaseInputVolume() {
    if (!Pipewire.ready || !sourceAudio) {
      return;
    }
    const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
    if (inputVolume >= maxVolume) {
      return;
    }
    setInputVolume(Math.min(maxVolume, inputVolume + stepVolume));
  }

  function decreaseInputVolume() {
    if (!Pipewire.ready || !sourceAudio) {
      return;
    }
    setInputVolume(Math.max(0, inputVolume - stepVolume));
  }

  function setInputVolume(newVolume: real) {
    if (!Pipewire.ready || !source || !source.ready || !sourceAudio) {
      Logger.w("AudioService", "No source available or not ready");
      return;
    }

    const maxVolume = Settings.data.audio.volumeOverdrive ? 1.5 : 1.0;
    const clampedVolume = Math.max(0, Math.min(maxVolume, newVolume));
    const delta = Math.abs(clampedVolume - sourceAudio.volume);
    if (delta < root.epsilon) {
      return;
    }

    // Set flag to prevent feedback loop, then set the actual volume
    isSettingInputVolume = true;
    sourceAudio.muted = false;
    sourceAudio.volume = clampedVolume;

    // Clear flag after a short delay to allow external changes to be detected
    Qt.callLater(() => {
                   isSettingInputVolume = false;
                 });
  }

  function setInputMuted(muted: bool) {
    if (!Pipewire.ready || !sourceAudio) {
      Logger.w("AudioService", "No source available or Pipewire not ready");
      return;
    }

    sourceAudio.muted = muted;
  }

  function getInputIcon() {
    if (inputMuted || inputVolume <= Number.EPSILON) {
      return "microphone-mute";
    }
    return "microphone";
  }

  // Device Selection
  function setAudioSink(newSink: PwNode) {
    if (!Pipewire.ready) {
      Logger.w("AudioService", "Pipewire not ready");
      return;
    }
    Pipewire.preferredDefaultAudioSink = newSink;
  }

  function setAudioSource(newSource: PwNode) {
    if (!Pipewire.ready) {
      Logger.w("AudioService", "Pipewire not ready");
      return;
    }
    Pipewire.preferredDefaultAudioSource = newSource;
  }
}
