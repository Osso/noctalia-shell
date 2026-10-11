import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets
import qs.Services.Compositor
import qs.Services.UI

Item {
  id: scene
  width: 800
  height: 600

  ShellScreen {
    id: primary
    name: "DP-1"
  }
  ShellScreen {
    id: secondary
    name: "HDMI-A-1"
  }
  Component {
    id: taskbarComponent
    Taskbar {
      widgetId: "Taskbar"
      section: "left"
      sectionWidgetIndex: 0
      width: implicitWidth
      height: implicitHeight
    }
  }

  TestCase {
    name: "ProductionTaskbar"
    when: windowShown
    property var widget

    function workspaces() {
      return [
        {
          id: 101,
          idx: 1,
          output: "DP-1",
          is_active: true,
          is_focused: true,
          active_window_id: 11
        },
        {
          id: 102,
          idx: 2,
          output: "DP-1",
          is_active: false,
          is_focused: false,
          active_window_id: 12
        },
        {
          id: 201,
          idx: 1,
          output: "HDMI-A-1",
          is_active: true,
          is_focused: false,
          active_window_id: 21
        }
      ];
    }

    function windowData(id, workspace, app, column, focused) {
      return {
        id: id,
        workspace_id: workspace,
        title: app + " window " + id,
        app_id: app,
        is_focused: focused,
        layout: {
          pos_in_scrolling_layout: [column, 1]
        }
      };
    }

    function init() {
      const settings = JSON.parse(JSON.stringify(Settings.data));
      settings.bar.position = "top";
      settings.bar.widgets.left = [
        {
          id: "Taskbar",
          hideMode: "visible",
          onlySameOutput: true,
          onlyActiveWorkspaces: true,
          colorizeIcons: false
        }
      ];
      Settings.data = settings;
      CompositorService.backend.recollectWorkspaces(workspaces());
      CompositorService.backend.recollectWindows([windowData(13, 101, "firefox", 2, false), windowData(21, 201, "mpv", 1, false), windowData(12, 102, "firefox", 1, false), windowData(11, 101, "zed", 1, true)]);
      Quickshell.commands = [];
      PanelService.events = [];
      BarService.settingsCalls = [];
      widget = createTemporaryObject(taskbarComponent, scene, {
        screen: primary
      });
      verify(widget !== null);
      wait(30);
    }

    function descendants(parent, predicate) {
      let matches = [];
      for (const child of parent.children) {
        if (predicate(child))
          matches.push(child);
        matches = matches.concat(descendants(child, predicate));
      }
      return matches;
    }

    function icons() {
      return descendants(widget, child => child.source !== undefined && child.asynchronous !== undefined);
    }

    function visibleIcons() {
      return icons().filter(icon => icon.visible);
    }

    function menu() {
      return descendants(widget, child => child.itemHeight === 24 && child.model !== undefined)[0];
    }

    function clickIcon(index, button) {
      const areas = descendants(visibleIcons()[index].parent, child => child.acceptedButtons !== undefined);
      compare(areas.length, 1);
      compare(areas[0].acceptedButtons, Qt.LeftButton | Qt.RightButton);
      compare(areas[0].preventStealing, true);
      compare(areas[0].hoverEnabled, true);
      compare(areas[0].cursorShape, Qt.PointingHandCursor);
      mouseClick(areas[0], areas[0].width / 2, areas[0].height / 2, button || Qt.LeftButton);
    }

    function test_order_filter_and_activation() {
      compare(icons().map(icon => icon.source), ["zed", "firefox", "firefox", "mpv"]);
      compare(visibleIcons().map(icon => icon.source), ["zed", "firefox"]);
      compare(widget.hasWindow, true);
      compare(visibleIcons()[0].opacity, 1);
      compare(visibleIcons()[1].opacity, 0.6);
      clickIcon(0);
      clickIcon(1);
      compare(Quickshell.commands, [["niri", "msg", "action", "focus-window", "--id", "11"], ["niri", "msg", "action", "focus-window", "--id", "13"]]);
      widget.widgetSettings = {
        hideMode: "visible",
        onlySameOutput: false,
        onlyActiveWorkspaces: true,
        colorizeIcons: false
      };
      wait(30);
      compare(visibleIcons().map(icon => icon.source), ["zed", "firefox", "mpv"]);
      widget.widgetSettings = {
        hideMode: "visible",
        onlySameOutput: false,
        onlyActiveWorkspaces: false,
        colorizeIcons: false
      };
      wait(30);
      compare(visibleIcons().map(icon => icon.source), ["zed", "firefox", "firefox", "mpv"]);
    }

    function test_workspace_group_transition() {
      const changed = workspaces();
      changed[0].is_active = false;
      changed[1].is_active = true;
      CompositorService.backend.recollectWorkspaces(changed);
      wait(30);
      compare(visibleIcons().map(icon => icon.source), ["firefox"]);
      clickIcon(0);
      compare(Quickshell.commands[0], ["niri", "msg", "action", "focus-window", "--id", "12"]);
      CompositorService.backend.handleWindowOpenedOrChanged({
        window: windowData(13, 102, "firefox", 2, false)
      });
      wait(30);
      compare(visibleIcons().map(icon => icon.source), ["firefox", "firefox"]);
      clickIcon(1);
      compare(Quickshell.commands[1], ["niri", "msg", "action", "focus-window", "--id", "13"]);
    }

    function test_context_actions_reset() {
      clickIcon(1, Qt.RightButton);
      wait(30);
      compare(widget.selectedWindow.id, 13);
      compare(menu().model.map(entry => entry.action), ["activate", "close", "widget-settings"]);
      compare(PanelService.events, ["open"]);
      menu().triggered("activate");
      compare(Quickshell.commands[0], ["niri", "msg", "action", "focus-window", "--id", "13"]);
      compare(widget.selectedWindow, null);
      compare(widget.selectedAppName, "");
      clickIcon(0, Qt.RightButton);
      wait(30);
      menu().triggered("close");
      compare(Quickshell.commands[1], ["niri", "msg", "action", "close-window", "--id", "11"]);
      clickIcon(0, Qt.RightButton);
      wait(30);
      menu().triggered("widget-settings");
      compare(BarService.settingsCalls, [
        {
          screen: "DP-1",
          section: "left",
          index: 0,
          id: "Taskbar"
        }
      ]);
      compare(widget.selectedWindow, null);
    }

    function test_launch_clear_reassign_data() {
      return [
        {
          tag: "horizontal",
          position: "top"
        },
        {
          tag: "vertical",
          position: "left"
        }
      ];
    }

    function test_launch_clear_reassign(data) {
      const settings = JSON.parse(JSON.stringify(Settings.data));
      settings.bar.position = data.position;
      Settings.data = settings;
      CompositorService.backend.handleWindowOpenedOrChanged({
        window: windowData(14, 101, "kitty", 3, false)
      });
      wait(30);
      compare(visibleIcons().map(icon => icon.source), ["zed", "firefox", "kitty"]);
      clickIcon(2);
      compare(Quickshell.commands[0], ["niri", "msg", "action", "focus-window", "--id", "14"]);
      widget.screen = secondary;
      wait(30);
      compare(visibleIcons().map(icon => icon.source), ["mpv"]);
      clickIcon(0);
      compare(Quickshell.commands[1], ["niri", "msg", "action", "focus-window", "--id", "21"]);
      CompositorService.backend.recollectWindows([]);
      CompositorService.backend.recollectWorkspaces([]);
      wait(30);
      compare(icons().length, 0);
      compare(widget.hasWindow, false);
      const reassigned = workspaces();
      reassigned[0].output = "HDMI-A-1";
      CompositorService.backend.recollectWorkspaces(reassigned);
      CompositorService.backend.recollectWindows([windowData(31, 101, "kitty", 1, true)]);
      wait(30);
      compare(visibleIcons().map(icon => icon.source), ["kitty"]);
      compare(widget.hasWindow, true);
      clickIcon(0);
      compare(Quickshell.commands[2], ["niri", "msg", "action", "focus-window", "--id", "31"]);
      widget.screen = primary;
      wait(30);
      compare(visibleIcons().length, 0);
      compare(widget.hasWindow, false);
      compare(Quickshell.commands.length, 3);
    }
  }
}
