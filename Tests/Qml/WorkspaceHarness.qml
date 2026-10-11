import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets
import qs.Services.Compositor

Item {
  id: scene

  width: 600
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
    id: workspaceComponent

    Workspace {
      widgetId: "Workspace"
      width: implicitWidth
      height: implicitHeight
    }
  }

  TestCase {
    id: test

    property var widget

    function fixtures() {
      return [
        {
          "id": 202,
          "idx": 2,
          "name": "Chat",
          "output": "HDMI-A-1",
          "is_focused": false,
          "is_active": false,
          "is_urgent": true,
          "active_window_id": 22
        },
        {
          "id": 103,
          "idx": 3,
          "name": "Empty",
          "output": "DP-1",
          "is_focused": false,
          "is_active": false,
          "is_urgent": false,
          "active_window_id": null
        },
        {
          "id": 101,
          "idx": 1,
          "name": "Code",
          "output": "DP-1",
          "is_focused": true,
          "is_active": true,
          "is_urgent": false,
          "active_window_id": 11
        },
        {
          "id": 201,
          "idx": 1,
          "name": "Video",
          "output": "HDMI-A-1",
          "is_focused": false,
          "is_active": true,
          "is_urgent": false,
          "active_window_id": 21
        },
        {
          "id": 102,
          "idx": 2,
          "name": "Web",
          "output": "DP-1",
          "is_focused": false,
          "is_active": false,
          "is_urgent": true,
          "active_window_id": 12
        }
      ];
    }

    function init() {
      const data = JSON.parse(JSON.stringify(Settings.data));
      data.bar.position = "top";
      Settings.data = data;
      CompositorService.backend.recollectWorkspaces(fixtures());
      CompositorService.backend.recollectWindows([
        {
          "id": 12,
          "workspace_id": 102,
          "title": "Browser",
          "app_id": "firefox",
          "is_focused": false,
          "layout": {
            "pos_in_scrolling_layout": [2, 1]
          }
        },
        {
          "id": 11,
          "workspace_id": 101,
          "title": "Editor",
          "app_id": "zed",
          "is_focused": true,
          "layout": {
            "pos_in_scrolling_layout": [1, 1]
          }
        }
      ]);
      Quickshell.commands = [];
      widget = createTemporaryObject(workspaceComponent, scene, {
        "screen": primary
      });
      verify(widget !== null);
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

    function visiblePills() {
      return descendants(widget, child => {
        return child.acceptedButtons === Qt.LeftButton && child.visible;
      }).sort((a, b) => {
        const first = a.mapToItem(widget, 0, 0);
        const second = b.mapToItem(widget, 0, 0);
        return widget.isVertical ? first.y - second.y : first.x - second.x;
      });
    }

    function labelItems() {
      return descendants(widget, child => {
        return child.family !== undefined && child.visible;
      });
    }

    function labels() {
      return labelItems().map(child => child.text);
    }

    function clickOrder(expected) {
      wait(20);
      const pills = visiblePills();
      compare(pills.length, expected.length);
      for (let i = 0; i < pills.length; i++) {
        mouseClick(pills[i], pills[i].width / 2, pills[i].height / 2);
        compare(Quickshell.commands[i], ["niri", "msg", "action", "focus-workspace", expected[i].toString()]);
      }
    }

    function test_initial_geometry() {
      // Check synchronous completed-component geometry, before polish/animation.
      compare(widget.localWorkspaces.count, 3);
      compare(widget.implicitWidth, 123);
      compare(widget.implicitHeight, 40);
      compare(widget.width, 123);
      compare(widget.height, 40);
      wait(20);
      compare(labels(), ["1", "2", "3"]);
      const pills = visiblePills();
      compare(pills.length, 3);
      fuzzyCompare(pills[0].width, 57.2, 0.0001);
      fuzzyCompare(pills[1].width, 26, 0.0001);
      fuzzyCompare(pills[2].width, 26, 0.0001);
      verify(pills[0].mapToItem(widget, 0, 0).x < pills[1].mapToItem(widget, 0, 0).x);
    }

    function test_output_assignment_and_click_order() {
      clickOrder([1, 2, 3]);
      widget.screen = secondary;
      Quickshell.commands = [];
      wait(20);
      compare(labels(), ["1", "2"]);
      clickOrder([1, 2]);
      const moved = fixtures();
      moved[0].output = "DP-1";
      moved[0].idx = 4;
      CompositorService.backend.recollectWorkspaces(moved);
      widget.screen = primary;
      Quickshell.commands = [];
      clickOrder([1, 2, 3, 4]);
    }

    function test_vertical_labels_and_activation() {
      const data = JSON.parse(JSON.stringify(Settings.data));
      data.bar.position = "left";
      Settings.data = data;
      widget.widgetSettings = {
        "labelMode": "name",
        "characterCount": 3
      };
      wait(20);
      compare(labels(), ["Co", "We", "Em"]);
      compare(widget.implicitWidth, 40);
      compare(widget.implicitHeight, 123);
      const pills = visiblePills();
      fuzzyCompare(pills[0].height, 57.2, 0.0001);
      fuzzyCompare(pills[1].height, 26, 0.0001);
      clickOrder([1, 2, 3]);
      const activated = fixtures();
      activated[2].is_focused = false;
      activated[2].is_active = false;
      activated[4].is_focused = true;
      activated[4].is_active = true;
      CompositorService.backend.recollectWorkspaces(activated);
      wait(20);
      const updated = visiblePills();
      fuzzyCompare(updated[0].height, 26, 0.0001);
      fuzzyCompare(updated[1].height, 57.2, 0.0001);
      Quickshell.commands = [];
      widget.switchByOffset(1);
      widget.switchByOffset(-1);
      compare(Quickshell.commands, [["niri", "msg", "action", "focus-workspace", "3"], ["niri", "msg", "action", "focus-workspace", "1"]]);
    }

    function test_filtered_focused_output_and_loader_context() {
      widget.widgetSettings = {
        "hideUnoccupied": true,
        "followFocusedScreen": true,
        "labelMode": "index+name",
        "characterCount": 3
      };
      widget.refreshWorkspaces();
      wait(20);
      compare(labels(), ["1 Cod", "2 Web"]);
      widget.screen = secondary;
      wait(20);
      compare(labels(), ["1 Cod", "2 Web"]);
      const activated = fixtures();
      activated[2].is_focused = false;
      activated[3].is_focused = true;
      CompositorService.backend.recollectWorkspaces(activated);
      wait(20);
      compare(labels(), ["1 Vid", "2 Cha"]);
      clickOrder([1, 2]);
      widget.widgetSettings = {
        "labelMode": "none"
      };
      widget.refreshWorkspaces();
      wait(20);
      compare(labels(), []);
      compare(widget.implicitWidth, 73);
    }

    function test_label_geometry_urgency_and_effect_inputs_data() {
      return [
        {
          "tag": "horizontal",
          "position": "top",
          "emptyColor": "#eeeeee"
        },
        {
          "tag": "vertical",
          "position": "left",
          "emptyColor": "#ffffff"
        }
      ];
    }

    function test_label_geometry_urgency_and_effect_inputs(data) {
      const settings = JSON.parse(JSON.stringify(Settings.data));
      settings.bar.position = data.position;
      Settings.data = settings;
      wait(20);
      const textItems = labelItems();
      const pills = visiblePills();
      compare(textItems.length, 3);
      fuzzyCompare(textItems[0].pointSize, 26 * 0.45, 0.0001);
      fuzzyCompare(textItems[1].pointSize, 26 * 0.42, 0.0001);
      compare(textItems[0].color, "#000000");
      compare(textItems[1].color, "#ffffff");
      compare(textItems[2].color, data.emptyColor);
      for (let i = 0; i < textItems.length; i++) {
        const position = textItems[i].mapToItem(pills[i], 0, 0);
        fuzzyCompare(position.x, (pills[i].width - textItems[i].width) / 2, 0.0001);
        fuzzyCompare(position.y, (pills[i].height - textItems[i].contentHeight) / 2, 0.0001);
      }
      widget.setDisplayedUrgency(widget.localWorkspaces.get(1), false);
      compare(textItems[1].color, "#eeeeee");
      widget.effectsActive = true;
      widget.masterProgress = 0.5;
      widget.effectColor = "#123456";
      const bursts = descendants(widget, child => child.visible && child.border !== undefined && child.border.width === 5);
      compare(bursts.length, 1);
      compare(bursts[0].border.color, "#123456");
      fuzzyCompare(bursts[0].width, pills[0].width + 9, 0.0001);
      fuzzyCompare(bursts[0].height, pills[0].height + 9, 0.0001);
      fuzzyCompare(bursts[0].opacity, 0.35, 0.0001);
      widget.effectsActive = false;
      verify(!bursts[0].visible);
    }

    function test_model_clear_reassignment_data() {
      return [
        {
          "tag": "horizontal",
          "position": "top",
          "labels": ["7 Rea", "9 Lat"]
        },
        {
          "tag": "vertical",
          "position": "left",
          "labels": ["7R", "9L"]
        }
      ];
    }

    function test_model_clear_reassignment(data) {
      const settings = JSON.parse(JSON.stringify(Settings.data));
      settings.bar.position = data.position;
      Settings.data = settings;
      widget.widgetSettings = {
        "labelMode": "index+name",
        "characterCount": 3
      };
      wait(20);
      CompositorService.backend.recollectWorkspaces([]);
      wait(20);
      compare(widget.localWorkspaces.count, 0);
      compare(visiblePills().length, 0);
      compare(labels(), []);
      widget.switchByOffset(1);
      compare(Quickshell.commands, []);

      const reassigned = fixtures();
      reassigned[2].idx = 7;
      reassigned[2].name = "Reassigned";
      reassigned[4].idx = 9;
      reassigned[4].name = "Later";
      reassigned[1].output = "HDMI-A-1";
      CompositorService.backend.recollectWorkspaces(reassigned);
      wait(20);
      compare(labels(), data.labels);
      clickOrder([7, 9]);

      widget.widgetSettings = {
        "labelMode": "none"
      };
      wait(20);
      compare(labels(), []);
      widget.widgetSettings = {
        "labelMode": "name",
        "characterCount": 3
      };
      wait(20);
      compare(labels(), widget.isVertical ? ["Re", "La"] : ["Rea", "Lat"]);
      CompositorService.backend.recollectWorkspaces([]);
      widget.destroy();
      widget = null;
      wait(20);
      CompositorService.backend.recollectWorkspaces(fixtures());
      widget = createTemporaryObject(workspaceComponent, scene, {
        "screen": secondary
      });
      verify(widget !== null);
      wait(20);
      compare(labels(), ["1", "2"]);
      Quickshell.commands = [];
      clickOrder([1, 2]);
    }

    name: "Workspace"
    when: windowShown
  }
}
