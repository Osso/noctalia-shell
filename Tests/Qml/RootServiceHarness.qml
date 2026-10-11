import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import Quickshell.Bluetooth
import qs.Commons
import qs.Services.Compositor
import qs.Services.Control
import qs.Services.Hardware
import qs.Services.Networking
import qs.Services.System
import qs.Services.UI

TestCase {
  name: "RootServices"
  when: windowShown

  IPCService {
    id: ipc
  }
  ShellScreen {
    id: primary
    name: "DP-1"
    model: "Fixture"
  }
  ShellScreen {
    id: secondary
    name: "DP-2"
    model: "Fixture"
  }

  function timer(owner, interval) {
    return Array.from(owner.resources).find(child => child.interval === interval);
  }

  function test_compositor_events_and_suspend_timer() {
    verify(CompositorService.isNiri);
    const backend = CompositorService.backend;
    verify(backend.initialized);
    backend.workspaces.append({
      id: 7,
      isFocused: true,
      isActive: true
    });
    backend.workspaceChanged();
    compare(CompositorService.workspaces.count, 1);
    compare(CompositorService.getCurrentWorkspace().id, 7);
    backend.windows = [
      {
        id: 42,
        title: "Fixture window",
        workspaceId: 7
      }
    ];
    backend.windowListChanged();
    compare(CompositorService.windows.count, 1);
    backend.focusedWindowIndex = 0;
    compare(CompositorService.getFocusedWindowTitle(), "Fixture window");
    CompositorService.lockAndSuspend();
    verify(PanelService.lockScreen.active);
    compare(CompositorService.lockAndSuspendCheckCount, 0);
    const before = Quickshell.commands.length;
    PanelService.lockScreen.item = {};
    tryVerify(() => Quickshell.commands.length === before + 1);
    compare(CompositorService.lockAndSuspendCheckCount, 0);
    compare(Quickshell.commands[before][2], "systemctl suspend || loginctl suspend");
    verify(!timer(CompositorService, 100).running);
  }

  function test_ipc_screen_callback_and_debounce() {
    Quickshell.screens = [primary];
    let received = null;
    ipc.withTargetScreen(screen => received = screen);
    compare(received, primary);
    Quickshell.screens = [primary, secondary];
    Settings.data.general.allowPanelsOnScreenWithoutBar = false;
    Settings.data.bar.monitors = [primary.name];
    received = null;
    ipc.withTargetScreen(screen => received = screen);
    ipc.withTargetScreen(screen => fail("must reject overlapping operation"));
    tryVerify(() => received === primary);
    compare(ipc.pendingCallback, null);
    Settings.data.general.allowPanelsOnScreenWithoutBar = true;
    received = null;
    ipc.withTargetScreen(screen => received = screen);
    tryVerify(() => received === secondary);
    compare(ipc.pendingCallback, null);
    Quickshell.screens = [];
  }

  function test_brightness_detection_disable_discards_generation() {
    compare(BrightnessService.ddcMonitors.length, 0);
    Settings.data.brightness.enableDdcSupport = true;
    const process = FixtureIo.find("ddcutil detect");
    verify(process.running);
    const generation = BrightnessService.ddcDetectionGeneration;
    process.finish(0, "Display 1\n   I2C bus: /dev/i2c-6\n   Model: Fixture Monitor\n   VCP version: 2.2", "");
    compare(BrightnessService.ddcMonitors.length, 1);
    compare(BrightnessService.ddcMonitors[0].busNum, "6");
    BrightnessService.ddcDetectionPending = true;
    Settings.data.brightness.enableDdcSupport = false;
    compare(BrightnessService.ddcDetectionGeneration, generation + 1);
    compare(BrightnessService.ddcDetectionPending, false);
    compare(BrightnessService.ddcMonitors.length, 0);
    verify(!process.running);
    BrightnessService.finishDdcDetection(generation, 0, "Display 1\n   I2C bus: /dev/i2c-6\n   Model: Fixture Monitor\n   VCP version: 2.2", "");
    compare(BrightnessService.ddcMonitors.length, 0);
  }

  function test_bluetooth_state_and_discovery_events() {
    verify(BluetoothService.available);
    const adapter = Bluetooth.defaultAdapter;
    const before = ToastService.messages.length;
    adapter.state = BluetoothAdapterState.Enabling;
    compare(ToastService.messages.length, before);
    adapter.enabled = true;
    adapter.state = BluetoothAdapterState.Enabled;
    compare(ToastService.messages.length, before + 1);
    compare(ToastService.messages[before][1], "toast.bluetooth.enabled");
    tryCompare(adapter, "discovering", true, 2000);
    adapter.state = BluetoothAdapterState.Blocked;
    verify(BluetoothService.lastBluetoothBlocked);
    const process = FixtureIo.find("rfkill list wifi");
    verify(process.running);
    process.finish(0, "Soft blocked: no", "");
    compare(ToastService.messages.length, before + 2);
    verify(!BluetoothService.airplaneModeToggled);
    adapter.enabled = false;
    adapter.state = BluetoothAdapterState.Disabled;
    process.finish(1, "", "fixture rfkill failure");
    compare(ToastService.messages[ToastService.messages.length - 1][1], "toast.bluetooth.disabled");
  }

  function test_notification_history_persistence_and_progress_event() {
    verify(NotificationService.historyFile.endsWith("notifications.json"));
    const historyFile = Array.from(NotificationService.children).find(child => child.path === NotificationService.historyFile);
    verify(historyFile !== undefined);
    NotificationService.addToHistory({
      id: "fixture",
      summary: "Concrete notification",
      body: "Body",
      appName: "Fixture",
      urgency: 1,
      timestamp: new Date(1000),
      cachedImage: ""
    });
    const writes = FixtureIo.writes;
    NotificationService.performSaveHistory();
    compare(FixtureIo.writes, writes + 1);
    NotificationService.historyList.clear();
    historyFile.loaded();
    compare(NotificationService.historyList.count, 1);
    compare(NotificationService.historyList.get(0).summary, "Concrete notification");
    compare(NotificationService.historyList.get(0).timestamp.getTime(), 1000);
    NotificationService.activeNotifications = {
      fixture: {
        metadata: {
          duration: 10000,
          paused: false,
          timestamp: Date.now() - 5000
        }
      }
    };
    NotificationService.activeList.append({
      id: "fixture",
      progress: 1
    });
    const progressTimer = timer(NotificationService, 50);
    verify(progressTimer.running);
    tryVerify(() => NotificationService.activeList.get(0).progress < 0.6);
    const progress = NotificationService.activeList.get(0).progress;
    verify(progress > 0.4 && progress < 0.6);
    NotificationService.activeList.clear();
    verify(!progressTimer.running);
    NotificationService.activeNotifications = {};
    NotificationService.imageQueue = [
      {
        src: "",
        imageId: "one"
      },
      {
        src: "",
        imageId: "two"
      }
    ];
    const panel = Array.from(NotificationService.children).find(child => child.mask !== undefined);
    const image = panel.children[0];
    image.processNextImage();
    compare(NotificationService.imageQueue.length, 1);
    compare(NotificationService.imageQueue[0].imageId, "two");
    image.processNextImage();
    compare(NotificationService.imageQueue.length, 0);
    compare(image.source.toString(), "");
  }
}
