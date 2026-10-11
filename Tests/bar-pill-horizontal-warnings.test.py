#!/usr/bin/env python3
"""Horizontal production pill/Loader proof with inert services and no desktop IO.

Reuses BarPill's locked settings backup and isolated offscreen runtime. Geometry,
hover delay/cancellation, animation, press/release and callbacks cover both
font densities at UI scales 1 and 1.25. Lint targets only the horizontal file.
"""

import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WIDGET = Path("Modules/Bar/Extras/BarPillHorizontal.qml")


def load_pill_helper():
    spec = importlib.util.spec_from_file_location(
        "bar_pill", ROOT / "Tests/bar-pill-warnings.test.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def run_lint(directory):
    load_pill_helper().load_helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / WIDGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("BAR_PILL_HORIZONTAL_LINT_COUNTS", dict(counts))
    assert not counts, f"horizontal warnings remain: {dict(counts)}"
    assert result.returncode == 0, f"unexpected qmllint exit {result.returncode}"


def run_behavior(directory):
    helper = load_pill_helper()
    helper.HARNESS = HARNESS
    helper.run_behavior(directory)


HARNESS = r"""import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Services.UI
import qs.Modules.Bar.Extras

Item {
  id: scene
  width: 800
  height: 600
  ShellScreen { id: fixtureScreen; name: "fixture" }
  Component {
    id: factory
    BarPill { screen: fixtureScreen }
  }
  TestCase {
    id: tests
    name: "BarPillHorizontal"
    when: windowShown
    property var widget
    SignalSpy { id: shownSpy; signalName: "shown" }
    SignalSpy { id: hiddenSpy; signalName: "hidden" }
    SignalSpy { id: enteredSpy; signalName: "entered" }
    SignalSpy { id: exitedSpy; signalName: "exited" }
    SignalSpy { id: clickSpy; signalName: "clicked" }
    SignalSpy { id: rightSpy; signalName: "rightClicked" }
    SignalSpy { id: middleSpy; signalName: "middleClicked" }
    SignalSpy { id: wheelSpy; signalName: "wheel" }

    function rows() {
      return [
        {tag: "default-1", density: "", scale: 1},
        {tag: "compact-1", density: "compact", scale: 1},
        {tag: "default-1.25", density: "", scale: 1.25},
        {tag: "compact-1.25", density: "compact", scale: 1.25}
      ];
    }
    function init() {
      Settings.data.bar.position = "top";
      Settings.dataChanged();
      widget = createTemporaryObject(factory, scene, {
        x: 200, y: 200, text: "42", suffix: "%", icon: "battery", tooltipText: "Charge"
      });
      verify(widget !== null);
      for (const spy of [shownSpy, hiddenSpy, enteredSpy, exitedSpy, clickSpy, rightSpy, middleSpy, wheelSpy]) {
        spy.target = widget;
        spy.clear();
      }
      wait(10);
    }
    function cleanup() { mouseMove(scene, 750, 550); }
    function pill() { return widget.children[0].item; }
    function descendants(item) {
      let children = [];
      for (const child of item.children)
        children = children.concat([child], descendants(child));
      return children;
    }
    function label() { return descendants(pill()).filter(child => child.text === "42%")[0]; }
    function icon() { return descendants(pill()).filter(child => child.icon === "battery")[0]; }
    function applyRow(row) {
      Style.uiScaleRatio = row.scale;
      Style.capsuleHeight = 40 * row.scale;
      widget.density = row.density;
      wait(10);
    }
    function test_geometry_data() { return rows(); }
    function test_geometry(row) {
      applyRow(row);
      const height = 40 * row.scale;
      compare(widget.width, height);
      compare(widget.height, height);
      compare(label().visible, false);
      widget.forceOpen = true;
      wait(150);
      compare(pill().screen, fixtureScreen);
      compare(widget.width, pill().width);
      compare(widget.height, height);
      compare(label().pointSize, Math.round(height * (row.density === "compact" ? 0.45 : 0.33)));
      compare(icon().pointSize, Math.round(height * (row.density === "compact" ? 0.65 : 0.48)));
      compare(icon().text, "B");
      compare(icon().parent.width, height);
      compare(label().text, "42%");
      compare(label().visible, true);
      const panel = label().parent;
      const overlap = Math.round(height * 0.5);
      const padding = Math.round(height * 0.2);
      compare(panel.width, Math.round(label().implicitWidth + padding * 2 + overlap));
      compare(widget.width, height + panel.width - overlap);
      compare(panel.opacity, 1);
      for (const opposite of [false, true]) {
        widget.oppositeDirection = opposite;
        wait(10);
        compare(icon().parent.x, opposite ? 0 : widget.width - height);
        compare(panel.x, icon().parent.x + height / 2 - (opposite ? 0 : panel.width));
        const offset = opposite ? Style.marginXS - Style.marginXXS : -Style.marginXS + Style.marginXXS;
        compare(label().x, (panel.width - label().width) / 2 + offset);
        console.log("HORIZONTAL_GEOMETRY", JSON.stringify([row.tag, opposite, widget.width, widget.height,
          panel.x, panel.width, label().x, label().width, label().height, icon().x, icon().y, icon().width, icon().height]));
      }
      widget.forceClose = true;
      widget.forceOpen = false;
      widget.show();
      widget.showDelayed();
      wait(200);
      compare(widget.width, height);
      compare(label().visible, false);
    }
    function test_hover_and_clicks_data() { return rows(); }
    function test_hover_and_clicks(row) {
      applyRow(row);
      mouseMove(widget, 20, 20);
      compare(enteredSpy.count, 1);
      compare(pill().hovered, true);
      compare(TooltipService.lastText, "Charge");
      widget.tooltipText = "Updated";
      compare(TooltipService.lastText, "Updated");
      wait(30);
      compare(pill().showPill, false);
      mouseMove(scene, 750, 550);
      wait(200);
      compare(shownSpy.count, 0);
      compare(pill().hovered, false);
      mouseMove(widget, 20, 20);
      tryCompare(shownSpy, "count", 1, 500);
      compare(label().parent.opacity, 1);
      for (const button of [Qt.LeftButton, Qt.RightButton, Qt.MiddleButton]) {
        mousePress(widget, 20, 20, button);
        compare(clickSpy.count + rightSpy.count + middleSpy.count, button === Qt.LeftButton ? 0 : button === Qt.RightButton ? 1 : 2);
        mouseRelease(widget, 20, 20, button);
      }
      compare(clickSpy.count, 1);
      compare(rightSpy.count, 1);
      compare(middleSpy.count, 1);
      mouseWheel(widget, 20, 20, 0, 120);
      compare(wheelSpy.signalArguments[0][0], 120);
      mouseMove(scene, 750, 550);
      compare(exitedSpy.count, 2);
      compare(TooltipService.lastText, "");
      tryCompare(hiddenSpy, "count", 1, 500);
      compare(label().visible, false);
      compare(label().parent.opacity, 0);
      compare(widget.width, 40 * row.scale);
    }
    function test_auto_hide_data() { return rows(); }
    function test_auto_hide(row) {
      applyRow(row);
      widget.autoHide = true;
      widget.show();
      tryCompare(shownSpy, "count", 1, 500);
      wait(150);
      compare(hiddenSpy.count, 0);
      compare(label().parent.opacity, 1);
      tryCompare(hiddenSpy, "count", 1, 3200);
      compare(pill().showPill, false);
      compare(label().parent.opacity, 0);
      compare(widget.width, 40 * row.scale);
    }
  }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-bar-pill-horizontal-"
    ) as temporary:
        (run_lint if args.mode == "lint" else run_behavior)(Path(temporary))


if __name__ == "__main__":
    main()
