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

  // Production exposes an Item; all runtime fixtures derive from Backend.
  function fixtureBackend(): Backend {
    return CompositorService.backend as Backend;
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
    const backend = root.fixtureBackend();
    root.compare(backend.kind, data.kind);
    root.verify(backend.initialized);
    root.compare(FixtureBackend.live, 1);
    root.compare(CompositorService.isMango, data.kind === "Mango");
    root.compare(CompositorService.isNiri, data.kind === "Niri");
    root.compare(CompositorService.isHyprland, data.kind === "Hyprland");
    root.compare(CompositorService.isSway, data.kind === "Sway");
    root.compare(CompositorService.workspaces.count, 1);
    root.compare(CompositorService.getCurrentWorkspace().id, 7);
    root.compare(CompositorService.getActiveWorkspaces()[0].id, 7);
    root.compare(CompositorService.windows.count, 1);
    root.compare(CompositorService.getFocusedWindow().id, 42);
    root.compare(CompositorService.getFocusedWindowTitle(), "Startupwindow");
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
    root.compare(JSON.stringify(FixtureBackend.actions), JSON.stringify([[data.kind, "focus", 42], [data.kind, "close", 43], [data.kind, "workspace", 7], [data.kind, "logout"]]));
    root.compare(Quickshell.commands.length, 0);
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
    root.compare(CompositorService.displayScalesLoaded, true);
    root.compare(CompositorService.getDisplayScale("DP-1"), 1.5);
    root.compare(CompositorService.getDisplayInfo("DP-1").width, 2560);
    root.compare(ShellState.writes, 0);
    ShellState.isLoaded = false;
    ShellState.display = {};
    ShellState.isLoaded = true;
    root.compare(CompositorService.displayScalesLoaded, true);
  }

  function test_events_replace_models_before_forwarding() {
    const backend = root.fixtureBackend();
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
    root.compare(JSON.stringify(root.events), JSON.stringify(["workspace:1", "windows:1", "windows:1", "active:Changedwindow"]));
    root.compare(CompositorService.getWindowsForWorkspace(8)[0].id, 44);
    root.compare(CompositorService.getCurrentWorkspace().id, 8);
    backend.windows = [];
    backend.focusedWindowIndex = -1;
    backend.windowListChanged();
    root.compare(CompositorService.windows.count, 0);
    root.compare(CompositorService.getFocusedWindow(), null);
    root.compare(CompositorService.getFocusedWindowTitle(), "");
    backend.workspaces.clear();
    backend.workspaceChanged();
    root.compare(CompositorService.getCurrentWorkspace(), null);
    root.compare(CompositorService.getActiveWorkspaces().length, 0);
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
    root.verify(PanelService.lockScreen.active);
    root.verify(root.suspendTimer().running);
    PanelService.lockScreen.active = data.active;
    if (data.threshold > 0) {
      root.tryCompare(CompositorService, "lockAndSuspendCheckCount", 1);
      root.compare(Quickshell.commands.length, 0);
      CompositorService.lockAndSuspendCheckCount = data.threshold;
    }
    PanelService.lockScreen.item = data.loaded ? {} : null;
    root.tryCompare(root.suspendTimer(), "running", false);
    root.compare(CompositorService.lockAndSuspendCheckCount, 0);
    root.compare(JSON.stringify(Quickshell.commands), JSON.stringify([["sh", "-c", "systemctl suspend || loginctl suspend"]]));
    root.wait(150);
    root.compare(Quickshell.commands.length, 1);
  }
}
