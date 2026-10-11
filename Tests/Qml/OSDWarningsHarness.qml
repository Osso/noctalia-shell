import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.OSD
import qs.Services.Hardware
import qs.Services.Keyboard
import qs.Services.Media

ShellRoot {
  id: harness

  OSD {
    id: osd
  }

  TestCase {
    id: clock
    when: false
  }

  function require(condition, message) {
    if (!condition) {
      console.error("OSD_BEHAVIOR_FAIL", message);
      Qt.exit(1);
      throw new Error(message);
    }
  }

  function descendants(item, predicate) {
    let found = predicate(item) ? [item] : [];
    for (const child of item.children || []) {
      found = found.concat(harness.descendants(child, predicate));
    }
    return found;
  }

  function assertDisplay(loader, icon, label) {
    harness.require(loader.active && loader.item, "OSD loaded");
    const panel = loader.item;
    harness.require(panel.screen === loader.modelData, "panel routed to " + loader.modelData.name);
    const icons = harness.descendants(panel.contentItem, item => item.icon !== undefined);
    harness.require(icons.length === 1 && icons[0].icon === icon && icons[0].text === icon, "icon content " + icon);
    const labels = harness.descendants(panel.contentItem, item => item.family !== undefined && item.visible);
    harness.require(labels.length === 1 && labels[0].text === label, "label content " + label);
  }

  function setLocation(location) {
    Settings.data = Object.assign({}, Settings.data, {
      osd: Object.assign({}, Settings.data.osd, {
        location: location
      })
    });
    clock.wait(20);
  }

  function assertDisplays(icon, label) {
    clock.wait(20);
    for (const loader of osd.instances) {
      harness.assertDisplay(loader, icon, label);
    }
  }

  function exerciseScreen() {
    harness.require(Quickshell.screens.length === 1 && osd.instances.length === 1, "one private headless screen");
    const first = osd.instances[0];
    first.showOSD(OSD.Type.Volume);
    harness.require(!first.active, "startup suppresses OSD");
    clock.wait(2100);
    harness.require(first.startupComplete, "startup timer completes");
    first.showOSD(OSD.Type.Volume);
    clock.wait(20);
    harness.assertDisplay(first, "volume-low", "25%");
    clock.wait(330);
    harness.require(!first.active && first.currentOSDType === -1, "timeout unloads/reset");
  }

  function exerciseAudio(location) {
    harness.setLocation(location);
    AudioService.volume = 0.75;
    harness.assertDisplays("volume-high", "75%");
    clock.wait(120);
    AudioService.volume = 0.003;
    harness.assertDisplays("volume-x", "0%");
    clock.wait(160);
    harness.assertDisplays("volume-x", "0%");
    AudioService.muted = true;
    harness.assertDisplays("volume-mute", "0%");
    AudioService.muted = false;
    Settings.data = Object.assign({}, Settings.data, {
      audio: Object.assign({}, Settings.data.audio, {
        volumeOverdrive: true
      })
    });
    AudioService.volume = 1.25;
    harness.assertDisplays("volume-high", "125%");
    AudioService.inputVolume = 0.65;
    harness.assertDisplays("microphone", "65%");
    AudioService.inputMuted = true;
    harness.assertDisplays("microphone-off", "0%");
    AudioService.inputMuted = false;
    clock.wait(330);
    for (const loader of osd.instances) {
      harness.require(!loader.active && loader.currentOSDType === -1, "audio timeout");
    }
    // Reset only fixture state so each orientation generates fresh signals.
    AudioService.volume = 0.25;
    AudioService.inputVolume = 0.4;
    clock.wait(330);
  }

  function exerciseBrightnessAndLocks() {
    for (const sample of [
      {
        value: 0.003,
        icon: "sun-off",
        label: "0%"
      },
      {
        value: 0.4,
        icon: "brightness-low",
        label: "40%"
      },
      {
        value: 0.8,
        icon: "brightness-high",
        label: "80%"
      }
    ]) {
      BrightnessService.monitor.brightnessUpdated(sample.value);
      harness.assertDisplays(sample.icon, sample.label);
    }
    BrightnessService.monitor.brightnessUpdated(NaN);
    harness.assertDisplays("brightness-high", "80%");
    LockKeysService.capsLockOn = true;
    LockKeysService.capsLockChanged(true);
    harness.assertDisplays("keyboard", "CAPS ON");
    clock.wait(330);
    for (const loader of osd.instances) {
      harness.require(!loader.active && loader.currentOSDType === -1 && loader.lastLockKeyChanged === "", "lock timeout clears state");
    }
    Settings.data = Object.assign({}, Settings.data, {
      osd: Object.assign({}, Settings.data.osd, {
        monitors: [Quickshell.screens[0].name]
      })
    });
    clock.wait(20);
    harness.require(osd.instances.length === 1, "monitor filtering");
    AudioService.volume = 0.6;
    harness.assertDisplays("volume-high", "60%");
  }

  Timer {
    interval: 50
    running: true
    onTriggered: {
      harness.exerciseScreen();
      harness.exerciseAudio("top_right");
      harness.exerciseBrightnessAndLocks();
      Settings.data = Object.assign({}, Settings.data, {
        osd: Object.assign({}, Settings.data.osd, {
          monitors: []
        })
      });
      clock.wait(2100);
      harness.exerciseAudio("left");
      harness.exerciseBrightnessAndLocks();
      console.log("OSD_BEHAVIOR_PASS");
      Qt.exit(0);
    }
  }
}
