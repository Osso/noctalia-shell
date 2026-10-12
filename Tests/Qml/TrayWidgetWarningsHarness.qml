import QtQuick
import QtTest
import Quickshell
import Quickshell.Services.SystemTray
import qs.Commons
import qs.Modules.Bar.Widgets
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
      property string tooltipTitle: ""
      property string icon: ""
      property bool onlyMenu: false
      property bool hasMenu: true
      property QtObject menu: QtObject {}
      property int activations: 0
      property int secondaryActivations: 0
      function activate() {
        activations++;
      }
      function secondaryActivate() {
        secondaryActivations++;
      }
    }
  }

  component TrayMenu: Item {
    width: 120
    property ShellScreen screen
    property var trayItem
    property string widgetSection
    property int widgetIndex
    property Item anchor
    property real menuX
    property real menuY
    function showAt(item, x, y) {
      anchor = item;
      menuX = x;
      menuY = y;
    }
  }

  Item {
    id: popup
    visible: false
    property alias trayMenuLoader: menuLoader
    property int opens: 0
    property int closes: 0
    function open() {
      opens++;
      visible = true;
    }
    function close() {
      closes++;
      visible = false;
    }
    Loader {
      id: menuLoader
      sourceComponent: TrayMenu {}
    }
  }

  QtObject {
    id: drawer
    property string widgetSection
    property int widgetIndex
    property int toggles: 0
    function toggle(item) {
      toggles++;
    }
  }

  Component {
    id: widgetComponent
    Tray {
      widgetId: "Tray"
      section: "left"
      sectionWidgetIndex: 1
    }
  }

  TestCase {
    name: "TrayWidgetWarnings"
    when: windowShown
    readonly property TrayMenu fixtureMenu: menuLoader.item as TrayMenu
    property var widget
    property var alpha
    property var beta
    property var gamma

    function descendants(owner, predicate) {
      let found = [];
      for (const child of owner.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function repeater() {
      const found = descendants(widget, child => child.itemAt !== undefined);
      compare(found.length, 1);
      return found[0];
    }

    function icon(index) {
      return descendants(repeater().itemAt(index), child => child.backer !== undefined)[0];
    }

    function mouse(index) {
      return descendants(repeater().itemAt(index), child => child.clicked !== undefined && child.wheel !== undefined)[0];
    }

    function click(index, button) {
      verify(waitForPolish(repeater().parent, 1000));
      tryCompare(icon(index), "status", Image.Ready);
      const area = mouse(index);
      mouseClick(area, area.width / 2, area.height / 2, button);
    }

    function settingsChanged(pinned, blacklist, enabled) {
      Settings.data = {
        bar: {
          position: Settings.data.bar.position,
          density: false,
          widgets: {
            left: [
              {
                id: "Clock"
              },
              {
                id: "Tray",
                pinned: pinned,
                blacklist: blacklist,
                drawerEnabled: enabled,
                colorizeIcons: false
              }
            ]
          }
        },
        colorSchemes: {
          darkMode: true
        }
      };
      Settings.settingsSaved();
    }

    function init() {
      popup.visible = false;
      popup.opens = 0;
      popup.closes = 0;
      menuLoader.active = true;
      fixtureMenu.trayItem = null;
      drawer.toggles = 0;
      TooltipService.text = "";
      Settings.data = {
        bar: {
          position: "top",
          density: false,
          widgets: {
            left: []
          }
        },
        colorSchemes: {
          darkMode: true
        }
      };
      settingsChanged([], [], false);
      alpha = createTemporaryObject(notifierComponent, scene, {
        name: "Alpha",
        tooltipTitle: "Alpha title",
        icon: Qt.resolvedUrl("icon.svg").toString()
      });
      beta = createTemporaryObject(notifierComponent, scene, {
        name: "Beta",
        icon: alpha.icon
      });
      gamma = createTemporaryObject(notifierComponent, scene, {
        name: "Gamma",
        icon: alpha.icon
      });
      SystemTray.items.values = [alpha, beta, gamma];
      PanelService.popup = popup;
      PanelService.drawer = drawer;
      widget = createTemporaryObject(widgetComponent, scene, {
        screen: fixtureScreen
      });
      verify(widget !== null);
      tryCompare(repeater(), "count", 3);
    }

    function cleanup() {
      PanelService.openedPanel = null;
      PanelService.popup = null;
      PanelService.drawer = null;
      SystemTray.items.values = [];
    }

    function test_status_source_and_activation() {
      tryCompare(icon(0), "status", Image.Ready);
      compare(icon(0).opacity, 1);
      beta.icon = "";
      tryCompare(icon(1), "status", Image.Null);
      compare(icon(1).opacity, 0);
      beta.icon = alpha.icon;
      click(0, Qt.LeftButton);
      compare(alpha.activations, 1);
      click(1, Qt.MiddleButton);
      compare(beta.secondaryActivations, 1);
      beta.onlyMenu = true;
      click(1, Qt.LeftButton);
      compare(beta.activations, 0);
      alpha.icon = "";
      tryCompare(icon(0), "status", Image.Null);
      compare(icon(0).opacity, 0);
    }

    function test_filter_sort_clear_reassignment() {
      // Tray preserves SystemTray order; sorting means a reordered model,
      // not a new alphabetical sorting policy.
      settingsChanged(["ALPHA*", "Gamma"], ["Beta"], true);
      tryCompare(repeater(), "count", 2);
      compare(widget.filteredItems, [alpha, gamma]);
      compare(widget.dropdownItems, []);
      SystemTray.items.values = [gamma, null, beta, alpha];
      tryCompare(widget, "filteredItems", [gamma, alpha]);
      click(0, Qt.LeftButton);
      compare(gamma.activations, 1);
      compare(alpha.activations, 0);
      SystemTray.items.values = [];
      tryCompare(repeater(), "count", 0);
      compare(widget.visible, false);
      SystemTray.items.values = [beta, alpha];
      settingsChanged([], [], false);
      tryCompare(repeater(), "count", 2);
      click(0, Qt.LeftButton);
      compare(beta.activations, 1);
      compare(gamma.activations, 1);
      settingsChanged([], [], true);
      tryCompare(repeater(), "count", 0);
      compare(widget.dropdownItems, [beta, alpha]);
      widget.toggleDrawer(widget);
      compare(drawer.toggles, 1);
      compare(drawer.widgetSection, "left");
      compare(drawer.widgetIndex, 1);
    }

    function test_menu_lifecycle_data() {
      return [
        {
          tag: "top",
          position: "top",
          x: -47,
          y: 40
        },
        {
          tag: "bottom",
          position: "bottom",
          x: -47,
          y: -40
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

    function test_menu_lifecycle(data) {
      Settings.data = Object.assign({}, Settings.data, {
        bar: Object.assign({}, Settings.data.bar, {
          position: data.position
        })
      });
      widget.onLoaded();
      compare(fixtureMenu.screen, fixtureScreen);
      click(1, Qt.RightButton);
      compare(popup.visible, true);
      compare(popup.opens, 1);
      compare(fixtureMenu.trayItem, beta);
      compare(fixtureMenu.widgetSection, "left");
      compare(fixtureMenu.widgetIndex, 1);
      compare(fixtureMenu.anchor, icon(1));
      compare(fixtureMenu.menuX, data.x);
      compare(fixtureMenu.menuY, data.y);
      click(1, Qt.RightButton);
      compare(popup.visible, false);
      menuLoader.active = false;
      click(0, Qt.RightButton);
      compare(popup.opens, 1);
      menuLoader.active = true;
      tryVerify(() => menuLoader.item !== null);
      click(2, Qt.RightButton);
      compare(fixtureMenu.trayItem, gamma);
      click(0, Qt.MiddleButton);
      compare(popup.visible, false);
      compare(alpha.secondaryActivations, 0);
      mouse(0).entered();
      compare(TooltipService.text, "Alpha title");
      compare(TooltipService.anchor, icon(0));
      mouse(0).exited();
      compare(TooltipService.text, "");
      gamma.hasMenu = false;
      click(2, Qt.RightButton);
      compare(popup.visible, false);
      PanelService.popup = null;
      compare(widget.trayMenu, null);
      PanelService.popup = popup;
      PanelService.popupMenuWindowRegistered(fixtureScreen);
      click(1, Qt.RightButton);
      compare(fixtureMenu.trayItem, beta);
      widget.toggleDrawer(widget);
      compare(popup.visible, false);
      compare(drawer.toggles, 1);
    }
  }
}
