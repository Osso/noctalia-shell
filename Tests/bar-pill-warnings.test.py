#!/usr/bin/env python3
"""Targeted BarPill lint and real pill/text/icon offscreen behavior.

Settings/style/tooltip services and ShellScreen are inert boundaries. Production
BarPillHorizontal and BarPillVertical are copied unchanged, never edited.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WIDGET = Path("Modules/Bar/Extras/BarPill.qml")


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory):
    helper = load_helper("workspace-runtime")
    write = helper.write_module
    singleton = helper.singleton
    write(
        directory,
        "Quickshell",
        {"ShellScreen": "import QtQuick\nQtObject { property string name }"},
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["bar"]["position"] = "top"
    style = dict(
        capsuleHeight=40,
        marginXS=3,
        marginXXS=2,
        marginM=8,
        radiusM=8,
        radiusL=12,
        fontWeightMedium=500,
        fontWeightBold=700,
        fontSizeM=12,
        fontSizeL=14,
        uiScaleRatio=1,
        animationNormal=80,
        animationFast=40,
        pillDelay=100,
        tooltipDelay=100,
        tooltipDelayLong=200,
        opacityFull=1,
        opacityNone=0,
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(
                    f"property real {key}: {value}" for key, value in style.items()
                )
                + '\nproperty color capsuleColor: "#202020"'
            ),
            "NColor": singleton(
                'property color transparent: "transparent"\nproperty color mHover: "#404040"\nproperty color mOnHover: "#00ff00"\nproperty color mOnSurface: "#ffffff"'
            ),
            "Icons": singleton(
                'property string defaultIcon: "disc"\nproperty string fontFamily: "sans-serif"\nfunction get(name) { return name === "battery" ? "B" : "V"; }'
            ),
            "Logger": singleton(
                "function w(...args) { console.warn(...args); }\nfunction callStack() { console.trace(); }"
            ),
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            name: (ROOT / f"Widgets/{name}.qml").read_text()
            for name in ("NText", "NIcon")
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton(
                'property string lastText: ""\nfunction show(item, text, direction, delay) { lastText = text; }\nfunction updateText(text) { lastText = text; }\nfunction hide() { lastText = ""; }'
            ),
            "BarService": singleton(
                'function getTooltipDirection() { return "bottom"; }'
            ),
        },
    )
    write(
        directory,
        "qs.Modules.Bar.Extras",
        {
            name: (ROOT / f"Modules/Bar/Extras/{name}.qml").read_text()
            for name in ("BarPill", "BarPillHorizontal", "BarPillVertical")
        },
    )
    (directory / "tst_bar_pill.qml").write_text(HARNESS)


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=load_helper("media-mini-warnings").isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"BarPill behavior exit {result.returncode}"
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"


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
    print("BAR_PILL_LINT_COUNTS", dict(counts))
    assert counts == {"missing-property": 8}, (
        f"owner qualification warnings remain: {dict(counts)}"
    )
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
    BarPill {
      screen: fixtureScreen
    }
  }
  TestCase {
    id: tests
    name: "BarPill"
    when: windowShown
    property var widget
    SignalSpy {
      id: shownSpy
      signalName: "shown"
    }
    SignalSpy {
      id: hiddenSpy
      signalName: "hidden"
    }
    SignalSpy {
      id: enteredSpy
      signalName: "entered"
    }
    SignalSpy {
      id: exitedSpy
      signalName: "exited"
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
    SignalSpy {
      id: wheelSpy
      signalName: "wheel"
    }

    function init() {
      Settings.data.bar.position = "top";
      Settings.dataChanged();
      widget = createTemporaryObject(pillFactory, scene, {
        x: 200,
        y: 200,
        text: "42",
        suffix: "%",
        icon: "battery",
        tooltipText: "Charge"
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

    function implementation() {
      return widget.children[0].item;
    }

    function descendants(item) {
      let children = [];
      for (const child of item.children)
        children = children.concat([child], descendants(child));
      return children;
    }

    function label() {
      return descendants(implementation()).filter(child => child.text === "42%")[0];
    }

    function test_labels_geometry_data() {
      return [
        {
          tag: "horizontal-mini",
          position: "top",
          density: "mini",
          vertical: false
        },
        {
          tag: "horizontal-compact",
          position: "bottom",
          density: "compact",
          vertical: false
        },
        {
          tag: "vertical-mini",
          position: "left",
          density: "mini",
          vertical: true
        },
        {
          tag: "vertical-compact",
          position: "right",
          density: "compact",
          vertical: true
        }
      ];
    }

    function test_labels_geometry(row) {
      Settings.data.bar.position = row.position;
      Settings.dataChanged();
      widget.density = row.density;
      widget.forceOpen = true;
      wait(150);
      const pill = implementation();
      compare(widget.isVerticalBar, row.vertical);
      compare(widget.width, pill.width);
      compare(widget.height, pill.height);
      compare(row.vertical ? widget.width : widget.height, 40);
      verify((row.vertical ? widget.height : widget.width) > 40);
      compare(label().visible, true);
      compare(label().text, "42%");
      compare(label().pointSize, row.density === "compact" ? (row.vertical ? 15 : 18) : 13);
      const icon = descendants(pill).filter(child => child.icon === "battery")[0];
      verify(icon.visible);
      compare(icon.text, "B");
      compare(icon.pointSize, row.density === "compact" ? 26 : 19);
      const panel = label().parent;
      compare(panel.opacity, 1);
      widget.customBackgroundColor = "#123456";
      widget.customTextIconColor = "#abcdef";
      wait(100);
      compare(pill.bgColor, Qt.color("#123456"));
      compare(label().color, Qt.color("#abcdef"));
      widget.hovered = true;
      wait(100);
      compare(pill.bgColor, Qt.color("#404040"));
      compare(label().color, Qt.color("#00ff00"));
      widget.hovered = false;
      widget.forceOpen = false;
      wait(200);
      compare(label().visible, false);
      compare(panel.opacity, 0);
      compare(widget.width, 40);
      compare(widget.height, 40);
    }

    function test_hover_delay_and_events_data() {
      return [
        {
          tag: "horizontal",
          position: "top"
        },
        {
          tag: "vertical",
          position: "left"
        }
      ];
    }

    function test_hover_delay_and_events(row) {
      Settings.data.bar.position = row.position;
      Settings.dataChanged();
      wait(20);
      mouseMove(widget, 20, 20);
      compare(enteredSpy.count, 1);
      compare(TooltipService.lastText, "Charge");
      wait(30);
      compare(implementation().showPill, false);
      tryCompare(shownSpy, "count", 1, 500);
      compare(label().parent.opacity, 1);
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
      compare(TooltipService.lastText, "");
      tryCompare(hiddenSpy, "count", 1, 500);
      compare(label().parent.opacity, 0);
      compare(widget.width, 40);
      compare(widget.height, 40);
    }

    function test_auto_hide_data() {
      return [
        {
          tag: "horizontal",
          position: "top"
        },
        {
          tag: "vertical",
          position: "right"
        }
      ];
    }

    function test_auto_hide(row) {
      Settings.data.bar.position = row.position;
      Settings.dataChanged();
      widget.autoHide = true;
      widget.show();
      tryCompare(shownSpy, "count", 1, 500);
      wait(150);
      compare(hiddenSpy.count, 0);
      compare(label().parent.opacity, 1);
      tryCompare(hiddenSpy, "count", 1, 3200);
      compare(label().parent.opacity, 0);
      compare(implementation().showPill, false);
      widget.showDelayed();
      wait(30);
      compare(implementation().showPill, false);
      widget.hide();
      wait(200);
      compare(shownSpy.count, 1);
    }

    function test_loader_replacement_and_force_close() {
      widget.forceOpen = true;
      for (const position of ["top", "left", "bottom", "right", "top"]) {
        Settings.data.bar.position = position;
        Settings.dataChanged();
        wait(100);
        compare(implementation().screen, fixtureScreen);
        compare(label().text, "42%");
        compare(label().parent.opacity, 1);
        compare(widget.width, implementation().width);
        compare(widget.height, implementation().height);
      }
      widget.forceClose = true;
      widget.forceOpen = false;
      widget.show();
      widget.showDelayed();
      wait(200);
      compare(widget.width, 40);
      compare(widget.height, 40);
      compare(label().visible, false);
      widget.forceClose = false;
      widget.oppositeDirection = true;
      widget.show();
      tryCompare(implementation(), "showPill", true, 500);
      wait(150);
      verify(label().parent.x > 0);
      widget.hide();
      wait(150);
      Settings.data.bar.position = "left";
      Settings.dataChanged();
      widget.rotateText = true;
      widget.forceOpen = true;
      wait(150);
      compare(label().rotation, -90);
      verify(widget.height > 40);
    }
  }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-bar-pill-") as temporary:
        (run_lint if args.mode == "lint" else run_behavior)(Path(temporary))


if __name__ == "__main__":
    main()
