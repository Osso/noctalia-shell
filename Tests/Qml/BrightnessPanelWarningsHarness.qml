import QtQuick
import QtTest
import Quickshell
import qs.Modules.Panels.Brightness
import qs.Services.Hardware

Item {
  id: scene
  width: 500
  height: 600

  ShellScreen {
    id: internalScreen
    name: "eDP-1"
    model: "Laptop"
    width: 1920
    height: 1080
  }
  ShellScreen {
    id: externalScreen
    name: "DP-1"
    model: "DDC-disabled"
    width: 2560
    height: 1440
  }
  ShellScreen {
    id: replacementScreen
    name: "fake-replacement"
    model: "Fixture"
    width: 1280
    height: 720
  }
  ShellScreen {
    id: unknownScreen
    name: "unknown"
    model: "No provider"
    width: 800
    height: 600
  }

  Component {
    id: panelComponent
    BrightnessPanel {
      width: preferredWidth
      height: preferredHeight
    }
  }

  TestCase {
    id: testCase
    name: "BrightnessPanelWarnings"
    when: windowShown
    property var panel

    function descendants(item, predicate) {
      let found = [];
      for (const child of item.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }

    function outputs() {
      const repeaters = descendants(panel.contentItem, child => child.itemAt !== undefined);
      compare(repeaters.length, 1);
      return repeaters[0];
    }

    function valueSlider(output) {
      const sliders = descendants(output, child => child.textSize !== undefined);
      compare(sliders.length, 1);
      return sliders[0];
    }

    function inputSlider(output) {
      const sliders = descendants(output, child => child.visualPosition !== undefined);
      compare(sliders.length, 1);
      return sliders[0];
    }

    function label(output) {
      const labels = descendants(output, child => child.description !== undefined);
      compare(labels.length, 1);
      return labels[0];
    }

    function brightnessIcon(output) {
      const icons = descendants(output, child => child.icon !== undefined);
      compare(icons.length, 1);
      return icons[0];
    }

    function init() {
      const service = BrightnessService;
      service.internalMonitor.brightness = 0.25;
      service.externalMonitor.brightness = 0.6;
      service.replacementMonitor.brightness = 0.4;
      service.internalMonitor.writes = [];
      service.externalMonitor.writes = [];
      service.replacementMonitor.writes = [];
      Quickshell.screens = [internalScreen, externalScreen];
      panel = panelComponent.createObject(scene);
      verify(panel !== null);
      tryVerify(() => panel.contentItem !== null);
      tryCompare(outputs(), "count", 2);
      wait(30);
    }

    function cleanup() {
      panel.destroy();
      panel = null;
      wait(0);
      Quickshell.screens = [];
    }

    function test_monitor_metadata_and_provider_updates() {
      const internal = outputs().itemAt(0);
      const external = outputs().itemAt(1);
      compare(label(internal).label, "eDP-1");
      compare(JSON.parse(label(internal).description), {
        model: "Laptop",
        width: 2880,
        height: 1620,
        scale: 1.5
      });
      compare(label(external).label, "DP-1");
      compare(JSON.parse(label(external).description), {
        model: "DDC-disabled",
        width: 2560,
        height: 1440,
        scale: 1
      });
      compare(valueSlider(internal).value, 0.25);
      compare(valueSlider(internal).text, "25%");
      compare(brightnessIcon(internal).icon, "brightness-low");
      BrightnessService.internalMonitor.brightness = 0.8;
      tryCompare(valueSlider(internal), "value", 0.8);
      compare(valueSlider(internal).text, "80%");
      compare(brightnessIcon(internal).icon, "brightness-high");
      compare(BrightnessService.internalMonitor.writes, []);
      compare(BrightnessService.externalMonitor.writes, []);
    }

    function dragAndCommit(output, monitor) {
      const slider = inputSlider(output);
      verify(slider.width > 100);
      const startX = slider.handle.x + slider.handle.width / 2;
      const endX = slider.leftPadding + slider.handle.width / 2 + 0.75 * (slider.availableWidth - slider.handle.width);
      const y = slider.height / 2;
      mousePress(slider, startX, y, Qt.LeftButton);
      verify(slider.pressed);
      const pressWrites = monitor.writes.length;
      verify(pressWrites > 0);
      mouseMove(slider, endX, y, 30, Qt.LeftButton);
      tryVerify(() => monitor.writes.length > pressWrites);
      verify(Math.abs(slider.value - 0.75) <= 0.02);
      const dragWrites = monitor.writes.length;
      const draggedValue = slider.value;
      mouseRelease(slider, endX, y, Qt.LeftButton);
      compare(slider.pressed, false);
      compare(monitor.writes.length, dragWrites + 1);
      compare(monitor.writes[monitor.writes.length - 1], draggedValue);
      compare(monitor.brightness, draggedValue);
      compare(valueSlider(output).text, Math.round(draggedValue * 100) + "%");
    }

    function test_actual_slider_drag_and_release_commit() {
      dragAndCommit(outputs().itemAt(0), BrightnessService.internalMonitor);
      compare(BrightnessService.externalMonitor.writes, []);
      compare(BrightnessService.replacementMonitor.writes, []);
    }

    function test_monitor_switch_routes_new_slider_only() {
      dragAndCommit(outputs().itemAt(0), BrightnessService.internalMonitor);
      const originalWrites = BrightnessService.internalMonitor.writes.slice();
      Quickshell.screens = [externalScreen, replacementScreen];
      tryCompare(outputs(), "count", 2);
      tryCompare(label(outputs().itemAt(1)), "label", "fake-replacement");
      compare(valueSlider(outputs().itemAt(1)).value, 0.4);
      compare(valueSlider(outputs().itemAt(0)).enabled, false);
      wait(30);
      dragAndCommit(outputs().itemAt(1), BrightnessService.replacementMonitor);
      compare(BrightnessService.internalMonitor.writes, originalWrites);
      compare(BrightnessService.externalMonitor.writes, []);
    }

    function test_ddc_disabled_and_missing_provider_never_write() {
      compare(BrightnessService.enableDdcSupport, false);
      const external = outputs().itemAt(1);
      compare(valueSlider(external).enabled, false);
      const slider = inputSlider(external);
      mouseDrag(slider, slider.width / 4, slider.height / 2, slider.width / 2, 0);
      compare(BrightnessService.externalMonitor.writes, []);
      // Guard coverage even if a caller emits a signal on a disabled control.
      valueSlider(external).moved(0.9);
      valueSlider(external).pressedChanged(false, 0.9);
      compare(BrightnessService.externalMonitor.writes, []);
      compare(BrightnessService.externalMonitor.brightness, 0.6);
      Quickshell.screens = [unknownScreen];
      tryCompare(outputs(), "count", 1);
      const unknown = valueSlider(outputs().itemAt(0));
      compare(unknown.enabled, false);
      compare(unknown.value, 0.5);
      compare(unknown.text, "N/A");
      unknown.moved(0.9);
      unknown.pressedChanged(false, 0.9);
      compare(BrightnessService.internalMonitor.writes, []);
      compare(BrightnessService.externalMonitor.writes, []);
      compare(BrightnessService.replacementMonitor.writes, []);
    }

    function test_close_targets_panel_owner() {
      const buttons = descendants(panel.contentItem, child => child.tooltipText === "tooltips.close");
      compare(buttons.length, 1);
      buttons[0].clicked();
      compare(panel.closeCount, 1);
    }
  }
}
