import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtTest
import qs.Widgets

Item {
  id: scene
  width: 800
  height: 600
  visible: true // Offscreen QPA, never a desktop surface.

  Item {
    id: anchor
    x: 40
    y: 50
  }

  Component {
    id: menuFactory
    NContextMenu {}
  }

  TestCase {
    name: "ProductionContextMenu"
    when: windowShown
    property var menu

    SignalSpy {
      id: triggeredSpy
      signalName: "triggered"
    }

    function entries() {
      return [
        {
          label: "Open",
          text: "Wrong",
          icon: "disc",
          action: "open"
        },
        {
          text: "Disabled",
          key: "disabled",
          enabled: false
        },
        {
          label: "Hidden",
          visible: false
        },
        {
          text: "Last",
          key: "last"
        },
        {
          text: "Index action"
        }
      ];
    }

    function openMenu() {
      menu.openAt(120, 100);
      tryCompare(menu, "opened", true);
      menu.contentItem.forceLayout();
      wait(30);
    }

    function delegateAt(index) {
      const delegate = menu.contentItem.itemAtIndex(index);
      verify(delegate !== null);
      return delegate;
    }

    function init() {
      menu = createTemporaryObject(menuFactory, scene, {
        model: entries()
      });
      verify(menu !== null);
      triggeredSpy.target = menu;
      triggeredSpy.clear();
    }

    function cleanup() {
      menu.close();
      tryCompare(menu, "visible", false);
      triggeredSpy.target = null;
    }

    function test_layout_and_items() {
      menu.itemHeight = 42;
      menu.itemPadding = 13;
      openMenu();
      compare(menu.width, 180);
      compare(menu.padding, 4);
      compare(menu.contentItem.count, 5);
      compare(menu.contentItem.spacing, 2);
      const first = delegateAt(0);
      compare(first.width, menu.contentItem.width);
      compare(first.height, 42);
      compare(first.itemText, "Open");
      compare(first.itemAction, "open");
      compare(first.contentItem.children[0].icon, "disc");
      compare(first.contentItem.children[0].visible, true);
      compare(first.contentItem.children[0].Layout.leftMargin, 13);
      compare(first.contentItem.children[1].text, "Open");
      compare(first.contentItem.children[1].Layout.leftMargin, 0);
      const disabled = delegateAt(1);
      compare(disabled.enabled, false);
      compare(disabled.opacity, 0.5);
      compare(disabled.contentItem.children[0].visible, false);
      compare(disabled.contentItem.children[1].Layout.leftMargin, 13);
      compare(delegateAt(2).visible, false);
      compare(delegateAt(2).height, 0);
      compare(delegateAt(4).itemAction, "4");
      menu.itemHeight = 46;
      menu.itemPadding = 17;
      tryCompare(first, "height", 46);
      compare(disabled.contentItem.children[1].Layout.leftMargin, 17);
      menu.height = 70;
      compare(menu.contentItem.interactive, true);
    }

    function test_pointer_activation_closes_after_signal() {
      openMenu();
      let visibleAtTrigger = false;
      menu.triggered.connect(function () {
        visibleAtTrigger = menu.visible;
      });
      mouseClick(delegateAt(1));
      compare(triggeredSpy.count, 0);
      compare(menu.visible, true);
      mouseClick(delegateAt(3));
      compare(triggeredSpy.count, 1);
      compare(triggeredSpy.signalArguments[0][0], "last");
      compare(visibleAtTrigger, true);
      tryCompare(menu, "visible", false);
      openMenu();
      mouseClick(delegateAt(4));
      compare(triggeredSpy.signalArguments[1][0], "4");
      tryCompare(menu, "visible", false);
    }

    function test_keyboard_activation_and_escape() {
      openMenu();
      delegateAt(0).forceActiveFocus();
      tryCompare(delegateAt(0), "activeFocus", true);
      keyClick(Qt.Key_Space);
      compare(triggeredSpy.count, 1);
      compare(triggeredSpy.signalArguments[0][0], "open");
      tryCompare(menu, "visible", false);
      openMenu();
      delegateAt(3).forceActiveFocus();
      keyClick(Qt.Key_Escape);
      tryCompare(menu, "visible", false);
      compare(triggeredSpy.count, 1);
    }

    function test_position_reopen_and_model_replacement() {
      menu.openAtItem(anchor, 7, 9);
      tryCompare(menu, "opened", true);
      compare(menu.x, 47);
      compare(menu.y, 59);
      menu.close();
      tryCompare(menu, "visible", false);
      menu.openAtItem(anchor);
      tryCompare(menu, "opened", true);
      compare(menu.x, 40);
      compare(menu.y, 50);
      menu.model = [
        {
          text: "Replacement",
          action: "replacement"
        }
      ];
      tryCompare(menu.contentItem, "count", 1);
      menu.contentItem.forceLayout();
      wait(30);
      compare(delegateAt(0).contentItem.children[1].text, "Replacement");
      mouseClick(delegateAt(0));
      compare(triggeredSpy.signalArguments[0][0], "replacement");
      tryCompare(menu, "visible", false);
      menu.model = [];
      openMenu();
      compare(menu.contentItem.count, 0);
      menu.close();
    }

    function test_two_instances_keep_delegate_owners() {
      openMenu();
      menu.close();
      tryCompare(menu, "visible", false);
      const other = createTemporaryObject(menuFactory, scene, {
        model: [
          {
            text: "Other",
            action: "other"
          }
        ],
        itemHeight: 60,
        itemPadding: 21
      });
      verify(other !== null);
      other.openAt(350, 100);
      tryCompare(other, "opened", true);
      other.contentItem.forceLayout();
      wait(30);
      const otherDelegate = other.contentItem.itemAtIndex(0);
      verify(otherDelegate !== null);
      compare(otherDelegate.height, 60);
      compare(otherDelegate.contentItem.children[1].Layout.leftMargin, 21);
      other.close();
      tryCompare(other, "visible", false);
      menu.model = [
        {
          text: "Recreated",
          action: "recreated"
        }
      ];
      menu.itemHeight = 44;
      menu.itemPadding = 11;
      openMenu();
      compare(delegateAt(0).height, 44);
      compare(delegateAt(0).contentItem.children[1].Layout.leftMargin, 11);
      mouseClick(delegateAt(0));
      compare(triggeredSpy.signalArguments[0][0], "recreated");
      tryCompare(menu, "visible", false);
      compare(other.visible, false);
      compare(otherDelegate.height, 60);
    }
  }
}
