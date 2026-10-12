import QtQuick
import QtTest
import Quickshell as FixtureShell
import Quickshell.Io as FixtureProcesses
import qs.Commons
import qs.Services.Hardware

TestCase {
  id: suite

  name: "BrightnessServiceOffscreen"
  property var brightnessEvents: []

  function init() {
    compare(Settings.data.brightness.enableDdcSupport, false);
    FixtureShell.Quickshell.screens = [];
    BrightnessService.ddcMonitors = [];
    BrightnessService.appleDisplayPresent = false;
    BrightnessService.ddcDetectionPending = false;
    suite.brightnessEvents = [];
    FixtureShell.Quickshell.commands = [];
  }

  function cleanup() {
    FixtureShell.Quickshell.screens = [];
    compare(BrightnessService.monitors.length, 0);
    compare(Settings.data.brightness.enableDdcSupport, false);
  }

  function test_unused_broken_getter_removed() {
    compare(typeof BrightnessService.getDetectedDisplays, "undefined");
  }

  function test_instances_are_screen_monitors_not_detection_records() {
    BrightnessService.ddcMonitors = [
      {
        model: "DDC Fixture",
        busNum: "7",
        isDdc: true
      }
    ];
    FixtureShell.Quickshell.screens = [internalScreen, ddcScreen];
    compare(BrightnessService.monitors.length, 2);
    const internal = BrightnessService.getMonitorForScreen(internalScreen);
    const ddc = BrightnessService.getMonitorForScreen(ddcScreen);
    verify(internal !== undefined);
    verify(ddc !== undefined);
    compare(internal.modelData, internalScreen);
    compare(ddc.modelData, ddcScreen);
    compare(internal.screenModel, "Internal Fixture");
    compare(ddc.screenModel, "DDC Fixture");
    compare(internal.busNum, "");
    compare(ddc.busNum, "7");
    compare(ddc.isDdc, false);
    compare(ddc.method, "internal");
    compare(BrightnessService.getAvailableMethods(), ["internal"]);
    verify(BrightnessService.monitors[0] !== BrightnessService.ddcMonitors[0]);
    FixtureShell.Quickshell.screens = [ddcScreen, internalScreen];
    compare(BrightnessService.monitors[0].modelData, ddcScreen);
    compare(BrightnessService.monitors[1].modelData, internalScreen);
    compare(BrightnessService.getMonitorForScreen(ddcScreen).busNum, "7");
    FixtureShell.Quickshell.screens = [internalScreen];
    compare(BrightnessService.monitors.length, 1);
    compare(BrightnessService.getMonitorForScreen(ddcScreen), undefined);
    compare(BrightnessService.ddcMonitors.length, 1);
  }

  function test_process_collect_exit_stop_with_ddc_disabled() {
    const process = FixtureProcesses.FixtureIo.processes.find(value => value.command[0] === "ddcutil");
    verify(process !== undefined);
    compare(process.running, false);
    const generation = BrightnessService.ddcDetectionGeneration;
    BrightnessService.requestDdcDetection();
    compare(process.running, false);
    compare(BrightnessService.ddcDetectionGeneration, generation);
    BrightnessService.ddcMonitors = [
      {
        model: "retained",
        busNum: "8",
        isDdc: true
      }
    ];
    process.running = true; // Inert fixture lifecycle only; never executes command.
    process.stdout.text = "Display 1\n I2C bus: /dev/i2c-7\n Model: DDC Fixture\n";
    process.stderr.text = "fixture error";
    process.stdout.streamFinished();
    process.stderr.streamFinished();
    compare(process.output, process.stdout.text);
    compare(process.errorOutput, "fixture error");
    process.exited(0);
    compare(process.output, "");
    compare(process.errorOutput, "");
    compare(process.exitObserved, true);
    compare(BrightnessService.ddcMonitors[0].model, "retained");
    process.running = false;
    compare(process.exitObserved, false);
    compare(process.running, false);
    compare(BrightnessService.ddcDetectionGeneration, generation);
    compare(BrightnessService.ddcDetectionPending, false);
    const warnings = Logger.warnings.length;
    process.running = true;
    process.running = false; // Failed-start callback with no exited signal.
    compare(Logger.warnings.length, warnings); // Disabled completions are ignored.
    compare(BrightnessService.ddcMonitors[0].model, "retained");
  }

  function test_apple_collector_updates_singleton_and_matching_monitor() {
    FixtureShell.Quickshell.screens = [internalScreen, appleScreen];
    const process = FixtureProcesses.FixtureIo.processes.find(value => value.command[0] === "sh" && value.command[2].indexOf("asdbctl") !== -1);
    verify(process !== undefined);
    process.stdout.text = "  fixture display  \n";
    process.stdout.streamFinished();
    compare(BrightnessService.appleDisplayPresent, true);
    compare(BrightnessService.getMonitorForScreen(appleScreen).isAppleDisplay, true);
    compare(BrightnessService.getMonitorForScreen(internalScreen).isAppleDisplay, false);
    process.stdout.text = " \n";
    process.stdout.streamFinished();
    compare(BrightnessService.appleDisplayPresent, false);
    compare(BrightnessService.getMonitorForScreen(appleScreen).isAppleDisplay, false);
  }

  function test_monitor_brightness_signals_before_recorded_commands() {
    BrightnessService.ddcMonitors = [
      {
        model: "DDC Fixture",
        busNum: "7",
        isDdc: true
      }
    ];
    FixtureShell.Quickshell.screens = [internalScreen, ddcScreen];
    const internal = BrightnessService.getMonitorForScreen(internalScreen);
    const ddc = BrightnessService.getMonitorForScreen(ddcScreen);
    internal.initProc.stdout.text = "/fixture/backlight\n40\n100\n";
    internal.initProc.stdout.streamFinished();
    ddc.initProc.stdout.text = "/fixture/ddc-disabled\n20\n100\n";
    ddc.initProc.stdout.streamFinished();
    compare(internal.brightness, 0.4);
    compare(ddc.brightness, 0.2);
    compare(internal.brightnessControlAvailable, true);
    compare(suite.brightnessEvents.length, 2);
    compare(suite.brightnessEvents[0].screen, internalScreen);
    compare(suite.brightnessEvents[1].screen, ddcScreen);
    suite.brightnessEvents = [];
    internal.setBrightness(0.65);
    compare(suite.brightnessEvents, [
      {
        screen: internalScreen,
        value: 0.65,
        stored: 0.65,
        commands: 0
      }
    ]);
    compare(FixtureShell.Quickshell.commands, [["brightnessctl", "s", "65%"]]);
    internal.refreshProc.stdout.text = "70\n100\n";
    internal.refreshProc.stdout.streamFinished();
    compare(suite.brightnessEvents.length, 2);
    compare(suite.brightnessEvents[1].value, 0.7);
    internal.refreshProc.stdout.streamFinished();
    compare(suite.brightnessEvents.length, 2);
    internal.brightness = NaN;
    internal.publishBrightnessUpdate();
    compare(suite.brightnessEvents.length, 2);
    ddc.setBrightness(0.3);
    compare(suite.brightnessEvents[2].screen, ddcScreen);
    compare(suite.brightnessEvents[2].value, 0.3);
    compare(FixtureShell.Quickshell.commands[1], ["brightnessctl", "s", "30%"]);
  }

  FixtureShell.ShellScreen {
    id: internalScreen
    name: "fixture-internal"
    model: "Internal Fixture"
  }
  FixtureShell.ShellScreen {
    id: ddcScreen
    name: "fixture-ddc"
    model: "DDC Fixture"
  }
  FixtureShell.ShellScreen {
    id: appleScreen
    name: "fixture-apple"
    model: "StudioDisplay Fixture"
  }

  Connections {
    target: BrightnessService
    function onMonitorBrightnessChanged(monitor, value) {
      suite.brightnessEvents = suite.brightnessEvents.concat([
        {
          screen: monitor.modelData,
          value: value,
          stored: monitor.brightness,
          commands: FixtureShell.Quickshell.commands.length
        }
      ]);
    }
  }
}
