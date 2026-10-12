import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Modules.Panels.Launcher
import qs.Modules.Panels.Launcher.Plugins
import qs.Services.Keyboard
import qs.Services.Media
import qs.Services.System
import qs.Services.UI

Item {
  id: harness

  Launcher {
    id: launcher
  }
  EmojiPlugin {
    id: plugin
    launcher: launcher
  }

  TestCase {
    name: "EmojiRecorderWarnings"

    function init() {
      ScreenRecorderService.isRecording = false;
      ScreenRecorderService.isPending = false;
      ScreenRecorderService.hasActiveRecording = false;
      ProgramCheckerService.gpuScreenRecorderAvailable = false;
      for (const process of FixtureIo.processes)
        process.running = false;
      FixtureIo.commands = [];
      Quickshell.commands = [];
      ToastService.errors = [];
      ToastService.notices = [];
    }

    function test_emoji_filter_selection() {
      compare(plugin.getResults("unrelated").length, 0);
      EmojiService.loaded = false;
      compare(plugin.getResults(">emoji")[0].name, "plugins.emoji-loading");
      const before = launcher.updates;
      EmojiService.loaded = true;
      compare(launcher.updates, before + 1);
      plugin.selectCategory("food");
      compare(launcher.updates, before + 2);
      compare(plugin.getResults(">emoji ")[0].emojiChar, "🍎");
      verify(plugin.isBrowsingMode);
      const results = plugin.getResults(">emoji  CAT  ");
      compare(results.length, 1);
      compare(results[0].name, "Cat");
      compare(results[0].description, "pet, cat • Category: animals");
      verify(!plugin.isBrowsingMode);
      compare(plugin.getResults(">emoji absent").length, 0);
      results[0].onActivate();
      compare(EmojiService.copied[0], "🐈");
      compare(launcher.closes, 1);
      plugin.commands()[0].onActivate();
      compare(launcher.searchText, ">emoji ");
      plugin.onOpened();
      compare(plugin.selectedCategory, "recent");
      compare(FixtureIo.commands.length, 0);
    }

    function test_discovery_collectors() {
      ScreenRecorderService.discoveryInProgress = false;
      ScreenRecorderService.discoveryQueued = false;
      ScreenRecorderService.refreshCaptureSources();
      compare(FixtureIo.commands.length, 2);
      compare(FixtureIo.commands[0], ["gpu-screen-recorder", "--list-capture-options"]);
      compare(FixtureIo.commands[1], ["gpu-screen-recorder", "--list-monitors"]);
      const capture = FixtureIo.processes.find(p => p.command[1] === "--list-capture-options");
      const monitors = FixtureIo.processes.find(p => p.command[1] === "--list-monitors");
      monitors.complete(0, "DP-1|1920x1080\n", "");
      verify(ScreenRecorderService.discoveryInProgress);
      capture.complete(0, "region\n/dev/video0|640x480\n", "");
      verify(!ScreenRecorderService.discoveryInProgress);
      compare(ScreenRecorderService.primaryMonitorResolution, "1920x1080");
      compare(ScreenRecorderService.captureSources.map(s => s.key), ["region", "DP-1", "portal"]);
    }

    function test_recorder_commands_state() {
      ScreenRecorderService.startRecording();
      compare(FixtureIo.commands.length, 0);
      ProgramCheckerService.gpuScreenRecorderAvailable = true;
      Settings.data.screenRecorder.videoSource = "focused";
      ScreenRecorderService.primaryMonitorResolution = "2560x1440";
      ScreenRecorderService.startRecording();
      verify(ScreenRecorderService.isPending);
      verify(!ScreenRecorderService.isRecording);
      compare(ScreenRecorderService.outputPath, "/fixture/videos/fixture-time.mp4");
      compare(FixtureIo.commands.length, 1);
      compare(FixtureIo.commands[0].slice(0, 2), ["sh", "-c"]);
      const script = FixtureIo.commands[0][2];
      verify(script.includes("-w focused -s 2560x1440 -f 60"));
      verify(script.includes('-a "default_output|default_input"'));
      verify(script.includes('-o "/fixture/videos/fixture-time.mp4"'));
      ScreenRecorderService.startRecording();
      compare(FixtureIo.commands.length, 1);
      ScreenRecorderService.handlePendingTimer(true);
      verify(ScreenRecorderService.isRecording);
      verify(ScreenRecorderService.hasActiveRecording);
      ScreenRecorderService.stopRecording();
      verify(!ScreenRecorderService.isRecording);
      verify(!ScreenRecorderService.isPending);
      compare(Quickshell.commands.length, 1);
      verify(Quickshell.commands[0][2].includes("pkill -SIGINT"));
    }

    function test_recorder_portal_preflight() {
      ProgramCheckerService.gpuScreenRecorderAvailable = true;
      Settings.data.screenRecorder.videoSource = "portal";
      ScreenRecorderService.startRecording();
      compare(FixtureIo.commands.length, 1);
      verify(FixtureIo.commands[0][2].includes("pidof xdg-desktop-portal"));
      const portal = FixtureIo.processes.find(p => p.command[0] === "sh" && p.command[2].includes("pidof xdg-desktop-portal"));
      portal.complete(1, "", "");
      verify(!ScreenRecorderService.isPending);
      compare(ToastService.errors[0][0], "toast.recording.no-portals");
      compare(FixtureIo.commands.length, 1);
      ScreenRecorderService.startRecording();
      portal.complete(0, "", "");
      compare(FixtureIo.commands.length, 3);
      verify(FixtureIo.commands[2][2].includes("-w portal"));
      verify(!FixtureIo.commands[2][2].includes("-s 2560x1440"));
      verify(ScreenRecorderService.isPending);
    }

    function test_recorder_exit_collectors() {
      ProgramCheckerService.gpuScreenRecorderAvailable = true;
      Settings.data.screenRecorder.videoSource = "focused";
      ScreenRecorderService.startRecording();
      const process = FixtureIo.processes.find(p => p.command[0] === "sh" && p.command[2].includes("GPU_SCREEN_RECORDER_NOT_INSTALLED"));
      process.complete(7, "", "fixture encoder rejected\n");
      verify(!ScreenRecorderService.isPending);
      compare(ToastService.errors.length, 1);
      compare(ToastService.errors[0][1], "fixture encoder rejected");
      ScreenRecorderService.startRecording();
      process.complete(0, "GPU_SCREEN_RECORDER_NOT_INSTALLED\n", "");
      compare(ToastService.errors[1][0], "toast.recording.not-installed");
      ScreenRecorderService.startRecording();
      process.complete(0, "", "");
      verify(!ScreenRecorderService.isPending);
      compare(ToastService.errors.length, 2);
      ScreenRecorderService.startRecording();
      ScreenRecorderService.handlePendingTimer(true);
      process.complete(0, "", "");
      verify(!ScreenRecorderService.isRecording);
      verify(!ScreenRecorderService.hasActiveRecording);
      compare(ToastService.notices[0][0], "toast.recording.saved");
      compare(ToastService.notices[0][1], "/fixture/videos/fixture-time.mp4");
    }
  }
}
