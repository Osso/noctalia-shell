#!/usr/bin/env python3
"""Bounded production BarPillVertical lint and offscreen interaction proof.

Reuse read-only BarPill fixture services and isolated settings backup/runner.
No canonical settings bootstrap or desktop surfaces are exercised.
"""

import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
import tempfile

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
WIDGET = Path("Modules/Bar/Extras/BarPillVertical.qml")


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lint(directory):
    load_helper("media-mini-warnings").stage_modules(directory)
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
    print("BAR_PILL_VERTICAL_LINT_COUNTS", dict(counts))
    assert not counts, f"vertical warnings remain: {dict(counts)}"
    assert result.returncode == 0, f"unexpected qmllint exit {result.returncode}"


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
  ShellScreen {
    id: fixtureScreen
    name: "fixture"
  }
  Component {
    id: pillFactory
    BarPillVertical {
      screen: fixtureScreen
    }
  }
  TestCase {
    id: tests
    name: "BarPillVertical"
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

    function init() {
      widget = createTemporaryObject(pillFactory, scene, {
        x: 200, y: 200, text: "42", suffix: "%", icon: "battery", tooltipText: "Charge"
      });
      verify(widget !== null);
      for (const spy of [shownSpy, hiddenSpy, enteredSpy, exitedSpy, clickSpy, rightSpy, middleSpy, wheelSpy]) {
        spy.target = widget;
        spy.clear();
      }
      wait(10);
    }

    function cleanup() {
      mouseMove(scene, 750, 550);
    }

    function descendants(item) {
      let children = [];
      for (const child of item.children)
        children = children.concat([child], descendants(child));
      return children;
    }

    function label() {
      return descendants(widget).filter(child => child.text === "42%")[0];
    }

    function test_geometry_data() {
      return [
        {tag: "default-up", density: "", downward: false, rotated: false},
        {tag: "compact-down", density: "compact", downward: true, rotated: false},
        {tag: "default-rotated-down", density: "", downward: true, rotated: true},
        {tag: "compact-rotated-up", density: "compact", downward: false, rotated: true}
      ];
    }

    function test_geometry(row) {
      widget.density = row.density;
      widget.oppositeDirection = row.downward;
      widget.rotateText = row.rotated;
      compare(widget.width, 40);
      compare(widget.height, 40);
      widget.forceOpen = true;
      wait(150);
      const text = label();
      const panel = text.parent;
      const icon = descendants(widget).filter(child => child.icon === "battery")[0];
      compare(text.text, "42%");
      compare(text.visible, true);
      compare(text.pointSize, row.density === "compact" ? 15 : 13);
      compare(text.rotation, row.rotated ? -90 : 0);
      compare(text.getVerticalCenterOffset(), row.downward ? 3 : -3);
      compare(icon.text, "B");
      compare(icon.pointSize, row.density === "compact" ? 26 : 19);
      compare(widget.width, 40);
      compare(widget.height, 40 + widget.maxPillHeight - 20);
      compare(panel.height, widget.maxPillHeight);
      compare(panel.width, widget.maxPillWidth);
      compare(panel.opacity, 1);
      compare(panel.y, row.downward ? 20 : widget.height - 20 - panel.height);
      compare(icon.parent.y, row.downward ? 0 : widget.height - 40);
      compare(text.anchors.verticalCenterOffset, row.downward ? 2 : -2);
      widget.customBackgroundColor = "#123456";
      widget.customTextIconColor = "#abcdef";
      compare(widget.bgColor, Qt.color("#123456"));
      compare(text.color, Qt.color("#abcdef"));
      widget.hovered = true;
      compare(widget.bgColor, Qt.color("#404040"));
      compare(text.color, Qt.color("#00ff00"));
      widget.hovered = false;
      widget.forceOpen = false;
      tryCompare(hiddenSpy, "count", 1, 500);
      compare(text.visible, false);
      compare(panel.opacity, 0);
      compare(widget.height, 40);
    }

    function test_hover_and_click_routing() {
      mouseMove(widget, 20, 20);
      compare(enteredSpy.count, 1);
      compare(widget.hovered, true);
      compare(TooltipService.lastText, "Charge");
      widget.tooltipText = "Updated";
      compare(TooltipService.lastText, "Updated");
      wait(30);
      compare(widget.showPill, false);
      tryCompare(shownSpy, "count", 1, 500);
      mouseClick(widget, 20, 20, Qt.LeftButton);
      mouseClick(widget, 20, 20, Qt.RightButton);
      mouseClick(widget, 20, 20, Qt.MiddleButton);
      compare(clickSpy.count, 1);
      compare(rightSpy.count, 1);
      compare(middleSpy.count, 1);
      mouseWheel(widget, 20, 20, 0, 120);
      compare(wheelSpy.count, 1);
      compare(wheelSpy.signalArguments[0][0], 120);
      mouseMove(scene, 750, 550);
      compare(exitedSpy.count, 1);
      compare(widget.hovered, false);
      compare(TooltipService.lastText, "");
      tryCompare(hiddenSpy, "count", 1, 500);
      compare(label().parent.opacity, 0);
      compare(widget.height, 40);
    }

    function test_delayed_auto_hide_and_cancel() {
      widget.autoHide = true;
      widget.show();
      tryCompare(shownSpy, "count", 1, 500);
      wait(150);
      compare(hiddenSpy.count, 0);
      compare(label().parent.opacity, 1);
      tryCompare(hiddenSpy, "count", 1, 3200);
      compare(widget.showPill, false);
      compare(label().parent.opacity, 0);
      widget.showDelayed();
      wait(30);
      compare(widget.showPill, false);
      widget.hide();
      wait(200);
      compare(shownSpy.count, 1);
    }

    function test_force_closed_and_locked_open() {
      widget.forceClose = true;
      widget.show();
      widget.showDelayed();
      mouseMove(widget, 20, 20);
      wait(200);
      compare(widget.showPill, false);
      compare(widget.height, 40);
      compare(label().visible, false);
      mouseMove(scene, 750, 550);
      widget.forceClose = false;
      widget.forceOpen = true;
      widget.hide();
      wait(150);
      compare(label().visible, true);
      verify(widget.height > 40);
      widget.forceOpen = false;
      tryCompare(hiddenSpy, "count", 1, 500);
      compare(widget.height, 40);
    }
  }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-pill-vertical-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint":
            run_lint(directory)
        else:
            helper = load_helper("bar-pill-warnings")
            helper.HARNESS = HARNESS
            helper.run_behavior(directory)


if __name__ == "__main__":
    main()
