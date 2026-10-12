import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Modules.Cards
import qs.Modules.Panels.ControlCenter
import qs.Services.UI

ShellRoot {
  Item {
    id: scene
    width: 1200
    height: 800
    property var first
    property var second
    property var detachedCard
    property var detachedProfile
    property int phase: 0
    property bool directOnly: false

    Component {
      id: panelFactory
      ControlCenterPanel {
        width: 520
        height: 300
      }
    }

    Component {
      id: secondPanelFactory
      ControlCenterPanel {
        readonly property int shortcutsHeight: 73
        width: 520
        height: 300
      }
    }

    // Unrelated creation-context root must not become the supplied card owner.
    ControlCenterPanel {
      id: root
      screen: Quickshell.screens[1]
      property Component shortcutFactory: Component {
        ShortcutsCard {}
      }
    }

    Component {
      id: profileFactory
      ProfileCard {
        width: 520
        height: 80
      }
    }

    Component {
      id: actionFactory
      Item {
        id: action
        property ShellScreen screen
        property string widgetId
        property string section
        property int sectionWidgetIndex
        property int sectionWidgetsCount
        property var widgetSettings
        signal activated(string caption, string monitor)
        implicitWidth: 60
        implicitHeight: 32
        function activate() {
          action.activated(action.widgetSettings.caption, action.screen.name);
        }
        onActivated: (caption, monitor) => {
          PanelService.actionEvents = PanelService.actionEvents.concat([
            {
              caption: caption,
              monitor: monitor
            }
          ]);
        }
      }
    }

    function check(condition, message) {
      if (!condition)
        throw new Error("CARD_CONTEXT_FAIL: " + message);
    }

    function descendants(item, predicate) {
      let found = [];
      for (const child of item.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function cards(panel) {
      return descendants(panel, child => child.uptimeText !== undefined || child.controlCenter !== undefined);
    }

    function assertProfileRoutes(card, screen) {
      const buttons = descendants(card, child => child.clicked !== undefined && ["settings", "power", "close"].includes(child.icon));
      check(buttons.length === 3, "three profile actions");
      const names = [["settingsPanel"], ["sessionMenuPanel", "controlCenterPanel"], ["controlCenterPanel"]];
      for (let i = 0; i < buttons.length; ++i) {
        PanelService.events = [];
        buttons[i].clicked();
        check(PanelService.events.length === names[i].length, "profile lookup count");
        for (let j = 0; j < names[i].length; ++j) {
          check(PanelService.events[j].name === names[i][j], "profile panel name");
          check(PanelService.events[j].screen === screen, "profile action screen");
        }
      }
      check(PanelService.panel.requestedTab === 0, "settings general tab");
    }

    function assertShortcuts(card, owner) {
      check(card.controlCenter === owner, "explicit shortcut owner");
      const boxes = card.children.filter(child => child.border !== undefined);
      check(boxes.length === 2, "two shortcut sections");
      for (const box of boxes)
        check(box.Layout.preferredHeight === owner.shortcutsHeight, "shortcut owner height");
      const widgets = descendants(card, child => child.activated !== undefined);
      check(widgets.length === 2, "two shortcut actions");
      PanelService.actionEvents = [];
      for (let i = 0; i < widgets.length; ++i) {
        check(widgets[i].screen === owner.screen, "shortcut widget screen phase " + scene.phase + ": " + widgets[i].screen.name + " versus " + owner.screen.name);
        check(widgets[i].section === "quickSettings", "shortcut section");
        check(widgets[i].sectionWidgetIndex === 0, "shortcut index");
        widgets[i].activate();
        check(PanelService.actionEvents.length === i + 1, "shortcut emitted action");
        check(PanelService.actionEvents[i].caption === (i === 0 ? "Left" : "Right"), "shortcut action caption");
        check(PanelService.actionEvents[i].monitor === owner.screen.name, "shortcut action monitor");
      }
    }

    function assertLoadedPanels() {
      for (const panel of [scene.first, scene.second]) {
        const loaded = cards(panel);
        check(loaded.length === 2, "production panel loaded both cards");
        const profile = loaded.find(child => child.uptimeText !== undefined);
        const shortcuts = loaded.find(child => child.controlCenter !== undefined);
        check(profile.screen === panel.screen, "profile declared screen supplied by panel");
        assertProfileRoutes(profile, panel.screen);
        assertShortcuts(shortcuts, panel);
      }
    }

    function createOwners() {
      check(Quickshell.screens.length === 2, "two actual ShellScreens");
      check(Quickshell.screens[0] !== Quickshell.screens[1], "distinct actual ShellScreens");
      check(Quickshell.screens[0].name === "first" && Quickshell.screens[1].name === "second", "offscreen names");
      Style.uiScaleRatio = 1;
      ControlCenterWidgetRegistry.widgets = {
        "Action": actionFactory
      };
      scene.first = panelFactory.createObject(scene, {
        "screen": Quickshell.screens[0]
      });
      scene.second = secondPanelFactory.createObject(scene, {
        "screen": Quickshell.screens[1],
        "x": 560
      });
      check(scene.first !== null && scene.second !== null, "two actual panel owners");
      check(scene.first.shortcutsHeight === 52 && scene.second.shortcutsHeight === 73, "distinct panel heights");
      scene.first.open();
      scene.second.open();
    }

    function assertDetachedOwners() {
      assertShortcuts(scene.detachedCard, scene.first);
      check(scene.first.shortcutsHeight === 52, "initial shortcut height");
      Style.uiScaleRatio = 1.5;
      check(scene.first.shortcutsHeight === 78, "reactive production shortcut height");
      assertShortcuts(scene.detachedCard, scene.first);
      check(scene.second.shortcutsHeight === 73, "second owner height independent of first");
      // Widget screens are assigned on load, so exercise a fresh card per owner.
      scene.detachedCard.destroy();
      scene.detachedCard = root.shortcutFactory.createObject(scene, {
        "controlCenter": scene.second,
        "width": 520,
        "height": 100
      });
      scene.check(scene.detachedCard !== null, "second explicit shortcut owner accepted");
      assertProfileRoutes(scene.detachedProfile, Quickshell.screens[0]);
      scene.detachedProfile.screen = Quickshell.screens[1];
      assertProfileRoutes(scene.detachedProfile, Quickshell.screens[1]);
      scene.first.destroy();
    }

    Timer {
      interval: 60
      running: true
      repeat: true
      onTriggered: {
        try {
          switch (scene.phase++) {
          case 0:
            scene.createOwners();
            if (scene.directOnly)
              scene.phase = 4;
            break;
          case 1:
          case 3:
            scene.assertLoadedPanels();
            scene.first.close();
            scene.second.close();
            break;
          case 2:
            scene.check(scene.cards(scene.first).length === 0 && scene.cards(scene.second).length === 0, "closed loaders dispose cards");
            scene.first.open();
            scene.second.open();
            break;
          case 4:
            scene.detachedCard = root.shortcutFactory.createObject(scene, {
              "controlCenter": scene.first,
              "width": 520,
              "height": 100
            });
            scene.check(scene.detachedCard !== null, "explicit shortcut owner accepted");
            scene.detachedProfile = profileFactory.createObject(scene, {
              "screen": Quickshell.screens[0]
            });
            scene.check(scene.detachedCard !== null && scene.detachedProfile !== null, "explicit card dependencies accepted");
            break;
          case 5:
            scene.assertDetachedOwners();
            break;
          case 6:
            scene.assertShortcuts(scene.detachedCard, scene.second);
            console.log("CARD_CONTEXT_PASS: two screens, panel loaders/recreation, owner shadow, reactive height/screen, actions, owner disposal");
            Qt.quit();
          }
        } catch (error) {
          console.error(error.message);
          Qt.quit();
        }
      }
    }
  }
}
