import QtQuick
import QtTest
import qs.Commons
import qs.Widgets

TestCase {
  id: suite
  name: "ButtonEnabledWarnings"
  width: 600
  height: 400
  when: windowShown
  visible: true

  Component {
    id: buttonFactory
    NButton {
      text: "Action"
      icon: "disc"
      tooltipText: "Action tooltip"
    }
  }
  Component {
    id: inputFactory
    NTextInput {}
  }
  SignalSpy {
    id: clickSpy
    signalName: "clicked"
  }
  SignalSpy {
    id: rightSpy
    signalName: "rightClicked"
  }
  SignalSpy {
    id: middleSpy
    signalName: "middleClicked"
  }

  function cleanup() {
    mouseMove(suite, 550, 350);
  }

  function test_button_data() {
    return [
          {
            tag: "filled",
            outlined: false
          },
          {
            tag: "outlined",
            outlined: true
          }
        ];
  }

  function test_button(row) {
    const button = createTemporaryObject(buttonFactory, suite, {
                                           x: 50,
                                           y: 50,
                                           outlined: row.outlined
                                         });
    verify(button !== null);
    for (const spy of [clickSpy, rightSpy, middleSpy]) {
      spy.target = button;
      spy.clear();
      verify(spy.valid);
    }
    mouseMove(suite, 550, 350);
    compare(button.enabled, true);
    compare(button.opacity, 1);
    tryCompare(button, "color", row.outlined ? NColor.transparent : NColor.mPrimary);
    compare(button.border.width, row.outlined ? Style.borderS : 0);
    tryCompare(button.border, "color", row.outlined ? NColor.mPrimary : NColor.transparent);
    mouseMove(button, button.width / 2, button.height / 2);
    tryCompare(button, "hovered", true);
    tryCompare(button, "color", NColor.mHover);
    mousePress(button, button.width / 2, button.height / 2);
    compare(clickSpy.count, 1);
    mouseRelease(button, button.width / 2, button.height / 2);
    compare(clickSpy.count, 1);
    mouseClick(button, button.width / 2, button.height / 2, Qt.RightButton);
    mouseClick(button, button.width / 2, button.height / 2, Qt.MiddleButton);
    compare(rightSpy.count, 1);
    compare(middleSpy.count, 1);
    mouseMove(suite, 550, 350);
    tryCompare(button, "hovered", false);
    button.enabled = false;
    compare(button.opacity, 0.6);
    tryCompare(button, "color", row.outlined ? NColor.transparent : Qt.lighter(NColor.mSurfaceVariant, 1.2));
    tryCompare(button.border, "color", NColor.mOutline);
    mouseMove(button, button.width / 2, button.height / 2);
    compare(button.hovered, false);
    for (const mouseButton of [Qt.LeftButton, Qt.RightButton, Qt.MiddleButton])
      mouseClick(button, button.width / 2, button.height / 2, mouseButton);
    compare(clickSpy.count, 1);
    compare(rightSpy.count, 1);
    compare(middleSpy.count, 1);
    mouseMove(suite, 550, 350);
    button.enabled = true;
    compare(button.opacity, 1);
    mouseClick(button, button.width / 2, button.height / 2);
    compare(clickSpy.count, 2);
  }

  function test_text_input_enabled() {
    const field = createTemporaryObject(inputFactory, suite, {
                                          x: 50,
                                          y: 150,
                                          width: 300,
                                          text: "seed"
                                        });
    verify(field !== null);
    compare(field.enabled, true);
    mouseClick(field.inputItem, 10, field.inputItem.height / 2);
    tryCompare(field.inputItem, "activeFocus", true);
    field.inputItem.selectAll();
    keyClick(Qt.Key_A);
    compare(field.text, "a");
    field.enabled = false;
    compare(field.inputItem.enabled, false);
    mouseClick(field.inputItem, 10, field.inputItem.height / 2);
    keyClick(Qt.Key_B);
    compare(field.text, "a");
    field.enabled = true;
    compare(field.inputItem.enabled, true);
    mouseClick(field.inputItem, 10, field.inputItem.height / 2);
    tryCompare(field.inputItem, "activeFocus", true);
    field.inputItem.selectAll();
    keyClick(Qt.Key_C);
    compare(field.text, "c");
  }
}
