import QtQuick
import QtTest
import Quickshell
import Quickshell.Services.SystemTray
import qs.Commons
import qs.Modules.Panels.Tray
import qs.Modules.MainScreen
import qs.Services.UI

Item {
  id: scene
  width: 600
  height: 600

  ShellScreen {
    id: fixtureScreen
    name: "fixture"
  }

  Component {
    id: notifierComponent
    QtObject {
      property string name
      property string tooltipTitle
      property string icon: ""
      property bool onlyMenu: false
      property bool hasMenu: true
      property QtObject menu: QtObject {}
      property int activations: 0
      property int secondaryActivations: 0
      property int up: 0
      property int down: 0
      function activate() {
        activations++;
      }
      function secondaryActivate() {
        secondaryActivations++;
      }
      function scrollUp() {
        up++;
      }
      function scrollDown() {
        down++;
      }
    }
  }

  PopupMenuWindow {
    id: popup
  }

  Component {
    id: drawerComponent
    TrayDrawerPanel {
      width: preferredWidth
      height: preferredHeight
      widgetSection: "left"
      widgetIndex: 1
    }
  }

  TestCase {
    name: "TrayDrawerWarnings"
    when: windowShown
    property var drawer
    property var alpha
    property var beta
    property var gamma

    function descendants(parent, predicate) {
      let found = [];
      for (const child of parent.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function repeater() {
      const found = descendants(drawer.contentItem, child => child.itemAt !== undefined);
      compare(found.length, 1);
      return found[0];
    }

    function icon(index) {
      const found = descendants(repeater().itemAt(index), child => child.backer !== undefined);
      compare(found.length, 1);
      return found[0];
    }

    function mouse(index) {
      const found = descendants(repeater().itemAt(index), child => child.clicked !== undefined && child.wheel !== undefined);
      compare(found.length, 1);
      return found[0];
    }

    function click(index, button) {
      drawer.visible = true;
      verify(waitForPolish(repeater().parent, 1000));
      const area = mouse(index);
      mouseClick(area, area.width / 2, area.height / 2, button);
    }

    function pin(rules) {
      // TrayMenu replaces the widget object, then emits settingsSaved.
      const widgets = Settings.data.bar.widgets.left;
      const updated = Object.assign({}, widgets[1]);
      updated.pinned = rules;
      widgets[1] = updated;
      Settings.data.bar.widgets.left = widgets;
      Settings.settingsSaved();
    }

    function init() {
      popup.visible = false;
      popup.opens = 0;
      popup.closes = 0;
      popup.trayMenuLoader.active = true;
      popup.trayMenuLoader.item.trayItem = null;
      TooltipService.text = "";
      Settings.data = {
        bar: {
          position: "top",
          widgets: {
            left: [
              {
                id: "Clock"
              },
              {
                id: "Tray",
                pinned: [],
                colorizeIcons: false
              }
            ],
            right: [
              {
                id: "Tray",
                pinned: ["Beta"]
              }
            ]
          }
        },
        colorSchemes: {
          darkMode: true
        }
      };
      alpha = createTemporaryObject(notifierComponent, scene, {
        name: "Alpha",
        tooltipTitle: "Alpha title",
        icon: "image://alpha"
      });
      beta = createTemporaryObject(notifierComponent, scene, {
        name: "Beta",
        icon: "image://beta"
      });
      gamma = createTemporaryObject(notifierComponent, scene, {
        name: "Gamma",
        icon: "image://gamma"
      });
      SystemTray.items.values = [alpha, beta, gamma];
      PanelService.popup = popup;
      drawer = createTemporaryObject(drawerComponent, scene, {
        screen: fixtureScreen
      });
      verify(drawer !== null);
      PanelService.openedPanel = drawer;
      tryVerify(() => drawer.contentItem !== null);
      tryCompare(repeater(), "count", 3);
    }

    function cleanup() {
      PanelService.openedPanel = null;
      PanelService.popup = null;
      SystemTray.items.values = [];
    }

    function test_pin_unpin_order_selection() {
      compare(drawer.trayValues, [alpha, beta, gamma]);
      compare(icon(0).source, "image://alpha");
      compare(icon(1).source, "image://beta");
      compare(icon(2).source, "image://gamma");
      pin(["ALPHA*"]);
      tryCompare(repeater(), "count", 2);
      compare(drawer.trayValues, [beta, gamma]);
      click(0, Qt.LeftButton);
      compare(beta.activations, 1);
      compare(alpha.activations, 0);
      compare(drawer.closeCount, 1);
      drawer.visible = true;
      pin([]);
      tryCompare(repeater(), "count", 3);
      compare(drawer.trayValues, [alpha, beta, gamma]);
      click(2, Qt.MiddleButton);
      compare(gamma.secondaryActivations, 1);
      compare(beta.secondaryActivations, 0);
      beta.onlyMenu = true;
      click(1, Qt.LeftButton);
      compare(beta.activations, 1);
      drawer.visible = true;
      pin(["*"]);
      tryCompare(repeater(), "count", 0);
      compare(drawer.visible, false);
      drawer.widgetSection = "right";
      drawer.widgetIndex = 0;
      tryCompare(repeater(), "count", 2);
      compare(drawer.trayValues, [alpha, gamma]);
    }

    function test_context_open_close_and_loader_reassignment_data() {
      return [
        {
          tag: "top",
          position: "top",
          x: -47,
          y: 30
        },
        {
          tag: "left",
          position: "left",
          x: 34,
          y: 0
        },
        {
          tag: "right",
          position: "right",
          x: -128,
          y: 0
        }
      ];
    }

    function test_context_open_close_and_loader_reassignment(data) {
      Settings.data.bar.position = data.position;
      click(1, Qt.RightButton);
      compare(popup.visible, true);
      compare(popup.opens, 1);
      compare(popup.trayMenuLoader.item.trayItem, beta);
      compare(popup.trayMenuLoader.item.widgetSection, "left");
      compare(popup.trayMenuLoader.item.widgetIndex, 1);
      compare(popup.trayMenuLoader.item.anchor, icon(1));
      compare(popup.trayMenuLoader.item.menuX, data.x);
      compare(popup.trayMenuLoader.item.menuY, data.y);
      click(1, Qt.RightButton);
      compare(popup.visible, false);
      popup.trayMenuLoader.active = false;
      click(0, Qt.RightButton);
      compare(popup.opens, 1);
      popup.trayMenuLoader.active = true;
      tryVerify(() => popup.trayMenuLoader.item !== null);
      click(2, Qt.RightButton);
      compare(popup.trayMenuLoader.item.trayItem, gamma);
      compare(popup.visible, true);
      mouse(0).entered();
      compare(popup.visible, false);
      compare(TooltipService.text, "Alpha title");
      compare(TooltipService.anchor, icon(0));
      mouse(0).exited();
      compare(TooltipService.text, "");
      gamma.hasMenu = false;
      click(2, Qt.RightButton);
      compare(popup.visible, false);
    }

    function test_model_clear_reassign_geometry_and_handlers() {
      compare(drawer.columns, 3);
      compare(drawer.rows, 1);
      compare(drawer.preferredWidth, 110);
      compare(drawer.contentItem.contentPreferredWidth, 110);
      compare(drawer.preferredHeight, 42);
      mouseWheel(mouse(1), 10, 10, 0, 120);
      mouseWheel(mouse(2), 10, 10, 0, -120);
      compare(beta.up, 1);
      compare(gamma.down, 1);
      SystemTray.items.values = [];
      tryCompare(repeater(), "count", 0);
      compare(drawer.visible, false);
      SystemTray.items.values = [gamma, alpha];
      drawer.visible = true;
      tryCompare(repeater(), "count", 2);
      compare(icon(0).source, "image://gamma");
      compare(icon(1).source, "image://alpha");
      compare(drawer.preferredWidth, 76);
      compare(drawer.contentItem.contentPreferredWidth, 76);
      click(0, Qt.LeftButton);
      compare(gamma.activations, 1);
      compare(alpha.activations, 0);
      const many = [];
      for (let i = 0; i < 9; i++)
        many.push(createTemporaryObject(notifierComponent, scene, {
          name: "item-" + i
        }));
      SystemTray.items.values = many;
      tryCompare(repeater(), "count", 9);
      compare(drawer.columns, 8);
      compare(drawer.rows, 2);
      compare(drawer.contentItem.contentPreferredHeight, 76);
      verify(waitForPolish(repeater().parent, 1000));
      compare(repeater().itemAt(8).x, 0);
      compare(repeater().itemAt(8).y, 34);
    }
  }
}
