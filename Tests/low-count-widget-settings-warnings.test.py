#!/usr/bin/env python3
"""Five settings editors: real controls, synthetic state, masked host config."""

import argparse
from collections import Counter
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
NAMES = ("Brightness", "KeyboardLayout", "Microphone", "Spacer", "Volume")
TARGETS = [
    Path("Modules/Panels/Settings/Bar/WidgetSettings") / f"{name}Settings.qml"
    for name in NAMES
]


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


isolation = load_helper("grouped-osd-settings-warnings.test.py")

HARNESS = """
import QtQuick
import QtQuick.Controls
import QtTest
import qs.Modules.Panels.Settings.Bar.WidgetSettings

TestCase {
  id: suite
  name: "LowCountWidgetSettings"
  width: 800
  height: 600
  visible: true
  when: windowShown

  function descendants(item) {
    let items = [item];
    for (const child of item.children || [])
      items = items.concat(descendants(child));
    return items;
  }

  function editor(name, data, metadata) {
    const component = Qt.createComponent("qs/Modules/Panels/Settings/Bar/WidgetSettings/" + name + "Settings.qml");
    compare(component.status, Component.Ready, component.errorString());
    const result = createTemporaryObject(component, suite, {
      width: 700,
      widgetData: data,
      widgetMetadata: metadata
    });
    verify(result !== null);
    wait(30);
    return result;
  }

  function choose(option, index) {
    const combo = descendants(option).find(item => item.popup !== undefined && item.currentIndex !== undefined);
    verify(combo !== undefined);
    combo.forceActiveFocus();
    keyClick(Qt.Key_Home);
    for (let step = 0; step < index; step++)
      keyClick(Qt.Key_Down);
    compare(combo.contentItem.text, option.model[index].name);
  }

  function test_displayModes_data() {
    return [
      {
        tag: "Brightness",
        name: "Brightness",
        middle: "alwaysShow"
      },
      {
        tag: "KeyboardLayout",
        name: "KeyboardLayout",
        middle: "forceOpen"
      },
      {
        tag: "Microphone",
        name: "Microphone",
        middle: "alwaysShow"
      },
      {
        tag: "Volume",
        name: "Volume",
        middle: "alwaysShow"
      }
    ];
  }

  function test_displayModes(row) {
    const source = {
      id: row.name,
      retained: 37
    };
    const original = JSON.stringify(source);
    const view = editor(row.name, source, {
      displayMode: "onhover"
    });
    const option = descendants(view).find(item => item.currentKey !== undefined && item.model !== undefined);
    verify(option !== undefined);
    compare(option.currentKey, "onhover");
    compare(JSON.stringify(option.model.map(item => item.key)), JSON.stringify(["onhover", row.middle, "alwaysHide"]));
    verify(option.width > 0 && option.height > 0);
    verify(option.width <= view.width);
    for (let index = 0; index < option.model.length; index++) {
      choose(option, index);
      compare(view.valueDisplayMode, option.model[index].key);
      compare(option.currentKey, option.model[index].key);
      const saved = view.saveSettings();
      compare(saved.displayMode, option.model[index].key);
      compare(saved.retained, 37);
      verify(saved !== source);
      compare(JSON.stringify(source), original);
    }
    view.visible = false;
    const other = editor(row.name, {
      displayMode: row.middle
    }, {
      displayMode: "onhover"
    });
    compare(other.saveSettings().displayMode, row.middle);
    compare(view.saveSettings().displayMode, "alwaysHide");
    const reopened = editor(row.name, view.saveSettings(), {
      displayMode: "onhover"
    });
    compare(reopened.valueDisplayMode, "alwaysHide");
  }

  function typeWidth(input, text) {
    input.inputItem.forceActiveFocus();
    keyClick(Qt.Key_A, Qt.ControlModifier);
    for (const character of text)
      keyClick(character);
    compare(input.text, text);
  }

  function test_spacerCopySaveAndLayout() {
    const source = {
      id: "Spacer",
      retained: 19,
      width: 42
    };
    const original = JSON.stringify(source);
    const view = editor("Spacer", source, {
      width: 24
    });
    const input = descendants(view).find(item => item.inputItem !== undefined);
    verify(input !== undefined);
    compare(input.text, "42");
    verify(input.width > 0 && input.height > 0);
    compare(input.width, view.width);
    typeWidth(input, "73");
    const saved = view.saveSettings();
    compare(saved.width, 73);
    compare(saved.retained, 19);
    verify(saved !== source);
    compare(JSON.stringify(source), original);
    typeWidth(input, "0");
    compare(view.saveSettings().width, 24);
    typeWidth(input, "invalid");
    compare(view.saveSettings().width, 24);
    view.visible = false;
    const defaults = editor("Spacer", {}, {
      width: 31
    });
    const defaultInput = descendants(defaults).find(item => item.inputItem !== undefined);
    compare(defaultInput.text, "31");
    const reopened = editor("Spacer", saved, {
      width: 24
    });
    compare(reopened.saveSettings().width, 73);
    compare(JSON.stringify(source), original);
  }
}
"""


def stage_behavior(directory, shadow):
    helper = load_helper("clock-settings-warnings.test.py")
    helper.stage_runtime(directory)
    (directory / "tst_clock.qml").unlink()
    helper.write_module(
        directory,
        "qs.Modules.Panels.Settings.Bar.WidgetSettings",
        {target.stem: (ROOT / target).read_text() for target in TARGETS},
    )
    if shadow:
        # Colliding real-control properties expose accidental dynamic ownership.
        declarations = {
            "NComboBox": 'property string valueDisplayMode: "shadow"\n',
            "NTextInput": "property var widgetData: ({width: 999})\nproperty var widgetMetadata: ({width: 998})\n",
        }
        for name, declaration in declarations.items():
            path = directory / "qs/Widgets" / f"{name}.qml"
            path.write_text(
                path.read_text().replace("id: root", "id: root\n" + declaration, 1)
            )
    harness = directory / "tst_low_count_settings.qml"
    harness.write_text(HARNESS)
    return harness


def run_sandboxed(mode, directory):
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for path in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == path and " - tmpfs " in line for line in mounts
        ), path
    environment = isolation.isolated_environment(directory)
    if mode == "lint":
        load_helper("media-mini-warnings.test.py").stage_modules(directory)
        failures = []
        for target in TARGETS:
            code, output = isolation.run_child(
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "-I",
                    str(directory),
                    str(directory / "qs" / target),
                ],
                directory,
                environment,
            )
            warnings = [
                line for line in output.splitlines() if line.startswith("Warning:")
            ]
            counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
            print(
                target.name,
                dict(counts),
                "TOTAL",
                len(warnings),
                "EXIT",
                code,
                flush=True,
            )
            (directory / f"{target.stem}.lint.log").write_text(output)
            if warnings or code:
                failures.append(target.name)
        assert not failures, failures
        return
    harness = stage_behavior(directory, mode == "behavior-shadow")
    code, output = isolation.run_child(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ],
        directory,
        environment,
    )
    (directory / f"{mode}.log").write_text(output)
    assert code == 0, code
    assert "7 passed, 0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior", "behavior-shadow"))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.addaudithook(isolation.audit)
    with (
        patch("os.stat", isolation.guard_metadata(os.stat)),
        patch("os.lstat", isolation.guard_metadata(os.lstat)),
        patch("os.readlink", isolation.guard_metadata(os.readlink)),
    ):
        isolation.prove_denial()
        if args.sandbox:
            run_sandboxed(args.mode, args.sandbox)
            return
        with tempfile.TemporaryDirectory(
            prefix="noctalia-low-count-settings-"
        ) as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            command = [
                "bwrap",
                "--die-with-parent",
                "--unshare-all",
                "--new-session",
                "--ro-bind",
                "/",
                "/",
                "--perms",
                "000",
                "--tmpfs",
                "/home",
                "--tmpfs",
                "/syncthing",
                "--ro-bind",
                str(ROOT),
                str(ROOT),
                "--tmpfs",
                "/tmp",
                "--tmpfs",
                "/run",
                "--bind",
                temporary,
                temporary,
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                temporary,
                "--",
                "/usr/bin/python3",
                str(Path(__file__).absolute()),
                args.mode,
                "--sandbox",
                temporary,
            ]
            code, _ = isolation.run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


if __name__ == "__main__":
    main()
