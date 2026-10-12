#!/usr/bin/env python3
"""AllScreens-only lint and private offscreen routing with synthetic screens.

Runtime keeps installed Variants and production Loader bindings. Only screen
objects, service state and window leaves are fixtures; no surfaces are created.
Installed ShellScreen metadata is tested by source lint, not the fake screens.
"""

import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).absolute().parents[1]
TARGET = Path("Modules/MainScreen/AllScreens.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = helper("grid-list-warnings.test.py")
fixtures = helper("about-tab-warnings.test.py")


def stage_runtime(directory, mutation):
    write, singleton = fixtures.write_module, fixtures.singleton
    write(
        directory,
        "qs.TestScreens",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Quickshell": singleton("property var screens: []"),
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                "property QtObject data: QtObject { property QtObject bar: QtObject { property var monitors: [] }; property QtObject general: QtObject { property bool allowPanelsOnScreenWithoutBar: false } }"
            ),
            "Logger": singleton("function d(...args) {}"),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "BarService": singleton("property bool isVisible: true"),
            "Routes": singleton(
                'property var live: ({})\nproperty var events: []\nfunction add(kind, screen) { const key = kind + ":" + screen.name; if (live[key]) throw new Error("duplicate " + key); live[key] = screen; events = events.concat(["+" + key]); }\nfunction remove(kind, screen) { const key = kind + ":" + screen.name; if (live[key] !== screen) throw new Error("wrong removal " + key); delete live[key]; events = events.concat(["-" + key]); }'
            ),
        },
    )
    source = (ROOT / TARGET).read_text()
    # Installed Variants stays real; synthetic screen types cannot create windows.
    source = source.replace(
        "import Quickshell\n", "import Quickshell as Native\nimport qs.TestScreens\n"
    )
    source = source.replace("Variants {", "Native.Variants {", 1)
    if mutation:
        source = source.replace("screen: modelData", "screen: Quickshell.screens[0]")
        source = source.replace(
            "screen: screenDelegate.modelData", "screen: Quickshell.screens[0]"
        )
    leaves = {}
    for name in (
        "MainScreen",
        "BarContentWindow",
        "BarExclusionZone",
        "PopupMenuWindow",
    ):
        leaves[name] = f'''import QtQuick
import qs.TestScreens
import qs.Services.UI
Item {{
  property ShellScreen screen
  Component.onCompleted: Routes.add("{name}", screen)
  Component.onDestruction: Routes.remove("{name}", screen)
}}
'''
    write(directory, "qs.Modules.MainScreen", {"AllScreens": source, **leaves})
    shutil.copyfile(
        ROOT / "Tests/Qml/AllScreensWarningsHarness.qml", directory / "qs/shell.qml"
    )


def execute(args, directory, environment):
    if args.mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ]
    else:
        stage_runtime(directory, args.mutation)
        command = ["quickshell", "--no-color", "-p", str(directory / "qs/shell.qml")]
    code, output = isolation.run_audited(
        directory, environment, command, "all-screens-" + args.mode
    )
    if args.mode == "lint":
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print("ALL_SCREENS_LINT_COUNTS", dict(counts), "EXIT", code)
        assert counts == {}, counts
        assert code == 0, code
    else:
        assert code == 0, f"runtime exit {code}"
        assert "ALL_SCREENS_RUNTIME_PASS 9 routing/lifecycle cases" in output, output
        assert not re.search(
            r" WARN | ERROR | FATAL |ReferenceError|TypeError|Binding loop", output
        ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--mutation", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-all-screens-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        execute(args, directory, isolation.isolated_environment(directory))


if __name__ == "__main__":
    main()
