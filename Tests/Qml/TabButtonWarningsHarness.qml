pragma ComponentBehavior: Bound

import QtQuick
import QtTest
import qs.Widgets

TestCase {
  id: suite
  name: "TabButtonOwners"
  width: 640
  height: 400
  visible: true
  when: windowShown

  Component {
    id: sceneFactory
    Item {
      id: scene
      width: 600
      height: 350
      property alias first: firstBar
      property alias second: secondBar
      property alias secondButton: independentButton
      property alias delegates: tabs
      property alias shadow: shadowParent
      property bool icons: false
      property int count: 3
      property int clicks: 0
      property int indexAtClick: -1

      NTabBar {
        id: firstBar
        width: 400
        focus: true
        Keys.onRightPressed: firstBar.currentIndex = (firstBar.currentIndex + 1) % scene.count
        Keys.onLeftPressed: firstBar.currentIndex = (firstBar.currentIndex + scene.count - 1) % scene.count
        Repeater {
          id: tabs
          model: scene.count
          delegate: scene.icons ? iconFactory : textFactory
        }
      }
      NTabBar {
        id: secondBar
        y: 100
        width: 400
        currentIndex: 2
        NTabButton {
          id: independentButton
          text: "Independent"
          tabIndex: 1
          checked: secondBar.currentIndex === tabIndex
        }
      }
      Item {
        id: shadowParent
        y: 200
        width: 400
        height: 50
        property int currentIndex: 99
        property NTabBar tabBar: secondBar
      }
      Component {
        id: textFactory
        TextTab {
          id: textTab
          text: "Tab " + textTab.index
          tabIndex: index
          checked: firstBar.currentIndex === index
          onClicked: {
            scene.clicks++;
            scene.indexAtClick = firstBar.currentIndex;
          }
        }
      }
      Component {
        id: iconFactory
        NIconTabButton {
          required property int index
          icon: "star"
          tabIndex: index
          checked: firstBar.currentIndex === index
          onClicked: {
            scene.clicks++;
            scene.indexAtClick = firstBar.currentIndex;
          }
        }
      }
    }
  }
  component TextTab: NTabButton {
    required property int index
  }

  function test_selection_data() {
    return [
      {
        tag: "text",
        icons: false
      },
      {
        tag: "icon",
        icons: true
      }
    ];
  }

  function test_selection(data) {
    const scene = createTemporaryObject(sceneFactory, suite, {
      icons: data.icons
    });
    verify(scene !== null);
    tryCompare(scene.delegates, "count", 3);
    const button = scene.delegates.itemAt(1);
    verify(button.width > 0);
    mouseClick(button, button.width / 2, button.height / 2);
    compare(scene.clicks, 1);
    compare(scene.indexAtClick, 0);
    compare(scene.first.currentIndex, 1);
    compare(scene.second.currentIndex, 2);
    compare(button.checked, true);
    mouseClick(scene.secondButton, scene.secondButton.width / 2, scene.secondButton.height / 2);
    compare(scene.second.currentIndex, 1);
    compare(scene.first.currentIndex, 1);
    compare(scene.secondButton.checked, true);
    scene.first.forceActiveFocus();
    keyClick(Qt.Key_Right);
    compare(scene.first.currentIndex, 2);
    compare(button.checked, false);
    compare(scene.delegates.itemAt(2).checked, true);
    keyClick(Qt.Key_Left);
    compare(scene.first.currentIndex, 1);
    scene.count = 0;
    tryCompare(scene.delegates, "count", 0);
    scene.count = 3;
    tryCompare(scene.delegates, "count", 3);
    const recreated = scene.delegates.itemAt(0);
    tryVerify(() => recreated.width > 0 && recreated.height > 0);
    mouseClick(recreated, recreated.width / 2, recreated.height / 2);
    compare(scene.first.currentIndex, 0);
    compare(scene.second.currentIndex, 1);
    compare(scene.clicks, 2);
    compare(recreated.checked, true);
  }

  function test_owner_shadow_data() {
    return test_selection_data();
  }

  function test_owner_shadow(data) {
    const scene = createTemporaryObject(sceneFactory, suite, {
      icons: data.icons
    });
    verify(scene !== null);
    tryCompare(scene.delegates, "count", 3);
    const button = scene.delegates.itemAt(1);
    button.parent = scene.shadow;
    button.width = 150;
    button.height = 45;
    mouseClick(button, 75, 22);
    compare(scene.first.currentIndex, 1, "explicit owner survives ancestry collision");
    compare(scene.second.currentIndex, 2);
    compare(scene.shadow.currentIndex, 99);
    compare(scene.clicks, 1);
    compare(button.checked, true);
  }
}
