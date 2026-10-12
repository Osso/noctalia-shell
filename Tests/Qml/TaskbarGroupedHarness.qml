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
    id: groupedComponent
    TaskbarGrouped {
      widgetId: "TaskbarGrouped"
      section: "left"
      sectionWidgetIndex: 2
      width: implicitWidth
      height: implicitHeight
    }
  }

  TestCase {
    name: "ProductionTaskbarGrouped"
    when: windowShown
    property var widget

    function workspaces() {
      return [
        {
          id: 101,
          idx: 1,
          name: "Code",
          output: "DP-1",
          is_focused: true,
          is_active: true,
          is_urgent: false,
          active_window_id: 11
        },
        {
          id: 102,
          idx: 2,
          name: "Web",
          output: "DP-1",
          is_focused: false,
          is_active: false,
          is_urgent: false,
          active_window_id: 12
        },
        {
          id: 103,
          idx: 3,
          name: "Empty",
          output: "DP-1",
          is_focused: false,
          is_active: false,
          is_urgent: false,
          active_window_id: null
        },
        {
          id: 201,
          idx: 1,
          name: "Video",
          output: "HDMI-A-1",
          is_focused: false,
          is_active: true,
          is_urgent: false,
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
          id: "Clock"
        },
        {
          id: "Tray"
        },
        {
          id: "TaskbarGrouped",
          labelMode: "index",
          hideUnoccupied: false
        }
      ];
      Settings.data = settings;
      CompositorService.backend.recollectWorkspaces(workspaces());
      // Deliberately shuffled: real Niri normalization must order window columns.
      CompositorService.backend.recollectWindows([windowData(13, 101, "firefox", 2, false), windowData(21, 201, "mpv", 1, false), windowData(12, 102, "firefox", 1, false), windowData(11, 101, "zed", 1, true)]);
      Quickshell.commands = [];
      PanelService.events = [];
      BarService.settingsCalls = [];
      widget = createTemporaryObject(groupedComponent, scene, {
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

    function clickAreas() {
      return descendants(widget, child => child.acceptedButtons === (Qt.LeftButton | Qt.RightButton) && child.enabled);
    }

    function menu() {
      return descendants(widget, child => child.itemHeight === 24 && child.model !== undefined)[0];
    }

    function labels() {
      return descendants(widget, child => child.family !== undefined && child.visible).map(child => child.text);
    }

    function clickIcon(index, button) {
      const areas = descendants(icons()[index].parent, child => child.acceptedButtons !== undefined);
      compare(areas.length, 1);
      mouseClick(areas[0], areas[0].width / 2, areas[0].height / 2, button || Qt.LeftButton);
    }

    function badgeLabel(text) {
      const matches = descendants(widget, child => child.family !== undefined && child.text === text && child.visible);
      compare(matches.length, 1);
      return matches[0];
    }

    function badgeBackground(label) {
      const matches = label.parent.children.filter(child => child.radius !== undefined && child.z === 0 && child.width === label.parent.width && child.height === label.parent.height);
      compare(matches.length, 1);
      return matches[0];
    }

    function compareBadge(text, background, foreground) {
      const label = badgeLabel(text);
      compare(badgeBackground(label).color, background);
      compare(label.color, foreground);
    }

    function test_urgency_cooldown_survives_rebuild_data() {
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

    function test_urgency_cooldown_survives_rebuild(data) {
      const settings = JSON.parse(JSON.stringify(Settings.data));
      settings.bar.position = data.position;
      Settings.data = settings;
      compareBadge("2", NColor.mSecondary, NColor.mOnSecondary);

      const urgent = workspaces();
      urgent[1].is_urgent = true;
      CompositorService.backend.recollectWorkspaces(urgent);
      wait(30);
      compareBadge("2", NColor.mError, NColor.mOnError);

      // Recreate delegates on another output, then restore the cooled state.
      // Both outputs have workspace index 1; urgency must not leak between them.
      urgent[0].is_urgent = true;
      CompositorService.backend.recollectWorkspaces(urgent);
      widget.screen = secondary;
      wait(30);
      compareBadge("1", NColor.mSecondary, NColor.mOnSecondary);
      widget.screen = primary;
      CompositorService.backend.recollectWorkspaces(workspaces());
      wait(30);
      compareBadge("2", NColor.mError, NColor.mOnError);
      compareBadge("1", NColor.mPrimary, NColor.mOnPrimary);

      // A cleared urgent flag must not clear either badge before five seconds.
      wait(4500);
      compareBadge("2", NColor.mError, NColor.mOnError);
      const label = badgeLabel("2");
      tryCompare(badgeBackground(label), "color", NColor.mSecondary, 1200);
      compare(label.color, NColor.mOnSecondary);

      // Rebuilding after expiry must restore the settled non-urgent state.
      widget.screen = secondary;
      widget.screen = primary;
      wait(30);
      compareBadge("2", NColor.mSecondary, NColor.mOnSecondary);
    }

    function test_groups_order_geometry_and_clicks() {
      compare(widget.localWorkspaces.count, 3);
      compare(labels(), ["1", "2", "3"]);
      compare(icons().map(icon => icon.source), ["zed", "firefox", "firefox"]);
      for (const icon of icons()) {
        compare(icon.width, 32);
        compare(icon.height, 32);
      }
      for (let i = 0; i < 3; i++)
        clickIcon(i);
      compare(Quickshell.commands, [["niri", "msg", "action", "focus-window", "--id", "11"], ["niri", "msg", "action", "focus-window", "--id", "13"], ["niri", "msg", "action", "focus-window", "--id", "12"]]);
      const emptyArea = clickAreas()[3];
      mouseClick(emptyArea, emptyArea.width / 2, emptyArea.height / 2);
      compare(Quickshell.commands[3], ["niri", "msg", "action", "focus-workspace", "3"]);
    }

    function test_context_action_order_and_reset() {
      clickIcon(1, Qt.RightButton);
      wait(30);
      compare(widget.selectedWindow.id, 13);
      compare(widget.selectedAppName, "firefox");
      compare(menu().model.map(item => item.action), ["activate", "close", "widget-settings"]);
      compare(PanelService.events, ["open"]);
      menu().triggered("activate");
      compare(PanelService.events, ["open", "close"]);
      compare(Quickshell.commands[0], ["niri", "msg", "action", "focus-window", "--id", "13"]);
      compare(widget.selectedWindow, null);
      compare(widget.selectedAppName, "");
      clickIcon(2, Qt.RightButton);
      wait(30);
      menu().triggered("close");
      compare(Quickshell.commands[1], ["niri", "msg", "action", "close-window", "--id", "12"]);
      const emptyArea = clickAreas()[3];
      mouseClick(emptyArea, emptyArea.width / 2, emptyArea.height / 2, Qt.RightButton);
      wait(30);
      compare(menu().model.map(item => item.action), ["widget-settings"]);
      menu().triggered("widget-settings");
      compare(BarService.settingsCalls, [
        {
          screen: "DP-1",
          section: "left",
          index: 2,
          id: "TaskbarGrouped"
        }
      ]);
    }

    function test_launch_output_clear_and_reassignment_data() {
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

    function test_launch_output_clear_and_reassignment(data) {
      const settings = JSON.parse(JSON.stringify(Settings.data));
      settings.bar.position = data.position;
      Settings.data = settings;
      CompositorService.backend.handleWindowOpenedOrChanged({
        window: windowData(14, 102, "kitty", 2, false)
      });
      wait(30);
      compare(icons().map(icon => icon.source), ["zed", "firefox", "firefox", "kitty"]);
      clickIcon(3);
      compare(Quickshell.commands[0], ["niri", "msg", "action", "focus-window", "--id", "14"]);
      widget.screen = secondary;
      wait(30);
      compare(labels(), ["1"]);
      compare(icons().map(icon => icon.source), ["mpv"]);
      clickIcon(0);
      compare(Quickshell.commands[1], ["niri", "msg", "action", "focus-window", "--id", "21"]);
      CompositorService.backend.recollectWindows([]);
      CompositorService.backend.recollectWorkspaces([]);
      wait(30);
      compare(widget.localWorkspaces.count, 0);
      compare(icons().length, 0);
      compare(clickAreas().length, 0);
      widget.switchByOffset(1);
      compare(Quickshell.commands.length, 2);
      const reassigned = workspaces();
      reassigned[0].idx = 7;
      reassigned[0].output = "HDMI-A-1";
      CompositorService.backend.recollectWorkspaces(reassigned);
      CompositorService.backend.recollectWindows([windowData(31, 101, "kitty", 1, true)]);
      wait(30);
      compare(labels(), ["1", "7"]);
      compare(icons().map(icon => icon.source), ["kitty"]);
      clickIcon(0);
      compare(Quickshell.commands[2], ["niri", "msg", "action", "focus-window", "--id", "31"]);
      widget.screen = null;
      wait(30);
      compare(widget.localWorkspaces.count, 0);
      widget.screen = primary;
      wait(30);
      compare(labels(), ["2", "3"]);
    }
  }
}
