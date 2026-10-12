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
          text: "Text " + index
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
      interval: 100
      running: true
      function check(condition, message) {
        if (!condition)
          throw new Error("TAB_RELOAD_ASSERT: " + message);
      }
      onTriggered: {
        check(textTabs.itemAt(1).tabBar === first, "text owner assigned");
        check(iconTabs.itemAt(1).tabBar === second, "icon owner assigned");
        first.currentIndex = 1;
        check(textTabs.itemAt(1).checked && !iconTabs.itemAt(1).checked, "independent selection");
        scene.count = 0;
        check(textTabs.count === 0 && iconTabs.count === 0, "delegate teardown");
        scene.count = 3;
        check(textTabs.itemAt(1).tabBar === first, "recreated text owner");
        check(iconTabs.itemAt(1).tabBar === second, "recreated icon owner");
        check(textTabs.itemAt(1).checked && iconTabs.itemAt(2).checked, "recreated checked bindings");
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
