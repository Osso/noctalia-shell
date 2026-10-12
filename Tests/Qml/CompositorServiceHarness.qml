import QtQuick
import QtTest
import Quickshell
import Fixture
import qs.Commons
import qs.Services.UI
import qs.Services.Compositor

TestCase {
  id: root
  name: "CompositorService"
  when: root.windowShown
  property var events: []

  Connections {
    target: CompositorService
    function onWorkspaceChanged() {
      root.events = root.events.concat(["workspace:" + CompositorService.workspaces.count]);
    }
    function onWindowListChanged() {
      root.events = root.events.concat(["windows:" + CompositorService.windows.count]);
    }
    function onActiveWindowChanged() {
      root.events = root.events.concat(["active:" + CompositorService.getFocusedWindowTitle()]);
    }
  }

  function suspendTimer() {
    return Array.from(CompositorService.resources).find(child => child.interval === 100);
  }

  function init() {
    root.suspendTimer().stop();
    CompositorService.lockAndSuspendCheckCount = 0;
    PanelService.lockScreen.active = false;
    PanelService.lockScreen.item = null;
    Quickshell.commands = [];
    FixtureBackend.actions = [];
    root.events = [];
  }

  function cleanup() {
    root.suspendTimer().stop();
  }

  function test_backend_selection_data() {
    return [
      {
        tag: "mango-priority",
        environment: {
          XDG_CURRENT_DESKTOP: "MaNgO",
          NIRI_SOCKET: "n",
          HYPRLAND_INSTANCE_SIGNATURE: "h",
          SWAYSOCK: "s"
        },
        kind: "Mango"
      },
      {
        tag: "niri-priority",
        environment: {
          NIRI_SOCKET: "n",
          HYPRLAND_INSTANCE_SIGNATURE: "h",
          SWAYSOCK: "s"
        },
        kind: "Niri"
      },
      {
        tag: "hyprland-priority",
        environment: {
          HYPRLAND_INSTANCE_SIGNATURE: "h",
          SWAYSOCK: "s"
        },
        kind: "Hyprland"
      },
      {
        tag: "sway",
        environment: {
          SWAYSOCK: "s"
        },
        kind: "Sway"
      },
      {
        tag: "existing-default",
        environment: {},
        kind: "Niri"
      }
    ];
  }

  function test_backend_selection(data) {
    Quickshell.environment = data.environment;
    CompositorService.detectCompositor();
    const backend = CompositorService.backend;
    compare(backend.kind, data.kind);
    verify(backend.initialized);
    compare(FixtureBackend.live, 1);
    compare(CompositorService.isMango, data.kind === "Mango");
    compare(CompositorService.isNiri, data.kind === "Niri");
    compare(CompositorService.isHyprland, data.kind === "Hyprland");
    compare(CompositorService.isSway, data.kind === "Sway");
    compare(CompositorService.workspaces.count, 1);
    compare(CompositorService.getCurrentWorkspace().id, 7);
    compare(CompositorService.getActiveWorkspaces()[0].id, 7);
    compare(CompositorService.windows.count, 1);
    compare(CompositorService.getFocusedWindow().id, 42);
    compare(CompositorService.getFocusedWindowTitle(), "Startupwindow");
    CompositorService.focusWindow({
      id: 42
    });
    CompositorService.closeWindow({
      id: 43
    });
    CompositorService.switchToWorkspace({
      id: 7
    });
    CompositorService.logout();
    compare(JSON.stringify(FixtureBackend.actions), JSON.stringify([[data.kind, "focus", 42], [data.kind, "close", 43], [data.kind, "workspace", 7], [data.kind, "logout"]]));
    compare(Quickshell.commands.length, 0);
  }

  function test_cache_loaded_event() {
    ShellState.isLoaded = false;
    CompositorService.displayScales = {};
    CompositorService.displayScalesLoaded = false;
    ShellState.display = {
      "DP-1": {
        scale: 1.5,
        width: 2560
      }
    };
    ShellState.isLoaded = true;
    compare(CompositorService.displayScalesLoaded, true);
    compare(CompositorService.getDisplayScale("DP-1"), 1.5);
    compare(CompositorService.getDisplayInfo("DP-1").width, 2560);
    compare(ShellState.writes, 0);
    ShellState.isLoaded = false;
    ShellState.display = {};
    ShellState.isLoaded = true;
    compare(CompositorService.displayScalesLoaded, true);
  }

  function test_events_replace_models_before_forwarding() {
    const backend = CompositorService.backend;
    backend.workspaces.clear();
    backend.workspaces.append({
      id: 8,
      isFocused: true,
      isActive: true
    });
    backend.workspaceChanged();
    backend.windows = [
      {
        id: 44,
        title: "Changed\r\nwindow",
        workspaceId: 8
      }
    ];
    backend.focusedWindowIndex = 0;
    backend.windowListChanged();
    backend.activeWindowChanged();
    compare(JSON.stringify(root.events), JSON.stringify(["workspace:1", "windows:1", "windows:1", "active:Changedwindow"]));
    compare(CompositorService.getWindowsForWorkspace(8)[0].id, 44);
    compare(CompositorService.getCurrentWorkspace().id, 8);
    backend.windows = [];
    backend.focusedWindowIndex = -1;
    backend.windowListChanged();
    compare(CompositorService.windows.count, 0);
    compare(CompositorService.getFocusedWindow(), null);
    compare(CompositorService.getFocusedWindowTitle(), "");
    backend.workspaces.clear();
    backend.workspaceChanged();
    compare(CompositorService.getCurrentWorkspace(), null);
    compare(CompositorService.getActiveWorkspaces().length, 0);
  }

  function test_suspend_timer_data() {
    return [
      {
        tag: "confirmed",
        active: true,
        loaded: true,
        threshold: 0
      },
      {
        tag: "component-timeout",
        active: true,
        loaded: false,
        threshold: 20
      },
      {
        tag: "activation-timeout",
        active: false,
        loaded: false,
        threshold: 30
      }
    ];
  }

  function test_suspend_timer(data) {
    CompositorService.lockAndSuspend();
    verify(PanelService.lockScreen.active);
    verify(root.suspendTimer().running);
    PanelService.lockScreen.active = data.active;
    if (data.threshold > 0) {
      tryCompare(CompositorService, "lockAndSuspendCheckCount", 1);
      compare(Quickshell.commands.length, 0);
      CompositorService.lockAndSuspendCheckCount = data.threshold;
    }
    PanelService.lockScreen.item = data.loaded ? {} : null;
    tryCompare(root.suspendTimer(), "running", false);
    compare(CompositorService.lockAndSuspendCheckCount, 0);
    compare(JSON.stringify(Quickshell.commands), JSON.stringify([["sh", "-c", "systemctl suspend || loginctl suspend"]]));
    wait(150);
    compare(Quickshell.commands.length, 1);
  }
}
