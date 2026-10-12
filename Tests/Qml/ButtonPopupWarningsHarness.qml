import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
import qs.Widgets
import qs.Services.UI

ShellRoot {
  id: suite

  TestCase {
    id: input
    when: false
  }

  FloatingWindow {
    id: window
    implicitWidth: 640
    implicitHeight: 480
    visible: true // Runner permits only software/offscreen Qt.

    Item {
      id: anchorOne
      x: 30
      y: 40
      width: 100
      height: 40
    }
    Item {
      id: anchorTwo
      x: 300
      y: 200
      width: 100
      height: 40
    }

    NButton {
      id: buttonOne
      x: 50
      y: 100
      text: "Action"
      tooltipText: "Owner tooltip"
      visible: false
    }
    NButton {
      id: buttonTwo
      x: 50
      y: 100
      text: "Action"
      tooltipText: "Owner tooltip"
      visible: false
    }
  }

  Component {
    id: popupFactory
    NPopupContextMenu {}
  }

  function require(condition, message) {
    if (!condition)
      throw new Error(message);
  }

  function equal(actual, expected, message) {
    require(actual === expected, message + ": got " + actual + ", expected " + expected);
  }

  function settle() {
    input.wait(40);
  }

  function descendants(item, predicate) {
    let matches = predicate(item) ? [item] : [];
    for (const child of item.children || [])
      matches = matches.concat(descendants(child, predicate));
    return matches;
  }

  function mouseArea(item) {
    return descendants(item, child => child.acceptedButtons !== undefined)[0];
  }

  function entries(popup) {
    return descendants(popup.contentItem, child => child.itemAction !== undefined);
  }

  function makePopup(height, label) {
    return popupFactory.createObject(suite, {
      itemHeight: height,
      model: [
        {
          label: label,
          action: "first"
        },
        {
          label: "Disabled",
          action: "disabled",
          enabled: false
        },
        {
          label: "Hidden",
          action: "hidden",
          visible: false
        }
      ]
    });
  }

  function testButtonInput() {
    const button = buttonOne;
    button.visible = true;
    settle();
    try {
      const counts = {
        left: 0,
        right: 0,
        middle: 0,
        entered: 0,
        exited: 0
      };
      button.clicked.connect(() => counts.left++);
      button.rightClicked.connect(() => counts.right++);
      button.middleClicked.connect(() => counts.middle++);
      button.entered.connect(() => counts.entered++);
      button.exited.connect(() => counts.exited++);
      button.forceActiveFocus();
      settle();
      equal(button.activeFocus, true, "button explicit focus");
      input.mouseMove(button, 10, 10);
      settle();
      equal(button.hovered, true, "button hovered");
      equal(TooltipService.lastText, "Owner tooltip", "tooltip shown");
      input.mousePress(button, 10, 10);
      equal(counts.left, 1, "press dispatch");
      equal(TooltipService.lastText, "", "press hides tooltip");
      input.mouseRelease(button, 10, 10);
      equal(counts.left, 1, "release does not redispatch");
      input.mouseClick(button, 10, 10, Qt.RightButton);
      input.mouseClick(button, 10, 10, Qt.MiddleButton);
      equal(counts.right, 1, "right dispatch");
      equal(counts.middle, 1, "middle dispatch");
      input.mouseMove(window.contentItem, 600, 440);
      settle();
      equal(button.hovered, false, "hover exit");
      require(counts.entered > 0 && counts.exited > 0, "enter/exit signals");
      button.enabled = false;
      input.mouseClick(button, 10, 10);
      equal(counts.left, 1, "disabled click rejected");
      button.enabled = true;
      input.mouseClick(button, 10, 10);
      equal(counts.left, 2, "reenabled dispatch");
    } finally {
      input.mouseMove(window.contentItem, 600, 440);
      button.visible = false;
      settle();
    }
  }

  function testButtonTooltipOwner() {
    const button = buttonTwo;
    button.visible = true;
    settle();
    try {
      // Runner can inject an empty tooltipText into the production MouseArea.
      const area = mouseArea(button);
      require(area !== undefined, "button mouse area");
      input.mouseMove(button, 10, 10);
      settle();
      equal(TooltipService.lastText, "Owner tooltip", "root tooltip with child shadow");
      input.mouseMove(window.contentItem, 600, 440);
      settle();
      equal(TooltipService.lastText, "", "exit hides root tooltip");
      input.mouseMove(button, 10, 10);
      settle();
      area.canceled();
      equal(button.hovered, false, "cancel clears hover");
      equal(TooltipService.lastText, "", "cancel hides tooltip");
    } finally {
      button.visible = false;
      settle();
    }
  }

  function testPopupPositionAndClose() {
    const popup = makePopup(31, "Position");
    try {
      popup.openAt(17, 23, anchorOne);
      settle();
      equal(popup.visible, true, "popup opened");
      equal(popup.anchor.item, anchorOne, "anchor item");
      equal(popup.anchor.rect.x, 17, "anchor x");
      equal(popup.anchor.rect.y, 23, "anchor y");
      equal(popup.contentItem.Window.window.x, window.contentItem.Window.window.x + anchorOne.x + 17, "actual popup x");
      equal(popup.contentItem.Window.window.y, window.contentItem.Window.window.y + anchorOne.y + 23, "actual popup y");
      popup.closeMenu();
      equal(popup.visible, false, "closeMenu hides");
      popup.openAtItem(anchorTwo);
      settle();
      equal(popup.anchor.item, anchorTwo, "reopen owner");
      equal(popup.anchor.rect.x, 0, "default x");
      equal(popup.anchor.rect.y, 0, "default y");
      popup.close();
      equal(popup.visible, false, "close hides");
    } finally {
      popup.destroy();
      settle();
    }
  }

  function testPopupHoverAndActivation() {
    const popup = makePopup(32, "Clickable");
    try {
      const actions = [];
      popup.triggered.connect(action => actions.push(action));
      popup.openAt(0, 0, anchorOne);
      settle();
      const rows = entries(popup);
      equal(rows.length, 3, "all delegates instantiated");
      equal(rows[2].visible, false, "hidden delegate");
      input.mouseMove(rows[0], 20, 15);
      settle();
      equal(mouseArea(rows[0]).containsMouse, true, "popup hover");
      input.mouseClick(rows[0], 20, 15);
      equal(actions.join(","), "first", "enabled activation");
      equal(popup.visible, true, "parent controls closing");
      input.mouseClick(rows[1], 20, 15);
      equal(actions.length, 1, "disabled activation rejected");
      popup.close();
    } finally {
      popup.destroy();
      settle();
    }
  }

  function testPopupFocusEscape() {
    const popup = makePopup(32, "Escape");
    try {
      popup.openAt(0, 0, anchorOne);
      settle();
      const focusItems = descendants(popup.contentItem, item => item.focus);
      require(focusItems.length > 0, "popup focus item exists");
      popup.contentItem.Window.window.requestActivate();
      focusItems[0].forceActiveFocus();
      settle();
      equal(focusItems[0].activeFocus, true, "popup focus acquired");
      input.keyClick(Qt.Key_Escape);
      settle();
      equal(popup.visible, false, "Escape closes focused popup");
    } finally {
      popup.destroy();
      settle();
    }
  }

  function testPopupRecreationOwners() {
    const first = makePopup(29, "Short");
    let second = makePopup(47, "Second owner with a substantially longer label");
    try {
      const firstActions = [];
      const secondActions = [];
      first.triggered.connect(action => firstActions.push(action));
      second.triggered.connect(action => secondActions.push(action));
      first.openAt(0, 0, anchorOne);
      second.openAt(0, 0, anchorTwo);
      settle();
      equal(entries(first)[0].height, 29, "first height owner");
      equal(entries(second)[0].height, 47, "second height owner");
      require(second.calculatedWidth > first.calculatedWidth, "independent width");
      input.mouseClick(entries(second)[0], 20, 15);
      equal(secondActions.length, 1, "second dispatch owner");
      equal(firstActions.length, 0, "first not dispatched");
      first.model = [];
      settle();
      equal(entries(first).length, 0, "delegates cleared");
      first.model = [
        {
          text: "Replacement",
          key: "replacement"
        }
      ];
      first.itemHeight = 35;
      settle();
      equal(entries(first).length, 1, "delegate recreated");
      equal(entries(first)[0].height, 35, "recreated height owner");
      input.mouseClick(entries(first)[0], 20, 15);
      equal(firstActions.join(","), "replacement", "recreated action");
      first.close();
      equal(mouseArea(entries(first)[0]).enabled, false, "closed owner disables click");
      equal(mouseArea(entries(second)[0]).enabled, true, "other owner still open");
      second.close();
      second.destroy();
      settle();
      second = makePopup(53, "New instance");
      second.openAtItem(anchorTwo, 5, 6);
      settle();
      equal(entries(second)[0].height, 53, "new instance delegates");
      equal(second.anchor.rect.x, 5, "new instance position");
      second.close();
    } finally {
      first.destroy();
      second.destroy();
      settle();
    }
  }

  Timer {
    interval: 150
    running: true
    onTriggered: {
      try {
        suite.testButtonInput();
        suite.testButtonTooltipOwner();
        suite.testPopupPositionAndClose();
        suite.testPopupHoverAndActivation();
        suite.testPopupFocusEscape();
        suite.testPopupRecreationOwners();
        console.log("BUTTON_POPUP_PASS 6 cases");
        Qt.exit(0);
      } catch (error) {
        console.error("BUTTON_POPUP_FAIL", error.message);
        Qt.exit(1);
      }
    }
  }
}
