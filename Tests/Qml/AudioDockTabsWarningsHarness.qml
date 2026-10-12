import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.Media
import qs.Tabs

TestCase {
  id: testCase
  name: "AudioDockTabsWarnings"
  width: 1000
  height: 2400
  visible: true
  when: windowShown

  Component {
    id: audioComponent
    AudioTab {
      width: 1000
    }
  }
  Component {
    id: dockComponent
    DockTab {
      width: 1000
    }
  }

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function control(tab, label) {
    const matches = descendants(tab).filter(item => item.label === label && (item.toggled !== undefined || item.selected !== undefined || item.buttonClicked !== undefined || item.changeValue !== undefined));
    compare(matches.length, 1, label);
    return matches[0];
  }

  function init() {
    AudioService.speaker.audio.volume = 0.4;
    AudioService.speaker.audio.muted = false;
    AudioService.headphones.audio.volume = 0.7;
    AudioService.sink = AudioService.speaker;
    AudioService.source = AudioService.microphone;
    AudioService.inputVolume = 0.3;
    AudioService.inputMuted = false;
    AudioService.isSwitchingSink = false;
    AudioService.volumeWrites = [];
    AudioService.sinks = [AudioService.speaker, AudioService.headphones];
    AudioService.sources = [AudioService.microphone, AudioService.headset];
    Settings.data.audio.volumeOverdrive = false;
    Settings.data.audio.mprisBlacklist = ["FirstPlayer", "SecondPlayer"];
    Settings.data.audio.visualizerType = "linear";
    Settings.data.audio.visualizerQuality = "low";
    Settings.data.audio.cavaFrameRate = "30";
    Settings.data.dock.enabled = true;
    Settings.data.dock.displayMode = "always_visible";
    Settings.data.dock.monitors = ["eDP-1"];
    Settings.data.dock.onlySameOutput = false;
    Settings.data.dock.colorizeIcons = false;
    Quickshell.screens = [Quickshell.laptop, Quickshell.external];
  }

  function test_audioVolumeOwnerAndDeviceSwitch() {
    const tab = createTemporaryObject(audioComponent, testCase);
    verify(tab !== null);
    wait(120);
    compare(tab.localVolume, 0.4);
    compare(AudioService.volumeWrites.length, 0);
    AudioService.speaker.audio.volume = 0.55;
    compare(tab.localVolume, 0.55);
    const sliders = descendants(tab).filter(item => item.moved !== undefined && item.text !== undefined && item.stepSize === 0.01);
    compare(sliders.length, 2);
    sliders[0].moved(0.62);
    tryCompare(AudioService.speaker.audio, "volume", 0.62);
    compare(AudioService.volumeWrites.join(","), "0.62");
    AudioService.isSwitchingSink = true;
    sliders[0].moved(0.9);
    wait(140);
    compare(AudioService.volumeWrites.join(","), "0.62");
    const headphones = descendants(tab).find(item => item.text === "Headphones" && item.clicked !== undefined);
    verify(headphones !== undefined);
    headphones.clicked();
    compare(AudioService.sink, AudioService.headphones);
    compare(tab.localVolume, 0.7);
    AudioService.isSwitchingSink = false;
    wait(120);
    compare(AudioService.volumeWrites.join(","), "0.62");
    AudioService.headphones.audio.volume = 0.81;
    compare(tab.localVolume, 0.81);
    const headset = descendants(tab).find(item => item.text === "Headset" && item.clicked !== undefined);
    headset.clicked();
    compare(AudioService.source, AudioService.headset);
    sliders[1].moved(0.45);
    compare(AudioService.inputVolume, 0.45);
  }

  function test_audioTogglesAndOptions() {
    const tab = createTemporaryObject(audioComponent, testCase);
    verify(tab !== null);
    control(tab, "settings.audio.volumes.mute-output.label").toggled(true);
    compare(AudioService.speaker.audio.muted, true);
    control(tab, "settings.audio.volumes.mute-input.label").toggled(true);
    compare(AudioService.inputMuted, true);
    control(tab, "settings.audio.volumes.volume-overdrive.label").toggled(true);
    compare(Settings.data.audio.volumeOverdrive, true);
    const output = descendants(tab).find(item => item.moved !== undefined && item.value === tab.localVolume);
    compare(output.to, 1.5);
    const visualizer = control(tab, "settings.audio.media.visualizer-type.label");
    compare(visualizer.itemCount(), 4);
    visualizer.activateCurrentIndex(3);
    compare(Settings.data.audio.visualizerType, "wave");
    control(tab, "settings.audio.media.visualizer-quality.label").activateCurrentIndex(1);
    compare(Settings.data.audio.visualizerQuality, "high");
    control(tab, "settings.audio.media.frame-rate.label").activateCurrentIndex(2);
    compare(Settings.data.audio.cavaFrameRate, 100);
    const step = control(tab, "settings.audio.volumes.step-size.label");
    step.changeValue(1, 1);
    compare(Settings.data.audio.volumeStep, step.value);
  }

  function test_blacklistDelegatesAndRemoval() {
    const tab = createTemporaryObject(audioComponent, testCase);
    verify(tab !== null);
    wait(50);
    let chips = descendants(tab).filter(item => item.pad !== undefined);
    compare(chips.length, 2);
    for (let index = 0; index < chips.length; index++) {
      const row = chips[index].children[0];
      compare(row.x, chips[index].pad);
      compare(row.y, chips[index].pad);
      compare(row.children[0].text, Settings.data.audio.mprisBlacklist[index]);
      verify(chips[index].width > 0);
      verify(chips[index].height > 0);
    }
    const before = MediaService.updates;
    descendants(chips[1]).find(item => item.icon === "close" && item.clicked !== undefined).clicked();
    compare(Settings.data.audio.mprisBlacklist.join(","), "FirstPlayer");
    compare(MediaService.updates, before + 1);
    const input = control(tab, "settings.audio.media.excluded-player.label");
    input.text = " ThirdPlayer ";
    input.buttonClicked();
    compare(Settings.data.audio.mprisBlacklist.join(","), "FirstPlayer,ThirdPlayer");
    input.text = "thirdplayer";
    input.buttonClicked();
    compare(Settings.data.audio.mprisBlacklist.join(","), "FirstPlayer,ThirdPlayer");
    wait(50);
    chips = descendants(tab).filter(item => item.pad !== undefined);
    compare(chips.length, 2);
    compare(chips[1].children[0].children[0].text, "ThirdPlayer");
  }

  function test_dockMonitorOwnersAndRepopulation() {
    const tab = createTemporaryObject(dockComponent, testCase);
    verify(tab !== null);
    wait(50);
    let monitors = descendants(tab).filter(item => item.monitorName !== undefined);
    compare(monitors.length, 2);
    compare(monitors[0].label, "eDP-1");
    compare(monitors[0].description, "Laptop:1920x1080@1");
    compare(monitors[1].description, "External:3840x2160@1.5");
    compare(monitors[0].checked, true);
    compare(monitors[1].checked, false);
    monitors[1].toggled(true);
    compare(Settings.data.dock.monitors.join(","), "eDP-1,DP-1");
    monitors[0].toggled(false);
    compare(Settings.data.dock.monitors.join(","), "DP-1");
    Quickshell.screens = [Quickshell.external, Quickshell.laptop];
    wait(50);
    monitors = descendants(tab).filter(item => item.monitorName !== undefined);
    compare(monitors[0].label, "DP-1");
    compare(monitors[0].checked, true);
    monitors[1].toggled(true);
    compare(Settings.data.dock.monitors.join(","), "DP-1,eDP-1");
  }

  function test_dockTogglesAndOptions() {
    const tab = createTemporaryObject(dockComponent, testCase);
    verify(tab !== null);
    const enabled = control(tab, "settings.dock.enabled.label");
    const mode = control(tab, "settings.dock.appearance.display.label");
    compare(mode.itemCount(), 3);
    enabled.toggled(false);
    compare(Settings.data.dock.enabled, false);
    compare(mode.visible, false);
    enabled.toggled(true);
    compare(mode.visible, true);
    mode.activateCurrentIndex(1);
    compare(Settings.data.dock.displayMode, "auto_hide");
    mode.activateCurrentIndex(2);
    compare(Settings.data.dock.displayMode, "exclusive");
    control(tab, "settings.dock.monitors.only-same-output.label").toggled(true);
    control(tab, "settings.dock.appearance.colorize-icons.label").toggled(true);
    compare(Settings.data.dock.onlySameOutput, true);
    compare(Settings.data.dock.colorizeIcons, true);
    const sliders = descendants(tab).filter(item => item.moved !== undefined && item.text !== undefined);
    compare(sliders.length, 3);
    sliders[0].moved(0.65);
    sliders[1].moved(1.25);
    sliders[2].moved(0.8);
    compare(Settings.data.dock.backgroundOpacity, 0.65);
    compare(Settings.data.dock.floatingRatio, 1.25);
    compare(Settings.data.dock.size, 0.8);
  }

  function test_saveSnapshotAndCancelReopen() {
    const audio = createTemporaryObject(audioComponent, testCase);
    const dock = createTemporaryObject(dockComponent, testCase);
    verify(audio !== null && dock !== null);
    control(audio, "settings.audio.media.visualizer-type.label").activateCurrentIndex(3);
    control(dock, "settings.dock.appearance.display.label").activateCurrentIndex(1);
    // Tabs edit immediately: save is a synthetic snapshot; cancel/close cannot roll back.
    const saved = JSON.stringify({
      visualizer: Settings.data.audio.visualizerType,
      dockMode: Settings.data.dock.displayMode
    });
    compare(saved, '{"visualizer":"wave","dockMode":"auto_hide"}');
    control(audio, "settings.audio.media.visualizer-type.label").activateCurrentIndex(2);
    control(dock, "settings.dock.appearance.display.label").activateCurrentIndex(2);
    audio.destroy();
    dock.destroy();
    wait(0);
    compare(Settings.data.audio.visualizerType, "mirrored");
    compare(Settings.data.dock.displayMode, "exclusive");
    const reopenedAudio = createTemporaryObject(audioComponent, testCase);
    const reopenedDock = createTemporaryObject(dockComponent, testCase);
    verify(reopenedAudio !== null && reopenedDock !== null);
    compare(control(reopenedAudio, "settings.audio.media.visualizer-type.label").currentKey, "mirrored");
    compare(control(reopenedDock, "settings.dock.appearance.display.label").currentKey, "exclusive");
    compare(JSON.parse(saved).visualizer, "wave");
    compare(JSON.parse(saved).dockMode, "auto_hide");
  }
}
