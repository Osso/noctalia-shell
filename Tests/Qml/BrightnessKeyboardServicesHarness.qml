import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.Hardware
import qs.Services.Keyboard
import qs.Services.UI

TestCase {
  id: suite

  property var brightnessEvents: []

  function test_ddc_enable_exit_then_stop_order() {
    compare(Settings.data.brightness.enableDdcSupport, false);
    compare(BrightnessService.ddcDetectionGeneration, 0);
    const process = FixtureIo.processes.find(value => {
      return value.command[0] === "ddcutil";
    });
    verify(process !== undefined);
    compare(process.running, false);
    Settings.data.brightness.enableDdcSupport = true;
    compare(process.running, true);
    compare(BrightnessService.ddcDetectionGeneration, 1);
    BrightnessService.requestDdcDetection();
    compare(BrightnessService.ddcDetectionPending, true);
    process.stdout.text = "Display 1\n   I2C bus: /dev/i2c-7\n   Model: Fixture LCD\n";
    process.stdout.streamFinished();
    compare(BrightnessService.ddcMonitors.length, 0);
    process.exited(0);
    compare(BrightnessService.ddcMonitors.length, 1);
    compare(BrightnessService.ddcMonitors[0].busNum, "7");
    compare(BrightnessService.ddcDetectionGeneration, 1);
    process.running = false;
    compare(process.running, true);
    compare(BrightnessService.ddcDetectionGeneration, 2);
    compare(BrightnessService.ddcDetectionPending, false);
    Settings.data.brightness.enableDdcSupport = false;
    compare(process.running, false);
    compare(BrightnessService.ddcMonitors.length, 0);
    compare(BrightnessService.ddcDetectionGeneration, 3);
    BrightnessService.finishDdcDetection(2, 0, "Display 1\n   Model: Stale\n", "");
    compare(BrightnessService.ddcMonitors.length, 0);
  }

  function test_keyboard_initialization_then_toast_order() {
    compare(KeyboardLayoutService.isInitialized, false);
    KeyboardLayoutService.setCurrentLayout("English (US)");
    compare(KeyboardLayoutService.currentLayout, "us");
    compare(KeyboardLayoutService.previousLayout, "us");
    compare(ToastService.notices.length, 0);
    tryCompare(KeyboardLayoutService, "isInitialized", true, 2500);
    compare(KeyboardLayoutService.previousLayout, "us");
    KeyboardLayoutService.setCurrentLayout("fr+oss");
    compare(KeyboardLayoutService.currentLayout, "fr");
    compare(KeyboardLayoutService.previousLayout, "fr");
    compare(ToastService.notices, [
              {
                "message": "toast.keyboard-layout.changed:FR",
                "duration": 2000
              }
            ]);
    KeyboardLayoutService.setCurrentLayout("French");
    compare(ToastService.notices.length, 1);
    Settings.data.notifications.enableKeyboardLayoutToast = false;
    KeyboardLayoutService.setCurrentLayout("German (DE)");
    compare(KeyboardLayoutService.previousLayout, "de");
    compare(ToastService.notices.length, 1);
    Settings.data.notifications.enableKeyboardLayoutToast = true;
    KeyboardLayoutService.setCurrentLayout("");
    KeyboardLayoutService.setCurrentLayout("us");
    compare(ToastService.notices.length, 1);
    KeyboardLayoutService.setCurrentLayout("de");
    compare(ToastService.notices[1].message, "toast.keyboard-layout.changed:DE");
  }

  function test_monitor_publish_before_command_and_refresh_signal() {
    Quickshell.screens = [screen];
    compare(BrightnessService.monitors.length, 1);
    const monitor = BrightnessService.getMonitorForScreen(screen);
    verify(monitor !== undefined);
    monitor.initProc.stdout.text = "/fixture/backlight\n40\n100\n";
    monitor.initProc.stdout.streamFinished();
    compare(monitor.brightness, 0.4);
    compare(monitor.brightnessPath, "/fixture/backlight/brightness");
    compare(suite.brightnessEvents.length, 1);
    compare(suite.brightnessEvents[0].screen, screen);
    suite.brightnessEvents = [];
    Quickshell.commands = [];
    monitor.setBrightness(0.65);
    compare(suite.brightnessEvents, [
              {
                "screen": screen,
                "value": 0.65,
                "stored": 0.65,
                "commands": 0
              }
            ]);
    compare(Quickshell.commands, [["brightnessctl", "s", "65%"]]);
    monitor.refreshProc.stdout.text = "70\n100\n";
    monitor.refreshProc.stdout.streamFinished();
    compare(suite.brightnessEvents.length, 2);
    compare(suite.brightnessEvents[1].value, 0.7);
    monitor.refreshProc.stdout.streamFinished();
    compare(suite.brightnessEvents.length, 2);
    Quickshell.screens = [];
    compare(BrightnessService.monitors.length, 0);
    compare(Quickshell.commands.length, 1);
  }

  name: "BrightnessKeyboardServices"

  ShellScreen {
    id: screen

    name: "fixture-screen"
    model: "Fixture LCD"
  }

  Connections {
    function onMonitorBrightnessChanged(monitor, value) {
      suite.brightnessEvents = suite.brightnessEvents.concat([
                                                               {
                                                                 "screen": monitor.modelData,
                                                                 "value": value,
                                                                 "stored": monitor.brightness,
                                                                 "commands": Quickshell.commands.length
                                                               }
                                                             ]);
    }

    target: BrightnessService
  }
}
