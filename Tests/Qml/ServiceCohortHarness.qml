import Fixture
import QtQuick
import QtTest
import Quickshell.Hyprland
import Quickshell.I3
import Quickshell.Io
import Quickshell.Wayland
import qs.Services.Compositor
import qs.Services.Keyboard

TestCase {
  id: testCase
  name: "ServiceCohort"
  property var service: null
  property var signalOrder: []

  Component {
    id: niriFactory
    NiriService {}
  }
  Component {
    id: swayFactory
    SwayService {}
  }
  Component {
    id: hyprlandFactory
    HyprlandService {}
  }
  Component {
    id: modelFactory
    EventModel {}
  }
  SignalSpy {
    id: capsSpy
    target: LockKeysService
    signalName: "capsLockChanged"
  }
  SignalSpy {
    id: numSpy
    target: LockKeysService
    signalName: "numLockChanged"
  }
  SignalSpy {
    id: scrollSpy
    target: LockKeysService
    signalName: "scrollLockChanged"
  }
  SignalSpy {
    id: workspaceSpy
    target: testCase.service
    signalName: "workspaceChanged"
  }
  SignalSpy {
    id: windowsSpy
    target: testCase.service
    signalName: "windowListChanged"
  }
  Connections {
    target: testCase.service
    function onWindowListChanged() {
      testCase.signalOrder.push("windows");
    }
    function onActiveWindowChanged() {
      testCase.signalOrder.push("active");
    }
  }

  function child(owner, predicate) {
    for (let i = 0; i < owner.data.length; ++i) {
      if (predicate(owner.data[i]))
        return owner.data[i];
    }
    fail("service child not found");
  }

  function cleanup() {
    if (service) {
      service.destroy();
      service = null;
      wait(0);
    }
    compare(FixtureIo.liveSockets, 0);
    workspaceSpy.clear();
    windowsSpy.clear();
    signalOrder = [];
  }

  function test_lock_initial_reads_and_transitions() {
    const locks = LockKeysService;
    const directory = child(locks, value => value.entries !== undefined);
    FixtureIo.files = {
      "/sys/class/leds/kbd::capslock/brightness": "1\n",
      "/sys/class/leds/kbd::numlock/brightness": "0\n",
      "/sys/class/leds/kbd::scrolllock/brightness": "1\n"
    };
    directory.entries = ["unrelated", "kbd::capslock", "second::capslock", "kbd::numlock", "kbd::scrolllock"];
    capsSpy.clear();
    numSpy.clear();
    scrollSpy.clear();
    directory.status = 1;
    compare(locks.pendingInitialReads, 3);
    compare(locks.initialCheckDone, false);
    tryCompare(locks, "initialCheckDone", true);
    compare(locks.pendingInitialReads, 0);
    compare(locks.capsLockOn, true);
    compare(locks.numLockOn, false);
    compare(locks.scrollLockOn, true);
    compare(capsSpy.count + numSpy.count + scrollSpy.count, 0);
    compare(FixtureIo.reloads, [locks.capsBrightnessPath, locks.numBrightnessPath, locks.scrollBrightnessPath]);

    FixtureIo.files = {
      "/sys/class/leds/kbd::capslock/brightness": "0\n",
      "/sys/class/leds/kbd::numlock/brightness": "1\n",
      "/sys/class/leds/kbd::scrolllock/brightness": "0\n"
    };
    locks.refreshAllStates();
    tryCompare(capsSpy, "count", 1);
    compare(numSpy.count, 1);
    compare(scrollSpy.count, 1);
    compare(capsSpy.signalArguments[0][0], false);
    compare(numSpy.signalArguments[0][0], true);
    compare(scrollSpy.signalArguments[0][0], false);
    locks.refreshAllStates();
    wait(0);
    compare(capsSpy.count + numSpy.count + scrollSpy.count, 3);
    locks.numBrightnessPath = "";
    locks.refreshAllStates();
    compare(locks.numLockOn, false);
    compare(numSpy.signalArguments[1][0], false);
  }

  function test_niri_socket_parsing_order_and_disposal() {
    service = niriFactory.createObject(testCase);
    compare(FixtureIo.liveSockets, 2);
    const sockets = service.data.filter(value => value.parser !== undefined);
    compare(sockets.length, 2);
    const command = sockets[0];
    const events = sockets[1];
    FixtureIo.writes = [];
    service.initialize();
    compare(command.connected, true);
    compare(events.connected, true);
    compare(FixtureIo.writes.map(value => value.value), ['"EventStream"\n', '"Workspaces"\n', '"Windows"\n', '"Outputs"\n']);
    verify(FixtureIo.writes.every(value => value.connected));
    events.parser.read(JSON.stringify({
      WorkspacesChanged: {
        workspaces: [
          {
            id: 3,
            idx: 2,
            output: "DP-1",
            is_active: true,
            active_window_id: 9
          },
          {
            id: 1,
            idx: 1,
            output: "DP-1",
            is_focused: true
          },
          {
            id: 2,
            idx: 1,
            output: "HDMI-1"
          }
        ]
      }
    }));
    compare(workspaceSpy.count, 1);
    compare(service.workspaces.count, 3);
    compare(service.workspaces.get(0).id, 1);
    compare(service.workspaces.get(1).isOccupied, true);
    command.parser.read(JSON.stringify({
      Ok: {
        Outputs: {
          "DP-1": {
            name: "DP-1",
            logical: {
              scale: 1.5,
              width: 1280,
              height: 720,
              x: 10,
              y: 20
            },
            physical_size: [500, 300],
            modes: [
              {
                refresh_rate: 60000
              }
            ]
          }
        }
      }
    }));
    compare(CompositorService.scales["DP-1"].scale, 1.5);
    compare(CompositorService.scales["DP-1"].refresh_rate, 60000);
    compare(CompositorService.scales["DP-1"].x, 10);
    command.parser.read(JSON.stringify({
      Ok: {
        Windows: [
          {
            id: 9,
            workspace_id: 3,
            is_focused: true,
            title: "Nine",
            layout: {
              pos_in_scrolling_layout: [5, 0]
            }
          },
          {
            id: 4,
            workspace_id: 1,
            layout: {}
          }
        ]
      }
    }));
    compare(service.windows[0].id, 4);
    compare(service.windows[1].output, "DP-1");
    compare(service.focusedWindowIndex, 1);
    compare(signalOrder, ["windows", "active"]);
    events.parser.read(JSON.stringify({
      WindowFocusChanged: {
        id: 4
      }
    }));
    compare(service.focusedWindowIndex, 0);
    compare(service.windows[1].isFocused, false);
    events.parser.read(JSON.stringify({
      WindowClosed: {
        id: 4
      }
    }));
    compare(service.focusedWindowIndex, -1);
    compare(service.windows.length, 1);
    events.parser.read(JSON.stringify({
      KeyboardLayoutsChanged: {
        keyboard_layouts: {
          names: ["English", "French"],
          current_idx: 0
        }
      }
    }));
    events.parser.read(JSON.stringify({
      KeyboardLayoutSwitched: {
        idx: 1
      }
    }));
    compare(KeyboardLayoutService.currentLayout, "French");
    events.parser.read(JSON.stringify({
      OverviewOpenedOrClosed: {
        is_open: true
      }
    }));
    compare(service.overviewActive, true);
    events.parser.read(JSON.stringify({
      WorkspaceActivated: {
        id: 3
      }
    }));
    events.parser.read(JSON.stringify({
      OutputsChanged: {}
    }));
    events.parser.read(JSON.stringify({
      ConfigLoaded: {}
    }));
    compare(FixtureIo.writes.slice(-3).map(value => value.value), ['"Workspaces"\n', '"Outputs"\n', '"Outputs"\n']);
    compare(command.connected, true);
    compare(events.connected, true);
    events.parser.read(JSON.stringify({
      WorkspacesChanged: {
        workspaces: []
      }
    }));
    compare(service.workspaces.count, 0);
    // Disposal must release both sockets; a new service starts disconnected.
    service.destroy();
    service = null;
    wait(0);
    compare(FixtureIo.liveSockets, 0);
    service = niriFactory.createObject(testCase);
    verify(service.data.filter(value => value.parser !== undefined).every(value => !value.connected));
  }

  function test_compositor_events_and_rebind_data() {
    return [
      {
        tag: "sway",
        hyprland: false
      },
      {
        tag: "hyprland",
        hyprland: true
      }
    ];
  }

  function selectBackend(hyprland): var {
    return hyprland ? Hyprland : I3;
  }

  function test_compositor_events_and_rebind(row) {
    const backend = selectBackend(row.hyprland);
    const oldModel = modelFactory.createObject(testCase) as EventModel;
    const newModel = modelFactory.createObject(testCase) as EventModel;
    backend.workspaces = oldModel;
    const toplevels = row.hyprland ? Hyprland.toplevels : ToplevelManager.toplevels;
    toplevels.values = [
      {
        address: "abc",
        title: "Editor",
        appId: "editor",
        activated: true,
        workspace: {
          id: 2
        },
        monitor: {
          name: "DP-1"
        }
      }
    ];
    service = (row.hyprland ? hyprlandFactory : swayFactory).createObject(testCase);
    oldModel.values = [
      {
        id: 2,
        num: 2,
        name: "two",
        monitor: {
          name: "DP-1"
        },
        active: true,
        focused: true
      }
    ];
    compare(service.workspaces.count, 0); // Connections disabled before initialize.
    service.initialize();
    tryCompare(service.workspaces, "count", 1);
    compare(service.workspaces.get(0).idx, 2);
    compare(service.workspaces.get(0).output, "DP-1");
    compare(service.windows[0].title, "Editor");
    compare(service.focusedWindowIndex, 0);
    const processes = service.data.filter(value => value.command !== undefined);
    const outputs = processes[0];
    const keyboards = processes[1];
    const output = row.hyprland ? {
      name: "DP-1",
      scale: 1.25,
      width: 1920,
      height: 1080,
      x: 50,
      refreshRate: 144,
      activeWorkspace: {
        id: 2
      }
    } : {
      name: "DP-1",
      scale: 1.25,
      current_mode: {
        width: 1920,
        height: 1080,
        refresh: 144000
      },
      rect: {
        x: 50,
        y: 0
      },
      current_workspace: "two",
      active: true
    };
    const encoded = JSON.stringify([output]);
    outputs.stdout.read(encoded.slice(0, 12));
    outputs.stdout.read(encoded.slice(12));
    outputs.exited(0);
    compare(CompositorService.scales["DP-1"].width, 1920);
    compare(CompositorService.scales["DP-1"].scale, 1.25);
    compare(CompositorService.scales["DP-1"].x, 50);
    compare(outputs.accumulatedOutput, "");
    outputs.stdout.read("[]");
    outputs.exited(0);
    compare(Object.keys(CompositorService.scales).length, 0);
    keyboards.stdout.read(JSON.stringify(row.hyprland ? {
      keyboards: [
        {
          main: true,
          active_keymap: "French"
        }
      ]
    } : [
      {
        type: "keyboard",
        xkb_active_layout_name: "French"
      }
    ]));
    keyboards.exited(0);
    compare(KeyboardLayoutService.currentLayout, "French");
    compare(keyboards.accumulatedOutput, "");

    workspaceSpy.clear();
    backend.workspaces = newModel;
    oldModel.values = [];
    compare(workspaceSpy.count, 0);
    newModel.values = [
      {
        id: 5,
        num: 5,
        name: "five",
        monitor: {
          name: "HDMI-1"
        },
        urgent: true
      }
    ];
    compare(workspaceSpy.count, 1);
    compare(service.workspaces.get(0).idx, 5);
    compare(service.workspaces.get(0).isUrgent, true);
    outputs.running = false;
    windowsSpy.clear();
    backend.rawEvent(row.hyprland ? {
      name: "monitoradded",
      data: ""
    } : {
      type: "output",
      data: ""
    });
    compare(workspaceSpy.count, 2);
    tryCompare(outputs, "running", true);
    tryCompare(windowsSpy, "count", 1);
    backend.rawEvent(row.hyprland ? {
      name: "activelayout",
      data: "kbd,English"
    } : {
      type: "get_inputs",
      data: "kbd,English"
    });
    compare(KeyboardLayoutService.currentLayout, "English");
    service.destroy();
    service = null;
    wait(0);
    newModel.values = [];
    backend.rawEvent(row.hyprland ? {
      name: "monitorremoved",
      data: ""
    } : {
      type: "output",
      data: ""
    });
    wait(60);
    compare(workspaceSpy.count, 3); // Last live keyboard event only; nothing after disposal.
    oldModel.destroy();
    newModel.destroy();
  }
}
