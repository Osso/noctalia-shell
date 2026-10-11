import QtQuick
import QtQuick.Controls
import QtTest
import qs.Commons
import qs.Services.UI
import qs.Services.Power
import qs.Widgets

Item {
  id: scene
  width: 800
  height: 600

  Component {
    id: buttonFactory
    NIconButton {}
  }
  Component {
    id: hotFactory
    NIconButtonHot {}
  }
  Component {
    id: sliderFactory
    NSlider {}
  }
  Component {
    id: toggleFactory
    NToggle {}
  }
  Component {
    id: radioFactory
    NRadioButton {}
  }
  Component {
    id: checkboxFactory
    NCheckbox {}
  }
  Component {
    id: spinFactory
    NSpinBox {}
  }
  Component {
    id: labelFactory
    NLabel {}
  }
  Component {
    id: statFactory
    NCircleStat {}
  }
  Component {
    id: shadowFactory
    NDropShadow {}
  }

  TestCase {
    id: tests
    name: "SimpleWidgets"
    when: windowShown

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
    SignalSpy {
      id: enterSpy
      signalName: "entered"
    }
    SignalSpy {
      id: exitSpy
      signalName: "exited"
    }
    SignalSpy {
      id: toggleSpy
      signalName: "toggled"
    }
    SignalSpy {
      id: movedSpy
      signalName: "moved"
    }
    SignalSpy {
      id: wheelSpy
      signalName: "wheel"
    }

    function init() {
      Style.uiScaleRatio = 1;
      Style.radiusL = 12;
      TooltipService.hide();
      mouseMove(scene, 750, 550);
    }

    function cleanup() {
      mouseMove(scene, 750, 550);
    }

    function create(factory, properties) {
      const widget = createTemporaryObject(factory, scene, properties || {});
      verify(widget !== null);
      wait(20);
      return widget;
    }

    function observe(spy, widget) {
      spy.target = widget;
      spy.clear();
      verify(spy.valid);
    }

    function descendants(item) {
      let result = [];
      for (const child of item.children)
        result = result.concat([child], descendants(child));
      return result;
    }

    function test_buttons_data() {
      return [
        {
          tag: "plain",
          factory: buttonFactory
        },
        {
          tag: "hot",
          factory: hotFactory
        }
      ];
    }

    function test_buttons(row) {
      const widget = create(row.factory, {
        x: 100,
        y: 100,
        icon: "disc",
        tooltipText: "Action"
      });
      for (const spy of [clickSpy, rightSpy, middleSpy, enterSpy, exitSpy])
        observe(spy, widget);
      compare(widget.enabled, true);
      compare(widget.allowClickWhenDisabled, false);
      compare(widget.baseSize, 32);
      compare(widget.applyUiScale, true);
      compare(widget.density, "");
      compare(widget.width, 32);
      compare(widget.height, 32);
      compare(widget.radius, 12);
      compare(widget.color, NColor.mSurfaceVariant);
      const icon = descendants(widget).filter(child => child.icon === "disc")[0];
      compare(icon.color, NColor.mPrimary);
      mouseMove(widget, 16, 16);
      compare(widget.hovering, true);
      compare(enterSpy.count, 1);
      compare(TooltipService.lastText, "Action");
      compare(widget.color, NColor.mHover);
      compare(icon.color, NColor.mOnHover);
      mousePress(widget, 16, 16);
      if (row.tag === "hot") {
        compare(widget.pressed, true);
        compare(widget.scale, 0.92);
      }
      mouseRelease(widget, 16, 16);
      compare(clickSpy.count, 1);
      compare(TooltipService.lastText, "");
      mouseClick(widget, 16, 16, Qt.RightButton);
      mouseClick(widget, 16, 16, Qt.MiddleButton);
      compare(rightSpy.count, 1);
      compare(middleSpy.count, 1);
      if (row.tag === "hot") {
        compare(widget.pressed, false);
        compare(widget.scale, 1);
        widget.hot = true;
        mouseMove(scene, 750, 550);
        compare(widget.color, NColor.mPrimary);
        compare(icon.color, NColor.mOnPrimary);
        widget.hot = false;
      }
      mouseMove(scene, 750, 550);
      verify(exitSpy.count > 0);
      compare(widget.hovering, false);
      widget.enabled = false;
      compare(widget.opacity, 0.5);
      mouseMove(widget, 16, 16);
      compare(widget.hovering, false);
      // These widgets intentionally keep their input layer alive while disabled.
      compare(TooltipService.lastText, "Action");
      mouseClick(widget, 16, 16);
      compare(clickSpy.count, 1);
      widget.allowClickWhenDisabled = true;
      mouseClick(widget, 16, 16);
      // Hot release requires hovering, unlike the plain button's click handler.
      compare(clickSpy.count, row.tag === "plain" ? 2 : 1);
      widget.enabled = true;
      Style.uiScaleRatio = 1.5;
      compare(widget.width, 48);
      compare(widget.height, 48);
      widget.applyUiScale = false;
      compare(widget.width, 32);
      widget.baseSize = 10;
      compare(widget.radius, 5);
      widget.colorBg = "#123456";
      mouseMove(scene, 750, 550);
      compare(widget.color, Qt.color("#123456"));
    }

    function test_plain_button_wheel() {
      const widget = create(buttonFactory, {
        x: 100,
        y: 100
      });
      observe(wheelSpy, widget);
      mouseWheel(widget, 16, 16, 0, 120);
      compare(wheelSpy.count, 1);
      compare(wheelSpy.signalArguments[0][0], 120);
    }

    function test_slider_drag_geometry_disabled() {
      const widget = create(sliderFactory, {
        x: 100,
        y: 100,
        width: 200,
        from: 0,
        to: 100,
        stepSize: 10,
        value: 20,
        tooltipText: "Volume"
      });
      observe(movedSpy, widget);
      compare(widget.snapAlways, true);
      compare(widget.heightRatio, 0.7);
      compare(widget.knobDiameter, 22);
      compare(widget.trackHeight, 8);
      compare(widget.cutoutExtra, 4);
      compare(widget.padding, 2);
      compare(widget.implicitHeight, 22);
      compare(widget.background.height, 8);
      compare(widget.background.radius, 4);
      compare(widget.handle.width, 22);
      const knob = widget.handle.children[0];
      compare(knob.width, 22);
      compare(knob.radius, 11);
      compare(knob.border.color, NColor.mPrimary);
      mouseMove(widget.handle, 11, 11);
      compare(widget.hovering, true);
      compare(TooltipService.lastText, "Volume");
      const start = widget.handle.x + 11;
      mousePress(widget, start, widget.height / 2);
      compare(widget.pressed, true);
      compare(TooltipService.lastText, "");
      mouseMove(widget, 170, widget.height / 2, 20);
      mouseRelease(widget, 170, widget.height / 2);
      compare(widget.value, 90);
      verify(movedSpy.count > 0);
      widget.enabled = false;
      const count = movedSpy.count;
      mouseClick(widget, 10, widget.height / 2);
      compare(widget.value, 90);
      compare(movedSpy.count, count);
      widget.fillColor = "#123456";
      compare(knob.border.color, Qt.color("#123456"));
      Style.radiusL = 3;
      compare(knob.radius, 3);
      compare(widget.background.radius, 3);
      Style.uiScaleRatio = 1.5;
      compare(widget.knobDiameter, 34);
      compare(widget.trackHeight, 20);
      compare(widget.cutoutExtra, 4);
      widget.snapAlways = false;
      compare(widget.snapMode, Slider.SnapOnRelease);
    }

    function test_toggle_checkbox_data() {
      return [
        {
          tag: "toggle",
          factory: toggleFactory
        },
        {
          tag: "checkbox",
          factory: checkboxFactory
        }
      ];
    }

    function test_toggle_checkbox(row) {
      const widget = create(row.factory, {
        x: 100,
        y: 100,
        width: 240
      });
      observe(toggleSpy, widget);
      observe(enterSpy, widget);
      observe(exitSpy, widget);
      compare(widget.checked, false);
      compare(widget.label, "");
      compare(widget.description, "");
      const control = widget.children[widget.children.length - 1];
      mouseMove(control, control.width / 2, control.height / 2);
      compare(widget.hovering, true);
      compare(enterSpy.count, 1);
      mouseClick(control, control.width / 2, control.height / 2);
      compare(toggleSpy.count, 1);
      compare(toggleSpy.signalArguments[0][0], true);
      // Consumer owns checked state; emission alone must not change it.
      compare(widget.checked, false);
      widget.checked = true;
      compare(control.color, NColor.mPrimary);
      mouseClick(control, control.width / 2, control.height / 2);
      compare(toggleSpy.signalArguments[1][0], false);
      mouseMove(scene, 750, 550);
      compare(widget.hovering, false);
      compare(exitSpy.count, 1);
      if (row.tag === "toggle") {
        compare(widget.baseSize, 26);
        compare(control.width, 44);
        compare(control.height, 26);
        compare(control.radius, 12);
        const thumb = control.children[0];
        compare(thumb.width, 20);
        compare(thumb.x, 21);
        compare(thumb.color, NColor.mOnPrimary);
        widget.checked = false;
        compare(thumb.x, 3);
        compare(widget.opacity, 1);
      } else {
        compare(control.width, 22);
        compare(control.height, 22);
        compare(control.radius, 2);
        compare(control.children[0].visible, true);
      }
      widget.enabled = false;
      mouseClick(control, control.width / 2, control.height / 2);
      compare(toggleSpy.count, 2);
      compare(widget.checked, row.tag !== "toggle");
      if (row.tag === "toggle")
        compare(widget.opacity, 0.6);
    }

    function test_radio_checked_geometry_disabled() {
      const widget = create(radioFactory, {
        x: 100,
        y: 100,
        text: "Choice"
      });
      observe(clickSpy, widget);
      compare(widget.checked, false);
      compare(widget.pointSize, 12);
      compare(widget.indicator.width, 20);
      compare(widget.indicator.height, 20);
      compare(widget.indicator.radius, 10);
      compare(widget.contentItem.text, "Choice");
      mouseClick(widget, 10, widget.height / 2);
      compare(widget.checked, true);
      compare(clickSpy.count, 1);
      compare(widget.indicator.border.color, NColor.mPrimary);
      compare(widget.indicator.children[0].color, NColor.mPrimary);
      widget.checked = false;
      widget.enabled = false;
      mouseClick(widget, 10, widget.height / 2);
      compare(widget.checked, false);
      compare(clickSpy.count, 1);
      widget.pointSize = 18;
      compare(widget.indicator.width, 30);
      compare(widget.indicator.radius, 12);
    }

    function test_spin_click_repeat_bounds_disabled() {
      const widget = create(spinFactory, {
        x: 100,
        y: 100,
        width: 240,
        value: 5,
        from: 0,
        to: 10
      });
      compare(widget.stepSize, 1);
      compare(widget.initialRepeatDelay, 400);
      compare(widget.repeatInterval, 80);
      compare(widget.rampFactor, 4);
      compare(widget.maxStepMultiplier, 10);
      widget.initialRepeatDelay = 40;
      widget.repeatInterval = 20;
      const control = widget.children[widget.children.length - 1];
      compare(control.width, 120);
      compare(control.height, 28);
      compare(control.radius, 4);
      mouseClick(control, 110, 14);
      compare(widget.value, 6);
      mouseClick(control, 10, 14);
      compare(widget.value, 5);
      mouseWheel(control, 60, 14, 0, 120);
      compare(widget.value, 6);
      mousePress(control, 110, 14);
      tryCompare(widget, "value", 10, 500);
      mouseRelease(control, 110, 14);
      compare(widget._repeatDirection, 0);
      widget.value = 5;
      widget.enabled = false;
      mouseClick(control, 110, 14);
      compare(widget.value, 5);
      // Existing shadowed enabled gates buttons/input, not the scroll layer.
      mouseWheel(control, 60, 14, 0, -120);
      compare(widget.value, 4);
      const input = descendants(control).filter(child => child.selectByMouse === true)[0];
      compare(input.enabled, false);
      widget.enabled = true;
      input.forceActiveFocus();
      input.text = "9";
      keyClick(Qt.Key_Return);
      compare(widget.value, 9);
      compare(input.focus, false);
    }

    function test_label_stat_shadow() {
      const label = create(labelFactory, {
        x: 100,
        y: 100,
        width: 240
      });
      compare(label.children[0].visible, false);
      compare(label.children[1].visible, false);
      label.label = "Charge";
      label.description = "<i>Battery</i>";
      compare(label.children[0].text, "Charge");
      compare(label.children[0].visible, true);
      compare(label.children[1].text, "<i>Battery</i>");
      compare(label.children[1].visible, true);
      label.labelColor = "#123456";
      label.descriptionColor = "#654321";
      compare(label.children[0].color, Qt.color("#123456"));
      compare(label.children[1].color, Qt.color("#654321"));
      const stat = create(statFactory, {
        x: 400,
        y: 100,
        value: 42,
        icon: "disc"
      });
      compare(stat.width, 68);
      compare(stat.height, 92);
      compare(stat.radius, 4);
      compare(stat.suffix, "%");
      compare(stat.contentScale, 1);
      compare(stat.flat, false);
      compare(stat.color, NColor.mSurface);
      const number = descendants(stat).filter(child => child.text === "42%")[0];
      verify(number !== undefined);
      compare(number.pointSize, 10.8);
      stat.contentScale = 0.5;
      wait(40);
      compare(number.pointSize, 5.4);
      compare(stat.width, 68);
      compare(stat.height, 92);
      stat.value = 75;
      compare(number.text, "75%");
      compare(stat.animatedValue, 75);
      stat.flat = true;
      compare(stat.color, NColor.transparent);
      compare(stat.border.width, 0);
      const shadow = create(shadowFactory, {
        source: stat
      });
      compare(shadow.source, stat);
      compare(shadow.autoPaddingEnabled, false);
      compare(shadow.shadowHorizontalOffset, 2);
      compare(shadow.shadowVerticalOffset, 3);
      compare(shadow.shadowOpacity, 0.4);
      compare(shadow.shadowBlur, 0.6);
      compare(shadow.layer.enabled, false);
      // Instantiate the real effect without creating a visible desktop surface.
      Settings.data.general.enableShadows = true;
      Settings.dataChanged();
      wait(20);
      compare(shadow.layer.enabled, true);
      PowerProfileService.noctaliaPerformanceMode = true;
      compare(shadow.layer.enabled, false);
      PowerProfileService.noctaliaPerformanceMode = false;
      Settings.data.general.enableShadows = false;
      Settings.dataChanged();
    }
  }
}
