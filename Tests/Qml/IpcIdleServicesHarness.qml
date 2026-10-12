import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Services.Control
import qs.Services.Media
import qs.Services.Power
import qs.Services.UI

TestCase {
  id: testCase
  name: "IpcIdleServices"

  ShellScreen {
    id: firstScreen
    name: "first"
  }
  ShellScreen {
    id: secondScreen
    name: "second"
  }
  Component {
    id: ipcFactory
    IPCService {}
  }

  function handler(service, targetName) {
    for (const child of service.children) {
      if (child.target === targetName)
        return child;
    }
    fail("Missing private handler: " + targetName);
  }

  function init() {
    Quickshell.screens = [firstScreen, secondScreen];
    MediaService.seeks = [];
    Logger.warnings = [];
    Logger.errors = [];
    FixtureIo.commands = [];
    FixtureIo.signals = [];
    ToastService.notices = [];
  }

  function cleanup() {
    IdleInhibitorService.removeManualInhibitor();
    IdleInhibitorService.removeInhibitor("application");
    IdleInhibitorService.activeInhibitors = [];
    FixtureIo.process.running = false;
    IdleInhibitorService.strategy = "systemd";
  }

  function test_ipc_parse_and_response() {
    const ipc = createTemporaryObject(ipcFactory, testCase);
    verify(ipc !== null);
    const media = handler(ipc, "media");
    media.seekRelative("-12.5");
    media.seekByRatio("0.75");
    media.seekRelative("bad");
    media.seekByRatio("bad");
    compare(JSON.stringify(MediaService.seeks), JSON.stringify([
                                                                 {
                                                                   relative: -12.5
                                                                 },
                                                                 {
                                                                   ratio: 0.75
                                                                 }
                                                               ]));
    compare(Logger.warnings.length, 2);

    const state = handler(ipc, "state");
    ShellState.snapshot = {
      bar: {
        visible: true
      },
      count: 2
    };
    compare(JSON.stringify(JSON.parse(state.all())), JSON.stringify(ShellState.snapshot));
    ShellState.snapshot = null;
    verify(JSON.parse(state.all()).error.includes("State snapshot unavailable"));
    const circular = {};
    circular.self = circular;
    ShellState.snapshot = circular;
    verify(JSON.parse(state.all()).error.includes("Failed to serialize state:"));
    compare(Logger.errors.length, 2);
  }

  function test_screen_capture_two_instances_recreation() {
    const left = createTemporaryObject(ipcFactory, testCase);
    const right = createTemporaryObject(ipcFactory, testCase);
    verify(left !== null && right !== null);
    let leftResults = [];
    let rightResults = [];
    left.withTargetScreen(screen => leftResults.push(screen.name));
    left.withTargetScreen(screen => leftResults.push("should not run"));
    right.withTargetScreen(screen => rightResults.push(screen.name));
    tryCompare(left, "pendingCallback", null);
    tryCompare(right, "pendingCallback", null);
    compare(JSON.stringify(leftResults), '["second"]');
    compare(JSON.stringify(rightResults), '["second"]');
    compare(Logger.warnings.length, 1);

    Settings.data.general.allowPanelsOnScreenWithoutBar = false;
    Settings.data.bar.monitors = ["first"];
    left.withTargetScreen(screen => leftResults.push(screen.name));
    tryCompare(left, "pendingCallback", null);
    compare(JSON.stringify(leftResults), '["second","first"]');
    Settings.data.general.allowPanelsOnScreenWithoutBar = true;
    left.withTargetScreen(screen => leftResults.push(screen.name));
    tryCompare(left, "pendingCallback", null);
    compare(JSON.stringify(leftResults), '["second","first","second"]');

    Quickshell.screens = [firstScreen];
    right.withTargetScreen(screen => rightResults.push(screen.name));
    compare(JSON.stringify(rightResults), '["second","first"]');
    Settings.data.bar.monitors = [];
  }

  function test_toggle_registry_and_exit() {
    const service = IdleInhibitorService;
    const ipc = createTemporaryObject(ipcFactory, testCase);
    const toggle = handler(ipc, "idleInhibitor");
    compare(toggle.toggle(), true);
    verify(service.isInhibited);
    compare(JSON.stringify(service.activeInhibitors), '["manual"]');
    compare(JSON.stringify(FixtureIo.commands), JSON.stringify([["systemd-inhibit", "--what=idle", "--why=Manually activated by user", "--mode=block", "sleep", "infinity"]]));
    compare(service.addInhibitor("manual"), false);
    compare(service.addInhibitor("application", "Playback"), true);
    compare(FixtureIo.commands.length, 1);
    compare(toggle.toggle(), false);
    verify(service.isInhibited);
    compare(service.removeInhibitor("application"), true);
    verify(!service.isInhibited);
    compare(JSON.stringify(FixtureIo.signals), '[15]');
    compare(service.removeInhibitor("missing"), false);
    compare(ToastService.notices.length, 2);

    service.strategy = "wayland";
    compare(toggle.toggle(), true);
    compare(JSON.stringify(FixtureIo.commands[1]), '["wayhibitor"]');
    FixtureIo.process.running = false;
    FixtureIo.process.exited(7, 0);
    verify(!service.isInhibited);
    compare(JSON.stringify(service.activeInhibitors), '["manual"]');
  }

  function test_timeout_event_and_cancellation() {
    const service = IdleInhibitorService;
    service.changeTimeout(-1);
    compare(service.timeout, null);
    verify(!service.isInhibited);
    service.changeTimeout(1);
    compare(service.timeout, 1);
    verify(service.isInhibited);
    tryCompare(service, "isInhibited", false, 2500);
    compare(service.timeout, null);
    compare(service.activeInhibitors.length, 0);
    compare(JSON.stringify(FixtureIo.signals), '[15]');

    service.addManualInhibitor(5);
    service.changeTimeout(2);
    compare(service.timeout, 7);
    service.addManualInhibitor(null);
    compare(service.timeout, null);
    wait(1100);
    verify(service.isInhibited);
    service.removeManualInhibitor();
    verify(!service.isInhibited);
  }
}
