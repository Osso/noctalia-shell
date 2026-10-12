pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import qs.Widgets

ShellRoot {
  Item {
    id: scene
    visible: false
    property int count: 3

    NTabBar {
      id: first
      Repeater {
        id: textTabs
        model: scene.count
        NTabButton {
          required property int index
          id: textTab
          text: "Text " + textTab.index
          tabIndex: index
          checked: first.currentIndex === index
        }
      }
    }
    NTabBar {
      id: second
      currentIndex: 2
      Repeater {
        id: iconTabs
        model: scene.count
        NIconTabButton {
          required property int index
          icon: "star"
          tabIndex: index
          checked: second.currentIndex === index
        }
      }
    }
    Timer {
      id: probe
      interval: 100
      running: true
      function check(condition, message) {
        if (!condition)
          throw new Error("TAB_RELOAD_ASSERT: " + message);
      }
      onTriggered: {
        probe.check((textTabs.itemAt(1) as NTabButton).tabBar === first, "text owner assigned");
        probe.check((iconTabs.itemAt(1) as NIconTabButton).tabBar === second, "icon owner assigned");
        first.currentIndex = 1;
        probe.check((textTabs.itemAt(1) as NTabButton).checked && !(iconTabs.itemAt(1) as NIconTabButton).checked, "independent selection");
        scene.count = 0;
        probe.check(textTabs.count === 0 && iconTabs.count === 0, "delegate teardown");
        scene.count = 3;
        probe.check((textTabs.itemAt(1) as NTabButton).tabBar === first, "recreated text owner");
        probe.check((iconTabs.itemAt(1) as NIconTabButton).tabBar === second, "recreated icon owner");
        probe.check((textTabs.itemAt(1) as NTabButton).checked && (iconTabs.itemAt(2) as NIconTabButton).checked, "recreated checked bindings");
        console.log("TAB_PRIVATE_READY");
      }
    }
  }
  Connections {
    target: Quickshell
    function onReloadCompleted() {
      Quickshell.inhibitReloadPopup();
    }
  }
}
