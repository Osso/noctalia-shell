import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Panels.ControlCenter
import qs.Services.Media
import qs.Services.Networking

Item {
  id: scene
  width: 1100
  height: 1000

  ShellScreen {
    id: firstScreen
    name: "DP-1"
  }
  ShellScreen {
    id: secondScreen
    name: "DP-2"
  }

  Component {
    id: panelComponent
    ControlCenterPanel {
      width: preferredWidth
      height: preferredHeight
    }
  }

  TestCase {
    id: testCase
    name: "ControlCenterPanelWarnings"
    when: windowShown
    property var panel
    property var otherPanel

    function descendants(item, predicate) {
      let found = [];
      for (const child of item.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function rows(owner) {
      const repeaters = descendants(owner.contentItem, child => child.itemAt !== undefined);
      compare(repeaters.length, 1);
      return repeaters[0];
    }

    function card(row) {
      const cards = descendants(row, child => child.cardKind !== undefined);
      compare(cards.length, 1);
      return cards[0];
    }

    function configure(cards, position, monitors, weather, left, right) {
      Settings.data = {
        controlCenter: {
          cards: cards,
          position: position,
          shortcuts: {
            left: left,
            right: right
          }
        },
        bar: {
          monitors: monitors
        },
        location: {
          weatherEnabled: weather
        }
      };
    }

    function allCards() {
      return [
        {
          id: "profile-card",
          enabled: true
        },
        {
          id: "shortcuts-card",
          enabled: true
        },
        {
          id: "audio-card",
          enabled: true
        },
        {
          id: "weather-card",
          enabled: true
        },
        {
          id: "media-sysmon-card",
          enabled: true
        }
      ];
    }

    function init() {
      Style.uiScaleRatio = 1;
      Style.marginL = 12;
      MediaService.autoSwitchingPaused = false;
      VPNService.pollingRefs = 0;
      VPNService.starts = 0;
      VPNService.stops = 0;
      configure(allCards(), "center", [], true, [], []);
      panel = panelComponent.createObject(scene, {
        screen: firstScreen
      });
      otherPanel = panelComponent.createObject(scene, {
        screen: secondScreen,
        x: 550
      });
      verify(panel !== null);
      verify(otherPanel !== null);
      tryVerify(() => panel.contentItem !== null && otherPanel.contentItem !== null);
      tryCompare(rows(panel), "count", 5);
    }

    function cleanup() {
      panel.close();
      otherPanel.close();
      panel.destroy();
      otherPanel.destroy();
      panel = null;
      otherPanel = null;
      wait(0);
      compare(VPNService.pollingRefs, 0);
    }

    function test_card_routing_layout_and_owner_heights() {
      for (let i = 0; i < 5; i++) {
        compare(rows(panel).itemAt(i).active, false);
        compare(rows(panel).itemAt(i).item, null);
      }
      panel.open();
      tryCompare(panel, "weatherHeight", 173);
      compare(otherPanel.weatherHeight, 210);
      compare(otherPanel.isPanelOpen, false);
      compare(panel.preferredHeight, 64 + 52 + 60 + 173 + 260 + 6 * 12);
      const heights = [64, 52, 60, 173, 260];
      const ids = allCards().map(entry => entry.id);
      let expectedY = 0;
      wait(40);
      for (let i = 0; i < 5; i++) {
        const row = rows(panel).itemAt(i);
        compare(row.active, true);
        compare(card(row).cardKind, ids[i]);
        compare(row.height, heights[i]);
        compare(row.y, expectedY);
        compare(row.width, panel.width - 24);
        expectedY += heights[i] + 12;
      }
      // Distinct owners must never share the mutable weather height binding.
      otherPanel.weatherHeight = 291;
      panel.weatherHeight = 187;
      tryCompare(rows(panel).itemAt(3), "height", 187);
      compare(rows(otherPanel).itemAt(3).Layout.preferredHeight, 291);
      Style.uiScaleRatio = 1.5;
      tryCompare(rows(panel).itemAt(0), "height", 96);
      compare(panel.preferredWidth, 690);
      compare(panel.preferredHeight, 96 + 78 + 90 + 187 + 390 + 72);
      panel.close();
      for (let i = 0; i < 5; i++) {
        tryCompare(rows(panel).itemAt(i), "item", null);
        compare(rows(panel).itemAt(i).active, false);
      }
      panel.open();
      tryCompare(panel, "weatherHeight", 173);
      compare(card(rows(panel).itemAt(4)).cardKind, "media-sysmon-card");
    }

    function test_reorder_disable_weather_and_reopen() {
      panel.open();
      configure([
        {
          id: "audio-card",
          enabled: true
        },
        {
          id: "weather-card",
          enabled: true
        },
        {
          id: "profile-card",
          enabled: false
        },
        {
          id: "shortcuts-card",
          enabled: true
        }
      ], "center", [], false, [], []);
      tryCompare(rows(panel), "count", 4);
      compare(card(rows(panel).itemAt(0)).cardKind, "audio-card");
      compare(rows(panel).itemAt(1).active, false);
      compare(rows(panel).itemAt(2).active, false);
      compare(rows(panel).itemAt(1).item, null);
      compare(card(rows(panel).itemAt(3)).cardKind, "shortcuts-card");
      wait(40);
      compare(rows(panel).itemAt(0).y, 0);
      compare(rows(panel).itemAt(3).y, 72);
      compare(panel.preferredHeight, 60 + 52 + 36);
      configure(allCards(), "center", [], true, [], []);
      tryCompare(rows(panel), "count", 5);
      tryCompare(panel, "weatherHeight", 173);
      compare(card(rows(panel).itemAt(3)).cardKind, "weather-card");
    }

    function test_screen_and_position_anchor_bindings() {
      configure([], "close_to_bar_button", ["DP-1"], true, [], []);
      compare(panel.hasBarOnScreen, true);
      compare(panel.shouldCenter, false);
      compare(panel.panelAnchorHorizontalCenter, false);
      compare(otherPanel.hasBarOnScreen, false);
      compare(otherPanel.panelAnchorHorizontalCenter, true);
      compare(otherPanel.panelAnchorVerticalCenter, true);
      panel.screen = secondScreen;
      compare(panel.shouldCenter, true);
      configure([], "top_right", [], true, [], []);
      compare(panel.panelAnchorRight, true);
      compare(panel.panelAnchorTop, true);
      compare(panel.panelAnchorLeft, false);
      compare(panel.panelAnchorBottom, false);
      compare(panel.panelAnchorHorizontalCenter, false);
      compare(panel.panelAnchorVerticalCenter, false);
      configure([], "bottom_center", [], true, [], []);
      compare(panel.panelAnchorHorizontalCenter, true);
      compare(panel.panelAnchorBottom, true);
      compare(panel.panelAnchorRight, false);
      configure([], "center", [], true, [], []);
      compare(panel.panelAnchorVerticalCenter, true);
    }

    function test_open_close_media_and_vpn_interactions() {
      configure(allCards(), "center", [], true, [
        {
          id: "VPN"
        }
      ], []);
      panel.open();
      compare(MediaService.autoSwitchingPaused, true);
      compare(panel.vpnPollingRegistered, true);
      compare(otherPanel.vpnPollingRegistered, false);
      compare(VPNService.pollingRefs, 1);
      panel.open();
      compare(VPNService.starts, 1);
      panel.close();
      compare(MediaService.autoSwitchingPaused, false);
      compare(VPNService.pollingRefs, 0);
      panel.close();
      compare(VPNService.stops, 1);
      configure(allCards(), "center", [], true, [], [
        {
          id: "VPN"
        }
      ]);
      otherPanel.open();
      compare(otherPanel.vpnPollingRegistered, true);
      compare(panel.vpnPollingRegistered, false);
      compare(VPNService.starts, 2);
      otherPanel.close();
      compare(VPNService.stops, 2);
      configure(allCards(), "center", [], true, [
        {
          id: "Audio"
        }
      ], []);
      panel.open();
      compare(VPNService.pollingRefs, 0);
      compare(panel.vpnPollingRegistered, false);
    }
  }
}
